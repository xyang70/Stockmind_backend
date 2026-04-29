from fastapi import APIRouter, Request,HTTPException, status
import logging

from app.api.schemas import APIResponse

router = APIRouter(tags=["Info"])

logger = logging.getLogger(__name__)


@router.get("/", response_model=APIResponse)
async def read_root(request: Request) -> APIResponse:
    config = request.app.state.config
    return APIResponse(
        success=True,
        message=f"{config.title} API is running",
        data={"version": config.version},
    )


@router.get("/available-models", response_model=APIResponse)
async def get_available_models(request: Request) -> APIResponse:
    models = request.app.state.llm_factory.get_available_models()
    return APIResponse(
        success=True,
        message="Available LLM models retrieved successfully",
        data={"models": models},
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
