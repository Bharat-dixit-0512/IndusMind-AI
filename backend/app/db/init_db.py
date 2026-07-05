import logging
from sqlalchemy.orm import Session
from app.db.session import engine, Base, SessionLocal
from app.db.base import User  # Make sure models are registered
from app.models.user import UserRole
from app.core.security import hash_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db(db: Session) -> None:
    # Tables are created using SQLAlchemy metadata
    logger.info("Creating tables...")
    Base.metadata.create_all(bind=engine)
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
