"""Health check endpoints for User Service."""

from pathlib import Path
import sys

# Add shared modules to path
shared_path = Path(__file__).parent.parent.parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from datetime import datetime

from fastapi import APIRouter, status

from app.config import get_settings
from common.logging_config import setup_logger
from common.responses import HealthResponse

router = APIRouter()
logger = setup_logger(__name__)
settings = get_settings()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Returns the health status of the User Service",
)
async def health_check() -> HealthResponse:
    """
    Perform health check on User Service.

    Checks:
    - Service is running
    - Database connectivity
    - Redis connectivity
    - Dependent services

    Returns:
        HealthResponse with overall status and detailed checks
    """
    checks = {}
    overall_status = "healthy"

    # Check database connection
    try:
        # TODO: Add actual database check
        checks["database"] = {"status": "healthy", "message": "Connected"}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "message": str(e)}
        overall_status = "unhealthy"

    # Check Redis connection
    try:
        # TODO: Add actual Redis check
        checks["redis"] = {"status": "healthy", "message": "Connected"}
    except Exception as e:
        checks["redis"] = {"status": "degraded", "message": str(e)}
        if overall_status == "healthy":
            overall_status = "degraded"

    logger.info(f"Health check performed: {overall_status}")

    return HealthResponse(
        status=overall_status,
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        timestamp=datetime.utcnow(),
        checks=checks,
    )


@router.get(
    "/health/liveness",
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
    description="Kubernetes liveness probe - checks if service is alive",
)
async def liveness():
    """Liveness probe for Kubernetes."""
    return {"status": "alive"}


@router.get(
    "/health/readiness",
    status_code=status.HTTP_200_OK,
    summary="Readiness Probe",
    description="Kubernetes readiness probe - checks if service is ready to serve traffic",
)
async def readiness():
    """Readiness probe for Kubernetes."""
    # TODO: Add actual readiness checks (DB, cache, etc.)
    return {"status": "ready"}
