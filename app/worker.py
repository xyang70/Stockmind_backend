import json
import logging
import asyncio
from arq.connections import RedisSettings
from dotenv import load_dotenv

from app.settings import WorkerConfig
from app.llm_models.llm_model_factory import LLMModelFactory
from app.data_providers.data_provider_factory import DataProviderFactory
from app.services.impl.analysis_service_impl import AnalysisServiceImpl
from app.services.impl.impl_data_processing import DataProcessingImpl
from app.config_builder import LLMConfigBuilder

logger = logging.getLogger(__name__)
load_dotenv()


async def analyze_data_job(ctx, payload: dict):
    """
    ARQ job for analyzing stock data using LLM models.
    
    Args:
        ctx: ARQ job context containing redis connection and job_id
        payload: Dict containing 'symbol', 'agent_name', 'model', and other analysis parameters
    
    Returns:
        Analysis result dictionary
    """
    redis = ctx["redis"]
    job_id = ctx["job_id"]

    try:
        # Update job status
        await redis.set(f"analysis:status:{job_id}", "running", ex=3600)

        # Load centralized worker configuration
        config = WorkerConfig()

        # Build LLM configuration using the centralized builder
        llm_model_config = LLMConfigBuilder.build(config)
        
        llm_factory = LLMModelFactory(config=llm_model_config)
        data_provider_factory = DataProviderFactory()
        data_provider = data_provider_factory.create_data_provider(config.data_provider)
        data_processor = DataProcessingImpl()

        llm_client = llm_factory.get_llm_model(
            payload["agent_name"],
            payload["model"],
        )

        analyze_service = AnalysisServiceImpl(
            data_processor=data_processor,
            llm_agent=llm_client,
            data_provider=data_provider,
        )

        # Run blocking I/O operation in thread pool to avoid blocking event loop
        result = await asyncio.to_thread(
            analyze_service.analyze_data,
            payload["symbol"]
        )

        # Set successful completion status and result
        await redis.set(f"analysis:status:{job_id}", "completed", ex=3600)
        await redis.set(
            f"analysis:result:{job_id}",
            json.dumps(result, ensure_ascii=False),
            ex=3600,
        )

        return result

    except Exception as e:
        # Log exception and set failure status
        logger.exception(f"Job {job_id} failed for symbol={payload.get('symbol')}")
        await redis.set(f"analysis:status:{job_id}", "failed", ex=3600)
        await redis.set(f"analysis:error:{job_id}", str(e), ex=3600)
        raise


class WorkerSettings:
    """ARQ Worker configuration using centralized settings"""
    
    functions = [analyze_data_job]
    
    # Initialize worker configuration once at startup
    _worker_config = WorkerConfig()
    
    # Configure Redis with centralized settings
    redis_settings = RedisSettings.from_dsn(_worker_config.redis_url)
    
    # Apply worker-specific ARQ settings
    concurrency = _worker_config.worker_concurrency
    job_timeout = _worker_config.worker_job_timeout
    max_tries = _worker_config.worker_max_tries
    queue_name = _worker_config.worker_queue_name