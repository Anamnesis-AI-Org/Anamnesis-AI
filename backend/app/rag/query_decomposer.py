"""query_decomposer.py — LLM-powered search query decomposition."""

import logging
from app.llm_client import call_agent
from app.schemas import ScenarioContext

logger = logging.getLogger(__name__)

# One decomposition per scenario: the 9 agent nodes share a ScenarioContext, so
# without this cache every run burns 9 identical Gemini calls. keyed by the
# scenario text + divergence year + horizon + domains.
_decompose_cache: dict[str, dict[str, str]] = {}

DECOMPOSER_PROMPT = """You are the search query optimizer for Anamnesis-AI.
Your job is to decompose the user's alternate-reality scenario and divergence context into specific, highly targeted search queries for various search engines and database portals.

Generate queries for:
1. wikipedia: General historical context, key figures, and timeline events surrounding the divergence.
2. worldbank: Socio-economic metrics, trade indicators, population growth, and production variables.
3. un_data: Sustainable development indicators, social progress, education, policy.
4. nasa: Climate anomalies, geographic variables, long-term environmental factors.
5. noaa: Regional temperatures, carbon concentrations, extreme weather indices.
6. arxiv: Academic literature, technical frameworks, theoretical physics, or modeling papers.

You must respond with ONLY a JSON object of the following format (do not include markdown code fences or explanations):
{
  "wikipedia": "wikipedia query",
  "worldbank": "worldbank indicator keywords",
  "un_data": "un data keywords",
  "nasa": "nasa earth science keywords",
  "noaa": "noaa weather climate keywords",
  "arxiv": "arxiv paper keywords"
}"""

async def decompose_query(context: ScenarioContext) -> dict[str, str]:
    """Decompose high-level scenario context into search queries for different sources."""
    cache_key = (
        f"{context.scenario}|{context.divergence_year}|"
        f"{context.time_horizon}|{','.join(context.focus_domains)}"
    )
    cached = _decompose_cache.get(cache_key)
    if cached is not None:
        logger.info("RAG Decomposer │ Cache HIT — reusing decomposed queries")
        return cached
    user_content = (
        f"Scenario: {context.scenario}\n"
        f"Divergence Year: {context.divergence_year}\n"
        f"Time Horizon: {context.time_horizon}\n"
        f"Focus Domains: {', '.join(context.focus_domains)}"
    )
    
    logger.info("RAG Decomposer │ Decomposing scenario query: %s...", context.scenario[:50])
    try:
        result = await call_agent(DECOMPOSER_PROMPT, user_content)
        # Validate that the returned dict has all expected keys, fallback to defaults if not
        keys = ["wikipedia", "worldbank", "un_data", "nasa", "noaa", "arxiv"]
        decomposed = {}
        for key in keys:
            val = result.get(key, "")
            if not val or not isinstance(val, str):
                # Fallback to simple default queries
                if key == "wikipedia":
                    decomposed[key] = f"{context.scenario} history"
                elif key == "worldbank":
                    decomposed[key] = f"GDP economic development {context.scenario[:30]}"
                elif key == "un_data":
                    decomposed[key] = f"development indicators {context.scenario[:30]}"
                elif key in ("nasa", "noaa"):
                    decomposed[key] = f"climate environment temperature {context.scenario[:30]}"
                else:
                    decomposed[key] = f"research paper model {context.scenario[:30]}"
            else:
                decomposed[key] = val
        
        logger.info("RAG Decomposer │ Successfully decomposed queries into %d sources", len(decomposed))
        _decompose_cache[cache_key] = decomposed
        # Bound the cache so a long-lived process cannot grow without limit.
        if len(_decompose_cache) > 32:
            _decompose_cache.pop(next(iter(_decompose_cache)))
        return decomposed
    except Exception as e:
        logger.error("RAG Decomposer │ Decomposer failed: %s. Using default queries.", e)
        # Complete fallback
        fallback = {
            "wikipedia": f"{context.scenario} history {context.divergence_year}",
            "worldbank": "economic metrics GDP",
            "un_data": "sustainable development index",
            "nasa": "climate global temperature anomalies",
            "noaa": "precipitation weather records",
            "arxiv": "simulation counterfactual model"
        }
        _decompose_cache[cache_key] = fallback
        return fallback
