"""A normal (non-async) database session for the Celery worker. Celery tasks are plain functions,
so the simple synchronous SQLAlchemy API is the right fit there."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _sync_url(url: str) -> str:
    if url == "CHANGE_ME":
        return "postgresql+psycopg://placeholder:placeholder@localhost:5432/placeholder"
    return url.replace("postgresql://", "postgresql+psycopg://", 1)


sync_engine = create_engine(_sync_url(settings.database_url), pool_pre_ping=True, pool_size=2, max_overflow=2)
SyncSession = sessionmaker(sync_engine, class_=Session, expire_on_commit=False)
