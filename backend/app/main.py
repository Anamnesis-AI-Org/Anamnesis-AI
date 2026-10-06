"""
FastAPI backend for Anamnesis-AI.

This module is the entrypoint for the multi-agent simulation platform. It exposes
the HTTP and WebSocket API, triggers the LangGraph orchestrator in the
background, and monitors the lifecycle of the domain agents as they run.

Key design patterns:
1. Agent orchestration: background tasks manage long-running multi-agent runs.
2. Realtime telemetry: a WebSocket channel streams live agent progress to the UI.
"""
import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import CORS_ORIGINS, MAX_CONCURRENT_SIMULATIONS, MAX_INPUT_LENGTH
from app.database import AsyncSessionLocal, create_tables, db_health_check, get_db
from app.logging_config import setup_logging
from app.models import AgentOutput, FinalReport, Scenario
from app.orchestrator import run_simulation_graph
from app.schemas import (
    FinalReportSchema,
    ScenarioCreateRequest,
    ScenarioCreateResponse,
    ScenarioStatusResponse,
    UnifiedTimelineEvent,
    BranchRequest,
    AskRequest,
    DebateRequest,
    AdjustRequest,
)
from app.telemetry import register_websocket, unregister_websocket
from app.simulation.branching_engine import create_branch_context
from app.exploration.qa_engine import answer_scenario_question
from app.exploration.debate_engine import run_agent_debate
from app.exploration.parameter_adjuster import adjust_scenario_parameters

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    # Skip Alembic, run automatic SQLAlchemy table creation on startup
    await create_tables()
    # Self-healing database migration for Phase 4 & 5 columns
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text("ALTER TABLE final_report ADD COLUMN causal_graph JSON"))
            await session.commit()
        except Exception as e:
            logger.info("Self-healing migration causal_graph ignored/failed: %s", e)
        try:
            await session.execute(text("ALTER TABLE final_report ADD COLUMN assumptions JSON"))
            await session.commit()
        except Exception as e:
            logger.info("Self-healing migration assumptions ignored/failed: %s", e)
        try:
            await session.execute(text("ALTER TABLE final_report ADD COLUMN agent_confidences JSON"))
            await session.commit()
        except Exception as e:
            logger.info("Self-healing migration agent_confidences ignored/failed: %s", e)
        try:
            await session.execute(text("ALTER TABLE final_report ADD COLUMN grounding_validations JSON"))
            await session.commit()
        except Exception as e:
            logger.info("Self-healing migration grounding_validations ignored/failed: %s", e)
        try:
            await session.execute(text("ALTER TABLE final_report ADD COLUMN uncertainty_score REAL"))
            await session.commit()
        except Exception as e:
            logger.info("Self-healing migration uncertainty_score ignored/failed: %s", e)
        try:
            await session.execute(text("ALTER TABLE final_report ADD COLUMN calibration_score INTEGER"))
            await session.commit()
        except Exception as e:
            logger.info("Self-healing migration calibration_score ignored/failed: %s", e)
    logger.info("Database tables created / verified")
    yield


app = FastAPI(lifespan=lifespan)


def _db_unavailable_exception() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail="Database unavailable. Check DATABASE_URL and ensure PostgreSQL is running.",
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def health_check() -> dict[str, str]:
    db_ok = await db_health_check()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
    }


@app.websocket("/api/scenarios/{scenario_id}/ws")
async def websocket_telemetry(websocket: WebSocket, scenario_id: str):
    await websocket.accept()
    await register_websocket(scenario_id, websocket)
    try:
        while True:
            # Maintain connection, client will only read
            await websocket.receive_text()
    except WebSocketDisconnect:
        unregister_websocket(scenario_id, websocket)
    except Exception:
        unregister_websocket(scenario_id, websocket)


@app.post("/api/scenarios", response_model=ScenarioCreateResponse, status_code=201)
async def create_scenario(
    request: ScenarioCreateRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
) -> ScenarioCreateResponse:
    """
    This endpoint initiates the multi-agent simulation. It takes a "What-If" scenario,
    saves it to the database, and kicks off the background orchestrator which coordinates
    the specialized domain agents.
    """
    # Input validation
    trimmed = request.raw_input.strip()
    if not trimmed:
        raise HTTPException(status_code=422, detail="Scenario input cannot be empty.")
    if len(trimmed) > MAX_INPUT_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"Input exceeds maximum length of {MAX_INPUT_LENGTH} characters.",
        )
    try:
        scenario = Scenario(raw_input=trimmed, status="pending")
        db.add(scenario)
        await db.commit()
        await db.refresh(scenario)
        background_tasks.add_task(run_simulation_background, scenario.id)
        return ScenarioCreateResponse(scenario_id=scenario.id)
    except HTTPException:
        raise
    except SQLAlchemyError:
        logger.exception("Database error while creating scenario")
        raise _db_unavailable_exception()
    except Exception:
        logger.exception("Unexpected error while creating scenario")
        raise _db_unavailable_exception()


