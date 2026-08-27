import os
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


engine = None
async_session_factory = None


def init_db(database_url: Optional[str] = None):
    global engine, async_session_factory

    if database_url is None:
        database_url = (
            f"postgresql+asyncpg://"
            f"{os.getenv('DATABASE_USER', 'postgres')}:"
            f"{os.getenv('DATABASE_PASSWORD', 'postgres')}@"
            f"{os.getenv('DATABASE_HOST', 'localhost')}:"
            f"{os.getenv('DATABASE_PORT', '5432')}/"
            f"{os.getenv('DATABASE_NAME', 'productdb')}"
        )

    engine = create_async_engine(
        database_url,
        echo=os.getenv("DEBUG", "false").lower() == "true",
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
