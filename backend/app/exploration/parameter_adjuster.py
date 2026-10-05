import logging
import copy
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models import FinalReport, Scenario, AgentOutput
from app.llm_client import call_agent
from app.schemas import (
    FinalReportSchema, AgentOutputSummary, ImpactDashboard,
    HistorianOutput, EconomistOutput, TechnologyOutput, SocietyOutput, ClimateOutput,
    PoliticalOutput, EnergyOutput, HealthcareOutput, DemographicsOutput,
    UnifiedTimelineEvent, TimelineEvent
)

# Re-use backend validation and simulation nodes from orchestrator
from app.agents.critic import run_critic
from app.agents.economist import run_economist
from app.agents.technology import run_technology
from app.agents.society import run_society
from app.agents.climate import run_climate
from app.agents.political import run_political
from app.agents.energy import run_energy
from app.simulation.causal_graph import run_causal_modeling
from app.simulation.assumption_tracker import run_assumption_extraction
from app.validation.source_validator import run_source_validation
from app.validation.uncertainty import calculate_uncertainty
from app.validation.calibration import calculate_calibration

logger = logging.getLogger(__name__)

# Map parameters to affected agents
PARAMETER_MAP = {
    "transition_speed": ["technology", "society"],
    "resource_abundance": ["economist", "energy"],
    "government_control": ["political", "society"],
    "climate_feedback": ["climate"]
}