@app.post("/api/scenarios/{scenario_id}/branch", response_model=ScenarioCreateResponse, status_code=201)
async def branch_scenario(
    scenario_id: str,
    request: BranchRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
) -> ScenarioCreateResponse:
    try:
        # Get branching context from branching engine
        divergence_year, pre_divergence_timeline_data, parent_raw_input = await create_branch_context(
            db, scenario_id, request.divergent_event_id
        )
        
        # Build child scenario text
        child_input = f"Branch of '{parent_raw_input}' at year {divergence_year} where: {request.alternative_event.strip()}"
        
        # Create branched child scenario record
        scenario = Scenario(raw_input=child_input, status="pending")
        db.add(scenario)
        await db.commit()
        await db.refresh(scenario)
        
        # Queue the background simulation task with pre-divergence timeline locked in
        background_tasks.add_task(run_simulation_background, scenario.id, pre_divergence_timeline_data)
        
        return ScenarioCreateResponse(scenario_id=scenario.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except SQLAlchemyError:
        logger.exception("Database error while branching scenario")
        raise _db_unavailable_exception()
    except Exception as exc:
        logger.exception("Unexpected error while branching scenario")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/scenarios/{scenario_id}/ask")
async def ask_scenario(
    scenario_id: str,
    request: AskRequest,
    db=Depends(get_db),
):
    try:
        response = await answer_scenario_question(db, scenario_id, request.question)
        return response
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in Q&A endpoint")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/scenarios/{scenario_id}/debate")
async def debate_scenario(
    scenario_id: str,
    request: DebateRequest,
    db=Depends(get_db),
):
    try:
        response = await run_agent_debate(
            db, 
            scenario_id, 
            request.topic, 
            request.agent_a, 
            request.agent_b
        )
        return response
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in debate endpoint")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/scenarios/{scenario_id}/adjust")
async def adjust_scenario(
    scenario_id: str,
    request: AdjustRequest,
    db=Depends(get_db),
):
    try:
        response = await adjust_scenario_parameters(db, scenario_id, request.adjustments)
        return response
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in adjust parameters endpoint")
        raise HTTPException(status_code=500, detail=str(exc))



_sim_semaphore: asyncio.Semaphore | None = None
_sim_semaphore_loop: asyncio.AbstractEventLoop | None = None


def _get_simulation_semaphore() -> asyncio.Semaphore:
    """Return the run limiter, re-binding it if the event loop changes.

    Created lazily so pytest (a fresh event loop per test) and uvicorn
    (one long-lived loop) both work. On the server the semaphore enforces
    ``MAX_CONCURRENT_SIMULATIONS``.
    """
    global _sim_semaphore, _sim_semaphore_loop
    loop = asyncio.get_running_loop()
    if _sim_semaphore is None or _sim_semaphore_loop is not loop:
        _sim_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SIMULATIONS)
        _sim_semaphore_loop = loop
    return _sim_semaphore


async def run_simulation_background(
    scenario_id: str, pre_divergence_timeline_data: list[dict] | None = None
) -> None:
    """Queue entry point: serialises simulation runs to cap peak memory.

    Each simulation fans out 9 agents plus RAG inside a single process. On
    Render's 512MB free instance, two concurrent runs exceeded the memory
    limit and the instance was OOM-killed — permanently orphaning those
    scenarios in "running" state. Queued scenarios stay "pending" until a
    slot frees up, so the browser never gets stuck on a dead run.
    """
    semaphore = _get_simulation_semaphore()
    if semaphore.locked():
        logger.info(
            "Simulation queue | scenario %s queued behind an active run (MAX_CONCURRENT_SIMULATIONS=%d)",
            scenario_id,
            MAX_CONCURRENT_SIMULATIONS,
        )
    async with semaphore:
        await _run_simulation_impl(scenario_id, pre_divergence_timeline_data)


