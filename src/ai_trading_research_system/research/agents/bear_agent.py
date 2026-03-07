from .base import BaseAgent
from ..schemas import ResearchContext

class BearThesisAgent(BaseAgent):
    name = "bear"

    def run(self, context: ResearchContext) -> dict:
        return {
            "counter_evidence": ["Positive narrative may already be partially priced in."],
            "risk_flags": ["valuation_risk"],
        }
