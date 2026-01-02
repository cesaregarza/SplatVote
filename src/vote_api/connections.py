"""Database and Redis connection management."""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from shared_lib.db import get_database_uri, get_redis_url

# Async database engine
async_engine = create_async_engine(
    get_database_uri(async_driver=True),
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    pool_pre_ping=True,
    poolclass=NullPool,  # Use NullPool for better async compatibility
)

# Session factory
async_session_factory = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


# Redis connection pool
redis_pool = redis.ConnectionPool.from_url(
    get_redis_url(),
    max_connections=10,
    decode_responses=True,
)

redis_client = redis.Redis(connection_pool=redis_pool)


def get_redis() -> redis.Redis:
    """Get Redis client."""
    return redis_client


@asynccontextmanager
async def db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions outside of request context."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
