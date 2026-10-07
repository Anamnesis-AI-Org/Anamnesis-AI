"""
Core multi-agent orchestration for Anamnesis-AI.

This module implements the simulation pipeline as a lightweight asyncio
sequence (parse -> historian -> batched domain agents -> critic ->
(feedback loop) -> narrator). It acts as the Orchestrator that decomposes a
user scenario and manages the lifecycle and communication between the
specialized domain agents (Historian, Economist, Technology, Society,
Climate, Political, Energy, Healthcare, Demographics) and the Critic that
converges their outputs.

Design patterns:
1. Agent-to-agent communication: each step is an independent agent analyzing
   the scenario from its own perspective.
2. Batched fan-out / fan-in: the Orchestrator runs domain agents in small
   batches (DOMAIN_CONCURRENCY, default 2) and converges them into the
   Critic agent (fan-in). An 8-way parallel fan-out OOM-killed Render's
   512MB free instance, so full parallelism is intentionally avoided.
3. Grounded reasoning: retrieval-augmented context is fetched before the
   simulation runs to reduce LLM hallucination.
"""
from __future__ import annotations

from statistics import mean
from typing import TypedDict

from pydantic import ValidationError
from typing_extensions import Required

from app.agents.critic import run_critic
from app.agents.economist import run_economist
from app.agents.historian import run_historian
from app.agents.society import run_society
from app.agents.technology import run_technology
from app.agents.climate import run_climate
from app.agents.political import run_political
from app.agents.energy import run_energy
from app.agents.healthcare import run_healthcare
from app.agents.demographics import run_demographics
from app.llm_client import AgentResponseError, call_agent
from app.prompts import ORCHESTRATOR_PARSE_PROMPT
from app.timeline_engine import create_unified_timeline
from app.schemas import (
	AgentOutputSummary,
	CriticOutput,
	EconomistOutput,
	FinalReportSchema,
	HistorianOutput,
	ImpactDashboard,
	ScenarioContext,
	SocietyOutput,
	TechnologyOutput,
	ClimateOutput,
	PoliticalOutput,
	EnergyOutput,
	HealthcareOutput,
	DemographicsOutput,
	UnifiedTimelineEvent,
	CausalLink,
	Assumption,
)

from app.simulation.causal_graph import run_causal_modeling
from app.simulation.assumption_tracker import run_assumption_extraction
from app.validation.source_validator import run_source_validation, validate_agent_grounding
from app.validation.uncertainty import calculate_uncertainty
from app.validation.calibration import calculate_calibration

import asyncio
import logging
import re

from app.config import DOMAIN_CONCURRENCY

logger = logging.getLogger(__name__)

def _merge_error(existing: str | None, new: str | None) -> str | None:
    """When multiple parallel agents fail in the same step, keep the first error."""
    return existing or new




def _agent_name_map() -> dict[str, str]:
    """Map snake_case node names to the short agent names used elsewhere."""
    return {
        "historian_node": "historian",
        "economist_node": "economist",
        "technology_node": "technology",
        "society_node": "society",
        "climate_node": "climate",
        "political_node": "political",
        "energy_node": "energy",
        "healthcare_node": "healthcare",
        "demographics_node": "demographics",
    }


