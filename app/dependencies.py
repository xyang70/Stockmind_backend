from fastapi import Request
from typing import Any


def get_llm(request: Request) -> Any:
    """
    FastAPI dependency injector
    Equivalent to Spring @Autowired
    """
    return request.app.state.llm_model