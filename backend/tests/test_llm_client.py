"""Unit tests for the LLM client JSON handling and retry logic.

The Gemini network layer is replaced by the autouse ``mock_llm`` fixture in
conftest.py, so these tests run offline.
"""

import json

import pytest

from app.llm_client import AgentResponseError, _parse_json, call_agent


class TestParseJson:
    def test_plain_json(self):
        assert _parse_json('{"a": 1}') == {"a": 1}

    def test_fenced_json(self):
        assert _parse_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json("not json at all")


class TestCallAgent:
    async def test_returns_parsed_dict(self):
        result = await call_agent("You are the climate agent.", "What if test?")
        assert isinstance(result, dict)
        assert "analysis_text" in result
        assert "impact_score" in result
        assert "timeline_events" in result

    async def test_orchestrator_shape(self):
        result = await call_agent("orchestrator", "test scenario")
        assert isinstance(result, dict)
        assert "scenario" in result
        assert "divergence_year" in result

    async def test_retry_on_invalid_json(self, monkeypatch):
        from app import llm_client

        async def bad_request(label, system_prompt, user_content, t0):
            return "not json", "test-model"

        async def good_retry(**kwargs):
            return json.dumps(
                {"confidence_score": 90, "confidence_explanation": "ok", "risk_notes": []}
            )

        monkeypatch.setattr(llm_client, "_request_with_failover", bad_request)
        monkeypatch.setattr(llm_client, "_retry_request_with_failover", good_retry)

        result = await call_agent("critic", "{}")
        assert result["confidence_score"] == 90

    async def test_raises_after_failed_retry(self, monkeypatch):
        from app import llm_client

        async def bad_request(label, system_prompt, user_content, t0):
            return "not json", "test-model"

        async def bad_retry(**kwargs):
            return "still not json"

        monkeypatch.setattr(llm_client, "_request_with_failover", bad_request)
        monkeypatch.setattr(llm_client, "_retry_request_with_failover", bad_retry)

        with pytest.raises(AgentResponseError):
            await call_agent("critic", "{}")
