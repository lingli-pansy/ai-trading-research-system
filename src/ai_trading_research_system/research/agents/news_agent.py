from .base import BaseAgent
from ..schemas import ResearchContext

class NewsAgent(BaseAgent):
    name = "news"

    def run(self, context: ResearchContext) -> dict:
        support = [f"News flow supportive: {item}" for item in context.news_summaries[:1]]
        uncertainties = ["Need follow-through from next news cycle to confirm demand durability."]
        return {"supporting_evidence": support, "uncertainties": uncertainties}
