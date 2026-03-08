"""
UC-09 Weekly Autonomous Paper: 一周自治 paper 编排（controller only）。
职责：snapshot → research → opportunity ranking → allocator → execution；其余委托 services。
"""
from __future__ import annotations

from dataclasses import dataclass, field
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
from ai_trading_research_system.autonomous.trigger_evaluator import evaluate_intraday_triggers
from ai_trading_research_system.research.orchestrator import ResearchOrchestrator
from ai_trading_research_system.strategy.translator import ContractTranslator
from ai_trading_research_system.execution.nautilus_paper_runner import NautilusPaperRunner
from ai_trading_research_system.services.experience_service import write_weekly_run
from ai_trading_research_system.services.weekly_finish_service import finish_week
from ai_trading_research_system.services.regime_context import get_regime_context
from ai_trading_research_system.services.benchmark_service import get_benchmark_return, get_benchmark_returns_and_volatility
from ai_trading_research_system.experience.store import write_intraday_trigger_event, write_health_trigger_event
from ai_trading_research_system.autonomous.portfolio_health import evaluate_portfolio_health
from ai_trading_research_system.autonomous.adjustment_trigger import (
    TRIGGER_CONCENTRATION_RISK,
    TRIGGER_BETA_SPIKE,
    TRIGGER_EXCESS_DRAWDOWN,
)


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
    evolution_decision: dict[str, Any] = field(default_factory=dict)


