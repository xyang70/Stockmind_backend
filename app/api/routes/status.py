from fastapi import APIRouter, Request

from app.api.schemas import APIResponse

router = APIRouter(tags=["Status"])


@router.get("/status", response_model=APIResponse)
async def server_status(request: Request) -> APIResponse:
    config = request.app.state.config
    return APIResponse(
        success=True,
        message="Server is operational",
        data={
            "version": config.version,
            "environment": config.environment,
            "debug": config.debug,
        },
    )

