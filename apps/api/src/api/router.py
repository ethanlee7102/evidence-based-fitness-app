from fastapi import APIRouter

from src.api import chat, health, profile

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(profile.router)
api_router.include_router(chat.router)