async def _run_simulation_impl(
    scenario_id: str, pre_divergence_timeline_data: list[dict] | None = None
) -> None:
    from app.telemetry import current_scenario_id, broadcast_log
    current_scenario_id.set(str(scenario_id))

    async with AsyncSessionLocal() as db:
        try:
            scenario = await db.get(Scenario, scenario_id)
            if scenario is None:
                raise RuntimeError(f"Scenario {scenario_id} not found")

            scenario.status = "running"
            await db.commit()

            await broadcast_log("[system] Workspace initialization complete. Seeding scenario context...")
            await broadcast_log(f"[system] Simulating query: \"{scenario.raw_input}\"")

            pre_divergence_timeline = None
            if pre_divergence_timeline_data:
                pre_divergence_timeline = [
                    UnifiedTimelineEvent.model_validate(ev) for ev in pre_divergence_timeline_data
                ]

            result = await run_simulation_graph(str(scenario_id), scenario.raw_input, pre_divergence_timeline)
            if result.get("error") is not None:
                scenario.status = "error"
                scenario.error_message = result["error"]
                await db.commit()
                await broadcast_log(f"[error] Simulation aborted: {result['error']}")
                return

            # Save individual agent outputs to AgentOutput table
            agent_mappings = [
                ("historian_output", "historian"),
                ("economist_output", "economist"),
                ("technology_output", "technology"),
                ("society_output", "society"),
                ("climate_output", "climate"),
                ("political_output", "political"),
                ("energy_output", "energy"),
                ("healthcare_output", "healthcare"),
                ("demographics_output", "demographics"),
            ]
            for state_key, agent_name in agent_mappings:
                output_val = result.get(state_key)
                if output_val:
                    timeline_list = []
                    for ev in output_val.timeline_events:
                        timeline_list.append({"year": ev.year, "event": ev.event})
                    
                    s_data = {"timeline_events": timeline_list}
                    if hasattr(output_val, "impact_score"):
                        s_data["impact_score"] = output_val.impact_score

                    db.add(AgentOutput(
                        scenario_id=scenario.id,
                        agent_name=agent_name,
                        analysis_text=output_val.analysis_text,
                        structured_data=s_data,
                    ))

            final_report = result["final_report"].model_dump(exclude={"agent_outputs"})
            db.add(FinalReport(scenario_id=scenario.id, **final_report))
            scenario.status = "done"
            scenario.error_message = None
            await db.commit()
            await broadcast_log("[system] Simulation finalized. Synthesizing final dashboard indicators...")
        except Exception as exc:
            logger.exception("Unexpected error while running scenario %s", scenario_id)
            try:
                scenario = await db.get(Scenario, scenario_id)
                if scenario is not None:
                    scenario.status = "error"
                    scenario.error_message = f"Unexpected error: {str(exc)}"
                    await db.commit()
            except Exception:
                logger.exception("Failed to persist error state for scenario %s", scenario_id)


@app.get("/api/scenarios/{scenario_id}/status", response_model=ScenarioStatusResponse)
async def get_scenario_status(
    scenario_id: str,
    db=Depends(get_db),
) -> ScenarioStatusResponse:
    try:
        scenario = await db.get(Scenario, scenario_id)
        if scenario is None:
            raise HTTPException(status_code=404, detail="Scenario not found")

        result = await db.execute(select(AgentOutput.agent_name).where(AgentOutput.scenario_id == scenario_id))
        completed_agents = [row[0] for row in result.all()]
        return ScenarioStatusResponse(
            status=scenario.status,
            completed_agents=completed_agents,
            error_message=scenario.error_message,
        )
    except HTTPException:
        raise
    except SQLAlchemyError:
        logger.exception("Database error while getting scenario status")
        raise _db_unavailable_exception()
    except Exception:
        logger.exception("Unexpected error while getting scenario status")
        raise _db_unavailable_exception()


@app.get("/api/scenarios/{scenario_id}/report", response_model=FinalReportSchema)
async def get_scenario_report(
    scenario_id: str,
    db=Depends(get_db),
) -> FinalReportSchema:
    try:
        scenario = await db.get(Scenario, scenario_id)
        if scenario is None:
            raise HTTPException(status_code=404, detail="Scenario not found")

        if scenario.status != "done":
            raise HTTPException(status_code=409, detail=f"Report not ready, current status: {scenario.status}")

        result = await db.execute(select(FinalReport).where(FinalReport.scenario_id == scenario_id))
        report = result.scalar_one_or_none()
        if report is None:
            raise HTTPException(status_code=500, detail="Final report is missing for a completed scenario")

        agent_result = await db.execute(
            select(AgentOutput).where(
                AgentOutput.scenario_id == scenario_id,
                AgentOutput.agent_name.in_(["historian", "economist", "technology", "society", "climate", "political", "energy", "healthcare", "demographics"]),
            )
        )
        agent_rows = {agent_output.agent_name: agent_output for agent_output in agent_result.scalars().all()}

        return FinalReportSchema.model_validate(
            {
                "scenario_summary": report.scenario_summary,
                "alternate_timeline": report.alternate_timeline,
                "agent_outputs": [
                    {
                        "agent_name": agent_name,
                        "analysis_text": agent_rows[agent_name].analysis_text,
                        "timeline_events": agent_rows[agent_name].structured_data.get("timeline_events"),
                        "impact_score": agent_rows[agent_name].structured_data.get("impact_score"),
                    }
                    for agent_name in ["historian", "economist", "technology", "society", "climate", "political", "energy", "healthcare", "demographics"]
                    if agent_name in agent_rows
                ],
                "impact_dashboard": report.impact_dashboard,
                "confidence_score": report.confidence_score,
                "confidence_explanation": report.confidence_explanation,
                "risk_notes": report.risk_notes,
                "sources_consulted": report.sources_consulted,
                "retrieved_documents": report.retrieved_documents,
                "causal_graph": report.causal_graph or [],
                "assumptions": report.assumptions or [],
                "agent_confidences": report.agent_confidences or [],
                "grounding_validations": report.grounding_validations or [],
                "uncertainty_score": report.uncertainty_score or 0.0,
                "calibration_score": report.calibration_score or 100,
            }
        )
    except HTTPException:
        raise
    except SQLAlchemyError:
        logger.exception("Database error while getting scenario report")
        raise _db_unavailable_exception()
    except Exception:
        logger.exception("Unexpected error while getting scenario report")
        raise _db_unavailable_exception()
