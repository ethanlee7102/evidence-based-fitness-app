import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import api_router
from src.core import anthropic_provider, embedding_provider, llm_provider

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Clean up shared httpx clients on shutdown
    await embedding_provider.client.aclose()
    await llm_provider.client.aclose()
    await anthropic_provider.client.aclose()


app = FastAPI(
    title="Flame Fitness API",
    description="AI-powered workout logging with RAG chatbot",
    version="0.1.0",
    lifespan=lifespan,
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
