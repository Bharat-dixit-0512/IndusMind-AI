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

    # Auto-rewrite database connection string schemes
    # 1. Translate postgres:// to postgresql:// (required by SQLAlchemy 1.4+)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    
    # 2. Add pg8000 driver suffix if missing, as pg8000 is our installed driver
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+pg8000://", 1)

    connect_args = {}
    
    # 3. Handle sslmode / ssl parameter for pg8000 to work out of the box with SSL-enforced dbs (e.g. Render/Supabase)
    if "sslmode" in url or "ssl=" in url:
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed.query)
        sslmode = query_params.pop("sslmode", [None])[0]
        ssl_val = query_params.pop("ssl", [None])[0]
        
        # Re-build query string without sslmode/ssl to prevent pg8000 driver parsing errors
        new_query = urllib.parse.urlencode(query_params, doseq=True)
        parsed = parsed._replace(query=new_query)
        url = urllib.parse.urlunparse(parsed)
        
        # Configure SSL context for pg8000
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connect_args["ssl_context"] = ssl_context
        logger.info("SSL connection configured for PostgreSQL (sslmode/ssl parameter detected and mapped to ssl_context).")

    engine = create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20, connect_args=connect_args)
    try:
        with engine.connect():
            pass
        logger.info(f"Connected to PostgreSQL successfully: {_redact(url)}")
        return engine
    except Exception as e:
        # No SQLite fallback: PostgreSQL is the single source of truth. If it is
        # unreachable the app refuses to start rather than silently writing to a
        # divergent local database. (The test suite passes an explicit sqlite://
        # DATABASE_URL and takes the branch above.)
        raise RuntimeError(
            f"Could not connect to the configured PostgreSQL database ({_redact(url)}): {e}\n"
            "PostgreSQL is required. Start PostgreSQL (e.g. your Docker DB) and confirm DATABASE_URL "
            "points at the correct database, then retry. For intentional offline local development set "
            "DATABASE_URL to an explicit sqlite:/// URL."
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
