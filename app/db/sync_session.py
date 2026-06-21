"""Separate SYNC SQLAlchemy engine + session for Celery workers.

Celery tasks run synchronously and must NOT share the FastAPI async session.
They use this dedicated sync sessionmaker (psycopg driver) instead.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
_sessionmaker: sessionmaker[Session] | None = None


def get_sync_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_settings().effective_sync_database_url,
            pool_pre_ping=True,
            future=True,
        )
    return _engine


def get_sync_sessionmaker() -> sessionmaker[Session]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = sessionmaker(
            bind=get_sync_engine(), expire_on_commit=False, autoflush=False
        )
    return _sessionmaker


@contextmanager
def sync_session_scope() -> Iterator[Session]:
    """Context manager yielding a transactional sync session for tasks/scripts."""
    session = get_sync_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
