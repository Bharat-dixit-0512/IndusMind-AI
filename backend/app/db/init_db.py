import logging
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from app.db.session import engine, Base, SessionLocal
from app.db.base import User  # Make sure models are registered
from app.models.user import UserRole
from app.core.security import hash_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _apply_lightweight_migrations() -> None:
    """
    SQLAlchemy's create_all() only creates missing TABLES, never adds new
    COLUMNS to tables that already exist. This applies the small set of
    additive column migrations this project needs so an existing dev/prod DB
    picks them up without a full migration framework. Each is guarded so it's
    a no-op when the column is already present.
    """
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    if "documents" in table_names:
        existing_columns = {col["name"] for col in inspector.get_columns("documents")}
        if "category" not in existing_columns:
            logger.info("Migrating: adding documents.category column.")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE documents ADD COLUMN category VARCHAR"))

    # reports.report_type moved from a native DB enum to a plain VARCHAR so
    # new report types (e.g. EXECUTIVE) don't need an ALTER TYPE migration.
    # Convert an existing Postgres native-enum column in place; SQLite already
    # stores it as text so it needs nothing.
    if "reports" in table_names and engine.dialect.name == "postgresql":
        try:
            report_type_col = next(
                (c for c in inspector.get_columns("reports") if c["name"] == "report_type"), None
            )
            type_str = str(report_type_col["type"]).lower() if report_type_col else ""
            if report_type_col is not None and "char" not in type_str and "text" not in type_str:
                logger.info("Migrating: converting reports.report_type from native enum to VARCHAR.")
                with engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE reports ALTER COLUMN report_type TYPE VARCHAR USING report_type::text"
                    ))
        except Exception as e:
            logger.warning(f"Could not convert reports.report_type to VARCHAR (may already be text): {e}")


def init_db(db: Session) -> None:
    # Tables are created using SQLAlchemy metadata
    logger.info("Creating tables...")
    Base.metadata.create_all(bind=engine)
    _apply_lightweight_migrations()
    logger.info("Tables created successfully.")

    # Create default admin user if not exists
    logger.info("Checking for default admin user...")
    admin_email = "admin@industrial.ai"
    admin = db.query(User).filter(User.email == admin_email).first()
    if not admin:
        logger.info(f"Creating default admin user: {admin_email}")
        admin = User(
            email=admin_email,
            password_hash=hash_password("adminpassword123"),
            full_name="System Administrator",
            role=UserRole.ADMIN
        )
        db.add(admin)
        db.commit()
        logger.info("Default admin user created successfully.")
    else:
        logger.info("Default admin user already exists.")


def main() -> None:
    logger.info("Initializing database...")
    db = SessionLocal()
    try:
        init_db(db)
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise e
    finally:
        db.close()
    logger.info("Database initialization completed.")


if __name__ == "__main__":
    main()
