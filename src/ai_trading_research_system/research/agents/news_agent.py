from .base import BaseAgent
from ..schemas import ResearchContext


class NewsAgent(BaseAgent):
    """Uses context.news_summaries so Contract can vary with real data."""

    name = "news"

    def run(self, context: ResearchContext) -> dict:
        support = [f"News: {item}" for item in context.news_summaries[:3]]
        uncertainties = ["Need follow-through from next news cycle to confirm demand durability."]
        # Vary counter_evidence by content length so Synthesis can produce different actions
        if len(context.news_summaries) >= 2:
            uncertainties.append("Multiple news streams; confirm consistency before entry.")
        return {"supporting_evidence": support, "uncertainties": uncertainties}
