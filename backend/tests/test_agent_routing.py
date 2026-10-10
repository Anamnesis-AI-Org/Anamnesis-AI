"""Tests for LLM-based agent participation routing.

The router asks the LLM which domains may be affected by a scenario and
must fall back to keyword matching whenever the LLM call fails or returns
unusable data. Historian always participates.
"""

import pytest

import app.orchestrator as orch
from app.orchestrator import _match_agents, _route_agents


def _fake_router(payload):
    async def _call(system_prompt, user_content):
        assert "participation-routing" in system_prompt.lower()
        if isinstance(payload, Exception):
            raise payload
        return payload

    return _call


@pytest.mark.asyncio
class TestRouteAgents:
    async def test_llm_domains_used_and_ordered_canonically(self, monkeypatch):
        monkeypatch.setattr(
            orch,
            "call_agent",
            _fake_router(
                {
                    "domains": [
                        "technology",
                        "society",
                        "political",
                        "energy",
                        "economist",
                        "historian",
                    ]
                }
            ),
        )
        matched = await _route_agents("What if Newton ate that apple?")
        assert matched == [
            "historian",
            "economist",
            "technology",
            "society",
            "political",
            "energy",
        ]

    async def test_alias_names_normalized(self, monkeypatch):
        monkeypatch.setattr(
            orch, "call_agent", _fake_router({"domains": ["economy", "politics", "tech"]})
        )
        matched = await _route_agents("scenario text")
        assert matched == ["historian", "economist", "technology", "political"]

    async def test_historian_forced_even_if_llm_omits_it(self, monkeypatch):
        monkeypatch.setattr(orch, "call_agent", _fake_router({"domains": ["climate"]}))
        matched = await _route_agents("scenario text")
        assert matched == ["historian", "climate"]

    async def test_unknown_domain_names_dropped(self, monkeypatch):
        monkeypatch.setattr(
            orch, "call_agent", _fake_router({"domains": ["wizard", "economist"]})
        )
        matched = await _route_agents("scenario text")
        assert matched == ["historian", "economist"]

    async def test_single_string_domains_accepted(self, monkeypatch):
        monkeypatch.setattr(orch, "call_agent", _fake_router({"domains": "healthcare"}))
        matched = await _route_agents("scenario text")
        assert matched == ["historian", "healthcare"]

    async def test_llm_failure_falls_back_to_keywords(self, monkeypatch):
        monkeypatch.setattr(orch, "call_agent", _fake_router(RuntimeError("api down")))
        text = "What if GDP growth collapsed after 1990?"
        matched = await _route_agents(text)
        assert matched == _match_agents(text)
        assert "economist" in matched

    async def test_unusable_payload_falls_back_to_keywords(self, monkeypatch):
        monkeypatch.setattr(
            orch, "call_agent", _fake_router({"scenario": "no domains key"})
        )
        text = "What if global warming accelerated after 2000?"
        matched = await _route_agents(text)
        assert "climate" in matched

    async def test_empty_domain_list_falls_back(self, monkeypatch):
        monkeypatch.setattr(orch, "call_agent", _fake_router({"domains": []}))
        text = "What if artificial intelligence arrived in 1980?"
        matched = await _route_agents(text)
        assert "technology" in matched
