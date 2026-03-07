from collections import defaultdict
from ai_trading_research_system.data.providers import MockDataProvider
from ai_trading_research_system.research.schemas import ResearchContext, DecisionContract
from ai_trading_research_system.research.agents.news_agent import NewsAgent
from ai_trading_research_system.research.agents.fundamental_agent import FundamentalAgent
from ai_trading_research_system.research.agents.technical_agent import TechnicalContextAgent
from ai_trading_research_system.research.agents.bull_agent import BullThesisAgent
from ai_trading_research_system.research.agents.bear_agent import BearThesisAgent
from ai_trading_research_system.research.agents.uncertainty_agent import UncertaintyAgent
from ai_trading_research_system.research.agents.synthesis_agent import SynthesisAgent

class ResearchOrchestrator:
    def __init__(self, data_provider: MockDataProvider | None = None):
        self.data_provider = data_provider or MockDataProvider()
        self.agents = [
            NewsAgent(),
            FundamentalAgent(),
            TechnicalContextAgent(),
            BullThesisAgent(),
            BearThesisAgent(),
            UncertaintyAgent(),
        ]
        self.synthesis = SynthesisAgent()

    def build_context(self, symbol: str) -> ResearchContext:
        price = self.data_provider.get_price(symbol)
        fundamentals = self.data_provider.get_fundamentals(symbol)
        news = self.data_provider.get_news(symbol)

        price_summary = f"{symbol} last price {price.last_price}, daily change {price.change_pct:.1f}%, volume ratio {price.volume_ratio}."
        fundamentals_summary = (
            f"Revenue growth {fundamentals.revenue_growth:.0%}, gross margin {fundamentals.gross_margin:.0%}, "
            f"PE TTM {fundamentals.pe_ttm}. Notes: {fundamentals.notes}"
        )
        news_summaries = [f"{item.title} — {item.summary}" for item in news]

        return ResearchContext(
            symbol=symbol,
            price_summary=price_summary,
            fundamentals_summary=fundamentals_summary,
            news_summaries=news_summaries,
        )

    def run(self, symbol: str) -> DecisionContract:
        context = self.build_context(symbol)
        aggregated: dict = defaultdict(list)

        for agent in self.agents:
            result = agent.run(context)
            for key, value in result.items():
                if isinstance(value, list):
                    aggregated[key].extend(value)
                else:
                    aggregated[key] = value

        return self.synthesis.run(context, dict(aggregated))