def _match_agents(raw_input: str) -> list[str]:
    """Pick the agents that should run for a scenario.

    Keyword matching against the user's scenario text. A domain with no
    keyword match is skipped entirely. Historian always runs (baseline);
    the critic always runs afterwards (converges whatever agents ran).
    """
    text = raw_input.lower()
    name_map = _agent_name_map()
    matched: list[str] = []
    seen: set[str] = set()

    keywords = [
        (r"\beconomy\b|\beconomic\b|\bgdp\b", "economist"),
        (r"\btrade\b|tariff|trade deficit|trade surplus", "economist"),
        (r"\binflation\b|recession|unemployment", "economist"),
        (r"\bcurrency\b|exchange rate|devaluation", "economist"),
        (r"\bfinance\b|market\b|fiscal\b|monetary\b|tax\b|revenue|deficit", "economist"),
        (r"\bhealth\b|healthcare|hospital|epidemic|pandemic|epidemiology|outbreak", "healthcare"),
        (r"\bdisease\b|infection|mortality|life expectancy|public health", "healthcare"),
        (r"\bclimate\b|global warming|greenhouse", "climate"),
        (r"\benvironment\b|emission|carbon\s*footprint|biodiversity|deforestation", "climate"),
        (r"\bwarming\b|ice\s*cover|sea\s*level|temperature\s*rise", "climate"),
        (r"\bflood\b|drought|wildfire|extreme weather", "climate"),
        (r"\benergy\b|electricity|\boil\b|\bgas\b|fuel|renewable|coal|power grid", "energy"),
        (r"\bpolitical\b|politics|election|government|\bpolicy\b|\bvote\b", "political"),
        (r"\bprime minister\b|president|chancellor|legislature|parliament", "political"),
        (r"\bwar\b|civil\s*war|conflict|invasion|border|peace treaty|sanction", "political"),
        (r"\bsociety\b|population|culture|social\b|immigration|citizen", "society"),
        (r"\beducation\b|literacy|inequality|\bgini\b", "society"),
        (r"demograph|migration|urbanization|fertility|aging|birth rate|death rate", "demographics"),
        (r"\btechnology\b|innovation|\bai\b|artificial\s*intelligence|internet\b|\btech\b", "technology"),
        (r"bio\s*tech|biometric|cloud\b|automation|robot\b|space\b", "technology"),
        (r"machine learning|data\s*center|semiconductor", "technology"),
    ]

    for pattern, name in keywords:
        if re.search(pattern, text) and name not in seen:
            seen.add(name)
            matched.append(name)

    if "historian" not in seen:
        seen.add("historian")
        matched.append("historian")

    ordered: list[str] = []
    for name in name_map.values():
        if name in seen:
            ordered.append(name)
    return ordered


class GraphState(TypedDict, total=False):
	scenario_id: Required[str]
	raw_input: Required[str]
	scenario_context: ScenarioContext | None
	historian_output: HistorianOutput | None
	economist_output: EconomistOutput | None
	technology_output: TechnologyOutput | None
	society_output: SocietyOutput | None
	climate_output: ClimateOutput | None
	political_output: PoliticalOutput | None
	energy_output: EnergyOutput | None
	healthcare_output: HealthcareOutput | None
	demographics_output: DemographicsOutput | None
	critic_output: CriticOutput | None
	final_report: FinalReportSchema | None
	error: str | None
	# RAG lists accumulated across steps.
	retrieved_documents: list[str]
	sources_consulted: list[str]
	iteration: int
	critic_feedback: str | None
	pre_divergence_timeline: list[UnifiedTimelineEvent] | None
	matched_agents: list[str]


def _get_other_agents_outputs(state: GraphState, current_agent: str) -> list[AgentOutputSummary]:
	outputs = []
	agents = [
		("economist", state.get("economist_output")),
		("technology", state.get("technology_output")),
		("society", state.get("society_output")),
		("climate", state.get("climate_output")),
		("political", state.get("political_output")),
		("energy", state.get("energy_output")),
		("healthcare", state.get("healthcare_output")),
		("demographics", state.get("demographics_output")),
	]
	for name, output in agents:
		if name != current_agent and output is not None:
			outputs.append(
				AgentOutputSummary(
					agent_name=output.agent_name,
					analysis_text=output.analysis_text,
					timeline_events=output.timeline_events,
					impact_score=output.impact_score,
				)
			)
	return outputs


async def parse_scenario(state: GraphState) -> dict:
	try:
		# Obtain the structured scenario context via the orchestrator LLM call.
		result = await call_agent(ORCHESTRATOR_PARSE_PROMPT, state["raw_input"])
		context = ScenarioContext.model_validate(result)
		return {"scenario_context": context}
	except (AgentResponseError, ValidationError) as exc:
		return {"error": str(exc)}


