from .base import BaseAgent
from ..schemas import ResearchContext

class TechnicalContextAgent(BaseAgent):
    name = "technical"

    def run(self, context: ResearchContext) -> dict:
        return {
            "supporting_evidence": [context.price_summary],
            "counter_evidence": ["Short-term extension after recent upside may lead to choppy follow-through."],
        }
