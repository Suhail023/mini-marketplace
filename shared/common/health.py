"""Shared health check endpoints (health, liveness, readiness)."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from common.logging_config import setup_logger
from common.responses import HealthResponse

logger = setup_logger(__name__)


async def check_database(get_session_factory: Callable[[], Any]) -> dict[str, str]:
    """Run SELECT 1 against the database.

    The session factory is resolved through a getter on every call because
    services assign it in init_db() at startup; importing it by name would
    capture the initial None forever.
    """
    session_factory = get_session_factory()
    if session_factory is None:
        return {"status": "unhealthy", "message": "Not initialized"}
    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        # Details stay in the logs; /health is publicly reachable via the gateway.
        logger.exception("Database health check failed")
        return {"status": "unhealthy", "message": "Database unreachable"}
    return {"status": "healthy", "message": "Connected"}


def build_health_router(
    service_name: str,
    version: str,
    get_session_factory: Callable[[], Any],
) -> APIRouter:
    """Build /health, /health/liveness and /health/readiness for a service.

    - /health: full report with dependency checks; 503 when unhealthy.
    - /health/liveness: process is up; never touches dependencies.
    - /health/readiness: 503 until the database is reachable.
    """
    router = APIRouter(tags=["health"])

    @router.get("/health")
    async def health_check():
        checks = {"database": await check_database(get_session_factory)}
        healthy = all(c["status"] == "healthy" for c in checks.values())
        health = HealthResponse(
            status="healthy" if healthy else "unhealthy",
            service=service_name,
            version=version,
            timestamp=datetime.now(UTC),
            checks=checks,
        )
        return JSONResponse(
            content=health.model_dump(mode="json"),
            status_code=200 if healthy else 503,
        )

    @router.get("/health/liveness")
    async def liveness():
        return {"status": "alive"}

    @router.get("/health/readiness")
    async def readiness():
        db = await check_database(get_session_factory)
        if db["status"] != "healthy":
            return JSONResponse(content={"status": "not_ready"}, status_code=503)
        return {"status": "ready"}

    return router
