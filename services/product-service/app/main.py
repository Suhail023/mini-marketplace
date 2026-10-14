"""Product Service - CRUD + stock management for the Mini Marketplace."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Config, get_settings
from app.database import db
from app.models import Base
from app.routers import internal, products
from app.utils.logging import setup_logger
from common.auth import validate_auth_settings
from common.errors import register_error_handlers
from common.health import build_health_router
from common.middleware import CORRELATION_ID_HEADER, CorrelationIDMiddleware

logger = setup_logger(__name__)


def create_app(config: Config | None = None) -> FastAPI:
    config = config or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        validate_auth_settings(jwt=True, internal_token=True)
        db.init(config.database.url, echo=config.DEBUG)
        await db.create_all(Base.metadata)
        logger.info(f"Database tables ensured for {config.SERVICE_NAME}")
        yield
        await db.close()
        logger.info("Database connection closed")

    app = FastAPI(
        title="Product Service",
        description="CRUD + stock management for the Mini Marketplace",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(CorrelationIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[CORRELATION_ID_HEADER],
    )
    register_error_handlers(app)

    app.include_router(products.router)
    app.include_router(internal.router)
    app.include_router(
        build_health_router(
            service_name=config.SERVICE_NAME,
            version=app.version,
            get_session_factory=lambda: db.session_factory,
        )
    )

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
