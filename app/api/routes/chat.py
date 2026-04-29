import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatAgentRequest(BaseModel):
    agent_name: str
    model: str


class ChatStreamRequest(BaseModel):
    message: str
    llm_agent_request: ChatAgentRequest | None = None
    chunk_size: int = 1
    chunk_delay_ms: int = 15


def _extract_text_from_llm_response(response: Any) -> str:
    if response is None:
        return ""

    text_attr = getattr(response, "text", None)
    if isinstance(text_attr, str) and text_attr.strip():
        return text_attr

    choices = getattr(response, "choices", None)
    if choices and len(choices) > 0:
        message = getattr(choices[0], "message", None)
        if message is not None:
            content = getattr(message, "content", None)
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts: list[str] = []
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        parts.append(str(item["text"]))
                if parts:
                    return "".join(parts)

    return str(response)


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def stream_chat(request: Request, payload: ChatStreamRequest) -> StreamingResponse:
    if not payload.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="message cannot be empty",
        )

    config = request.app.state.config
    agent_name = (
        payload.llm_agent_request.agent_name
        if payload.llm_agent_request
        else config.llm_agent
    )
    model_name = (
        payload.llm_agent_request.model
        if payload.llm_agent_request
        else config.llm_model_name
    )

    try:
        llm_client = request.app.state.llm_factory.get_llm_model(
            agent_name,
            model_name,
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

    chunk_size = max(1, payload.chunk_size)
    delay_seconds = max(0, payload.chunk_delay_ms) / 1000.0

    async def event_generator():
        try:
            yield _sse_event(
                "start",
                {"agent_name": agent_name, "model": model_name},
            )

            raw_response = await asyncio.to_thread(
                llm_client.send_request,
                payload.message,
            )
            text = _extract_text_from_llm_response(raw_response)

            for i in range(0, len(text), chunk_size):
                chunk = text[i : i + chunk_size]
                yield _sse_event("token", {"content": chunk})
                if delay_seconds > 0:
                    await asyncio.sleep(delay_seconds)

            yield _sse_event("end", {"done": True})
        except Exception as exc:
            logger.error("SSE chat stream failed: %s", str(exc), exc_info=True)
            yield _sse_event("error", {"detail": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

