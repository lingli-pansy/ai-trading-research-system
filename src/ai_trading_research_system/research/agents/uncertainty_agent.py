from .base import BaseAgent
from ..schemas import ResearchContext

class UncertaintyAgent(BaseAgent):
    name = "uncertainty"

    def run(self, context: ResearchContext) -> dict:
        return {
            "uncertainties": [
                "Need confirmation that recent demand commentary converts into reported revenue.",
                "Market regime could shift if macro risk-off returns.",
            ]
        }
