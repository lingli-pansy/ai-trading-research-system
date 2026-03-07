"""
Backtest pipeline: Research → Contract → Translator → BacktestRunner → Experience Store.
"""
from __future__ import annotations

from dataclasses import dataclass

from ai_trading_research_system.research.orchestrator import ResearchOrchestrator
from ai_trading_research_system.research.schemas import DecisionContract
from ai_trading_research_system.strategy.translator import ContractTranslator
from ai_trading_research_system.backtest.runner import run_backtest, BacktestMetrics
from ai_trading_research_system.experience.store import write_backtest_result


@dataclass
class BacktestPipeResult:
    contract: DecisionContract
    metrics: BacktestMetrics
    strategy_run_id: int


def run(
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    use_mock: bool = False,
    use_llm: bool = False,
) -> BacktestPipeResult:
    """
    Run Research → Contract → Translator → BacktestRunner → Store.
    Returns contract, backtest metrics, and strategy_run id from store.
    """
    start = start_date or _default_start()
    end = end_date or _default_end()
    orchestrator = ResearchOrchestrator(use_mock=use_mock, use_llm=use_llm)
    contract = orchestrator.run(symbol)
    signal = ContractTranslator().translate(contract)
    metrics = run_backtest(symbol=symbol, signal=signal, start_date=start, end_date=end)
    run_id = write_backtest_result(
        symbol=symbol,
        start_date=start,
        end_date=end,
        metrics=metrics,
    )
    return BacktestPipeResult(contract=contract, metrics=metrics, strategy_run_id=run_id)


def _default_start() -> str:
    from datetime import datetime, timedelta
    return (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d")


def _default_end() -> str:
    from datetime import datetime
    return datetime.utcnow().strftime("%Y-%m-%d")
