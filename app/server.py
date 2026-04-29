import logging
from contextlib import asynccontextmanager
from typing import Optional

import httpx
import uvicorn
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.analysis import router as analysis_router
from app.api.routes.health import router as health_router
from app.api.routes.info import router as info_router
from app.api.routes.status import router as status_router
from app.config_builder import LLMConfigBuilder
from app.data_providers.data_provider_factory import DataProviderFactory
from app.llm_models.llm_model_factory import LLMModelFactory
from app.services.impl.impl_data_processing import DataProcessingImpl
from app.settings import ServerConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class AnalysisAPIServer:
    """Production-grade FastAPI server for LLM Analysis."""

    def __init__(self, config: ServerConfig):
        self.config = config

        self.app = FastAPI(
            title=self.config.title,
            version=self.config.version,
            description="API for LLM-based analysis with EMA calculations",
            debug=self.config.debug,
            lifespan=self._lifespan,
        )
        self._setup_middleware()
        self._setup_routes()

        logger.info(
            "Server initialized: %s v%s (environment: %s)",
            self.config.title,
            self.config.version,
            self.config.environment,
        )

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        logger.info("Server is starting up...")
        app.state.config = self.config
        app.state.http = httpx.AsyncClient(timeout=15.0)

        logger.info("Initializing LLM model: %s", self.config.llm_model_name)
        llm_model_config = LLMConfigBuilder.build(self.config)
        app.state.llm_factory = LLMModelFactory(config=llm_model_config)

        app.state.redis = await create_pool(
            RedisSettings.from_dsn(self.config.redis_url)
        )

        app.state.data_provider_factory = DataProviderFactory()
        app.state.data_provider = app.state.data_provider_factory.create_data_provider(
            self.config.data_provider
        )

        app.state.data_processor = DataProcessingImpl()

        yield

        logger.info("Server is shutting down...")
        http_client = getattr(app.state, "http", None)
        if http_client:
            await http_client.aclose()

        llm_model = getattr(app.state, "llm_model", None)
        if llm_model and hasattr(llm_model, "close"):
            await llm_model.close()

    def _setup_middleware(self) -> None:
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.debug("Middleware configured")

    def _setup_routes(self) -> None:
        self.app.include_router(info_router)
        self.app.include_router(health_router)
        self.app.include_router(status_router)
        self.app.include_router(analysis_router)

    def run(self, host: Optional[str] = None, port: Optional[int] = None) -> None:
        host = host or self.config.host
        port = port or self.config.port

        logger.info(
            "Starting %s server on %s:%s (environment: %s)",
            self.config.title,
            host,
            port,
            self.config.environment,
        )

        try:
            uvicorn.run(
                self.app,
                host=host,
                port=port,
                log_level="debug" if self.config.debug else "warning",
            )
        except Exception as exc:
            logger.error("Failed to start server: %s", str(exc), exc_info=True)
            raise
