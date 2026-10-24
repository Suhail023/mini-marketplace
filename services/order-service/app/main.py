"""Order Service - Orchestrates Product and Payment services."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import db
from app.models import Base
from app.publisher import OutboxPublisher
from app.routers import orders
from app.utils.logging import setup_logger
from common.auth import validate_auth_settings
from common.errors import register_error_handlers
from common.health import build_health_router
from common.middleware import CORRELATION_ID_HEADER, CorrelationIDMiddleware

logger = setup_logger(__name__)
settings = get_settings()


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        validate_auth_settings(jwt=True, internal_token=True)
        db.init(
            settings.database.url,
            echo=settings.DEBUG,
            pool_size=settings.database.POOL_SIZE,
            max_overflow=settings.database.MAX_OVERFLOW,
            pool_timeout=settings.database.POOL_TIMEOUT,
            pool_recycle=settings.database.POOL_RECYCLE,
        )
        await db.create_all(Base.metadata)
        logger.info("Order Service database tables ensured")

        publisher_task = asyncio.create_task(OutboxPublisher().run())
        logger.info("Outbox publisher background task started")

        yield

        publisher_task.cancel()
        with suppress(asyncio.CancelledError):
            await publisher_task
        await db.close()
        logger.info("Order Service shut down")

    app = FastAPI(
        title="Order Service",
        description="Order orchestration - calls Product and Payment services",
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
    register_error_handlers(app)

    app.include_router(orders.router)
    app.include_router(
        build_health_router(
            service_name=settings.SERVICE_NAME,
            version=app.version,
            get_session_factory=lambda: db.session_factory,
        )
    )

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8003)
