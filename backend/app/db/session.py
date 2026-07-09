import re
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()


def _redact(url: str) -> str:
    """Hide the password when logging a database URL."""
    return re.sub(r"://([^:/@]+):[^@]+@", r"://\1:***@", url)


def _build_engine():
    """
    Builds the SQLAlchemy engine.

    PostgreSQL is the single source of truth. If DATABASE_URL points at
    PostgreSQL (or any non-SQLite database) and it cannot be reached at
    startup, we FAIL LOUDLY instead of silently falling back to a local
    SQLite file — a silent fallback forks the data (uploads land in SQLite
    while the operator believes Postgres is authoritative) and is exactly what
    caused "the UI shows 10 documents but Postgres has 3". A SQLite fallback is
    only used when it is explicitly opted into (ALLOW_SQLITE_FALLBACK) or when
    DATABASE_URL is itself a sqlite:// URL (used by the test suite / offline
    local dev).
    """
    url = settings.DATABASE_URL.strip()
    is_sqlite = url.lower().startswith("sqlite")

    if is_sqlite:
        logger.info(f"Using SQLite database (explicitly configured): {_redact(url)}")
        return create_engine(url, connect_args={"check_same_thread": False})

    engine = create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20)
    try:
        with engine.connect():
            pass
        logger.info(f"Connected to PostgreSQL successfully: {_redact(url)}")
        return engine
    except Exception as e:
        if settings.ALLOW_SQLITE_FALLBACK:
            logger.warning(
                "Could not connect to PostgreSQL (%s): %s. ALLOW_SQLITE_FALLBACK is enabled, "
                "so falling back to a LOCAL SQLite database. WARNING: data written now will NOT "
                "be in PostgreSQL.", _redact(url), e
            )
            import os
            sqlite_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "industrial_brain.db"
            )
            return create_engine(f"sqlite:///{sqlite_path}", connect_args={"check_same_thread": False})

        raise RuntimeError(
            f"Could not connect to the configured PostgreSQL database ({_redact(url)}): {e}\n"
            "PostgreSQL is the single source of truth for this application, so it refuses to start on a "
            "divergent local database. Start PostgreSQL (e.g. your Docker DB) and confirm DATABASE_URL "
            "points at the correct database, then retry. For intentional offline local development set "
            "DATABASE_URL to an explicit sqlite:/// URL, or set ALLOW_SQLITE_FALLBACK=true."
        ) from e


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    FastAPI dependency that yields a database session and closes it on request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
