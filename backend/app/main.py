import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import init_db, get_db
from app.services.auth_service import AuthService
from app.api import api_router
from app.core.redis import RedisClient
from app.api.metrics import prometheus_metrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("jobqueue.backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Distributed Job Queue Backend...")
    # Initialize DB schema
    await init_db()
    
    # Initialize default admin
    async for db in get_db():
        await AuthService.ensure_default_admin(db)
        break
        
    logger.info("Backend initialized and ready to receive requests.")
    yield
    logger.info("Shutting down backend and closing resources...")
    await RedisClient.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-inspired Distributed Job Queue System API with RBAC, Redis priorities, DLQ, and Prometheus observability.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits cross-origin requests from web dashboards
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0"
    }


STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
STATIC_INDEX = os.path.join(STATIC_DIR, "index.html")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/metrics", include_in_schema=False)
async def root_metrics(response: Response, db: AsyncSession = Depends(get_db)):
    return await prometheus_metrics(db=db)


@app.get("/", tags=["Dashboard"], include_in_schema=False)
@app.get("/dashboard", tags=["Dashboard"], include_in_schema=False)
async def serve_dashboard():
    if os.path.exists(STATIC_INDEX):
        return FileResponse(STATIC_INDEX)
    return {
        "name": settings.PROJECT_NAME,
        "docs_url": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }
