"""
Finish week: benchmark + report + summary. Used by weekly_paper_pipe after execution loop only.
Pipe does: mandate, snapshot, research, allocation, execution; this service does the rest.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_trading_research_system.autonomous.schemas import WeeklyTradingMandate
from ai_trading_research_system.services.benchmark_service import get_benchmark_return, compare_to_benchmark
from ai_trading_research_system.services.report_service import (
    generate_and_write as report_generate_and_write,
    build_weekly_result_summary,
)
from ai_trading_research_system.experience.store import (
    write_weekly_portfolio_experience,
    write_portfolio_health_snapshot,
    write_experience_insight_snapshot,
)
from ai_trading_research_system.experience.analyzer import analyze_experience_from_store

# Avoid circular import: pipe defines WeeklyPaperResult
def _result_type():
    from ai_trading_research_system.pipeline.weekly_paper_pipe import WeeklyPaperResult
    return WeeklyPaperResult


def finish_week(
    *,
    mandate: WeeklyTradingMandate,
    capital: float,
    benchmark: str,
    duration_days: int,
    total_pnl: float,
    total_trades: int,
    run_ids: list[int],
    key_trades: list[str],
    no_trade_reasons: list[str],
    daily_research: list[dict[str, Any]],
    snapshot_source: str,
    use_mock: bool,
    state: str,
    report_dir: Path,
    turnover_pct: float = 0.0,
    max_drawdown: float = 0.0,
    opportunity_ranking: list[dict[str, Any]] | None = None,
    replacement_decisions: list[dict[str, Any]] | None = None,
    retained_positions: list[dict[str, Any]] | None = None,
    rejected_opportunities: list[dict[str, Any]] | None = None,
    policy_summary: dict[str, Any] | None = None,
    intraday_adjustments: list[dict[str, Any]] | None = None,
    portfolio_health: dict[str, Any] | None = None,
    health_based_adjustments: list[dict[str, Any]] | None = None,
) -> Any:
    """
    After execution loop: compute benchmark, write report, build summary, return WeeklyPaperResult.
    Pipe must only do mandate, snapshot, research, allocation, execution; then call this.
    """
    WeeklyPaperResult = _result_type()
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
        max_drawdown=max_drawdown,
        trade_count=total_trades,
        period=f"day_0_to_{duration_days}",
        benchmark_source=benchmark_source,
    )
    report_dir = report_dir or Path(".")
    policy_summary = policy_summary or {}
    # Experience-driven insights（基于历史周数据，不含本周）
    insights = analyze_experience_from_store(mandate_id=mandate.mandate_id, limit_weeks=30)
    experience_insights_report = {
        "summary": "本周表现与历史经验对比："
        + ("建议根据下方洞察微调策略或政策。" if insights.strategy_adjustment_suggested else "未触发策略调整建议。"),
        "strategy_adjustment_suggested": insights.strategy_adjustment_suggested,
        "insights": insights.to_dict(),
    }
    why_replacements = ""
    if replacement_decisions:
        why_replacements = f"因新机会分数差达到策略阈值，执行 {len(replacement_decisions)} 次仓位替换。"
    report_path = report_generate_and_write(
        mandate,
        bench_result,
        key_trades=key_trades,
        risk_events=[],
        no_trade_days=len(no_trade_reasons),
        no_trade_reasons=no_trade_reasons[:5],
        daily_research=daily_research,
        report_dir=report_dir,
        turnover_pct=turnover_pct,
        opportunity_ranking=opportunity_ranking or [],
        replacement_decisions=replacement_decisions or [],
        why_replacements_happened=why_replacements,
        why_candidates_rejected=rejected_opportunities or [],
        replacements_skipped_due_to_threshold=policy_summary.get("replacements_skipped_due_to_threshold", 0)
        + policy_summary.get("rejected_due_to_threshold", 0),
        replacements_skipped_due_to_budget=policy_summary.get("replacements_skipped_due_to_budget", 0),
        intraday_adjustments=intraday_adjustments or [],
        portfolio_health=portfolio_health or {},
        health_based_adjustments=health_based_adjustments or [],
        experience_insights=experience_insights_report,
    )
    period = f"day_0_to_{duration_days}"
    if portfolio_health:
        write_portfolio_health_snapshot(mandate_id=mandate.mandate_id, period=period, snapshot=portfolio_health)
    policy_obj = getattr(mandate, "policy", None)
    experience_policy = {
        "score_gap_used": policy_summary.get("score_gap_used"),
        "replacements_executed": policy_summary.get("replacements_executed", 0),
        "replacements_skipped": (policy_summary.get("replacements_skipped_due_to_threshold", 0)
            + policy_summary.get("replacements_skipped_due_to_budget", 0)),
        "rejected_due_to_threshold": policy_summary.get("rejected_due_to_threshold", 0),
        "excess_return": bench_result.excess_return,
    }
    if policy_obj is not None:
        experience_policy["minimum_score_gap_for_replacement"] = policy_obj.minimum_score_gap_for_replacement
        experience_policy["max_replacements_per_rebalance"] = policy_obj.max_replacements_per_rebalance
        experience_policy["turnover_budget"] = policy_obj.turnover_budget
        experience_policy["retain_threshold"] = policy_obj.retain_threshold
    health_adj_summary = [
        {"trigger_type": a.get("trigger_type"), "period": a.get("period"), "reason": a.get("trigger_reason"), "severity": a.get("severity")}
        for a in (health_based_adjustments or [])
    ]
    write_weekly_portfolio_experience(
        mandate_id=mandate.mandate_id,
        period=period,
        top_opportunity_scores=opportunity_ranking or [],
        replaced_positions=replacement_decisions or [],
        retained_positions=retained_positions or [],
        policy_snapshot=experience_policy,
        health_adjustment_summary=health_adj_summary,
    )
    write_experience_insight_snapshot(
        mandate_id=mandate.mandate_id,
        period=period,
        insights=insights.to_dict(),
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
        snapshot_source=snapshot_source,
        market_data_source=market_data_source,
        benchmark_source=benchmark_source,
    )
    return WeeklyPaperResult(
        ok=True,
        mandate_id=mandate.mandate_id,
        status=state,
        capital_limit=capital,
        benchmark=benchmark,
        engine_type="nautilus",
        used_nautilus=True,
        report_path=report_path,
        summary=summary,
        strategy_run_ids=run_ids,
    )
