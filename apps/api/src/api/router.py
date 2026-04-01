from fastapi import APIRouter

from src.api import chat, health, profile, routines, workouts

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(profile.router)
api_router.include_router(chat.router)
api_router.include_router(workouts.router)
api_router.include_router(routines.router)
