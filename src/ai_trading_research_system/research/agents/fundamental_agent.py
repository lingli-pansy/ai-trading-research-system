from .base import BaseAgent
from ..schemas import ResearchContext

class FundamentalAgent(BaseAgent):
    name = "fundamental"

    def run(self, context: ResearchContext) -> dict:
        return {
            "key_drivers": ["revenue growth", "margin resilience"],
            "supporting_evidence": [context.fundamentals_summary],
            "counter_evidence": ["Valuation is no longer cheap relative to historical average."],
        }
