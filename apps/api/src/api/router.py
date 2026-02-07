from fastapi import APIRouter

from src.api import health, profile

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(profile.router)
