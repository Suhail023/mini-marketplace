"""Product Service - CRUD + stock management for the Mini Marketplace."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import database
from app.config import Config, get_settings
from app.database import close_db, init_db
from app.models import Base
from app.routers import products
from app.utils.errors import AppError, ConflictError, NotFoundError, ValidationError
from app.utils.logging import setup_logger
from common.health import build_health_router
from common.middleware import CORRELATION_ID_HEADER, CorrelationIDMiddleware

logger = setup_logger(__name__)


def create_app(config: Config = None) -> FastAPI:
    if config is None:
        config = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database_url = config.database.url
        if "sqlite" in database_url or "aiosqlite" in database_url:
            database_url = "sqlite+aiosqlite:///./product.db"
        db_engine = init_db(database_url)
        async with db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info(f"Database tables ensured for {config.SERVICE_NAME}")
        yield
        await close_db()
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

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": exc.message,
                    "type": exc.__class__.__name__,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": exc.message,
                    "type": "ValidationError",
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(NotFoundError)
    async def not_found_error_handler(request: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": exc.message,
                    "type": "NotFoundError",
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(ConflictError)
    async def conflict_error_handler(request: Request, exc: ConflictError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": exc.message,
                    "type": "ConflictError",
                    "details": exc.details,
                }
            },
        )

    app.include_router(products.router)

    app.include_router(
        build_health_router(
            service_name=config.SERVICE_NAME,
            version=app.version,
            get_session_factory=lambda: database.async_session_factory,
        )
    )

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