def run_weekly_autonomous_paper(
    *,
    mandate: Any = None,
    capital: float = 10_000.0,
    benchmark: str = "SPY",
    duration_days: int = 5,
    auto_confirm: bool = True,
    use_mock: bool = False,
    use_llm: bool = False,
    report_dir: Path | None = None,
    symbols: list[str] | None = None,
    experiment_id: str = "",
    cycle_number: int = 0,
    policy_version: str = "",
) -> WeeklyPaperResult:
    """
    执行一周自治 paper：mandate → snapshot → 每日 research all → rank → allocator → execution。
    mandate 可选；未传则 mandate_from_cli。symbols 为 watchlist；空则默认单 symbol。
    """
    if mandate is None:
        mandate = mandate_from_cli(
            capital=capital,
            benchmark=benchmark,
            duration_days=duration_days,
            auto_confirm=auto_confirm,
            watchlist=symbols,
        )
    else:
        capital = getattr(mandate, "capital_limit", capital) or capital
        benchmark = getattr(mandate, "benchmark", benchmark) or benchmark
        duration_days = getattr(mandate, "duration_trading_days", duration_days) or duration_days
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
    rejected_opportunities_week: list[dict[str, Any]] = []
    policy_summary_week: dict[str, Any] = {}
    intraday_adjustments_week: list[dict[str, Any]] = []
    health_based_adjustments_week: list[dict[str, Any]] = []
    portfolio_returns_list: list[float] = []
    decision_traces_week: list[dict[str, Any]] = []
    trigger_traces_week: list[dict[str, Any]] = []

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
        opportunity_ranking_week = [{"symbol": o.symbol, "score": o.score, "confidence": o.confidence, "risk": o.risk} for o in ranked]
        spy_returns, bench_ret_day, vol_day, max_dd_day = get_benchmark_returns_and_volatility(
            symbol=benchmark, lookback_days=min(max(day + 1, 2), 21)
        )
        n = min(len(portfolio_returns_list), len(spy_returns))
        portfolio_returns_aligned = portfolio_returns_list[-n:] if n else []
        spy_aligned = spy_returns[-n:] if n else []
        benchmark_data_day = {
            "benchmark_return": bench_ret_day,
            "volatility": vol_day,
            "max_drawdown": max_dd_day,
            "portfolio_returns": portfolio_returns_aligned,
            "spy_returns": spy_aligned,
        }
        health_day = evaluate_portfolio_health(
            snapshot, benchmark_data_day, snapshot.positions or [], initial_equity=capital
        )
        trigger, trigger_trace = evaluate_intraday_triggers(
            snapshot,
            opportunity_ranking_week,
            current_positions,
            mandate.policy,
            initial_equity=capital,
            portfolio_health=health_day,
        )
        trigger_traces_week.append(trigger_trace.to_dict() if hasattr(trigger_trace, "to_dict") else trigger_trace)
        if trigger is None:
            no_trade_reasons.append("no_trigger")
            continue
        if trigger.trigger_type in (TRIGGER_CONCENTRATION_RISK, TRIGGER_BETA_SPIKE, TRIGGER_EXCESS_DRAWDOWN):
            health_based_adjustments_week.append({
                "trigger_type": trigger.trigger_type,
                "trigger_reason": trigger.trigger_reason,
                "severity": trigger.severity,
                "period": f"day_{day}",
            })
            write_health_trigger_event(
                mandate_id=mandate.mandate_id,
                period=f"day_{day}",
                trigger_type=trigger.trigger_type,
                trigger_reason=trigger.trigger_reason,
                severity=trigger.severity,
                health_snapshot_excerpt=health_day.to_dict(),
            )
        alloc_result: AllocationResult = allocator.allocate(
            snapshot,
            mandate,
            signals,
            wait_confirmation=wait_any,
            portfolio_health=health_day,
            trigger_context=trigger_trace.to_dict() if hasattr(trigger_trace, "to_dict") else {},
        )
        decision_traces_week.extend(getattr(alloc_result, "decision_traces", []) or [])
        replacement_decisions_week.extend(alloc_result.replacement_decisions)
        positions_changed = [t.get("symbol") for t in alloc_result.target_positions if t.get("symbol")]
        intraday_adjustments_week.append({
            "trigger_type": trigger.trigger_type,
            "positions_changed": positions_changed,
            "rationale": trigger.trigger_reason,
        })
        write_intraday_trigger_event(
            mandate_id=mandate.mandate_id,
            period=f"day_{day}",
            trigger_type=trigger.trigger_type,
            trigger_reason=trigger.trigger_reason,
            severity=trigger.severity,
            positions_changed=positions_changed,
        )
        retained_positions_week.extend(alloc_result.retained_positions)
        rejected_opportunities_week.extend(alloc_result.rejected_opportunities)
        ps = alloc_result.policy_summary
        prev = policy_summary_week
        policy_summary_week = {
            "score_gap_used": ps.get("score_gap_used") if ps.get("score_gap_used") is not None else prev.get("score_gap_used"),
            "replacements_executed": prev.get("replacements_executed", 0) + ps.get("replacements_executed", 0),
            "replacements_skipped_due_to_threshold": prev.get("replacements_skipped_due_to_threshold", 0) + ps.get("replacements_skipped_due_to_threshold", 0),
            "replacements_skipped_due_to_budget": prev.get("replacements_skipped_due_to_budget", 0) + ps.get("replacements_skipped_due_to_budget", 0),
            "rejected_due_to_threshold": prev.get("rejected_due_to_threshold", 0) + ps.get("rejected_due_to_threshold", 0),
        }

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
        portfolio_returns_list.append(day_pnl / capital if capital else 0.0)

    sm.complete_week()
    report_dir = report_dir or Path(".")
    turnover_pct = min(100.0, 10.0 * total_trades) if total_trades else 0.0
    spy_returns_week, benchmark_return_week, vol_week, max_dd_week = get_benchmark_returns_and_volatility(
        symbol=benchmark, lookback_days=max(duration_days, 2)
    )
    n_week = min(len(portfolio_returns_list), len(spy_returns_week))
    portfolio_returns_week = portfolio_returns_list[-n_week:] if n_week else []
    spy_week = spy_returns_week[-n_week:] if n_week else []
    benchmark_data_week = {
        "benchmark_return": benchmark_return_week,
        "volatility": vol_week,
        "max_drawdown": max_dd_week,
        "portfolio_returns": portfolio_returns_week,
        "spy_returns": spy_week,
    }
    health = evaluate_portfolio_health(
        snapshot,
        benchmark_data_week,
        snapshot.positions or [],
        initial_equity=capital,
    )
    portfolio_health = health.to_dict()
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
        rejected_opportunities=rejected_opportunities_week,
        policy_summary=policy_summary_week,
        intraday_adjustments=intraday_adjustments_week,
        portfolio_health=portfolio_health,
        health_based_adjustments=health_based_adjustments_week,
        experiment_id=experiment_id or "",
        cycle_number=cycle_number or 0,
        policy_version=policy_version or "",
        decision_traces=decision_traces_week,
        trigger_traces=trigger_traces_week,
    )
