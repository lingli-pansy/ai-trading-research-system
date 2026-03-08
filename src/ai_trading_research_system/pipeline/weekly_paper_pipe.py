"""
UC-09 Weekly Autonomous Paper: 一周自治 paper 编排（controller only）。
职责：snapshot → research → opportunity ranking → allocator → execution；其余委托 services。
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
from ai_trading_research_system.autonomous.opportunity_ranking import OpportunityRanking, OpportunityScore
from ai_trading_research_system.research.orchestrator import ResearchOrchestrator
from ai_trading_research_system.strategy.translator import ContractTranslator
from ai_trading_research_system.execution.nautilus_paper_runner import NautilusPaperRunner
from ai_trading_research_system.services.experience_service import write_weekly_run
from ai_trading_research_system.services.weekly_finish_service import finish_week
from ai_trading_research_system.services.regime_context import get_regime_context


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
    symbols: list[str] | None = None,
) -> WeeklyPaperResult:
    """
    执行一周自治 paper：mandate → snapshot → 每日 research all → rank → allocator → execution。
    symbols 为 watchlist；空则默认单 symbol。Experience 写入含 weekly_portfolio_experience。
    """
    mandate = mandate_from_cli(
        capital=capital,
        benchmark=benchmark,
        duration_days=duration_days,
        auto_confirm=auto_confirm,
        watchlist=symbols,
    )
    sm = AutonomousExecutionStateMachine()
    sm.start()
    snapshot = get_account_snapshot(paper=True, mock=use_mock, initial_cash=capital, allow_fallback=True)
    allocator = PortfolioAllocator(max_position_pct=0.25)
    ranker = OpportunityRanking()
    orchestrator = ResearchOrchestrator(use_mock=use_mock, use_llm=use_llm)
    translator = ContractTranslator()
    symbols_list = mandate.watchlist
    total_pnl = 0.0
    total_trades = 0
    run_ids: list[int] = []
    key_trades: list[str] = []
    no_trade_reasons: list[str] = []
    daily_research: list[dict[str, Any]] = []
    opportunity_ranking_week: list[dict[str, Any]] = []
    replacement_decisions_week: list[dict[str, Any]] = []
    retained_positions_week: list[dict[str, Any]] = []

    spy_trend, vix_level = get_regime_context(use_mock)
    current_positions = {p.get("symbol"): p for p in (snapshot.positions or []) if p.get("symbol")}

    for day in range(duration_days):
        contracts_for_day: list[tuple[str, Any, Any]] = []
        for sym in symbols_list:
            context, contract = orchestrator.run_with_context(sym)
            contracts_for_day.append((sym, context, contract))
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
        if not contracts_for_day:
            continue
        ranked: list[OpportunityScore] = ranker.rank([(s, c) for s, _, c in contracts_for_day])
        contract_by_symbol = {s: (ctx, c) for s, ctx, c in contracts_for_day}
        wait_any = any(
            c.suggested_action in ("wait_confirmation", "watch", "forbid_trade") or c.confidence == "low"
            for _, _, c in contracts_for_day
        )
        signals = []
        for o in ranked:
            _, contract = contract_by_symbol[o.symbol]
            signal = translator.translate(contract)
            signals.append({
                "symbol": o.symbol,
                "size_fraction": signal.allowed_position_size,
                "rationale": signal.rationale,
                "score": o.score,
            })
        alloc_result: AllocationResult = allocator.allocate(snapshot, mandate, signals, wait_confirmation=wait_any)
        opportunity_ranking_week = [{"symbol": o.symbol, "score": o.score, "confidence": o.confidence, "risk": o.risk} for o in ranked]
        replacement_decisions_week.extend(alloc_result.replacement_decisions)
        retained = [t for t in alloc_result.target_positions if t.get("symbol") in current_positions]
        retained_positions_week.extend(retained)

        if alloc_result.no_trade:
            no_trade_reasons.append(alloc_result.no_trade_reason or "no_trade")
            continue
        day_pnl = 0.0
        day_trades = 0
        for target in alloc_result.target_positions:
            sym = target.get("symbol", "")
            if not sym or sym not in contract_by_symbol:
                continue
            _, contract = contract_by_symbol[sym]
            signal = translator.translate(contract)
            runner = NautilusPaperRunner(sym, lookback_days=5)
            runner.inject(signal)
            runner.start()
            result = runner.run_once(122.5, use_mock=use_mock)
            runner.stop()
            day_pnl += result.pnl
            day_trades += result.trade_count
            if result.trade_count > 0:
                key_trades.append(f"{sym} trades={result.trade_count} pnl={result.pnl:.2f}")
            ctx = contract_by_symbol[sym][0]
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
                    "news_snippets": getattr(ctx, "news_summaries", [])[:3],
                    "price_summary": getattr(ctx, "price_summary", ""),
                },
                regime_tag="weekly_paper",
                spy_trend=spy_trend,
                vix_level=vix_level,
            )
            run_ids.append(run_id)
        total_pnl += day_pnl
        total_trades += day_trades

    sm.complete_week()
    report_dir = report_dir or Path(".")
    turnover_pct = min(100.0, 10.0 * total_trades) if total_trades else 0.0
    return finish_week(
        mandate=mandate,
        capital=capital,
        benchmark=benchmark,
        duration_days=duration_days,
        total_pnl=total_pnl,
        total_trades=total_trades,
        run_ids=run_ids,
        key_trades=key_trades,
        no_trade_reasons=no_trade_reasons,
        daily_research=daily_research,
        snapshot_source=snapshot.source,
        use_mock=use_mock,
        state=sm.state,
        report_dir=report_dir,
        turnover_pct=turnover_pct,
        max_drawdown=0.0,
        opportunity_ranking=opportunity_ranking_week,
        replacement_decisions=replacement_decisions_week,
        retained_positions=retained_positions_week,
    )
