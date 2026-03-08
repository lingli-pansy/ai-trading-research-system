"""
WeeklyReportGenerator：生成用户可读的周报。
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any

from ai_trading_research_system.autonomous.benchmark import BenchmarkResult
from ai_trading_research_system.autonomous.schemas import WeeklyTradingMandate


@dataclass
class WeeklyReport:
    """周报结构；组合层指标 + opportunity_ranking + replacement_decisions（解释为何替换仓位）。"""
    mandate_id: str
    period: str
    portfolio_return_pct: float
    benchmark_return_pct: float
    excess_return_pct: float
    max_drawdown_pct: float
    turnover_pct: float
    trade_count: int
    key_trades: list[str]
    risk_events: list[str]
    no_trade_days: int
    no_trade_reasons: list[str]
    next_week_suggestion: str
    daily_research: list[dict[str, Any]]
    benchmark_source: str = "mock"
    opportunity_ranking: list[dict[str, Any]] = field(default_factory=list)
    replacement_decisions: list[dict[str, Any]] = field(default_factory=list)
    # Policy-level explanation
    why_replacements_happened: str = ""
    why_candidates_rejected: list[dict[str, Any]] = field(default_factory=list)
    replacements_skipped_due_to_threshold: int = 0
    replacements_skipped_due_to_budget: int = 0
    policy_used: dict[str, Any] = field(default_factory=dict)  # minimum_score_gap, max_replacements, turnover_budget
    intraday_adjustments: list[dict[str, Any]] = field(default_factory=list)  # trigger_type, positions_changed, rationale
    portfolio_health: dict[str, Any] = field(default_factory=dict)  # portfolio_health_snapshot
    health_based_adjustments: list[dict[str, Any]] = field(default_factory=list)  # 因健康监控触发的调整，便于区分
    experience_insights: dict[str, Any] = field(default_factory=dict)  # 本周表现与历史经验对比、是否触发策略调整建议
    proposed_evolution: dict[str, Any] = field(default_factory=dict)   # EvolutionProposal 序列化
    approved_evolution: dict[str, Any] = field(default_factory=dict)    # 批准的 policy/strategy 调整
    rejected_evolution: list[dict[str, Any]] = field(default_factory=list)  # 被拒的调整项
    experiment_id: str = ""
    cycle_number: int = 0
    policy_version: str = ""
    system_snapshot_at_week_end: dict[str, Any] = field(default_factory=dict)
    replay_analysis: dict[str, Any] = field(default_factory=dict)
    decision_traces_summary: dict[str, Any] = field(default_factory=dict)


class WeeklyReportGenerator:
    """生成周报（用户可读 + 可序列化）。"""

    def generate(
        self,
        mandate: WeeklyTradingMandate,
        benchmark_result: BenchmarkResult,
        *,
        key_trades: list[str] | None = None,
        risk_events: list[str] | None = None,
        no_trade_days: int = 0,
        no_trade_reasons: list[str] | None = None,
        daily_research: list[dict[str, Any]] | None = None,
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
    ) -> WeeklyReport:
        key_trades = key_trades or []
        risk_events = risk_events or []
        no_trade_reasons = no_trade_reasons or []
        daily_research = daily_research or []
        opportunity_ranking = opportunity_ranking or []
        replacement_decisions = replacement_decisions or []
        why_candidates_rejected = why_candidates_rejected or []
        if policy_used is None and getattr(mandate, "policy", None) is not None:
            p = mandate.policy
            policy_used = {
                "minimum_score_gap": p.minimum_score_gap_for_replacement,
                "max_replacements": p.max_replacements_per_rebalance,
                "turnover_budget": p.turnover_budget,
            }
        policy_used = policy_used or {}
        intraday_adjustments = intraday_adjustments or []
        portfolio_health = portfolio_health or {}
        health_based_adjustments = health_based_adjustments or []
        experience_insights = experience_insights or {}
        proposed_evolution = proposed_evolution or {}
        approved_evolution = approved_evolution or {}
        rejected_evolution = rejected_evolution or []
        experiment_id = experiment_id or ""
        cycle_number = cycle_number or 0
        policy_version = policy_version or ""
        system_snapshot_at_week_end = system_snapshot_at_week_end or {}
        replay_analysis = replay_analysis or {}
        decision_traces_summary = decision_traces_summary or {}
        if benchmark_result.excess_return > 0.02:
            suggestion = "组合跑赢基准，可维持当前风险偏好。"
        elif benchmark_result.trade_count == 0:
            suggestion = "本周无成交，建议检查入场条件或放宽信号阈值。"
        else:
            suggestion = "建议下周继续观察，可微调仓位上限。"
        return WeeklyReport(
            mandate_id=mandate.mandate_id,
            period=benchmark_result.period,
            portfolio_return_pct=benchmark_result.portfolio_return * 100,
            benchmark_return_pct=benchmark_result.benchmark_return * 100,
            excess_return_pct=benchmark_result.excess_return * 100,
            max_drawdown_pct=benchmark_result.max_drawdown * 100,
            turnover_pct=turnover_pct,
            trade_count=benchmark_result.trade_count,
            key_trades=key_trades,
            risk_events=risk_events,
            no_trade_days=no_trade_days,
            no_trade_reasons=no_trade_reasons,
            next_week_suggestion=suggestion,
            daily_research=daily_research,
            benchmark_source=getattr(benchmark_result, "benchmark_source", "mock"),
            opportunity_ranking=opportunity_ranking,
            replacement_decisions=replacement_decisions,
            why_replacements_happened=why_replacements_happened,
            why_candidates_rejected=why_candidates_rejected,
            replacements_skipped_due_to_threshold=replacements_skipped_due_to_threshold,
            replacements_skipped_due_to_budget=replacements_skipped_due_to_budget,
            policy_used=policy_used,
            intraday_adjustments=intraday_adjustments,
            portfolio_health=portfolio_health,
            health_based_adjustments=health_based_adjustments,
            experience_insights=experience_insights,
            proposed_evolution=proposed_evolution,
            approved_evolution=approved_evolution,
            rejected_evolution=rejected_evolution,
            experiment_id=experiment_id,
            cycle_number=cycle_number,
            policy_version=policy_version,
            system_snapshot_at_week_end=system_snapshot_at_week_end,
            replay_analysis=replay_analysis,
            decision_traces_summary=decision_traces_summary,
        )

    def to_dict(self, report: WeeklyReport) -> dict[str, Any]:
        return asdict(report)
