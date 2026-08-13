import json
import logging
from collections.abc import AsyncGenerator

import httpx

from src.utils.config import config

logger = logging.getLogger(__name__)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# Shared client — reuses TCP connections across calls.
# Cleaned up via FastAPI lifespan hook in app.py.
client = httpx.AsyncClient(timeout=60.0)


def _gemini_url(stream: bool = False, model: str | None = None) -> str:
    """Build the Gemini endpoint URL with API key."""
    model = model or config.LLM_MODEL
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
    messages: list[dict] | None = None,
    thinking_budget: int | None = None,
) -> dict:
    """Build the request body for Gemini.

    Args:
        prompt: The current user message (always appended as final turn).
        system: Optional system instruction (sent via system_instruction field).
        temperature: Sampling temperature.
        max_tokens: Max output tokens. NOTE: on Gemini 2.5 thinking models this
            budget is shared with hidden thinking tokens, which are spent first —
            a small max_tokens can be exhausted by thinking and truncate the visible
            output. Disable thinking (thinking_budget=0) for mechanical tasks.
        messages: Optional conversation history. Each dict has "role" ("user"|"assistant")
            and "content". Gemini requires strict user/model alternation — caller must
            ensure this.
        thinking_budget: If set, caps Gemini 2.5 thinking tokens via
            generationConfig.thinkingConfig.thinkingBudget. 0 disables thinking
            entirely (correct for non-reasoning tasks like query rewriting). None
            (default) leaves the model's default thinking behavior untouched.
    """
    # Build contents from history + current prompt
    if messages:
        role_map = {"assistant": "model", "user": "user"}
        contents = [
            {"role": role_map[msg["role"]], "parts": [{"text": msg["content"]}]}
            for msg in messages
        ]
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        # Warn if roles don't alternate (Gemini will 400)
        for i in range(1, len(contents)):
            if contents[i]["role"] == contents[i - 1]["role"]:
                logger.warning(
                    f"Non-alternating roles at position {i-1}/{i} "
                    f"({contents[i-1]['role']}/{contents[i]['role']}) — "
                    "Gemini may reject this request"
                )
                break
    else:
        contents = [{"role": "user", "parts": [{"text": prompt}]}]

    generation_config: dict = {
        "temperature": temperature,
        "maxOutputTokens": max_tokens,
    }
    if thinking_budget is not None:
        generation_config["thinkingConfig"] = {"thinkingBudget": thinking_budget}

    payload: dict = {
        "contents": contents,
        "generationConfig": generation_config,
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
    messages: list[dict] | None = None,
    model: str | None = None,
    thinking_budget: int | None = None,
) -> str:
    """Generate a full response (non-streaming).

    Used by the eval pipeline where we just need the final answer.

    `model` overrides `config.LLM_MODEL` for a single call — used by the eval
    judge dispatcher to select a specific Gemini variant. Cross-family judging
    (Claude) is routed to `anthropic_provider.generate` upstream, not here.

    `thinking_budget` caps Gemini 2.5 thinking tokens (0 disables thinking) — pass
    it for mechanical, non-reasoning calls so hidden thinking can't exhaust
    `max_tokens` and truncate the output.
    """
    if config.LLM_PROVIDER != "google":
        raise NotImplementedError(f"LLM provider '{config.LLM_PROVIDER}' not yet supported")

    if not config.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not configured")

    response = await client.post(
        _gemini_url(stream=False, model=model),
        headers={"Content-Type": "application/json"},
        json=_build_gemini_payload(
            prompt, system, temperature, max_tokens, messages, thinking_budget
        ),
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Gemini API error {response.status_code}: {response.text}"
        )

    data = response.json()
    parts = data["candidates"][0]["content"]["parts"]

    # Gemini 2.5 Flash includes thinking parts (thought: true) — skip them
    text_parts = [p["text"] for p in parts if "text" in p and not p.get("thought")]
    if not text_parts:
        # Fallback: take any part with text
        text_parts = [p["text"] for p in parts if "text" in p]
    text = "".join(text_parts)

    usage = data.get("usageMetadata", {})
    thoughts = usage.get("thoughtsTokenCount", 0)
    log_msg = (
        f"LLM generate: {usage.get('promptTokenCount', '?')} prompt tokens, "
        f"{usage.get('candidatesTokenCount', '?')} completion tokens"
    )
    if thoughts:
        log_msg += f" ({thoughts} thinking tokens)"
    logger.info(log_msg)

    return text


async def generate_stream(
    prompt: str,
    system: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    messages: list[dict] | None = None,
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
        json=_build_gemini_payload(prompt, system, temperature, max_tokens, messages),
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
            for part in parts:
                # Skip Gemini 2.5 thinking parts
                if part.get("thought"):
                    continue
                if "text" in part:
                    yield part["text"]
