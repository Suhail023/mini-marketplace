"""Async database engine and session for Notification Service."""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()

engine = None
async_session_factory = None


def init_db(database_url: str | None = None):
    global engine, async_session_factory

    if database_url is None:
        database_url = settings.database.url

    engine = create_async_engine(
        database_url,
        echo=settings.DEBUG,
        pool_pre_ping=True,
    )

    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    return engine


async def get_db() -> AsyncSession:
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with async_session_factory() as session:
        yield session


async def close_db() -> None:
    global engine
    if engine:
        await engine.dispose()
        engine = None
