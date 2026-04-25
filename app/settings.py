# app/settings.py
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict, model_validator
from typing import Literal


class BaseAppConfig(BaseSettings):
    """Base configuration shared across server and worker"""
    
    # ============ Environment & Execution ============
    environment: Literal["development", "staging", "production"] = Field(
        default="development", 
        validation_alias="ENVIRONMENT",
        description="Application environment"
    )
    
    # ============ LLM Configuration ============
    llm_api_key: str = Field(..., validation_alias="GEMINI_API_KEY", description="Gemini API key")
    llm_model_name: str = Field(
        default="gemini-2.5-flash", 
        validation_alias="LLM_MODEL_NAME", 
        description="Gemini model name"
    )
    llm_agent: str = Field(
        default="gemini", 
        validation_alias="AGENT", 
        description="Default LLM agent to use"
    )
    
    # ============ OpenRouter Configuration ============
    open_router_api_key: str | None = Field(
        default=None, 
        validation_alias="OPEN_ROUTER_API_KEY", 
        description="OpenRouter API key"
    )
    yaml_config_path: str = Field(
        default="app/config/open_router.yml", 
        validation_alias="YAML_CONFIG_PATH", 
        description="Path to OpenRouter YAML config"
    )
    
    # ============ Data Provider Settings ============
    data_provider: str = Field(
        default="yfinance", 
        validation_alias="DATA_PROVIDER", 
        description="Data provider type (e.g., 'yfinance')"
    )
    
    # ============ Redis Settings ============
    redis_url: str = Field(
        default="redis://localhost:6379/0", 
        validation_alias="REDIS_URL", 
        description="Redis connection URL"
    )
    
    # ============ Computed Properties ============
    @property
    def debug(self) -> bool:
        """Enable debug mode for development environment"""
        return self.environment == "development"
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )


class ServerConfig(BaseAppConfig):
    """Server-specific configuration for FastAPI application"""
    
    # ============ Server Settings ============
    host: str = Field(
        default="127.0.0.1", 
        validation_alias="SERVER_HOST", 
        description="Server host address"
    )
    port: int = Field(
        default=8000, 
        validation_alias="SERVER_PORT", 
        description="Server port"
    )
    title: str = Field(
        default="LLM Analysis API", 
        validation_alias="API_TITLE", 
        description="API title"
    )
    version: str = Field(
        default="0.1.0", 
        validation_alias="API_VERSION", 
        description="API version"
    )
    allowed_origins_raw: str = Field(
        default="*", 
        validation_alias="ALLOWED_ORIGINS", 
        description="CORS allowed origins (comma-separated string)"
    )
    analysis_timeout_seconds: float = Field(
        default=20.0, 
        validation_alias="ANALYSIS_TIMEOUT_SECONDS", 
        description="Analysis timeout in seconds"
    )
    worker_queue_name: str = Field(
        default="default",
        validation_alias="WORKER_QUEUE_NAME",
        description="ARQ queue name for job enqueueing"
    )
    
    def __init__(self, **data):
        super().__init__(**data)
        # Parse allowed_origins after initialization
        raw = self.allowed_origins_raw
        if isinstance(raw, str):
            if not raw.strip():
                self.allowed_origins = ["*"]
            else:
                self.allowed_origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
        else:
            self.allowed_origins = raw if isinstance(raw, list) else ["*"]
    
    @property  
    def allowed_origins(self) -> list[str]:
        """Get CORS allowed origins as parsed list"""
        if not hasattr(self, '_allowed_origins'):
            raw = self.allowed_origins_raw
            if isinstance(raw, str):
                if not raw.strip():
                    self._allowed_origins = ["*"]
                else:
                    self._allowed_origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
            else:
                self._allowed_origins = raw if isinstance(raw, list) else ["*"]
        return self._allowed_origins
    
    @allowed_origins.setter 
    def allowed_origins(self, value: list[str]) -> None:
        """Set CORS allowed origins"""
        self._allowed_origins = value


class WorkerConfig(BaseAppConfig):
    """Worker-specific configuration for ARQ task queue"""
    
    # ============ Worker Settings ============
    worker_concurrency: int = Field(
        default=10, 
        validation_alias="WORKER_CONCURRENCY", 
        description="Number of concurrent worker tasks"
    )
    worker_queue_name: str = Field(
        default="default", 
        validation_alias="WORKER_QUEUE_NAME", 
        description="ARQ queue name for this worker"
    )
    worker_job_timeout: int = Field(
        default=3600, 
        validation_alias="WORKER_JOB_TIMEOUT", 
        description="Maximum job execution time in seconds"
    )
    worker_max_tries: int = Field(
        default=3, 
        validation_alias="WORKER_MAX_TRIES", 
        description="Maximum number of retries for failed jobs"
    )
    analysis_timeout_seconds: float = Field(
        default=20.0, 
        validation_alias="ANALYSIS_TIMEOUT_SECONDS", 
        description="Analysis timeout in seconds"
    )
    
    @property
    def worker_settings(self):
        """Get worker settings as a dictionary for ARQ integration"""
        return {
            "concurrency": self.worker_concurrency,
            "job_timeout": self.worker_job_timeout,
            "max_tries": self.worker_max_tries,
            "queueName": self.worker_queue_name,
        }