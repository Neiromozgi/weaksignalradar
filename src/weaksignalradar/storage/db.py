"""Database engine helpers for Stage A (A-04)."""

from __future__ import annotations

import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def database_url_from_env() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is required and must not be empty "
            "(set it in the local .env / process environment, never commit secrets)."
        )
    return url


def create_db_engine(url: str | None = None, *, echo: bool = False) -> Engine:
    return create_engine(url or database_url_from_env(), pool_pre_ping=True, echo=echo)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def check_db_ready(engine: Engine) -> bool:
    """Return True when a trivial round-trip to PostgreSQL succeeds."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
