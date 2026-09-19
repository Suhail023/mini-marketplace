"""Notification Service - Consumes order events and manages notifications."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.consumer import run_consumer
from app.database import close_db, init_db
from app.models import Base
from app.routers import notifications
from app.utils.logging import setup_logger

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
        return {"status": "healthy", "service": settings.SERVICE_NAME}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8005)
