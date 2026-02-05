import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import api_router

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

app = FastAPI(
    title="Flame Fitness API",
    description="AI-powered form analysis for the Big 3 lifts",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "Flame Fitness API", "version": "0.1.0"}
