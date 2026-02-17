"""Database configuration and session management"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from app.core.config import settings


# Create async engine
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Alias for background tasks
async_session_maker = AsyncSessionLocal

# Declarative base for models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.

    Usage in FastAPI endpoints:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database - create all tables if they don't exist"""
    async with async_engine.begin() as conn:
        # Create tables if they don't exist (preserves existing data)
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections"""
    await async_engine.dispose()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions in background tasks.

    Usage:
        async with get_db_session() as db:
            result = await db.execute(...)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