async def historian_node(state: GraphState) -> dict:
	if state.get("error"):
		return {"error": state["error"]}

	try:
		result, retrieved_docs, sources = await run_historian(
			state["scenario_context"],
			state.get("critic_feedback"),
			state.get("pre_divergence_timeline")
		)
		return {
			"historian_output": result,
			"retrieved_documents": retrieved_docs,
			"sources_consulted": sources
		}
	except AgentResponseError as exc:
		return {"error": f"historian failed: {str(exc)}"}


async def economist_node(state: GraphState) -> dict:
	if state.get("error"):
		return {"error": state["error"]}

	other_agents_outputs = _get_other_agents_outputs(state, "economist")

	try:
		result, retrieved_docs, sources = await run_economist(
			state["scenario_context"],
			state.get("historian_output"),
			other_agents_outputs,
			state.get("critic_feedback"),
			state.get("pre_divergence_timeline")
		)
		return {
			"economist_output": result,
			"retrieved_documents": retrieved_docs,
			"sources_consulted": sources
		}
	except AgentResponseError as exc:
		return {"error": f"economist failed: {str(exc)}"}


async def technology_node(state: GraphState) -> dict:
	if state.get("error"):
		return {"error": state["error"]}

	other_agents_outputs = _get_other_agents_outputs(state, "technology")

	try:
		result, retrieved_docs, sources = await run_technology(
			state["scenario_context"],
			state.get("historian_output"),
			other_agents_outputs,
			state.get("critic_feedback"),
			state.get("pre_divergence_timeline")
		)
		return {
			"technology_output": result,
			"retrieved_documents": retrieved_docs,
			"sources_consulted": sources
		}
	except AgentResponseError as exc:
		return {"error": f"technology failed: {str(exc)}"}


async def society_node(state: GraphState) -> dict:
	if state.get("error"):
		return {"error": state["error"]}

	other_agents_outputs = _get_other_agents_outputs(state, "society")

	try:
		result, retrieved_docs, sources = await run_society(
			state["scenario_context"],
			state.get("historian_output"),
			other_agents_outputs,
			state.get("critic_feedback"),
			state.get("pre_divergence_timeline")
		)
		return {
			"society_output": result,
			"retrieved_documents": retrieved_docs,
			"sources_consulted": sources
		}
	except AgentResponseError as exc:
		return {"error": f"society failed: {str(exc)}"}


async def climate_node(state: GraphState) -> dict:
	if state.get("error"):
		return {"error": state["error"]}

	other_agents_outputs = _get_other_agents_outputs(state, "climate")

	try:
		result, retrieved_docs, sources = await run_climate(
			state["scenario_context"],
			state.get("historian_output"),
			other_agents_outputs,
			state.get("critic_feedback"),
			state.get("pre_divergence_timeline")
		)
		return {
			"climate_output": result,
			"retrieved_documents": retrieved_docs,
			"sources_consulted": sources
		}
	except AgentResponseError as exc:
		return {"error": f"climate failed: {str(exc)}"}


async def political_node(state: GraphState) -> dict:
	if state.get("error"):
		return {"error": state["error"]}

	other_agents_outputs = _get_other_agents_outputs(state, "political")

	try:
		result, retrieved_docs, sources = await run_political(
			state["scenario_context"],
			state.get("historian_output"),
			other_agents_outputs,
			state.get("critic_feedback"),
			state.get("pre_divergence_timeline")
		)
		return {
			"political_output": result,
			"retrieved_documents": retrieved_docs,
			"sources_consulted": sources
		}
	except AgentResponseError as exc:
		return {"error": f"political failed: {str(exc)}"}


async def energy_node(state: GraphState) -> dict:
	if state.get("error"):
		return {"error": state["error"]}

	other_agents_outputs = _get_other_agents_outputs(state, "energy")

	try:
		result, retrieved_docs, sources = await run_energy(
			state["scenario_context"],
			state.get("historian_output"),
			other_agents_outputs,
			state.get("critic_feedback"),
			state.get("pre_divergence_timeline")
		)
		return {
			"energy_output": result,
			"retrieved_documents": retrieved_docs,
			"sources_consulted": sources
		}
	except AgentResponseError as exc:
		return {"error": f"energy failed: {str(exc)}"}


