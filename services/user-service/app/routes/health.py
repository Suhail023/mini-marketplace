"""Health check endpoints for User Service."""

from app import database
from app.config import get_settings
from common.health import build_health_router

settings = get_settings()

router = build_health_router(
    service_name=settings.SERVICE_NAME,
    version=settings.SERVICE_VERSION,
    get_session_factory=lambda: database.async_session_factory,
)
