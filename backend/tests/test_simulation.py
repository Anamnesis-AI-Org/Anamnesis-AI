import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import UnifiedTimelineEvent, AgentOutputSummary, TimelineEvent, BranchRequest
from app.simulation.causal_graph import run_causal_modeling
from app.simulation.assumption_tracker import run_assumption_extraction
from app.simulation.branching_engine import create_branch_context
from app.models import Scenario, FinalReport
from app.database import AsyncSessionLocal


class TestCausalModeling:
    async def test_run_causal_modeling_empty(self):
        links = await run_causal_modeling([])
        assert links == []

    async def test_run_causal_modeling_success(self):
        events = [
            UnifiedTimelineEvent(id="ev-0", year=1990, event="Divergence occurs", source_agent="historian"),
            UnifiedTimelineEvent(id="ev-1", year=1995, event="Economic changes", source_agent="economist"),
            UnifiedTimelineEvent(id="ev-2", year=2000, event="Tech growth", source_agent="technology")
        ]
        links = await run_causal_modeling(events)
        assert isinstance(links, list)
        assert len(links) > 0
        for link in links:
            assert link.source in ["ev-0", "ev-1", "ev-2"]
            assert link.target in ["ev-0", "ev-1", "ev-2"]
            assert link.description

    async def test_run_causal_modeling_invalid_target_filtered(self):
        events = [
            UnifiedTimelineEvent(id="different-ev-0", year=1990, event="Divergence", source_agent="historian"),
        ]
        # Since the mock returns links between ev-0 and ev-1, and neither matches "different-ev-0",
        # they should all be filtered out, returning an empty list.
        links = await run_causal_modeling(events)
        assert links == []


class TestAssumptionExtraction:
    async def test_run_assumption_extraction_empty(self):
        assumptions = await run_assumption_extraction([])
        assert assumptions == []

    async def test_run_assumption_extraction_success(self):
        outputs = [
            AgentOutputSummary(
                agent_name="historian",
                analysis_text="Some text",
                timeline_events=[TimelineEvent(year=1990, event="Event 1")]
            )
        ]
        assumptions = await run_assumption_extraction(outputs)
        assert isinstance(assumptions, list)
        assert len(assumptions) > 0
        for assumption in assumptions:
            assert assumption.agent_name
            assert assumption.assumption
            assert assumption.impact_level in ["high", "medium", "low"]


class TestBranchingEngine:
    @pytest.fixture
    async def db_session(self):
        """Provide a fresh in-memory SQLite database session for each test."""
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from app.database import Base
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", echo=False
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session

        await engine.dispose()

    async def test_create_branch_context_not_found(self, db_session: AsyncSession):
        with pytest.raises(ValueError, match="Final report not found"):
            await create_branch_context(db_session, "nonexistent-scenario", "ev-0")

    async def test_create_branch_context_success(self, db_session: AsyncSession):
        # Create a parent scenario
        parent_scenario = Scenario(
            id="parent-sc-1",
            raw_input="What if humans had wings?",
            status="done"
        )
        db_session.add(parent_scenario)
        
        # Create final report for the parent scenario
        parent_report = FinalReport(
            scenario_id="parent-sc-1",
            scenario_summary="Humans with wings summary",
            alternate_timeline=[
                {"id": "ev-0", "year": 1990, "event": "Divergence happens", "source_agent": "historian", "parent_ids": []},
                {"id": "ev-1", "year": 1995, "event": "Wings standard size increases", "source_agent": "historian", "parent_ids": ["ev-0"]},
                {"id": "ev-2", "year": 2000, "event": "Flying lanes regulated", "source_agent": "historian", "parent_ids": ["ev-1"]},
            ],
            impact_dashboard={"economy": 10, "technology": 20, "society": 30, "politics": 0, "climate": 0},
            confidence_score=90,
            confidence_explanation="Consistent",
            risk_notes=[],
            sources_consulted=[],
            retrieved_documents=[],
            causal_graph=[],
            assumptions=[]
        )
        db_session.add(parent_report)
        await db_session.commit()

        # Call create_branch_context
        # Branching at ev-1 (year 1995) should lock events strictly before 1995 (i.e. ev-0, year 1990)
        target_year, pre_divergence_events, parent_raw_input = await create_branch_context(
            db_session, "parent-sc-1", "ev-1"
        )
        
        assert target_year == 1995
        assert len(pre_divergence_events) == 1
        assert pre_divergence_events[0]["id"] == "ev-0"
        assert parent_raw_input == "What if humans had wings?"

        # Test divergent event ID not found
        with pytest.raises(ValueError, match="Divergent event ID non-existent-ev not found"):
            await create_branch_context(db_session, "parent-sc-1", "non-existent-ev")

        # Clean up
        await db_session.delete(parent_report)
        await db_session.delete(parent_scenario)
        await db_session.commit()


