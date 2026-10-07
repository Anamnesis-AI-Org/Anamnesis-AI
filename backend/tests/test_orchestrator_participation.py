"""Tests for conditional agent participation in the orchestration pipeline.

Only domain agents whose keywords match the scenario text should execute;
historian always runs and critic converges whatever ran.
"""

import pytest

from app.orchestrator import _match_agents, run_simulation_graph


class TestMatchAgents:
    def test_economy_keywords_select_economist(self):
        matched = _match_agents("What if GDP growth collapsed after 1990?")
        assert "economist" in matched

    def test_climate_keywords_select_climate(self):
        matched = _match_agents("What if global warming accelerated after 2000?")
        assert "climate" in matched

    def test_technology_keywords_select_technology(self):
        matched = _match_agents("What if artificial intelligence arrived in 1980?")
        assert "technology" in matched

    def test_historian_always_selected(self):
        matched = _match_agents("What if the moon was made of cheese?")
        assert "historian" in matched

    def test_unrelated_scenario_selects_only_historian(self):
        matched = _match_agents("What if the moon was made of cheese?")
        # No domain keyword matched -> only historian participates.
        assert matched == ["historian"]

    def test_economy_and_climate_both_selected(self):
        matched = _match_agents(
            "How would GDP and climate change if emissions kept rising?"
        )
        assert "economist" in matched
        assert "climate" in matched


@pytest.mark.asyncio
class TestRunSimulationGraph:
    async def test_full_pipeline_conditional_participation(self):
        state = await run_simulation_graph(
            "test-cond",
            "What if GDP growth collapsed after 1990?",
        )
        assert state.get("error") is None
        assert state["final_report"] is not None
        # Matched agents ran ...
        assert state["historian_output"] is not None
        assert state["economist_output"] is not None
        # ... unmatched domain agents did not.
        assert state["climate_output"] is None
        assert state["healthcare_output"] is None
        assert state["demographics_output"] is None
        # Participation recorded in state for downstream consumers.
        assert "economist" in state["matched_agents"]
        assert "climate" not in state["matched_agents"]
        # Report only contains summaries for agents that ran.
        names = {a.agent_name for a in state["final_report"].agent_outputs}
        assert "economist" in names
        assert "climate" not in names

    async def test_historian_only_scenario(self):
        state = await run_simulation_graph(
            "test-hist-only",
            "What if the moon was made of cheese?",
        )
        assert state.get("error") is None
        assert state["final_report"] is not None
        assert state["historian_output"] is not None
        assert state["economist_output"] is None
        assert state["matched_agents"] == ["historian"]
        names = {a.agent_name for a in state["final_report"].agent_outputs}
        assert names == {"historian"}
        # Dashboard defaults to 0 for agents that never ran.
        assert state["final_report"].impact_dashboard.economy == 0
