from fastapi import APIRouter

from src.api import health, analysis, videos

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(analysis.router)
api_router.include_router(videos.router)
