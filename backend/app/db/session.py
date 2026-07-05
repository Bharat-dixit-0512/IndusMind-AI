import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

# Try connecting to PostgreSQL, if it fails fallback to SQLite
try:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )
    # Test connection
    with engine.connect() as conn:
        pass
    logger.info("Connected to PostgreSQL successfully.")
except Exception as e:
    logger.warning(f"Could not connect to PostgreSQL: {e}. Falling back to SQLite local database.")
    sqlite_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
        "industrial_brain.db"
    )
    engine = create_engine(
        f"sqlite:///{sqlite_path}",
        connect_args={"check_same_thread": False}
    )
    logger.info(f"Local SQLite database engine initialized at {sqlite_path}")

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
