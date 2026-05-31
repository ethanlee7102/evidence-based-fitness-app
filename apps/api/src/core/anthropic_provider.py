"""Anthropic Messages API provider.

Minimal, eval-only counterpart to `llm_provider.generate` (Gemini). Used solely
by the RAG eval judge for cross-model validation (Run A: custom prompts judged
by Claude instead of Gemini). The chat pipeline never calls this.

Deliberately narrow: a single user turn + optional system prompt. No streaming,
no multi-turn `messages` history — the judge only ever sends one prompt. Mirrors
the Gemini `generate` signature so `judge.py` can dispatch between them by
model-ID prefix.
"""

import logging

import httpx

from src.utils.config import config

logger = logging.getLogger(__name__)

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

# Shared client — reuses TCP connections across calls.
# Cleaned up via FastAPI lifespan hook in app.py.
client = httpx.AsyncClient(timeout=60.0)


async def generate(
    prompt: str,
    system: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 8192,
    model: str = "claude-haiku-4-5",
) -> str:
    """Generate a full response from the Anthropic Messages API.

    Raises ValueError if the API key is unset. On a non-200 response, raises
    RuntimeError with the status code in the message — the eval judge's
    `_generate_with_retry` keys off that code (429 + >=500) to decide retries.
    """
    if not config.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    payload: dict = {
        "model": model,
        "max_tokens": max_tokens,  # required by the Messages API
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        payload["system"] = system

    response = await client.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": config.ANTHROPIC_API_KEY,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
        json=payload,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Anthropic API error {response.status_code}: {response.text}"
        )

    data = response.json()

    # content is a list of blocks; concatenate the text blocks.
    text = "".join(
        block["text"] for block in data.get("content", []) if block.get("type") == "text"
    )

    usage = data.get("usage", {})
    logger.info(
        f"Anthropic generate ({model}): "
        f"{usage.get('input_tokens', '?')} input tokens, "
        f"{usage.get('output_tokens', '?')} output tokens"
    )

    return text
