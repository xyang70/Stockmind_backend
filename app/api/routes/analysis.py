import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.api.schemas import APIResponse
from app.request_models.analysis_request import AnalysisRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/us/stocks/analysis", tags=["Results"])


@router.get("/{job_id}", response_model=APIResponse)
async def get_analysis_status(request: Request, job_id: str) -> APIResponse:
    try:
        redis = request.app.state.redis

        status_value = await redis.get(f"analysis:status:{job_id}")
        result_value = await redis.get(f"analysis:result:{job_id}")
        error_value = await redis.get(f"analysis:error:{job_id}")

        if status_value is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found",
            )

        data = {
            "job_id": job_id,
            "status": (
                status_value.decode()
                if isinstance(status_value, bytes)
                else status_value
            ),
        }

        if result_value:
            data["result"] = (
                result_value.decode()
                if isinstance(result_value, bytes)
                else result_value
            )

        if error_value:
            data["error"] = (
                error_value.decode()
                if isinstance(error_value, bytes)
                else error_value
            )

        return APIResponse(
            success=True,
            message="Job status retrieved successfully",
            data=data,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Unexpected error getting job status: %s", str(exc), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving job status",
        )


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def analyze_symbol(
    request: Request, analysis_request: AnalysisRequest
) -> APIResponse:
    try:
        logger.info(
            "Analysis requested for symbol: %s",
            analysis_request.symbol,
        )

        try:
            request.app.state.llm_factory.get_llm_model(
                analysis_request.llm_agent_request.agent_name,
                analysis_request.llm_agent_request.model,
            )
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"LLM dependency missing: {exc}",
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            )

        redis = request.app.state.redis
        config = request.app.state.config

        payload = {
            "symbol": analysis_request.symbol,
            "agent_name": analysis_request.llm_agent_request.agent_name,
            "model": analysis_request.llm_agent_request.model,
        }

        job = await redis.enqueue_job(
            "analyze_data_job",
            payload,
            _queue_name=config.worker_queue_name,
        )

        await redis.set(f"analysis:status:{job.job_id}", "queued", ex=3600)

        return APIResponse(
            success=True,
            message="Analysis job queued successfully",
            data={"job_id": job.job_id, "status": "queued"},
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Unexpected error queueing analysis: %s", str(exc), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while queueing analysis",
        )

@router.get("/stock_market_news", response_model=APIResponse)
async def get_stock_market_news(request: Request) -> APIResponse:
    try:
        data_provider = request.app.state.data_provider
        news = data_provider.get_news("SPY", enable_summary=False)

        return APIResponse(
            success=True,
            message="Stock market news retrieved successfully",
            data={"news": news},
        )

    except Exception as exc:
        logger.error(
            "Unexpected error getting stock market news: %s", str(exc), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving stock market news",
        )
