"""Notification Service - Consumes order events and manages notifications."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.consumer import run_consumer
from app.database import async_session_factory, close_db, init_db
from app.models import Base
from app.routers import notifications
from app.utils.logging import setup_logger
from common.middleware import CorrelationIDMiddleware
from common.responses import HealthResponse

logger = setup_logger(__name__)
settings = get_settings()


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db_engine = init_db()
        async with db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Notification Service database tables ensured")

        consumer_task = asyncio.create_task(run_consumer())
        logger.info("RabbitMQ consumer background task started")

        yield

        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
        await close_db()
        logger.info("Notification Service shut down")

    app = FastAPI(
        title="Notification Service",
        description="Consumes order events and manages user notifications",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(CorrelationIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(notifications.router)

    @app.get("/health")
    async def health_check():
        checks: dict = {}
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
            version="0.1.0",
            timestamp=datetime.utcnow(),
            checks=checks,
        )
        status_code = 200 if overall_status == "healthy" else 503
        return JSONResponse(content=health.model_dump(mode="json"), status_code=status_code)

    @app.get("/health/liveness")
    async def liveness():
        return {"status": "alive"}

    @app.get("/health/readiness")
    async def readiness():
        return {"status": "ready"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8005)
