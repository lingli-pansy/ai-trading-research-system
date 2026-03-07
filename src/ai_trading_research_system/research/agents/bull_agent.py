from .base import BaseAgent
from ..schemas import ResearchContext

class BullThesisAgent(BaseAgent):
    name = "bull"

    def run(self, context: ResearchContext) -> dict:
        return {
            "thesis": "Market may still be repricing stronger medium-term growth rather than just reacting to short-term momentum.",
            "supporting_evidence": ["Cross-source evidence points to resilient demand and acceptable operating leverage."],
        }
