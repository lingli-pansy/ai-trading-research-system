"""
UC-09 Weekly Autonomous Paper: 一周自治 paper 编排。
接入 research -> strategy -> nautilus paper 主线；写入 Experience Store；产出周报与 benchmark 对比。
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_trading_research_system.autonomous import (
    get_account_snapshot,
    mandate_from_cli,
    PortfolioAllocator,
    AutonomousExecutionStateMachine,
    BenchmarkComparator,
    WeeklyReportGenerator,
    AllocationResult,
    BenchmarkResult,
    WeeklyReport,
)
from ai_trading_research_system.autonomous.schemas import WeeklyTradingMandate, AccountSnapshot
from ai_trading_research_system.research.orchestrator import ResearchOrchestrator
from ai_trading_research_system.strategy.translator import ContractTranslator
from ai_trading_research_system.execution.nautilus_paper_runner import NautilusPaperRunner
from ai_trading_research_system.backtest.runner import run_paper_simulation, BacktestMetrics
from ai_trading_research_system.experience.writer import write_run_result, RunResultPayload


@dataclass
class WeeklyPaperResult:
    ok: bool
    mandate_id: str
    status: str
    capital_limit: float
    benchmark: str
    engine_type: str
    used_nautilus: bool
    report_path: str
    summary: dict[str, Any]
    strategy_run_ids: list[int]


def run_weekly_autonomous_paper(
    *,
    capital: float = 10_000.0,
    benchmark: str = "SPY",
    duration_days: int = 5,
    auto_confirm: bool = True,
    use_mock: bool = True,
    use_llm: bool = False,
    report_dir: Path | None = None,
) -> WeeklyPaperResult:
    """
    执行一周自治 paper：mandate -> snapshot -> 多轮 research/allocator/paper -> benchmark -> report -> store。
    默认 5 个 trading day 用 5 次迭代模拟（同一天内跑完），走 Nautilus 主线。
    """
    mandate = mandate_from_cli(
        capital=capital,
        benchmark=benchmark,
        duration_days=duration_days,
        auto_confirm=auto_confirm,
    )
    sm = AutonomousExecutionStateMachine()
    sm.start()
    snapshot = get_account_snapshot(paper=True, mock=True, initial_cash=capital)
    allocator = PortfolioAllocator(max_position_pct=0.25)
    orchestrator = ResearchOrchestrator(use_mock=use_mock, use_llm=use_llm)
    translator = ContractTranslator()
    # 默认 watchlist：单标的 NVDA 做最小闭环
    symbols = ["NVDA"]
    total_pnl = 0.0
    total_trades = 0
    run_ids: list[int] = []
    key_trades: list[str] = []
    no_trade_reasons: list[str] = []

    for day in range(duration_days):
        day_pnl = 0.0
        day_trades = 0
        for sym in symbols:
            contract = orchestrator.run(sym)
            signal = translator.translate(contract)
            wait = contract.suggested_action in ("wait_confirmation", "watch", "forbid_trade") or contract.confidence == "low"
            signals = [{"symbol": sym, "size_fraction": signal.allowed_position_size, "rationale": signal.rationale}]
            alloc_result = allocator.allocate(snapshot, mandate, signals, wait_confirmation=wait)
            if alloc_result.no_trade:
                no_trade_reasons.append(alloc_result.no_trade_reason or "no_trade")
                continue
            runner = NautilusPaperRunner(sym, lookback_days=5)
            runner.inject(signal)
            runner.start()
            result = runner.run_once(122.5, use_mock=use_mock)
            runner.stop()
            day_pnl += result.pnl
            day_trades += result.trade_count
            if result.trade_count > 0:
                key_trades.append(f"{sym} trades={result.trade_count} pnl={result.pnl:.2f}")
            # 写 Experience Store（每轮一次 run）
            start_d = (datetime.now(timezone.utc).date()).isoformat()
            end_d = start_d
            payload = RunResultPayload(
                symbol=sym,
                start_date=start_d,
                end_date=end_d,
                sharpe=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                pnl=result.pnl,
                trade_count=result.trade_count,
                extra={"weekly_paper_day": day, "mandate_id": mandate.mandate_id},
                regime_tag="weekly_paper",
            )
            run_id = write_run_result(payload)
            run_ids.append(run_id)
        total_pnl += day_pnl
        total_trades += day_trades

    sm.complete_week()
    portfolio_return = total_pnl / capital if capital else 0.0
    benchmark_return = 0.0  # mock: SPY 周收益暂用 0；后续可接 yfinance
    comp = BenchmarkComparator()
    bench_result = comp.compare(
        portfolio_return=portfolio_return,
        benchmark_return=benchmark_return,
        max_drawdown=0.0,
        trade_count=total_trades,
        period=f"day_0_to_{duration_days}",
    )
    gen = WeeklyReportGenerator()
    report = gen.generate(
        mandate,
        bench_result,
        key_trades=key_trades,
        risk_events=[],
        no_trade_days=sum(1 for _ in no_trade_reasons),
        no_trade_reasons=no_trade_reasons[:5],
    )
    report_dir = report_dir or Path(".")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = str(report_dir / f"weekly_report_{mandate.mandate_id}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        import json
        json.dump(gen.to_dict(report), f, ensure_ascii=False, indent=2)

    summary = {
        "portfolio_return": portfolio_return,
        "benchmark_return": benchmark_return,
        "excess_return": bench_result.excess_return,
        "trade_count": total_trades,
        "pnl": total_pnl,
        "report_path": report_path,
    }
    return WeeklyPaperResult(
        ok=True,
        mandate_id=mandate.mandate_id,
        status=sm.state,
        capital_limit=capital,
        benchmark=benchmark,
        engine_type="nautilus",
        used_nautilus=True,
        report_path=report_path,
        summary=summary,
        strategy_run_ids=run_ids,
    )
