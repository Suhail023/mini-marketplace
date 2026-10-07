"""Notification Service - Consumes order events and manages notifications."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import database
from app.config import get_settings
from app.consumer import run_consumer
from app.database import close_db, init_db
from app.models import Base
from app.routers import notifications
from app.utils.logging import setup_logger
from common.health import build_health_router
from common.middleware import CORRELATION_ID_HEADER, CorrelationIDMiddleware

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
        expose_headers=[CORRELATION_ID_HEADER],
    )

    app.include_router(notifications.router)

    app.include_router(
        build_health_router(
            service_name=settings.SERVICE_NAME,
            version=app.version,
            get_session_factory=lambda: database.async_session_factory,
        )
    )

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8005)
