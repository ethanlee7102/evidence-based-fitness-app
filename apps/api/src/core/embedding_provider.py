import asyncio
import logging

import httpx

from src.utils.config import config

RETRYABLE_STATUSES = {429, 500, 503}
MAX_RETRIES = 3
BACKOFF_DELAYS = [1, 2, 4]  # seconds

logger = logging.getLogger(__name__)

VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"

# Shared client — reuses TCP connections across calls.
# Cleaned up via FastAPI lifespan hook in app.py.
client = httpx.AsyncClient(timeout=30.0)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts for storage (ingestion).

    Uses input_type="document" so Voyage prepends its document prompt.
    Auto-batches into groups of EMBEDDING_BATCH_SIZE to stay under
    the 120K token limit for voyage-4-large.
    """
    if not texts:
        return []

    if not config.VOYAGE_API_KEY:
        raise ValueError("VOYAGE_API_KEY not configured")

    all_embeddings: list[list[float]] = [[] for _ in texts]
    batch_size = config.EMBEDDING_BATCH_SIZE

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        batch_num = i // batch_size + 1

        # Retry loop with exponential backoff for transient errors
        for attempt in range(MAX_RETRIES):
            response = await client.post(
                VOYAGE_API_URL,
                headers={
                    "Authorization": f"Bearer {config.VOYAGE_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": batch,
                    "model": config.EMBEDDING_MODEL,
                    "input_type": "document",
                },
            )

            if response.status_code == 200:
                break

            if response.status_code in RETRYABLE_STATUSES and attempt < MAX_RETRIES - 1:
                delay = BACKOFF_DELAYS[attempt]
                logger.warning(
                    f"Voyage API {response.status_code} on batch {batch_num}, "
                    f"retrying {attempt + 1}/{MAX_RETRIES} in {delay}s..."
                )
                await asyncio.sleep(delay)
                continue

            raise RuntimeError(
                f"Voyage API error {response.status_code}: {response.text}"
            )

        data = response.json()
        total_tokens = data.get("usage", {}).get("total_tokens", 0)
        logger.info(
            f"Embedded batch {batch_num} "
            f"({len(batch)} texts, {total_tokens} tokens)"
        )

        for item in data["data"]:
            all_embeddings[i + item["index"]] = item["embedding"]

    return all_embeddings


async def embed_query(query: str) -> list[float]:
    """Embed a single query for retrieval (search).

    Uses input_type="query" so Voyage prepends its query prompt.
    """
    if not config.VOYAGE_API_KEY:
        raise ValueError("VOYAGE_API_KEY not configured")

    response = await client.post(
        VOYAGE_API_URL,
        headers={
            "Authorization": f"Bearer {config.VOYAGE_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "input": [query],
            "model": config.EMBEDDING_MODEL,
            "input_type": "query",
        },
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Voyage API error {response.status_code}: {response.text}"
        )

    data = response.json()
    total_tokens = data.get("usage", {}).get("total_tokens", 0)
    logger.info(f"Embedded query ({total_tokens} tokens)")

    return data["data"][0]["embedding"]