async def healthcare_node(state: GraphState) -> dict:
	if state.get("error"):
		return {"error": state["error"]}

	other_agents_outputs = _get_other_agents_outputs(state, "healthcare")

	try:
		result, retrieved_docs, sources = await run_healthcare(
			state["scenario_context"],
			state.get("historian_output"),
			other_agents_outputs,
			state.get("critic_feedback"),
			state.get("pre_divergence_timeline")
		)
		return {
			"healthcare_output": result,
			"retrieved_documents": retrieved_docs,
			"sources_consulted": sources
		}
	except AgentResponseError as exc:
		return {"error": f"healthcare failed: {str(exc)}"}


async def demographics_node(state: GraphState) -> dict:
	if state.get("error"):
		return {"error": state["error"]}

	other_agents_outputs = _get_other_agents_outputs(state, "demographics")

	try:
		result, retrieved_docs, sources = await run_demographics(
			state["scenario_context"],
			state.get("historian_output"),
			other_agents_outputs,
			state.get("critic_feedback"),
			state.get("pre_divergence_timeline")
		)
		return {
			"demographics_output": result,
			"retrieved_documents": retrieved_docs,
			"sources_consulted": sources
		}
	except AgentResponseError as exc:
		return {"error": f"demographics failed: {str(exc)}"}


async def critic_node(state: GraphState) -> dict:
	if state.get("error"):
		return {"error": state["error"]}

	# Only agents that were selected to run must have outputs; skipped agents
	# stay None in state and are forwarded to the critic as None.
	run_names = state.get("matched_agents") or list(_agent_name_map().values())
	missing: list[str] = []
	if not state.get("historian_output"):
		missing.append("historian")
	for name in run_names:
		if name != "historian" and not state.get(f"{name}_output"):
			missing.append(name)
	if missing:
		return {"error": "critic skipped because agent outputs are missing: " + ", ".join(missing)}

	def _out(name: str):
		if name == "historian":
			return state.get("historian_output")
		return state.get(f"{name}_output")

	try:
		result = await run_critic(
			historian=state["historian_output"],
			economist=_out("economist"),
			technology=_out("technology"),
			society=_out("society"),
			climate=_out("climate"),
			political=_out("political"),
			energy=_out("energy"),
			healthcare=_out("healthcare"),
			demographics=_out("demographics"),
		)
		return {"critic_output": result}
	except AgentResponseError as exc:
		return {"error": f"critic failed: {str(exc)}"}

