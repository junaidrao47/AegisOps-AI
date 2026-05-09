from fastapi import APIRouter

from app.api.v1.routes import auth, health, incidents, log_ingestion, orchestrator

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(incidents.router, tags=["incidents"])
api_router.include_router(log_ingestion.router, tags=["logs"])
api_router.include_router(orchestrator.router, tags=["orchestrator"])
