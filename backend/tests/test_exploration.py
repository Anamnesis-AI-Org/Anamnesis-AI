import pytest
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Scenario, FinalReport, AgentOutput
from app.exploration.qa_engine import answer_scenario_question
from app.exploration.debate_engine import run_agent_debate
from app.exploration.parameter_adjuster import adjust_scenario_parameters

@pytest.fixture
async def seeded_scenario():
    """Seeds a complete done scenario with final report and agent outputs."""
    async with AsyncSessionLocal() as session:
        scenario = Scenario(
            raw_input="What if the Sahara became a forest?",
            status="done"
        )
        session.add(scenario)
        await session.commit()
        await session.refresh(scenario)
        scenario_id = scenario.id

        # Add agent outputs
        historian_out = AgentOutput(
            scenario_id=scenario_id,
            agent_name="historian",
            analysis_text="Green Sahara timeline coordinates.",
            structured_data={
                "timeline_events": [
                    {"year": 3000, "event": "Monsoons shift north."}
                ]
            }
        )
        economist_out = AgentOutput(
            scenario_id=scenario_id,
            agent_name="economist",
            analysis_text="Green Sahara trade networks grow.",
            structured_data={
                "timeline_events": [],
                "impact_score": 80
            }
        )
        session.add(historian_out)
        session.add(economist_out)

        # Add final report
        report = FinalReport(
            scenario_id=scenario_id,
            scenario_summary="Saharan rainforest scenario summary.",
            alternate_timeline=[
                {"year": 3000, "event": "Monsoons shift north.", "source_agent": "historian"}
            ],
            impact_dashboard={"economy": 80, "technology": 60, "society": 70, "politics": 75, "climate": 95},
            confidence_score=85,
            confidence_explanation="Consistent climate trajectory.",
            risk_notes=["Amazon fertilization might decrease due to dust reduction."],
            sources_consulted=["African Humid Period Studies"],
            retrieved_documents=["Core samples Mega Lake Chad"],
            causal_graph=[],
            assumptions=[],
            agent_confidences=[],
            grounding_validations=[],
            uncertainty_score=2.5,
            calibration_score=90
        )
        session.add(report)
        await session.commit()

        yield scenario_id

        # Clean up database after test runs
        from sqlalchemy import delete
        await session.execute(delete(AgentOutput).where(AgentOutput.scenario_id == scenario_id))
        await session.execute(delete(FinalReport).where(FinalReport.scenario_id == scenario_id))
        await session.execute(delete(Scenario).where(Scenario.id == scenario_id))
        await session.commit()


class TestExplorationQA:
    async def test_answer_scenario_question_success(self, seeded_scenario):
        async with AsyncSessionLocal() as db:
            result = await answer_scenario_question(
                db, 
                seeded_scenario, 
                "How does the Sahara forest affect rainfall?"
            )
            assert "answer" in result
            assert "citations" in result
            assert len(result["citations"]) > 0

    async def test_ask_endpoint_success(self, client, seeded_scenario):
        resp = await client.post(
            f"/api/scenarios/{seeded_scenario}/ask",
            json={"question": "What happens in year 3000?"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "citations" in data


class TestExplorationDebate:
    async def test_run_agent_debate_success(self, seeded_scenario):
        async with AsyncSessionLocal() as db:
            result = await run_agent_debate(
                db,
                seeded_scenario,
                "the speed of reforestation",
                "historian",
                "economist"
            )
            assert "rounds" in result
            assert "consensus" in result
            assert len(result["rounds"]) >= 2

    async def test_debate_endpoint_success(self, client, seeded_scenario):
        resp = await client.post(
            f"/api/scenarios/{seeded_scenario}/debate",
            json={
                "topic": "economic impacts of greening",
                "agent_a": "economist",
                "agent_b": "historian"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "rounds" in data
        assert "consensus" in data


class TestExplorationParameterAdjustment:
    async def test_adjust_scenario_parameters_success(self, seeded_scenario):
        async with AsyncSessionLocal() as db:
            result = await adjust_scenario_parameters(
                db,
                seeded_scenario,
                {"resource_abundance": 70, "transition_speed": 30}
            )
            assert "impact_dashboard" in result
            assert "confidence_score" in result
            assert "uncertainty_score" in result

            # Verify that db record was updated
            report_query = await db.execute(
                select(FinalReport).where(FinalReport.scenario_id == seeded_scenario)
            )
            updated_report = report_query.scalar_one_or_none()
            assert updated_report is not None
            assert updated_report.uncertainty_score is not None

    async def test_adjust_actually_reruns_affected_agents(self, seeded_scenario):
        """Affected agents must be genuinely re-run, not silently fall back.

        Regression guard: the adjuster used to pass the SQLAlchemy AgentOutput
        row where the agent runners expected a HistorianOutput, raising
        ``AttributeError: 'AgentOutput' object has no attribute 'model_dump_json'``.
        That error was swallowed by the per-agent try/except, so adjustments
        returned HTTP 200 while leaving every agent's output untouched.
        """
        async with AsyncSessionLocal() as db:
            result = await adjust_scenario_parameters(
                db, seeded_scenario, {"resource_abundance": 80}
            )

        scores = {a["agent_name"]: a["impact_score"] for a in result["agent_outputs"]}
        # The seeded DB score for the economist is 80 (stale). A genuine re-run
        # produces the canned agent score, proving the runner was invoked.
        assert scores["economist"] != 80
        assert scores["economist"] == 40

    async def test_adjust_endpoint_success(self, client, seeded_scenario):
        resp = await client.post(
            f"/api/scenarios/{seeded_scenario}/adjust",
            json={
                "adjustments": {
                    "resource_abundance": 80,
                    "government_control": 40
                }
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "impact_dashboard" in data
        assert "confidence_score" in data