async def narrator_node(state: GraphState) -> dict:
	scenario_context = state["scenario_context"]
	critic_output = state["critic_output"]

	# Collect only the agent outputs that actually ran (conditional
	# participation): skipped domain agents stay None in state.
	agent_outputs = {
		name: state.get(key)
		for name, key in (
			("historian", "historian_output"),
			("economist", "economist_output"),
			("technology", "technology_output"),
			("society", "society_output"),
			("climate", "climate_output"),
			("political", "political_output"),
			("energy", "energy_output"),
			("healthcare", "healthcare_output"),
			("demographics", "demographics_output"),
		)
	}
	agent_outputs = {name: out for name, out in agent_outputs.items() if out is not None}
	historian_output = agent_outputs["historian"]

	# Unify timeline via timeline engine
	alternate_timeline = create_unified_timeline({
		name: out.timeline_events for name, out in agent_outputs.items()
	})

	# If we have a pre-divergence timeline, prepend its events and filter new events
	pre_div = state.get("pre_divergence_timeline") or []
	if pre_div:
		div_year = scenario_context.divergence_year
		filtered_new_events = [ev for ev in alternate_timeline if ev.year >= div_year]
		combined_timeline = list(pre_div) + filtered_new_events
		combined_timeline.sort(key=lambda x: x.year)
		alternate_timeline = combined_timeline

	# Assign unique IDs, preserving pre-existing IDs
	existing_ids = {ev.id for ev in alternate_timeline if ev.id}
	idx = 0
	for ev in alternate_timeline:
		if not ev.id:
			new_id = f"ev-{idx}"
			while new_id in existing_ids:
				idx += 1
				new_id = f"ev-{idx}"
			existing_ids.add(new_id)
			ev.id = new_id
		idx += 1

	# Deduplicate and sort RAG references
	retrieved_documents = sorted(list(set(state.get("retrieved_documents", []))))
	sources_consulted = sorted(list(set(state.get("sources_consulted", []))))

	agent_outputs_summaries = [
		AgentOutputSummary(
			agent_name=out.agent_name,
			analysis_text=out.analysis_text,
			timeline_events=out.timeline_events,
			impact_score=getattr(out, "impact_score", None),
		)
		for out in agent_outputs.values()
	]

	# Extract causal graph and assumptions via our new simulation modules
	causal_graph = await run_causal_modeling(alternate_timeline)
	assumptions = await run_assumption_extraction(agent_outputs_summaries)

	# Phase 5: Confidence & Validation logic
	grounding_validations = await run_source_validation(agent_outputs_summaries, retrieved_documents)
	uncertainty_score = calculate_uncertainty(agent_outputs_summaries)
	calibration_score = calculate_calibration(alternate_timeline, scenario_context.divergence_year)

	def _impact(name: str) -> int:
		out = agent_outputs.get(name)
		return int(getattr(out, "impact_score", 0) or 0)

	final_report = FinalReportSchema(
		scenario_summary=scenario_context.scenario,
		alternate_timeline=alternate_timeline,
		agent_outputs=agent_outputs_summaries,
		impact_dashboard=ImpactDashboard(
			economy=_impact("economist"),
			technology=_impact("technology"),
			society=_impact("society"),
			politics=_impact("political"),
			climate=_impact("climate"),
		),
		confidence_score=critic_output.confidence_score,
		confidence_explanation=critic_output.confidence_explanation,
		risk_notes=critic_output.risk_notes,
		sources_consulted=sources_consulted,
		retrieved_documents=retrieved_documents,
		causal_graph=causal_graph,
		assumptions=assumptions,
		agent_confidences=critic_output.agent_confidences or [],
		grounding_validations=grounding_validations,
		uncertainty_score=uncertainty_score,
		calibration_score=calibration_score,
	)

	return {"final_report": final_report}


def _route_after_parse(state: GraphState) -> str:
	if state.get("error"):
		return "error"
	return "historian_node"


def _route_after_historian(state: GraphState) -> list[str] | str:
	if state.get("error"):
		return "error"
	return [
		"economist_node",
		"technology_node",
		"society_node",
		"climate_node",
		"political_node",
		"energy_node",
		"healthcare_node",
		"demographics_node",
	]


async def generate_feedback(state: GraphState) -> dict:
	critic_output = state["critic_output"]
	iteration = state.get("iteration", 0) + 1
	feedback_str = "Contradictions and risk areas identified by Critic:\n" + "\n".join(
		[f"- {note}" for note in critic_output.risk_notes]
	)
	return {
		"iteration": iteration,
		"critic_feedback": feedback_str,
	}


def _route_after_critic(state: GraphState) -> str:
	if state.get("error"):
		return "error"
	critic_output = state.get("critic_output")
	iteration = state.get("iteration", 0)
	if critic_output and critic_output.confidence_score < 75 and iteration < 2:
		return "generate_feedback"
	return "narrator_node"


# ====================================================================================
# SEQUENTIAL PIPELINE (replaces the LangGraph StateGraph)
# ====================================================================================
# The original StateGraph fanned out all 8 domain agents in parallel. Each
# agent spawns blocking RAG fetch threads (wikipedia/arXiv `to_thread`) plus
# LLM calls, so 8 at once plus a second queued simulation exceeded Render's
# 512MB free tier and the instance was OOM-killed mid-run. The pipeline below
# preserves the exact same stage order and outputs, but runs domain agents in
# small batches (DOMAIN_CONCURRENCY) with a shared asyncio.Semaphore and runs
# grounding validations sequentially.

_DOMAIN_STEPS: tuple[tuple[str, str], ...] = (
    ("economist_node", "economist"),
    ("technology_node", "technology"),
    ("society_node", "society"),
    ("climate_node", "climate"),
    ("political_node", "political"),
    ("energy_node", "energy"),
    ("healthcare_node", "healthcare"),
    ("demographics_node", "demographics"),
)

