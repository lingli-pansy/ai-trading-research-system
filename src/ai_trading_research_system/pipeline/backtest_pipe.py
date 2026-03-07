"""
Backtest pipeline: Research → Contract → Translator → BacktestRunner → Experience Store.
统一通过 experience/writer.write_run_result 写入，并落库 StrategySpec 快照。
"""
from __future__ import annotations

from dataclasses import dataclass

from ai_trading_research_system.research.orchestrator import ResearchOrchestrator
from ai_trading_research_system.research.schemas import DecisionContract
from ai_trading_research_system.strategy.translator import ContractTranslator
from ai_trading_research_system.strategy.spec_snapshot import contract_to_spec_snapshot
from ai_trading_research_system.backtest.runner import run_backtest, BacktestMetrics
from ai_trading_research_system.experience.writer import write_run_result, RunResultPayload


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
    Writes via write_run_result with strategy_spec_snapshot in parameters.
    Returns contract, backtest metrics, and strategy_run id from store.
    """
    start = start_date or _default_start()
    end = end_date or _default_end()
    orchestrator = ResearchOrchestrator(use_mock=use_mock, use_llm=use_llm)
    contract = orchestrator.run(symbol)
    signal = ContractTranslator().translate(contract)
    metrics = run_backtest(symbol=symbol, signal=signal, start_date=start, end_date=end)
    spec_snapshot = contract_to_spec_snapshot(contract, metrics)
    payload = RunResultPayload(
        symbol=symbol,
        start_date=start,
        end_date=end,
        sharpe=metrics.sharpe,
        max_drawdown=metrics.max_drawdown,
        win_rate=metrics.win_rate,
        pnl=metrics.pnl,
        trade_count=metrics.trade_count,
        extra={"strategy_spec_snapshot": spec_snapshot},
    )
    run_id = write_run_result(payload)
    return BacktestPipeResult(contract=contract, metrics=metrics, strategy_run_id=run_id)


def _default_start() -> str:
    from datetime import datetime, timedelta
    return (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d")


def _default_end() -> str:
    from datetime import datetime
    return datetime.utcnow().strftime("%Y-%m-%d")
