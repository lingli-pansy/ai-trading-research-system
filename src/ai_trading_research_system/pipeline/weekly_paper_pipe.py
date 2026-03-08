"""
UC-09 Weekly Autonomous Paper: 一周自治 paper 编排（controller only）。
职责：snapshot → research → strategy → allocation → execution；其余委托 services（benchmark、report、experience）。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_trading_research_system.autonomous import (
    get_account_snapshot,
    mandate_from_cli,
    PortfolioAllocator,
    AutonomousExecutionStateMachine,
    AllocationResult,
)
from ai_trading_research_system.autonomous.schemas import WeeklyTradingMandate, AccountSnapshot
from ai_trading_research_system.research.orchestrator import ResearchOrchestrator
from ai_trading_research_system.strategy.translator import ContractTranslator
from ai_trading_research_system.execution.nautilus_paper_runner import NautilusPaperRunner
from ai_trading_research_system.services.benchmark_service import get_benchmark_return, compare_to_benchmark
from ai_trading_research_system.services.report_service import (
    generate_and_write as report_generate_and_write,
    build_weekly_result_summary,
)
from ai_trading_research_system.services.experience_service import write_weekly_run


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
    use_mock: bool = False,
    use_llm: bool = False,
    report_dir: Path | None = None,
) -> WeeklyPaperResult:
    """
    执行一周自治 paper：mandate → snapshot → 多轮 research/allocator/paper → benchmark_service → report_service。
    Experience 写入由 experience_service 完成。
    """
    mandate = mandate_from_cli(
        capital=capital,
        benchmark=benchmark,
        duration_days=duration_days,
        auto_confirm=auto_confirm,
    )
    sm = AutonomousExecutionStateMachine()
    sm.start()
    snapshot = get_account_snapshot(paper=True, mock=use_mock, initial_cash=capital, allow_fallback=True)
    allocator = PortfolioAllocator(max_position_pct=0.25)
    orchestrator = ResearchOrchestrator(use_mock=use_mock, use_llm=use_llm)
    translator = ContractTranslator()
    symbols = ["NVDA"]
    total_pnl = 0.0
    total_trades = 0
    run_ids: list[int] = []
    key_trades: list[str] = []
    no_trade_reasons: list[str] = []
    daily_research: list[dict[str, Any]] = []

    for day in range(duration_days):
        day_pnl = 0.0
        day_trades = 0
        for sym in symbols:
            context, contract = orchestrator.run_with_context(sym)
            daily_research.append({
                "day": day,
                "symbol": sym,
                "thesis": contract.thesis,
                "suggested_action": contract.suggested_action,
                "confidence": contract.confidence,
                "key_drivers": contract.key_drivers[:5],
                "news_snippets": context.news_summaries[:5],
                "price_summary": context.price_summary,
                "fundamentals_summary": context.fundamentals_summary,
            })
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
            run_id = write_weekly_run(
                sym,
                result.pnl,
                result.trade_count,
                extra={
                    "weekly_paper_day": day,
                    "mandate_id": mandate.mandate_id,
                    "thesis": contract.thesis,
                    "suggested_action": contract.suggested_action,
                    "confidence": contract.confidence,
                    "news_snippets": context.news_summaries[:3],
                    "price_summary": context.price_summary,
                },
                regime_tag="weekly_paper",
            )
            run_ids.append(run_id)
        total_pnl += day_pnl
        total_trades += day_trades

    sm.complete_week()
    portfolio_return = total_pnl / capital if capital else 0.0
    benchmark_return, benchmark_source = get_benchmark_return(
        symbol=benchmark,
        lookback_days=duration_days,
    )
    if use_mock:
        benchmark_source = "mock"
    bench_result = compare_to_benchmark(
        portfolio_return=portfolio_return,
        benchmark_return=benchmark_return,
        max_drawdown=0.0,
        trade_count=total_trades,
        period=f"day_0_to_{duration_days}",
        benchmark_source=benchmark_source,
    )
    report_dir = report_dir or Path(".")
    report_path = report_generate_and_write(
        mandate,
        bench_result,
        key_trades=key_trades,
        risk_events=[],
        no_trade_days=sum(1 for _ in no_trade_reasons),
        no_trade_reasons=no_trade_reasons[:5],
        daily_research=daily_research,
        report_dir=report_dir,
    )
    market_data_source = "mock" if use_mock else "yfinance"
    summary = build_weekly_result_summary(
        portfolio_return=portfolio_return,
        benchmark_return=benchmark_return,
        excess_return=bench_result.excess_return,
        total_trades=total_trades,
        total_pnl=total_pnl,
        report_path=report_path,
        daily_research_count=len(daily_research),
        snapshot_source=snapshot.source,
        market_data_source=market_data_source,
        benchmark_source=benchmark_source,
    )
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
