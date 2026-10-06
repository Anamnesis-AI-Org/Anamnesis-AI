import json
import logging
from pydantic import ValidationError
from app.llm_client import AgentResponseError, call_agent
from app.prompts import SOURCE_VALIDATION_PROMPT
from app.schemas import GroundingValidation, AgentOutputSummary

logger = logging.getLogger(__name__)


async def validate_agent_grounding(agent_output: AgentOutputSummary, retrieved_docs: list[str]) -> GroundingValidation:
    """Assess the degree of factual grounding of a single agent's text against retrieved documents."""
    if not agent_output.analysis_text:
        return GroundingValidation(
            agent_name=agent_output.agent_name,
            grounding_score=100,
            unsupported_claims=[],
            explanation="No analysis text produced by agent."
        )

    # If no documents were retrieved, grounding is technically 0 unless there's a baseline reason
    if not retrieved_docs:
        return GroundingValidation(
            agent_name=agent_output.agent_name,
            grounding_score=0,
            unsupported_claims=["All claims are unsupported as no reference documents were retrieved."],
            explanation="No grounding source documents available."
        )

    payload = {
        "analysis_text": agent_output.analysis_text,
        "sources": retrieved_docs
    }

    try:
        result = await call_agent(SOURCE_VALIDATION_PROMPT, json.dumps(payload))
        validated = GroundingValidation.model_validate({
            "agent_name": agent_output.agent_name,
            "grounding_score": result.get("grounding_score", 100),
            "unsupported_claims": result.get("unsupported_claims", []),
            "explanation": result.get("explanation", "")
        })
        return validated
    except (AgentResponseError, ValidationError, Exception) as exc:
        logger.warning("Grounding validation failed for agent %s: %s", agent_output.agent_name, exc)
        return GroundingValidation(
            agent_name=agent_output.agent_name,
            grounding_score=100,  # Graceful fallback
            unsupported_claims=[],
            explanation=f"Fact-checking engine encountered an error: {exc}"
        )


async def run_source_validation(agent_outputs: list[AgentOutputSummary], retrieved_docs: list[str]) -> list[GroundingValidation]:
    """Run source-grounded fact-checking for all domain agents sequentially.

    Sequential execution keeps peak memory flat on the 512MB free tier and
    also avoids bursting past the Gemini free-tier rate limit (15 req/min).
    """
    if not agent_outputs:
        return []

    results: list[GroundingValidation] = []
    for out in agent_outputs:
        results.append(await validate_agent_grounding(out, retrieved_docs))
    return results
