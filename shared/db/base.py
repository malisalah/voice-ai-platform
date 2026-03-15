"""Async SQLAlchemy engine and session factory."""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from shared.utils.errors import DatabaseError

# Get database URL from environment
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/voiceai",
)

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create session factory
SessionFactory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Metadata object for migrations
metadata = MetaData()


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session.

    Usage:
        async with get_session() as session:
            await session.execute(query)
    """
    session: AsyncSession | None = None
    try:
        session = SessionFactory()
        yield session
    except Exception as exc:
        if session:
            await session.rollback()
        raise DatabaseError("Database operation failed") from exc
    finally:
        if session:
            await session.close()


async def get_connection() -> AsyncConnection:
    """Get an async database connection."""
    return await engine.connect()


async def init_models() -> None:
    """Initialize database models (create tables if not exist)."""
    from sqlalchemy.ext.asyncio import AsyncConnection

    from shared.models.base import Base

    async with engine.begin() as conn:
        # Run migrations if needed
        await conn.run_sync(Base.metadata.create_all)


async def drop_models() -> None:
    """Drop all database models (use with caution!)."""
    from sqlalchemy.ext.asyncio import AsyncConnection

    from shared.models.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
