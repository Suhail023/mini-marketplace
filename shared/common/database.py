"""Async SQLAlchemy engine/session lifecycle shared by every service."""

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class Database:
    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession] | None:
        return self._session_factory

    def init(self, url: str, *, echo: bool = False, **engine_kwargs: Any) -> AsyncEngine:
        self._engine = create_async_engine(url, echo=echo, pool_pre_ping=True, **engine_kwargs)
        self._session_factory = async_sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
        return self._engine

    async def create_all(self, metadata: MetaData) -> None:
        if self._engine is None:
            raise RuntimeError("Database not initialized")
        async with self._engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

    def session(self) -> AsyncSession:
        if self._session_factory is None:
            raise RuntimeError("Database not initialized")
        return self._session_factory()

    async def get_session(self) -> AsyncIterator[AsyncSession]:
        async with self.session() as session:
            yield session

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
        self._engine = None
        self._session_factory = None
