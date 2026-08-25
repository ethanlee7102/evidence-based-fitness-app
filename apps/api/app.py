import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import api_router
from src.core import anthropic_provider, embedding_provider, llm_provider, reranker
from src.utils import auth
from src.utils.config import config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm the JWKS cache so the first authenticated request doesn't pay the
    # blocking key fetch on the event loop. Best-effort: if it fails, verification
    # falls back to a lazy fetch on first use.
    try:
        await asyncio.to_thread(auth.get_jwks_client().get_signing_keys)
    except Exception as e:
        logger.warning(f"JWKS pre-warm failed (will fetch lazily): {e}")
    yield
    # Clean up shared httpx clients on shutdown
    await embedding_provider.client.aclose()
    await llm_provider.client.aclose()
    await anthropic_provider.client.aclose()
    await reranker.aclose()  # Voyage rerank client (no-op if reranking never used)


app = FastAPI(
    title="Flame Fitness API",
    description="AI-powered workout logging with RAG chatbot",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "Flame Fitness API", "version": "0.1.0"}
