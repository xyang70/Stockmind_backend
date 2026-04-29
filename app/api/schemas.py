from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class AnalysisResult(BaseModel):
    id: Optional[str] = Field(None, description="Unique result ID")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Timestamp of analysis",
    )
    data: Dict[str, Any] = Field(..., description="Analysis result data")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata"
    )

    @field_validator("data")
    @classmethod
    def data_not_empty(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if not value:
            raise ValueError("Data cannot be empty")
        return value


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    version: str
    environment: str


class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