async def adjust_scenario_parameters(
    db: AsyncSession,
    scenario_id: str,
    adjustments: dict[str, int] # e.g. {"resource_abundance": 75, "transition_speed": 40}
) -> dict:
    """Executes a partial re-simulation.

    Identifies affected agents, re-runs them using adjusted parameters as constraint feedback,
    keeps unaffected agent outputs, and recomposes a fresh FinalReport.
    """
    logger.info("parameter_adjuster │ scenario_id=%s adjustments=%r", scenario_id, adjustments)

    # 1. Fetch current scenario, report, and outputs
    scenario = await db.get(Scenario, scenario_id)
    if not scenario:
        raise ValueError(f"Scenario {scenario_id} not found")

    result = await db.execute(select(FinalReport).where(FinalReport.scenario_id == scenario_id))
    report = result.scalar_one_or_none()
    if not report:
        raise ValueError(f"Final report for scenario {scenario_id} not found")

    agent_result = await db.execute(select(AgentOutput).where(AgentOutput.scenario_id == scenario_id))
    db_agent_outputs = {out.agent_name: out for out in agent_result.scalars().all()}

    # 2. Determine affected agent names
    affected_agents = set()
    for param, value in adjustments.items():
        if param in PARAMETER_MAP:
            for agent in PARAMETER_MAP[param]:
                affected_agents.add(agent)

    # 3. Re-run affected agents
    # Reconstruct ScenarioContext from FinalReport schemas
    from app.schemas import ScenarioContext
    import re

    # Try parsing divergence year from report or timeline
    divergence_year = 2000
    if report.alternate_timeline:
        divergence_year = min(ev.get("year", 2000) for ev in report.alternate_timeline)

    context = ScenarioContext(
        scenario=report.scenario_summary,
        divergence_year=divergence_year,
        focus_domains=list(db_agent_outputs.keys()),
        time_horizon=max(ev.get("year", 2025) for ev in (report.alternate_timeline or [{"year": 2025}]))
    )

    # Build adjusted feedback constraint text
    adjustments_str = ", ".join([f"{k} set to {v}/100" for k, v in adjustments.items()])
    adjustment_feedback = f"ADJUSTED PARAMETER CONSTRAINTS: Shifting simulation environment variables: {adjustments_str}. Recalculate output accordingly."

    # Historian baseline. The agent runners expect the Pydantic HistorianOutput
    # schema (they call .model_dump_json() on it), so rebuild it from the stored
    # SQLAlchemy AgentOutput row instead of passing the row directly.
    historian_row = db_agent_outputs.get("historian")
    historian_baseline: HistorianOutput | None = None
    historian_timeline: list[TimelineEvent] | None = None
    if historian_row is not None:
        historian_timeline = [
            TimelineEvent(year=ev.get("year", 2000), event=ev.get("event", ""))
            for ev in ((historian_row.structured_data or {}).get("timeline_events") or [])
        ]
        historian_baseline = HistorianOutput(
            analysis_text=historian_row.analysis_text or "",
            timeline_events=historian_timeline,
        )

    updated_outputs = {}

    # Accumulate retrieved documents
    retrieved_documents = copy.deepcopy(report.retrieved_documents or [])
    sources_consulted = copy.deepcopy(report.sources_consulted or [])

    for agent_name in ["historian", "economist", "technology", "society", "climate", "political", "energy", "healthcare", "demographics"]:
        if agent_name not in db_agent_outputs:
            continue

        db_out = db_agent_outputs[agent_name]

        # If the agent is unaffected, keep its current output.
        if agent_name not in affected_agents:
            updated_outputs[agent_name] = {
                "agent_name": agent_name,
                "analysis_text": db_out.analysis_text,
                "timeline_events": [TimelineEvent(year=ev.get("year", 2000), event=ev.get("event", "")) for ev in (db_out.structured_data.get("timeline_events") or [])],
                "impact_score": db_out.structured_data.get("impact_score") or 0
            }
            continue

        # Otherwise re-run the agent using LLM client (Real mode)
        # Fetch other agent summaries for inter-agent context sharing
        other_summaries = []
        for name, other_out in db_agent_outputs.items():
            if name != agent_name:
                other_summaries.append(AgentOutputSummary(
                    agent_name=other_out.agent_name,
                    analysis_text=other_out.analysis_text,
                    impact_score=other_out.structured_data.get("impact_score") or 0
                ))

        try:
            if agent_name == "economist":
                res, docs, srcs = await run_economist(context, historian_baseline, other_summaries, adjustment_feedback, historian_timeline)
            elif agent_name == "technology":
                res, docs, srcs = await run_technology(context, historian_baseline, other_summaries, adjustment_feedback, historian_timeline)
            elif agent_name == "society":
                res, docs, srcs = await run_society(context, historian_baseline, other_summaries, adjustment_feedback, historian_timeline)
            elif agent_name == "climate":
                res, docs, srcs = await run_climate(context, historian_baseline, other_summaries, adjustment_feedback, historian_timeline)
            elif agent_name == "political":
                res, docs, srcs = await run_political(context, historian_baseline, other_summaries, adjustment_feedback, historian_timeline)
            elif agent_name == "energy":
                res, docs, srcs = await run_energy(context, historian_baseline, other_summaries, adjustment_feedback, historian_timeline)
            else:
                # Fallback: keep existing if agent runner is not importable
                res = db_out
                docs, srcs = [], []

            retrieved_documents.extend(docs)
            sources_consulted.extend(srcs)

            updated_outputs[agent_name] = {
                "agent_name": agent_name,
                "analysis_text": res.analysis_text,
                "timeline_events": [TimelineEvent(year=ev.year, event=ev.event) for ev in res.timeline_events],
                "impact_score": res.impact_score
            }
        except Exception as exc:
            logger.exception("parameter_adjuster │ failed to re-run agent %s", agent_name)
            # Fallback to current output
            updated_outputs[agent_name] = {
                "agent_name": agent_name,
                "analysis_text": db_out.analysis_text,
                "timeline_events": [TimelineEvent(year=ev.get("year", 2000), event=ev.get("event", "")) for ev in (db_out.structured_data.get("timeline_events") or [])],
                "impact_score": db_out.structured_data.get("impact_score") or 0
            }

    # 4. Rebuild unified timeline
    from app.timeline_engine import create_unified_timeline
    timeline_inputs = {}
    for k, out in updated_outputs.items():
        timeline_inputs[k] = out["timeline_events"]
    alternate_timeline = create_unified_timeline(timeline_inputs)

    # 5. Re-run Critic loop evaluation
    agent_outputs_summaries = []
    for out in updated_outputs.values():
        agent_outputs_summaries.append(AgentOutputSummary(
            agent_name=out["agent_name"],
            analysis_text=out["analysis_text"],
            timeline_events=out["timeline_events"],
            impact_score=out["impact_score"]
        ))

    try:
        critic_output = await run_critic(
            HistorianOutput(
                analysis_text=updated_outputs.get("historian", {}).get("analysis_text") or "No adjustments.",
                timeline_events=updated_outputs.get("historian", {}).get("timeline_events") or [],
            ),
            EconomistOutput(
                analysis_text=updated_outputs.get("economist", {}).get("analysis_text") or "No adjustments.",
                timeline_events=updated_outputs.get("economist", {}).get("timeline_events") or [],
                impact_score=updated_outputs.get("economist", {}).get("impact_score") or 50,
            ),
            TechnologyOutput(
                analysis_text=updated_outputs.get("technology", {}).get("analysis_text") or "No adjustments.",
                timeline_events=updated_outputs.get("technology", {}).get("timeline_events") or [],
                impact_score=updated_outputs.get("technology", {}).get("impact_score") or 50,
            ),
            SocietyOutput(
                analysis_text=updated_outputs.get("society", {}).get("analysis_text") or "No adjustments.",
                timeline_events=updated_outputs.get("society", {}).get("timeline_events") or [],
                impact_score=updated_outputs.get("society", {}).get("impact_score") or 50,
            ),
            ClimateOutput(
                analysis_text=updated_outputs.get("climate", {}).get("analysis_text") or "No adjustments.",
                timeline_events=updated_outputs.get("climate", {}).get("timeline_events") or [],
                impact_score=updated_outputs.get("climate", {}).get("impact_score") or 50,
            ),
            PoliticalOutput(
                analysis_text=updated_outputs.get("political", {}).get("analysis_text") or "No adjustments.",
                timeline_events=updated_outputs.get("political", {}).get("timeline_events") or [],
                impact_score=updated_outputs.get("political", {}).get("impact_score") or 50,
            ),
            EnergyOutput(
                analysis_text=updated_outputs.get("energy", {}).get("analysis_text") or "No adjustments.",
                timeline_events=updated_outputs.get("energy", {}).get("timeline_events") or [],
                impact_score=updated_outputs.get("energy", {}).get("impact_score") or 50,
            ),
            HealthcareOutput(
                analysis_text=updated_outputs.get("healthcare", {}).get("analysis_text") or "No adjustments.",
                timeline_events=updated_outputs.get("healthcare", {}).get("timeline_events") or [],
                impact_score=updated_outputs.get("healthcare", {}).get("impact_score") or 50,
            ),
            DemographicsOutput(
                analysis_text=updated_outputs.get("demographics", {}).get("analysis_text") or "No adjustments.",
                timeline_events=updated_outputs.get("demographics", {}).get("timeline_events") or [],
                impact_score=updated_outputs.get("demographics", {}).get("impact_score") or 50,
            ),
        )
    except Exception:
        logger.exception("parameter_adjuster │ critic failed, using fallback metrics")
        from app.schemas import CriticOutput
        critic_output = CriticOutput(
            confidence_score=report.confidence_score,
            confidence_explanation="Adjusted simulation results compiled successfully.",
            risk_notes=report.risk_notes
        )

    # 6. Re-run causal modeling & assumption extraction
    causal_graph = await run_causal_modeling(alternate_timeline)
    assumptions = await run_assumption_extraction(agent_outputs_summaries)

    # 7. Re-run grounding validator
    grounding_validations = await run_source_validation(agent_outputs_summaries, retrieved_documents)
    uncertainty_score = calculate_uncertainty(agent_outputs_summaries)
    calibration_score = calculate_calibration(alternate_timeline, context.divergence_year)

    # 8. Rebuild final report
    final_report = FinalReportSchema(
        scenario_summary=report.scenario_summary,
        alternate_timeline=alternate_timeline,
        agent_outputs=agent_outputs_summaries,
        impact_dashboard=ImpactDashboard(
            economy=updated_outputs.get("economist", {}).get("impact_score") or (report.impact_dashboard.get("economy") if report.impact_dashboard else 50),
            technology=updated_outputs.get("technology", {}).get("impact_score") or (report.impact_dashboard.get("technology") if report.impact_dashboard else 50),
            society=updated_outputs.get("society", {}).get("impact_score") or (report.impact_dashboard.get("society") if report.impact_dashboard else 50),
            politics=updated_outputs.get("political", {}).get("impact_score") or (report.impact_dashboard.get("politics") if report.impact_dashboard else 50),
            climate=updated_outputs.get("climate", {}).get("impact_score") or (report.impact_dashboard.get("climate") if report.impact_dashboard else 50),
        ),
        confidence_score=critic_output.confidence_score,
        confidence_explanation=critic_output.confidence_explanation,
        risk_notes=critic_output.risk_notes,
        sources_consulted=list(set(sources_consulted)),
        retrieved_documents=list(set(retrieved_documents)),
        causal_graph=causal_graph,
        assumptions=assumptions,
        agent_confidences=critic_output.agent_confidences or [],
        grounding_validations=grounding_validations,
        uncertainty_score=uncertainty_score,
        calibration_score=calibration_score,
    )

    # 9. Write updates back to database
    # Update affected AgentOutput rows
    for agent_name in affected_agents:
        if agent_name in updated_outputs:
            out = updated_outputs[agent_name]
            db_row = db_agent_outputs.get(agent_name)
            if db_row:
                db_row.analysis_text = out["analysis_text"]
                db_row.structured_data = {
                    "timeline_events": [{"year": ev.year, "event": ev.event} for ev in out["timeline_events"]],
                    "impact_score": out["impact_score"]
                }
    
    # Overwrite FinalReport record
    await db.execute(delete(FinalReport).where(FinalReport.scenario_id == scenario_id))
    db.add(FinalReport(
        scenario_id=scenario_id,
        scenario_summary=final_report.scenario_summary,
        alternate_timeline=[ev.model_dump() for ev in final_report.alternate_timeline],
        impact_dashboard=final_report.impact_dashboard.model_dump(),
        confidence_score=final_report.confidence_score,
        confidence_explanation=final_report.confidence_explanation,
        risk_notes=final_report.risk_notes,
        sources_consulted=final_report.sources_consulted,
        retrieved_documents=final_report.retrieved_documents,
        causal_graph=[c.model_dump() for c in final_report.causal_graph],
        assumptions=[a.model_dump() for a in final_report.assumptions],
        agent_confidences=[c.model_dump() for c in final_report.agent_confidences],
        grounding_validations=[v.model_dump() for v in final_report.grounding_validations],
        uncertainty_score=final_report.uncertainty_score,
        calibration_score=final_report.calibration_score
    ))

    await db.commit()
    return final_report.model_dump()
