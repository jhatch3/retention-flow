"""Engine and session management for the RetentionFlow database.

Two ways to get a :class:`~sqlalchemy.orm.Session`:

* :func:`session_scope` -- a context manager that commits on success and rolls
  back on error. Use it in scripts and the ETL / feature-engineering pipeline.
* :func:`get_db` -- a generator suitable as a FastAPI dependency. The caller
  (route handler) is responsible for committing.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings

_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    echo=_settings.db_echo,
    pool_size=_settings.db_pool_size,
    max_overflow=_settings.db_max_overflow,
    pool_pre_ping=_settings.db_pool_pre_ping,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional session scope for scripts and pipelines."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    """Yield a session for use as a FastAPI dependency."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
