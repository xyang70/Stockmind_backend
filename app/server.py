import logging
import httpx
import os
import asyncio
from typing import Any, Dict, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from app.request_models.analysis_request import AnalysisRequest
from app.services.analysis_service import AnalysisService
from pydantic import BaseModel, Field, validator
import uvicorn
from app.llm_models.llm_model_factory import LLMModelFactory
from app.data_providers.data_provider_factory import DataProviderFactory
from contextlib import asynccontextmanager
from app.services.impl.analysis_service_impl import AnalysisServiceImpl
from app.services.impl.impl_data_processing import DataProcessingImpl
import yaml


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Configuration
class ServerConfig:
    """Server configuration from environment variables"""
    
    def __init__(self):
        logger.info("Loading server configuration from environment variables")
        self.llm_api_key = os.getenv("GEMINI_API_KEY")
        self.llm_model_name = os.getenv("LLM_MODEL_NAME", "gemini-2.5-flash")
        self.llm_agent = os.getenv("AGENT", "gemini")
        self.host = os.getenv("SERVER_HOST", "127.0.0.1")
        self.port = int(os.getenv("SERVER_PORT", "8000"))
        self.title = os.getenv("API_TITLE", "LLM Analysis API")
        self.version = os.getenv("API_VERSION", "0.1.0")
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = self.environment == "development"
        self.allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
        self.data_provider = os.getenv("DATA_PROVIDER", "yfinance")
        self.yaml_config_path = os.getenv("YAML_CONFIG_PATH", "app/config/open_router.yml")
        self.open_router_api_key = os.getenv("OPEN_ROUTER_API_KEY")
        self.analysis_timeout_seconds = float(os.getenv("ANALYSIS_TIMEOUT_SECONDS", "20"))

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

        with open(self.config.yaml_config_path, "r") as f:
            self.llm_model_config = yaml.safe_load(f)

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
    def _get_llm_model_config(self):
        """Construct LLM model configuration based on environment variables"""
        open_router_cfg = self.llm_model_config.get("agents", {})
        open_router_agent_cfg = open_router_cfg.get("acree-ai", {}).get("trinity-large-preview-free", {})
        return {
            "gemini":{
                "model_name": self.config.llm_model_name,
                "temperature": 0.7,
                "api_key": self.config.llm_api_key,
                "request_url": None
            },
            "open_router":{
                "model_name": open_router_agent_cfg.get("model-name", "arcee-ai/trinity-large-preview:free"),
                "temperature": 0.7,
                "api_key": self.config.open_router_api_key,
                "request_url": open_router_cfg.get("request_url")
            }

        }
    @asynccontextmanager
    async def _lifespan(self,app: FastAPI):
        # Startup tasks
        app.state.config = self.config
        logger.info("Server is starting up...")
        app.state.config = self.config  # Store config in app state for access in routes
        app.state.open_router_config = self.llm_model_config
        app.state.http = httpx.AsyncClient(timeout=15.0)
        # default:create LLM model and data provider instances and store in app state for dependency injection
        logger.info(f"Initializing LLM model: {self.config.llm_model_name}")
        app.state.llm_factory = LLMModelFactory(config=self._get_llm_model_config())
        app.state.data_provider_factory = DataProviderFactory()
        # app.state.llm_model = app.state.llm_factory.get_llm_model(self.config.llm_agent)  # Initialize LLM model and store in app state
        app.state.data_provider = app.state.data_provider_factory.create_data_provider(self.config.data_provider)  # Initialize data provider and store in app state
        app.state.data_processor = DataProcessingImpl()  # Initialize data processor and store in app state
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
        
        @self.app.post(
            "/us/stocks/analysis",
            response_model=APIResponse,
            status_code=status.HTTP_201_CREATED,
            tags=["Results"]
        )
        async def analyze_symbol(request: AnalysisRequest):
            """Save analysis results with validation"""
            try:
                logger.info(f"Analysis requested for symbol: {request.symbol}")
                try:
                    logger.info(f"Retrieving LLM model for agent: {request.llm_agent_request.agent_name}")
                    llm_client = self.app.state.llm_factory.get_llm_model(
                        request.llm_agent_request.agent_name,request.llm_agent_request.model
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
                analyze_service: AnalysisService = AnalysisServiceImpl(
                    data_processor=self.app.state.data_processor,
                    llm_agent=llm_client,
                    data_provider=self.app.state.data_provider,
                )  # Create an instance of AnalysisService with dependencies
                print("analyze_service created")
                response = await asyncio.wait_for(
                    run_in_threadpool(analyze_service.analyze_data, request.symbol),
                    timeout=self.config.analysis_timeout_seconds,
                )
                # Validate result
                if not request.symbol:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Result data cannot be empty"
                    )
                
                # TODO: Persist to database or storage
                # logger.info(f"Result saved successfully: {request.id}")
                
                return APIResponse(
                    success=True,
                    message="Analysis result saved successfully",
                    data={"response": response}
                )
            
            except ValueError as e:
                logger.warning(f"Validation error: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=str(e)
                )
            except HTTPException:
                raise
            except asyncio.TimeoutError:
                logger.error(
                    "Analysis request timed out after %.1fs",
                    self.config.analysis_timeout_seconds,
                )
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="Analysis timed out",
                )
            except Exception as e:
                logger.error(f"Unexpected error saving results: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error while saving results"
                )
        
        # @self.app.post("/analyze", response_model=APIResponse, tags=["Analysis"])
        # async def analyze(data: Dict[str, Any]):
        #     """Endpoint to perform analysis (placeholder)"""
        #     try:
        #         logger.info("Analysis requested")

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


# if __name__ == "__main__":
#     load_dotenv()  # Load environment variables from .env file
#     # Load configuration
#     config = ServerConfig()
    
#     # Create and run server

#     server = AnalysisAPIServer(config=config)
#     server.run()
