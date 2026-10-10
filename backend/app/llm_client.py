"""llm_client.py — Gemini integration for structured JSON agent responses.

This client uses Google Gemini exclusively (no mock or alternate providers).
The API key is validated lazily on first use, so the module can be imported in
environments without credentials (for example, test collection). If Gemini is
unavailable, calls fail fast with ``AgentResponseError``.
"""

import json
import logging
import time

from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_MODEL_CHAIN

logger = logging.getLogger(__name__)

_model: str = GEMINI_MODEL
_client: "genai.Client | None" = None


class AgentResponseError(Exception):
    """Raised when an agent call fails or returns unparseable JSON."""


def _ensure_configured() -> "genai.Client":
    """Validate the API key and lazily construct the Gemini client."""
    global _client
    if _client is not None:
        return _client
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_key_here":
        raise AgentResponseError(
            "GEMINI_API_KEY is not set. Configure it in the environment to run simulations."
        )
    _client = genai.Client(api_key=GEMINI_API_KEY)
    logger.info(
        "LLM client │ provider=GEMINI primary_model=%s fallback_models=%s",
        _model,
        list(GEMINI_MODEL_CHAIN[1:]),
    )
    return _client


# ── Internal helpers ───────────────────────────────────────────────────────────

def _parse_json(raw: str) -> dict:
    """Strip whitespace/fences then parse JSON; raises ``json.JSONDecodeError``."""
    # Remove optional markdown code fences that models sometimes emit.
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop opening fence (e.g. ```json) and closing fence.
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
    return json.loads(text)


def _is_retryable_model_error(exc: Exception) -> bool:
    """Return True when a model failure is likely transient or quota-related."""
    text = str(exc).lower()
    retryable_markers = (
        "429",
        "resource_exhausted",
        "quota",
        "rate limit",
        "too many requests",
        "temporarily unavailable",
        "service unavailable",
        "unavailable",
        "deadline exceeded",
        "internal",
    )
    return any(marker in text for marker in retryable_markers)


def _ordered_models(preferred_model: str | None = None) -> list[str]:
    """Return model order, optionally prioritizing a specific model first."""
    if not preferred_model:
        return list(GEMINI_MODEL_CHAIN)

    ordered = [preferred_model]
    for model_name in GEMINI_MODEL_CHAIN:
        if model_name != preferred_model:
            ordered.append(model_name)
    return ordered


def _require_text(response: "object") -> str:
    """Extract the text payload from a ``generate_content`` response."""
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Gemini returned an empty response (no text content).")
    return text


async def _generate_with_model(
    model_name: str,
    system_prompt: str,
    user_content: str,
) -> str:
    client = _ensure_configured()
    response = await client.aio.models.generate_content(
        model=model_name,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
        ),
    )
    return _require_text(response)


async def _retry_generate_with_model(
    model_name: str,
    system_prompt: str,
    user_content: str,
    raw_text: str,
) -> str:
    client = _ensure_configured()
    # Multi-turn correction: replay the original request + the invalid reply,
    # then ask for pure JSON.
    contents = [
        types.Content(role="user", parts=[types.Part(text=user_content)]),
        types.Content(role="model", parts=[types.Part(text=raw_text)]),
        types.Content(
            role="user",
            parts=[
                types.Part(
                    text=(
                        "Your previous response was not valid JSON. "
                        "Respond with ONLY the JSON object matching the requested schema."
                    )
                )
            ],
        ),
    ]
    response = await client.aio.models.generate_content(
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
        ),
    )
    return _require_text(response)


async def _request_with_failover(
    label: str,
    system_prompt: str,
    user_content: str,
    t0: float,
) -> tuple[str, str]:
    """Execute a generation request with automatic model failover."""
    _ensure_configured()
    last_exc: Exception | None = None
    models = _ordered_models()

    for idx, model_name in enumerate(models, start=1):
        logger.info(
            "call_agent │ agent=%-12s → Gemini model=%s attempt=%d/%d",
            label,
            model_name,
            idx,
            len(models),
        )
        try:
            raw_text = await _generate_with_model(model_name, system_prompt, user_content)
            elapsed_api = time.perf_counter() - t0
            logger.info(
                "call_agent │ agent=%-12s response received from Gemini model=%s elapsed=%.4fs",
                label,
                model_name,
                elapsed_api,
            )
            return raw_text, model_name
        except Exception as exc:
            last_exc = exc
            elapsed = time.perf_counter() - t0
            if idx < len(models) and _is_retryable_model_error(exc):
                logger.warning(
                    "call_agent │ agent=%-12s model=%s failed (retryable) elapsed=%.4fs error=%s; switching model",
                    label,
                    model_name,
                    elapsed,
                    exc,
                )
                continue

            logger.error(
                "call_agent │ agent=%-12s model=%s failed (non-retryable or last model) elapsed=%.4fs error=%s",
                label,
                model_name,
                elapsed,
                exc,
            )
            break

    raise AgentResponseError(f"Gemini API call failed across configured models: {last_exc}") from last_exc


async def _retry_request_with_failover(
    label: str,
    system_prompt: str,
    user_content: str,
    raw_text: str,
    preferred_model: str,
    t_retry: float,
) -> str:
    """Retry JSON-correction turn with automatic model failover."""
    _ensure_configured()
    last_exc: Exception | None = None
    models = _ordered_models(preferred_model)

    for idx, model_name in enumerate(models, start=1):
        logger.info(
            "call_agent │ agent=%-12s → RETRY Gemini model=%s attempt=%d/%d",
            label,
            model_name,
            idx,
            len(models),
        )
        try:
            retry_raw = await _retry_generate_with_model(model_name, system_prompt, user_content, raw_text)
            return retry_raw
        except Exception as exc:
            last_exc = exc
            elapsed = time.perf_counter() - t_retry
            if idx < len(models) and _is_retryable_model_error(exc):
                logger.warning(
                    "call_agent │ agent=%-12s retry model=%s failed (retryable) elapsed=%.4fs error=%s; switching model",
                    label,
                    model_name,
                    elapsed,
                    exc,
                )
                continue

            logger.error(
                "call_agent │ agent=%-12s retry model=%s failed (non-retryable or last model) elapsed=%.4fs error=%s",
                label,
                model_name,
                elapsed,
                exc,
            )
            break

    raise AgentResponseError(f"Retry API call failed across configured models: {last_exc}") from last_exc


def _agent_label(system_prompt: str) -> str:
    """Derive a short agent name from the system prompt for log messages.

    NOTE: 'participation-routing', 'critic', 'causal', and 'assumption' are
    checked before other agents because their prompts contain other agent
    names in their bodies.
    """
    p = system_prompt.lower()
    if "participation-routing" in p:
        return "router"
    if "lead counterfactual researcher" in p:
        return "qa"
    if "structured research debate" in p:
        return "debate"
    if "decomposer" in p:
        return "decomposer"
    if "orchestrator" in p or "parse" in p:
        return "orchestrator"
    if "causal" in p:
        return "causal"
    if "assumption" in p:
        return "assumption"
    if "fact-checking" in p or "grounding" in p:
        return "validator"
    if "critic" in p:
        return "critic"
    if "climate" in p:
        return "climate"
    if "historian" in p:
        return "historian"
    if "economist" in p:
        return "economist"
    if "technology" in p:
        return "technology"
    if "society" in p:
        return "society"
    if "political" in p:
        return "political"
    if "energy" in p:
        return "energy"
    if "healthcare" in p:
        return "healthcare"
    if "demographics" in p:
        return "demographics"
    return "agent"



# ── Public API ─────────────────────────────────────────────────────────────────

async def call_agent(system_prompt: str, user_content: str) -> dict:
    """Send a structured prompt to Gemini and return the parsed JSON response.

    Flow
    ----
    1. Identify the agent from the system prompt for logging.
    2. Send the request to Gemini asynchronously and attempt JSON parse.
    3. On ``JSONDecodeError``, send one follow-up turn asking for pure JSON.
    4. If the retry also fails, raise ``AgentResponseError``.

    All timing and outcomes are logged at INFO level; errors at ERROR level.
    """
    label = _agent_label(system_prompt)
    mode = "REAL"

    try:
        from app.telemetry import broadcast_log
    except ImportError:
        broadcast_log = None

    logger.info("─" * 64)
    logger.info(
        "call_agent │ agent=%-12s mode=%s", label, mode
    )

    if broadcast_log:
        import asyncio
        asyncio.create_task(broadcast_log(f"{label.capitalize()} │ Analyzing scenario context ({mode} mode)..."))

    t0 = time.perf_counter()

    try:
        raw_text, used_model = await _request_with_failover(label, system_prompt, user_content, t0)
        elapsed_api = time.perf_counter() - t0
        if broadcast_log:
            import asyncio

            asyncio.create_task(
                broadcast_log(f"{label.capitalize()} │ Response compiled successfully (elapsed={elapsed_api:.2f}s).")
            )
    except AgentResponseError:
        raise

    try:
        result = _parse_json(raw_text)
        elapsed = time.perf_counter() - t0
        logger.info(
            "call_agent │ agent=%-12s JSON parsed OK  keys=%s  elapsed=%.4fs",
            label, list(result.keys()), elapsed,
        )
        return result
    except json.JSONDecodeError:
        logger.warning(
            "call_agent │ agent=%-12s JSON parse FAILED on first attempt "
            "— retrying with correction prompt.  "
            "Raw snippet: %.120r",
            label,
            raw_text,
        )

    # Retry: ask the model to return pure JSON ─────────────────────────────────
    logger.info(
        "call_agent │ agent=%-12s → RETRY (correction turn starting model=%s)",
        label,
        used_model,
    )
    t_retry = time.perf_counter()

    try:
        retry_raw = await _retry_request_with_failover(
            label=label,
            system_prompt=system_prompt,
            user_content=user_content,
            raw_text=raw_text,
            preferred_model=used_model,
            t_retry=t_retry,
        )
    except AgentResponseError:
        raise

    elapsed_retry = time.perf_counter() - t_retry
    logger.info(
        "call_agent │ agent=%-12s retry response received  "
        "elapsed=%.4fs",
        label,
        elapsed_retry,
    )

    try:
        result = _parse_json(retry_raw)
        elapsed_total = time.perf_counter() - t0
        logger.info(
            "call_agent │ agent=%-12s JSON parsed OK after retry  "
            "keys=%s  total_elapsed=%.4fs",
            label, list(result.keys()), elapsed_total,
        )
        return result
    except json.JSONDecodeError as exc:
        snippet = retry_raw[:200]
        elapsed_total = time.perf_counter() - t0
        logger.error(
            "call_agent │ agent=%-12s JSON parse FAILED after retry  "
            "total_elapsed=%.4fs  raw_snippet=%.200r",
            label, elapsed_total, snippet,
        )
        raise AgentResponseError(
            f"Failed to parse agent response as JSON after retry. "
            f"Raw response snippet: {snippet}"
        ) from exc
