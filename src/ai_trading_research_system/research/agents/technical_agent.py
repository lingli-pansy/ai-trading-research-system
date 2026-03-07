from .base import BaseAgent
from ..schemas import ResearchContext


class TechnicalContextAgent(BaseAgent):
    """Uses context.price_summary; counter only when daily change is negative (overextension risk)."""

    name = "technical"

    def run(self, context: ResearchContext) -> dict:
        support = [context.price_summary]
        # Fewer counter when price is up so Contract can vary: probe_small when up, wait when down
        if "daily change -" in context.price_summary or "daily change -" in context.fundamentals_summary:
            counter = ["Short-term extension after recent upside may lead to choppy follow-through."]
        else:
            counter = []
        return {"supporting_evidence": support, "counter_evidence": counter}
