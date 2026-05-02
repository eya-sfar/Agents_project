"""
database/connection.py
PostgreSQL connection pool via SQLAlchemy.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from config.settings import settings
from utils.logger import logger
from database.models import Base


engine = create_engine(
    settings.db.URL,
    pool_size=settings.db.POOL_SIZE,
    max_overflow=settings.db.MAX_OVERFLOW,
    pool_timeout=settings.db.POOL_TIMEOUT,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Usage:
        with get_session() as session:
            session.add(obj)
    """
    session = SessionLocal()

    try:
        yield session
        session.commit()

    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise

    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency-style database session generator.
    Useful for APIs.
    """
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


def init_db() -> None:
    """
    Create all tables using SQLAlchemy models.
    Safe to call multiple times.
    """
    logger.info("Initialising database schema...")

    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]

    logger.info(f"Connected to PostgreSQL: {version}")
    logger.info("Database schema ready.")


def drop_all() -> None:
    """
    Drop all tables.
    Use only in development or tests.
    """
    logger.warning("Dropping all tables...")

    Base.metadata.drop_all(bind=engine)

    logger.warning("All tables dropped.")