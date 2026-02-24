import json
import httpx
import logging
from collections.abc import AsyncGenerator

from src.utils.config import config

logger = logging.getLogger(__name__)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# Shared client — reuses TCP connections across calls.
# Cleaned up via FastAPI lifespan hook in app.py.
client = httpx.AsyncClient(timeout=60.0)


def _gemini_url(stream: bool = False) -> str:
    """Build the Gemini endpoint URL with API key."""
    model = config.LLM_MODEL
    if stream:
        return (
            f"{GEMINI_BASE_URL}/{model}:streamGenerateContent"
            f"?alt=sse&key={config.GOOGLE_API_KEY}"
        )
    return (
        f"{GEMINI_BASE_URL}/{model}:generateContent"
        f"?key={config.GOOGLE_API_KEY}"
    )


def _build_gemini_payload(
    prompt: str,
    system: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> dict:
    """Build the request body for Gemini."""
    payload: dict = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }

    if system:
        payload["system_instruction"] = {
            "parts": [{"text": system}],
        }

    return payload


async def generate(
    prompt: str,
    system: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    """Generate a full response (non-streaming).

    Used by the eval pipeline where we just need the final answer.
    """
    if config.LLM_PROVIDER != "google":
        raise NotImplementedError(f"LLM provider '{config.LLM_PROVIDER}' not yet supported")

    if not config.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not configured")

    response = await client.post(
        _gemini_url(stream=False),
        headers={"Content-Type": "application/json"},
        json=_build_gemini_payload(prompt, system, temperature, max_tokens),
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Gemini API error {response.status_code}: {response.text}"
        )

    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]

    usage = data.get("usageMetadata", {})
    logger.info(
        f"LLM generate: {usage.get('promptTokenCount', '?')} prompt tokens, "
        f"{usage.get('candidatesTokenCount', '?')} completion tokens"
    )

    return text


async def generate_stream(
    prompt: str,
    system: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> AsyncGenerator[str, None]:
    """Stream response tokens as they're generated.

    Used by the chat UI for real-time typing effect.
    Yields text chunks parsed from Gemini's SSE events.
    """
    if config.LLM_PROVIDER != "google":
        raise NotImplementedError(f"LLM provider '{config.LLM_PROVIDER}' not yet supported")

    if not config.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not configured")

    async with client.stream(
        "POST",
        _gemini_url(stream=True),
        headers={"Content-Type": "application/json"},
        json=_build_gemini_payload(prompt, system, temperature, max_tokens),
    ) as response:
        if response.status_code != 200:
            body = await response.aread()
            raise RuntimeError(
                f"Gemini API error {response.status_code}: {body.decode()}"
            )

        async for line in response.aiter_lines():
            # SSE format: "data: {json}\n\n"
            if not line.startswith("data: "):
                continue

            json_str = line[len("data: "):]
            try:
                chunk = json.loads(json_str)
            except json.JSONDecodeError:
                logger.debug(f"Skipped non-JSON SSE line: {json_str[:100]}")
                continue

            candidates = chunk.get("candidates", [])
            if not candidates:
                continue

            parts = candidates[0].get("content", {}).get("parts", [])
            if parts and "text" in parts[0]:
                yield parts[0]["text"]
