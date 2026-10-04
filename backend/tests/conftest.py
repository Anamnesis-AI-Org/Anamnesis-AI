"""Shared fixtures for Anamnesis-AI backend tests.

The ``mock_llm`` autouse fixture replaces the Gemini network layer with
deterministic canned JSON so the full multi-agent pipeline can be exercised
offline (no API key or network required).
"""

import json
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


# ── Deterministic canned agent responses (keyed by agent label) ────────────────

_DOMAIN_AGENTS = (
    "economist",
    "technology",
    "society",
    "climate",
    "political",
    "energy",
    "healthcare",
    "demographics",
)

_CANNED: dict[str, dict] = {
    "orchestrator": {
        "scenario": "Test alternate history scenario",
        "divergence_year": 2000,
        "focus_domains": ["economy", "technology", "society", "politics"],
        "time_horizon": 2030,
    },
    "historian": {
        "analysis_text": "Baseline context and the immediate divergence trajectory.",
        "timeline_events": [
            {"year": 2001, "event": "The divergence point takes effect."},
            {"year": 2010, "event": "A second milestone unfolds."},
        ],
    },
    "critic": {
        "confidence_score": 85,
        "confidence_explanation": "The timeline is internally consistent.",
        "risk_notes": ["Minor variance noted between domains."],
        "agent_confidences": [
            {
                "agent_name": "historian",
                "confidence_score": 85,
                "explanation": "Pacing matches expectations.",
            }
        ],
    },
    "causal": {
        "causal_links": [
            {
                "source": "ev-0",
                "target": "ev-1",
                "description": "The first event enabled the second.",
            }
        ]
    },
    "assumption": {
        "assumptions": [
            {
                "agent_name": "historian",
                "assumption": "Assumes continued institutional continuity.",
                "impact_level": "high",
            }
        ]
    },
    "validator": {
        "grounding_score": 92,
        "unsupported_claims": [],
        "explanation": "The analysis is well supported by the retrieved sources.",
    },
    "decomposer": {
        "wikipedia": "roman empire history",
        "worldbank": "gdp economic indicators",
        "un_data": "development indicators",
        "nasa": "climate anomalies",
        "noaa": "precipitation records",
        "arxiv": "counterfactual simulation model",
    },
    "qa": {
        "answer": "A detailed analytical answer.",
        "citations": ["Simulation report timeline"],
    },
    "debate": {
        "rounds": [
            {"round_num": 1, "agent_name": "a", "argument": "Opening argument from A."},
            {"round_num": 1, "agent_name": "b", "argument": "Opening argument from B."},
            {"round_num": 2, "agent_name": "a", "argument": "Rebuttal from A."},
            {"round_num": 2, "agent_name": "b", "argument": "Concluding summary from B."},
        ],
        "consensus": "The critic synthesizes a consensus.",
    },
}


def _canned_for_label(label: str) -> dict:
    if label in _DOMAIN_AGENTS:
        return {
            "analysis_text": f"{label} analysis of the scenario.",
            "timeline_events": [{"year": 2005, "event": f"{label} milestone."}],
            "impact_score": 40,
        }
    return _CANNED.get(label, _CANNED["orchestrator"])


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    """Replace the Gemini network layer with deterministic canned JSON."""
    from app import llm_client

    async def fake_request(label, system_prompt, user_content, t0):
        resolved = llm_client._agent_label(system_prompt)
        return json.dumps(_canned_for_label(resolved)), "test-model"

    async def fake_retry(*args, **kwargs):
        system_prompt = kwargs.get("system_prompt", args[1] if len(args) > 1 else "")
        resolved = llm_client._agent_label(system_prompt)
        return json.dumps(_canned_for_label(resolved))

    monkeypatch.setattr(llm_client, "_request_with_failover", fake_request)
    monkeypatch.setattr(llm_client, "_retry_request_with_failover", fake_retry)
    yield


@pytest.fixture
async def client():
    """Provide an async HTTP client wired to the FastAPI app."""
    @asynccontextmanager
    async def lifespan_app():
        async with app.router.lifespan_context(app):
            yield

    async with lifespan_app():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
