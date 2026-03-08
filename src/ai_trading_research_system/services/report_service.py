"""
Report service: generate weekly report and write to JSON file.
Used by UC-09 weekly controller and by application.commands.generate_weekly_report.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_trading_research_system.autonomous.schemas import WeeklyTradingMandate
from ai_trading_research_system.autonomous.benchmark import BenchmarkResult
from ai_trading_research_system.autonomous.weekly_report import WeeklyReportGenerator


def generate_and_write(
    mandate: WeeklyTradingMandate,
    benchmark_result: BenchmarkResult,
    *,
    key_trades: list[str] | None = None,
    risk_events: list[str] | None = None,
    no_trade_days: int = 0,
    no_trade_reasons: list[str] | None = None,
    daily_research: list[dict[str, Any]] | None = None,
    report_dir: Path | None = None,
    turnover_pct: float = 0.0,
    opportunity_ranking: list[dict[str, Any]] | None = None,
    replacement_decisions: list[dict[str, Any]] | None = None,
    why_replacements_happened: str = "",
    why_candidates_rejected: list[dict[str, Any]] | None = None,
    replacements_skipped_due_to_threshold: int = 0,
    replacements_skipped_due_to_budget: int = 0,
    policy_used: dict[str, Any] | None = None,
    intraday_adjustments: list[dict[str, Any]] | None = None,
    portfolio_health: dict[str, Any] | None = None,
    health_based_adjustments: list[dict[str, Any]] | None = None,
    experience_insights: dict[str, Any] | None = None,
    proposed_evolution: dict[str, Any] | None = None,
    approved_evolution: dict[str, Any] | None = None,
    rejected_evolution: list[dict[str, Any]] | None = None,
    experiment_id: str = "",
    cycle_number: int = 0,
    policy_version: str = "",
    system_snapshot_at_week_end: dict[str, Any] | None = None,
    replay_analysis: dict[str, Any] | None = None,
    decision_traces_summary: dict[str, Any] | None = None,
) -> str:
    """Generate weekly report and write to report_dir/weekly_report_{mandate_id}.json. Returns path."""
    if policy_used is None and getattr(mandate, "policy", None) is not None:
        p = mandate.policy
        policy_used = {
            "minimum_score_gap": p.minimum_score_gap_for_replacement,
            "max_replacements": p.max_replacements_per_rebalance,
            "turnover_budget": p.turnover_budget,
        }
    policy_used = policy_used or {}
    gen = WeeklyReportGenerator()
    report = gen.generate(
        mandate,
        benchmark_result,
        key_trades=key_trades or [],
        risk_events=risk_events or [],
        no_trade_days=no_trade_days,
        no_trade_reasons=no_trade_reasons or [],
        daily_research=daily_research or [],
        turnover_pct=turnover_pct,
        opportunity_ranking=opportunity_ranking or [],
        replacement_decisions=replacement_decisions or [],
        why_replacements_happened=why_replacements_happened,
        why_candidates_rejected=why_candidates_rejected or [],
        replacements_skipped_due_to_threshold=replacements_skipped_due_to_threshold,
        replacements_skipped_due_to_budget=replacements_skipped_due_to_budget,
        policy_used=policy_used,
        intraday_adjustments=intraday_adjustments or [],
        portfolio_health=portfolio_health or {},
        health_based_adjustments=health_based_adjustments or [],
        experience_insights=experience_insights or {},
        proposed_evolution=proposed_evolution or {},
        approved_evolution=approved_evolution or {},
        rejected_evolution=rejected_evolution or [],
        experiment_id=experiment_id or "",
        cycle_number=cycle_number or 0,
        policy_version=policy_version or "",
        system_snapshot_at_week_end=system_snapshot_at_week_end or {},
        replay_analysis=replay_analysis or {},
        decision_traces_summary=decision_traces_summary or {},
    )
    report_dir = report_dir or Path(".")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"weekly_report_{mandate.mandate_id}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(gen.to_dict(report), f, ensure_ascii=False, indent=2)
    return str(report_path)


def build_weekly_result_summary(
    *,
    portfolio_return: float,
    benchmark_return: float,
    excess_return: float,
    total_trades: int,
    total_pnl: float,
    report_path: str,
    daily_research_count: int,
    snapshot_source: str,
    market_data_source: str,
    benchmark_source: str,
    max_drawdown: float = 0.0,
    turnover_pct: float = 0.0,
) -> dict[str, Any]:
    """Build the summary dict for WeeklyPaperResult. Used by weekly_paper_pipe only for result assembly."""
    return {
        "portfolio_return": portfolio_return,
        "benchmark_return": benchmark_return,
        "excess_return": excess_return,
        "trade_count": total_trades,
        "pnl": total_pnl,
        "report_path": report_path,
        "daily_research_count": daily_research_count,
        "analysis_in_report": True,
        "snapshot_source": snapshot_source,
        "market_data_source": market_data_source,
        "benchmark_source": benchmark_source,
        "max_drawdown": max_drawdown,
        "turnover_pct": turnover_pct,
    }
