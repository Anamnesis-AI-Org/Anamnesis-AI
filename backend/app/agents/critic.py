import json

from pydantic import ValidationError

from app.llm_client import AgentResponseError, call_agent
from app.prompts import CRITIC_PROMPT
from app.schemas import (
	CriticOutput, EconomistOutput, HistorianOutput, SocietyOutput, 
	TechnologyOutput, ClimateOutput, PoliticalOutput, EnergyOutput, 
	HealthcareOutput, DemographicsOutput
)


async def run_critic(
	historian: HistorianOutput,
	economist: EconomistOutput | None = None,
	technology: TechnologyOutput | None = None,
	society: SocietyOutput | None = None,
	climate: ClimateOutput | None = None,
	political: PoliticalOutput | None = None,
	energy: EnergyOutput | None = None,
	healthcare: HealthcareOutput | None = None,
	demographics: DemographicsOutput | None = None,
) -> CriticOutput:
	# Conditional participation: domain agents that were skipped for this
	# scenario arrive as None and are omitted from the critic payload.
	payload = {
		"historian": historian.model_dump(),
	}
	for name, output in (
		("economist", economist),
		("technology", technology),
		("society", society),
		("climate", climate),
		("political", political),
		("energy", energy),
		("healthcare", healthcare),
		("demographics", demographics),
	):
		if output is not None:
			payload[name] = output.model_dump()
	result = await call_agent(CRITIC_PROMPT, json.dumps(payload))
	try:
		output = CriticOutput.model_validate(result)
	except ValidationError as exc:
		raise AgentResponseError(str(exc)) from exc
	output.confidence_score = max(0, min(100, output.confidence_score))
	return output