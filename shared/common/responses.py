"""Standard response models for all services."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Standard health check response."""

    status: str = Field(..., description="Health status: healthy, degraded, unhealthy")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    checks: dict[str, Any] = Field(default_factory=dict, description="Detailed health checks")


class ApiResponse(BaseModel):
    """Standard API response wrapper."""

    success: bool
    data: Any | None = None
    error: str | None = None
    message: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    message: str
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: dict[str, Any] | None = None
