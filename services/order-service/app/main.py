"""Order Service - Orchestrates Product and Payment services."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import close_db, init_db
from app.models import Base
from app.routers import orders
from app.utils.logging import setup_logger

logger = setup_logger(__name__)
settings = get_settings()


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db_engine = init_db()
        async with db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Order Service database tables ensured")
        yield
        await close_db()
        logger.info("Order Service shut down")

    app = FastAPI(
        title="Order Service",
        description="Order orchestration - calls Product and Payment services",
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

    app.include_router(orders.router)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": settings.SERVICE_NAME}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8003)
