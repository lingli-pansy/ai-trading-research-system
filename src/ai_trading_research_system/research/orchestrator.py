from collections import defaultdict

from dotenv import load_dotenv
from pathlib import Path
# 从项目根加载 .env（包在 src/ai_trading_research_system/research/，根在 ../../..）
_env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(_env_path)

from ai_trading_research_system.data.providers import MockDataProvider, YFinanceProvider
from ai_trading_research_system.research.schemas import ResearchContext, DecisionContract
from ai_trading_research_system.research.agents.news_agent import NewsAgent
from ai_trading_research_system.research.agents.fundamental_agent import FundamentalAgent
from ai_trading_research_system.research.agents.technical_agent import TechnicalContextAgent
from ai_trading_research_system.research.agents.bull_agent import BullThesisAgent
from ai_trading_research_system.research.agents.bear_agent import BearThesisAgent
from ai_trading_research_system.research.agents.uncertainty_agent import UncertaintyAgent
from ai_trading_research_system.research.agents.synthesis_agent import SynthesisAgent
from ai_trading_research_system.research.agents.llm_agent import LLMResearchAgent

class ResearchOrchestrator:
    # TODO(phase): TradingAgents 真接入时可通过 adapter 注入 graph，替代当前 agents 列表；见 docs/next_phase_interface.md
    def __init__(
        self,
        data_provider: MockDataProvider | YFinanceProvider | None = None,
        use_mock: bool = True,
        use_llm: bool = False,
    ):
        if data_provider is not None:
            self.data_provider = data_provider
        else:
            self.data_provider = MockDataProvider() if use_mock else YFinanceProvider()
        if use_llm:
            self.agents = [LLMResearchAgent()]
        else:
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
        rev = fundamentals.revenue_growth if fundamentals.revenue_growth is not None else 0.0
        gross = fundamentals.gross_margin if fundamentals.gross_margin is not None else 0.0
        pe = fundamentals.pe_ttm if fundamentals.pe_ttm is not None else 0.0
        notes = fundamentals.notes or "N/A"
        fundamentals_summary = (
            f"Revenue growth {rev:.0%}, gross margin {gross:.0%}, "
            f"PE TTM {pe}. Notes: {notes}"
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
