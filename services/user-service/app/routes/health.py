"""Health check endpoints for User Service."""

from datetime import datetime

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.database import async_session_factory
from common.logging_config import setup_logger
from common.responses import HealthResponse

router = APIRouter()
logger = setup_logger(__name__)
settings = get_settings()


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
)
async def health_check():
    checks = {}
    overall_status = "healthy"

    try:
        if async_session_factory:
            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
            checks["database"] = {"status": "healthy", "message": "Connected"}
        else:
            checks["database"] = {"status": "unhealthy", "message": "Not initialized"}
            overall_status = "unhealthy"
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "message": str(e)}
        overall_status = "unhealthy"

    health = HealthResponse(
        status=overall_status,
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        timestamp=datetime.utcnow(),
        checks=checks,
    )
    status_code = 200 if overall_status == "healthy" else 503
    return JSONResponse(content=health.model_dump(mode="json"), status_code=status_code)


@router.get("/health/liveness", status_code=status.HTTP_200_OK)
async def liveness():
    return {"status": "alive"}


@router.get("/health/readiness", status_code=status.HTTP_200_OK)
async def readiness():
    return {"status": "ready"}