_NODE_FUNCS = {
    "parse_scenario": parse_scenario,
    "historian_node": historian_node,
    "economist_node": economist_node,
    "technology_node": technology_node,
    "society_node": society_node,
    "climate_node": climate_node,
    "political_node": political_node,
    "energy_node": energy_node,
    "healthcare_node": healthcare_node,
    "demographics_node": demographics_node,
    "critic_node": critic_node,
    "generate_feedback": generate_feedback,
    "narrator_node": narrator_node,
}


async def _run_domain_batch(
    state: GraphState, sem: asyncio.Semaphore, batch: tuple[tuple[str, str], ...]
) -> None:
    """Run one batch of domain agent steps with bounded concurrency."""

    async def _one(node_name: str, agent_name: str) -> None:
        async with sem:
            try:
                update = await _NODE_FUNCS[node_name](state)
            except Exception as exc:  # keep first error, like _merge_error
                logger.exception("Domain agent %s failed", agent_name)
                if not state.get("error"):
                    state["error"] = f"{agent_name} agent failed: {exc}"
                return
            state.update(update)

    await asyncio.gather(*[_one(node, agent) for node, agent in batch])


async def run_simulation_graph(
    scenario_id: str,
    raw_input: str,
    pre_divergence_timeline: list[UnifiedTimelineEvent] | None = None,
) -> GraphState:
    """Execute the full pipeline with bounded memory usage.

    Only the domain agents matched by ``_match_agents`` execute for the
    scenario; historian always runs and critic converges whatever ran.
    """
    matched_agents = _match_agents(raw_input)
    logger.info("Matched agents for scenario %s: %s", scenario_id, matched_agents)
    matched_set = set(matched_agents)

    state: GraphState = {
        "scenario_id": scenario_id,
        "raw_input": raw_input,
        "scenario_context": None,
        "historian_output": None,
        "economist_output": None,
        "technology_output": None,
        "society_output": None,
        "climate_output": None,
        "political_output": None,
        "energy_output": None,
        "healthcare_output": None,
        "demographics_output": None,
        "critic_output": None,
        "final_report": None,
        "error": None,
        "retrieved_documents": [],
        "sources_consulted": [],
        "iteration": 0,
        "critic_feedback": None,
        "pre_divergence_timeline": pre_divergence_timeline,
        "matched_agents": matched_agents,
    }

    # Conditional participation: only matched domain agents execute.
    domain_steps = tuple(step for step in _DOMAIN_STEPS if step[1] in matched_set)

    # 1. parse -> historian (sequential, establishes scenario + baseline).
    for node_name in ("parse_scenario", "historian_node"):
        update = await _NODE_FUNCS[node_name](state)
        state.update(update)
        route = (
            _route_after_parse(state)
            if node_name == "parse_scenario"
            else _route_after_historian(state)
        )
        if route == "error":
            return state

    # 2. Batched domain fan-out (bounded concurrency instead of 8-way).
    batch_size = max(1, DOMAIN_CONCURRENCY)
    sem = asyncio.Semaphore(batch_size)
    for i in range(0, len(domain_steps), batch_size):
        await _run_domain_batch(state, sem, domain_steps[i : i + batch_size])
        if state.get("error"):
            return state

    # 3. critic (+ optional feedback loop, max 2 iterations like before).
    while True:
        update = await critic_node(state)
        state.update(update)
        route = _route_after_critic(state)
        if route == "generate_feedback":
            update = await generate_feedback(state)
            state.update(update)
            # Loopback: re-run historian then the domain batches once more.
            update = await historian_node(state)
            state.update(update)
            if _route_after_historian(state) == "error":
                return state
            for i in range(0, len(domain_steps), batch_size):
                await _run_domain_batch(state, sem, domain_steps[i : i + batch_size])
                if state.get("error"):
                    return state
            continue
        break

    if state.get("error"):
        return state

    # 4. narrator (assembles FinalReportSchema).
    update = await narrator_node(state)
    state.update(update)
    return state
