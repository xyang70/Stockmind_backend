import logging
import httpx
import os
import asyncio
from typing import Any, Dict, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from openai import api_key
from app.request_models.analysis_request import AnalysisRequest
from app.services.analysis_service import AnalysisService
from pydantic import BaseModel, Field, validator
import uvicorn
from app.llm_models.llm_model_factory import LLMModelFactory
from app.data_providers.data_provider_factory import DataProviderFactory
from contextlib import asynccontextmanager
from app.services.impl.analysis_service_impl import AnalysisServiceImpl
from app.services.impl.impl_data_processing import DataProcessingImpl
from arq import create_pool
from arq.connections import RedisSettings
from app.settings import ServerConfig
from app.config_builder import LLMConfigBuilder
from app.config_builder import LLMConfigBuilder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Request/Response Models
class AnalysisResult(BaseModel):
    """Schema for analysis results"""
    id: Optional[str] = Field(None, description="Unique result ID")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Timestamp of analysis")
    data: Dict[str, Any] = Field(..., description="Analysis result data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('data')
    def data_not_empty(cls, v):
        if not v:
            raise ValueError("Data cannot be empty")
        return v


class HealthResponse(BaseModel):
    """Schema for health check response"""
    status: str = Field(..., description="Service status")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    version: str
    environment: str


class APIResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AnalysisAPIServer:
    """Production-grade FastAPI server for LLM Analysis"""
    
    def __init__(self, config: ServerConfig):
        self.config = config

        self.app = FastAPI(
            title=self.config.title,
            version=self.config.version,
            description="API for LLM-based analysis with EMA calculations",
            debug=self.config.debug,
            lifespan=self._lifespan
        )
        self._setup_middleware()
        self._setup_routes()
            
        logger.info(
            f"Server initialized: {self.config.title} v{self.config.version} "
            f"(environment: {self.config.environment})"
        )
    
    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        # Startup tasks
        logger.info("Server is starting up...")
        app.state.config = self.config
        app.state.http = httpx.AsyncClient(timeout=15.0)
        
        # Build and store LLM configuration
        logger.info(f"Initializing LLM model: {self.config.llm_model_name}")
        llm_model_config = LLMConfigBuilder.build(self.config)
        app.state.llm_factory = LLMModelFactory(config=llm_model_config)
        
        # Initialize Redis
        app.state.redis = await create_pool(RedisSettings.from_dsn(self.config.redis_url))
        
        # Initialize data provider
        app.state.data_provider_factory = DataProviderFactory()
        app.state.data_provider = app.state.data_provider_factory.create_data_provider(self.config.data_provider)
        
        # Initialize data processor
        app.state.data_processor = DataProcessingImpl()
        
        yield  # Run the server
        
        # Shutdown tasks
        logger.info("Server is shutting down...")
        http_client = getattr(app.state, "http", None)
        if http_client:
            await http_client.aclose()
        
        # Perform any cleanup tasks here (e.g., close database connections)
        llm_model = getattr(app.state, "llm_model", None)
        if llm_model and hasattr(llm_model, "close"):
            await llm_model.close()

    def _setup_middleware(self) -> None:
        """Configure middleware"""
        # CORS configuration
        # allowed_origins is always a list (parsed from comma-separated string in config)
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.debug("Middleware configured")
    
    def _setup_routes(self) -> None:
        """Setup API routes with proper error handling"""
        
        @self.app.get("/", response_model=APIResponse, tags=["Info"])
        async def read_root():
            """Root endpoint - API information"""
            return APIResponse(
                success=True,
                message=f"{self.config.title} API is running",
                data={"version": self.config.version}
            )
        
        @self.app.get("/health", response_model=HealthResponse, tags=["Health"])
        async def health_check():
            """Health check endpoint"""
            logger.debug("Health check requested")
            return HealthResponse(
                status="healthy",
                version=self.config.version,
                environment=self.config.environment
            )

        @self.app.get("/available-models", response_model=APIResponse, tags=["Info"])
        async def get_available_models():
            """Get available LLM models"""
            logger.debug("Available models requested")
            return APIResponse(
                success=True,
                message="Available LLM models retrieved successfully",
                data={"models": [model.name for model in self.app.state.llm_factory.get_available_models()]}
            )

        @self.app.get(
            "/us/stocks/analysis/{job_id}",
            response_model=APIResponse,
            tags=["Results"]
        )
        async def get_analysis_status(job_id: str):
            try:
                redis = self.app.state.redis

                status_value = await redis.get(f"analysis:status:{job_id}")
                result_value = await redis.get(f"analysis:result:{job_id}")
                error_value = await redis.get(f"analysis:error:{job_id}")

                if status_value is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Job not found"
                    )

                data = {
                    "job_id": job_id,
                    "status": status_value.decode() if isinstance(status_value, bytes) else status_value,
                }

                if result_value:
                    data["result"] = result_value.decode() if isinstance(result_value, bytes) else result_value

                if error_value:
                    data["error"] = error_value.decode() if isinstance(error_value, bytes) else error_value

                return APIResponse(
                    success=True,
                    message="Job status retrieved successfully",
                    data=data,
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error("Unexpected error getting job status: %s", str(e), exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error while retrieving job status",
                )
            

        @self.app.post(
            "/us/stocks/analysis",
            response_model=APIResponse,
            status_code=status.HTTP_201_CREATED,
            tags=["Results"]
        )
        async def analyze_symbol(request: AnalysisRequest):
            try:
                    logger.info("Analysis requested for symbol: %s", request.symbol)

                    try:
                        self.app.state.llm_factory.get_llm_model(
                            request.llm_agent_request.agent_name,
                            request.llm_agent_request.model,
                        )
                    except ImportError as e:
                        raise HTTPException(
                            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=f"LLM dependency missing: {e}",
                        )
                    except ValueError as e:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=str(e),
                        )

                    redis = self.app.state.redis

                    payload = {
                        "symbol": request.symbol,
                        "agent_name": request.llm_agent_request.agent_name,
                        "model": request.llm_agent_request.model,
                    }

                    job = await redis.enqueue_job(
                        "analyze_data_job", 
                        payload,
                        _queue_name=self.config.worker_queue_name
                    )

                    # 初始化状态
                    await redis.set(
                        f"analysis:status:{job.job_id}",
                        "queued",
                        ex=3600,
                    )

                    return APIResponse(
                        success=True,
                        message="Analysis job queued successfully",
                        data={
                            "job_id": job.job_id,
                            "status": "queued",
                        },
                    )

            except HTTPException:
                raise
            except Exception as e:
                logger.error("Unexpected error queueing analysis: %s", str(e), exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error while queueing analysis",
                )


        @self.app.get("/status", response_model=APIResponse, tags=["Status"])
        async def server_status():
            """Detailed server status"""
            return APIResponse(
                success=True,
                message="Server is operational",
                data={
                    "version": self.config.version,
                    "environment": self.config.environment,
                    "debug": self.config.debug
                }
            )
    
    def run(self, host: Optional[str] = None, port: Optional[int] = None) -> None:
        """
        Run the server
        
        Args:
            host: Server host (defaults to config.host)
            port: Server port (defaults to config.port)
        """
        host = host or self.config.host
        port = port or self.config.port
        
        logger.info(
            f"Starting {self.config.title} server on {host}:{port} "
            f"(environment: {self.config.environment})"
        )
        
        try:
            uvicorn.run(
                self.app,
                host=host,
                port=port,
                log_level="debug" if self.config.debug else "warning"
            )
        except Exception as e:
            logger.error(f"Failed to start server: {str(e)}", exc_info=True)
            raise