class TestAPIBranching:
    async def test_api_branch_scenario_success(self, client):
        # Register a parent scenario and report in db
        async with AsyncSessionLocal() as db_session:
            from app.models import AgentOutput
            # Defensive: clear leftovers from a previously interrupted run.
            for model, key in ((FinalReport, "api-parent-sc"),):
                existing = await db_session.execute(
                    select(model).where(model.scenario_id == "api-parent-sc")
                )
                for row in existing.scalars().all():
                    await db_session.delete(row)
            existing_agents = await db_session.execute(
                select(AgentOutput).where(AgentOutput.scenario_id == "api-parent-sc")
            )
            for row in existing_agents.scalars().all():
                await db_session.delete(row)
            existing_sc = await db_session.get(Scenario, "api-parent-sc")
            if existing_sc:
                await db_session.delete(existing_sc)
            await db_session.commit()

            parent_scenario = Scenario(
                id="api-parent-sc",
                raw_input="What if Rome never fell?",
                status="done"
            )
            db_session.add(parent_scenario)
            
            parent_report = FinalReport(
                scenario_id="api-parent-sc",
                scenario_summary="Roman empire continues",
                alternate_timeline=[
                    {"id": "ev-0", "year": 1990, "event": "Pax Romana stabilized", "source_agent": "historian", "parent_ids": []},
                    {"id": "ev-1", "year": 1995, "event": "Roman roads digitized", "source_agent": "historian", "parent_ids": ["ev-0"]},
                ],
                impact_dashboard={"economy": 50, "technology": 50, "society": 50, "politics": 50, "climate": 50},
                confidence_score=95,
                confidence_explanation="Highly plausible",
                risk_notes=[],
                sources_consulted=[],
                retrieved_documents=[],
                causal_graph=[],
                assumptions=[]
            )
            db_session.add(parent_report)
            await db_session.commit()

        # Branch from ev-1 (year 1995)
        resp = await client.post(
            "/api/scenarios/api-parent-sc/branch",
            json={
                "divergent_event_id": "ev-1",
                "alternative_event": "Roman roads are electrified instead of digitized"
            }
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "scenario_id" in data
        child_scenario_id = data["scenario_id"]

        # Verify child scenario details
        async with AsyncSessionLocal() as db_session:
            child_scenario = await db_session.get(Scenario, child_scenario_id)
            assert child_scenario is not None
            assert child_scenario.raw_input == "Branch of 'What if Rome never fell?' at year 1995 where: Roman roads are electrified instead of digitized"
            assert child_scenario.status in ("pending", "running", "done")

            # Clean up (delete child rows; the branch endpoint queues a background
            # simulation that also writes child AgentOutput/FinalReport rows).
            from app.models import AgentOutput as _AgentOutput
            child_agent_rows = await db_session.execute(
                select(_AgentOutput).where(_AgentOutput.scenario_id == child_scenario_id)
            )
            for row in child_agent_rows.scalars().all():
                await db_session.delete(row)
            child_report_rows = await db_session.execute(
                select(FinalReport).where(FinalReport.scenario_id == child_scenario_id)
            )
            child_report = child_report_rows.scalar_one_or_none()
            if child_report:
                await db_session.delete(child_report)
            await db_session.delete(child_scenario)

            result = await db_session.execute(
                select(FinalReport).where(FinalReport.scenario_id == "api-parent-sc")
            )
            p_rep_obj = result.scalar_one_or_none()
            if p_rep_obj:
                await db_session.delete(p_rep_obj)
            p_agents = await db_session.execute(
                select(_AgentOutput).where(_AgentOutput.scenario_id == "api-parent-sc")
            )
            for row in p_agents.scalars().all():
                await db_session.delete(row)
            p_sc = await db_session.get(Scenario, "api-parent-sc")
            if p_sc:
                await db_session.delete(p_sc)
            await db_session.commit()

    async def test_api_branch_scenario_not_found(self, client):
        resp = await client.post(
            "/api/scenarios/nonexistent-parent/branch",
            json={
                "divergent_event_id": "ev-1",
                "alternative_event": "Alternative history"
            }
        )
        assert resp.status_code == 404
        assert "Final report not found" in resp.json()["detail"]
