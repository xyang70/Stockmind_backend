from fastapi import APIRouter, Request

from app.api.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    config = request.app.state.config
    return HealthResponse(
        status="healthy",
        version=config.version,
        environment=config.environment,
    )

