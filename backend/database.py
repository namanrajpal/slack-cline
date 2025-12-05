"""
Database configuration and connection management.

This module sets up SQLAlchemy with async PostgreSQL support
and provides session management utilities.
"""

import logging
from typing import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool

from config import settings

# Create declarative base for models
Base = declarative_base()

# Create async engine
# Disable SQL query logging to reduce verbosity - use structlog for important events
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Disabled to reduce log noise; use LOG_LEVEL=DEBUG for SQLAlchemy logs if needed
    poolclass=NullPool,  # Use NullPool for development simplicity
    future=True,
)

# Create session maker
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas if using SQLite (for testing)."""
    if "sqlite" in settings.database_url:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
    Yields:
        AsyncSession: Database session instance
    """
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Create all database tables."""
    # Import models to ensure they're registered
    from models.project import ProjectModel  # noqa
    from models.run import RunModel  # noqa
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logging.info("Database tables created successfully")


async def drop_tables():
    """Drop all database tables (for testing)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    logging.info("Database tables dropped successfully")


async def check_database_health() -> bool:
    """
    Check if database connection is healthy.
    
    Returns:
        bool: True if database is accessible, False otherwise
    """
    try:
        async with async_session_maker() as session:
            await session.execute("SELECT 1")
        return True
    except Exception as e:
        logging.error(f"Database health check failed: {e}")
        return False
