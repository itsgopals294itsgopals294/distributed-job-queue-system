from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.jobs import router as jobs_router
from app.api.admin import router as admin_router
from app.api.workers import router as workers_router
from app.api.metrics import router as metrics_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(jobs_router)
api_router.include_router(admin_router)
api_router.include_router(workers_router)
api_router.include_router(metrics_router)
