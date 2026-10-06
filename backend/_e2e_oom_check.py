"""Temporary E2E check: full pipeline via mocked LLM (deleted after use)."""
import asyncio
import json
import tracemalloc

from tests.conftest import _canned_for_label


async def main():
    from app import llm_client

    async def fake_request(label, system_prompt, user_content, t0):
        return json.dumps(_canned_for_label(llm_client._agent_label(system_prompt))), "test-model"

    async def fake_retry(*args, **kwargs):
        sp = kwargs.get("system_prompt", args[1] if len(args) > 1 else "")
        return json.dumps(_canned_for_label(llm_client._agent_label(sp)))

    llm_client._request_with_failover = fake_request
    llm_client._retry_request_with_failover = fake_retry

    # Block real network RAG fetches — measure orchestration memory only.
    from app.rag import retrieval_service
    async def fake_retrieve(self, q, domain, n_results=2):
        return ("CTX", [f"{domain} doc"], [domain])
    retrieval_service.RetrievalService.retrieve = fake_retrieve

    tracemalloc.start()
    from app.orchestrator import run_simulation_graph
    state = await run_simulation_graph("e2e-check", "What if Rome never fell?")
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert state.get("error") is None, state.get("error")
    rep = state["final_report"]
    print("status=OK agents=", len(rep.agent_outputs),
          "timeline=", len(rep.alternate_timeline),
          "confidence=", rep.confidence_score)
    print(f"python_alloc_current={current/1e6:.1f}MB peak={peak/1e6:.1f}MB")


asyncio.run(main())
