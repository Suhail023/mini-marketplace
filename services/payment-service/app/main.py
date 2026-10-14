"""Payment Service - Mock payment processing with idempotency."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import db
from app.models import Base
from app.routers import payments
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
        validate_auth_settings(internal_token=True)
        db.init(settings.database.url, echo=settings.DEBUG)
        await db.create_all(Base.metadata)
        logger.info("Payment Service database tables ensured")
        yield
        await db.close()
        logger.info("Payment Service shut down")

    app = FastAPI(
        title="Payment Service",
        description="Mock payment processing with idempotency",
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

    app.include_router(payments.router)
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

    uvicorn.run("app.main:app", host="0.0.0.0", port=8004)
