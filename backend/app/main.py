import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import auth, documents, chat, graph, compliance, reports
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.db.init_db import init_db
from app.services.graph_db import graph_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include Routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(documents.router, prefix=f"{settings.API_V1_STR}/documents", tags=["Documents"])
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["AI Chat"])
app.include_router(graph.router, prefix=f"{settings.API_V1_STR}/graph", tags=["Knowledge Graph"])
app.include_router(compliance.router, prefix=f"{settings.API_V1_STR}/compliance", tags=["Compliance Agent"])
app.include_router(reports.router, prefix=f"{settings.API_V1_STR}/reports", tags=["Reports"])


@app.on_event("startup")
def on_startup():
    logger.info("Starting up FastAPI application...")
    
    # 1. Initialize PostgreSQL tables and seed admin user
    try:
        logger.info("Initializing relational database...")
        db = SessionLocal()
        init_db(db)
        db.close()
        logger.info("Relational database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize relational database on startup: {e}")

    # 2. Reseed Neo4j with Centurion Plant if graph is active
    try:
        logger.info("Checking Graph database connectivity...")
        if graph_db.active:
            logger.info("Graph DB is active. Seeding/Verifying Centurion Plant nodes...")
            graph_db.load_centurion_mock_graph()
        else:
            logger.info("Graph DB is in mock mode. Centurion Plant mock dataset loaded.")
    except Exception as e:
        logger.error(f"Failed to verify/seed graph database: {e}")


@app.get("/")
def read_root():
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "api_docs": "/docs"
    }
