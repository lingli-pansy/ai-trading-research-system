from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import logging
import time

from dotenv import load_dotenv
from pathlib import Path
# 从项目根加载 .env（包在 src/ai_trading_research_system/research/，根在 ../../..）
_env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(_env_path)

from ai_trading_research_system.data.providers import MockDataProvider, YFinanceProvider
from ai_trading_research_system.data.market_data_service import get_market_data_service
from ai_trading_research_system.research.schemas import ResearchContext, DecisionContract
from ai_trading_research_system.research.agents.news_agent import NewsAgent
from ai_trading_research_system.research.agents.fundamental_agent import FundamentalAgent
from ai_trading_research_system.research.agents.technical_agent import TechnicalContextAgent
from ai_trading_research_system.research.agents.bull_agent import BullThesisAgent
from ai_trading_research_system.research.agents.bear_agent import BearThesisAgent
from ai_trading_research_system.research.agents.uncertainty_agent import UncertaintyAgent
from ai_trading_research_system.research.agents.synthesis_agent import SynthesisAgent
from ai_trading_research_system.research.agents.llm_agent import LLMResearchAgent

logger = logging.getLogger(__name__)


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
            self.data_provider = MockDataProvider() if use_mock else YFinanceProvider(fallback_to_mock=False)
        self.use_mock = use_mock
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
        # 并行拉取 price / fundamentals / news，避免 yfinance 串行拖慢（ticker.info / news 常 10–30s）
        t0 = time.perf_counter()
        mds = get_market_data_service(for_research=True) if not self.use_mock else None

        def _price() -> "PriceSnapshot":
            from ai_trading_research_system.data.models import PriceSnapshot
            if self.use_mock:
                p = self.data_provider.get_price(symbol)
                return PriceSnapshot(symbol=p.symbol, last_price=p.last_price, change_pct=p.change_pct, volume_ratio=p.volume_ratio)
            snap = mds.get_latest_price(symbol)
            return PriceSnapshot(
                symbol=symbol,
                last_price=snap.last_price,
                change_pct=snap.change_pct,
                volume_ratio=snap.volume_ratio,
            )

        def _fundamentals():
            return self.data_provider.get_fundamentals(symbol)

        def _news():
            return self.data_provider.get_news(symbol)

        with ThreadPoolExecutor(max_workers=3) as ex:
            fut_price = ex.submit(_price)
            fut_fund = ex.submit(_fundamentals)
            fut_news = ex.submit(_news)
            price = fut_price.result()
            fundamentals = fut_fund.result()
            news = fut_news.result()

        ctx_sec = time.perf_counter() - t0
        if ctx_sec > 5.0:
            logger.warning("[research] build_context(%s) took %.1fs (price+fundamentals+news)", symbol, ctx_sec)

        vol_str = f", volume ratio {price.volume_ratio}" if price.volume_ratio is not None else ""
        price_summary = f"{symbol} last price {price.last_price}, daily change {price.change_pct:.1f}%{vol_str}."
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
        context, contract = self.run_with_context(symbol)
        return contract

    def run_with_context(self, symbol: str) -> tuple[ResearchContext, DecisionContract]:
        """Run research and return (context, contract) for reporting (news, price, fundamentals)."""
        t0 = time.perf_counter()
        context = self.build_context(symbol)
        t_ctx = time.perf_counter() - t0
        aggregated: dict = defaultdict(list)

        for agent in self.agents:
            ta = time.perf_counter()
            result = agent.run(context)
            t_agent = time.perf_counter() - ta
            if t_agent > 10.0:
                logger.info("[research] %s agent=%s took %.1fs", symbol, getattr(agent, "name", agent.__class__.__name__), t_agent)
            for key, value in result.items():
                if isinstance(value, list):
                    aggregated[key].extend(value)
                else:
                    aggregated[key] = value

        contract = self.synthesis.run(context, dict(aggregated))
        total = time.perf_counter() - t0
        if total > 15.0:
            logger.info("[research] %s total=%.1fs (context=%.1fs)", symbol, total, t_ctx)
        return context, contract
