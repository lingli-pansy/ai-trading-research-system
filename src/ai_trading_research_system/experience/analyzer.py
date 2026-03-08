"""
Experience Analyzer: 从 weekly_portfolio_experience、health_adjustment_events、opportunity_ranking 快照
分析历史经验，产出 ExperienceInsights，供 StrategyRefiner 与 policy evolution 使用。
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from ai_trading_research_system.experience.store import (
    read_weekly_portfolio_experience_history,
    read_health_trigger_events,
)


@dataclass
class ExperienceInsights:
    """经验分析结果：替换失败模式、高 turnover 触发、政策与超额收益关联、风险事件相关性。"""
    frequent_replacement_failures: list[dict[str, Any]] = field(default_factory=list)
    """常见替换失败原因及频次，如 [{"reason": "score_gap_below", "count": 5}]。"""
    triggers_excessive_turnover: list[dict[str, Any]] = field(default_factory=list)
    """与高换手相关的触发类型，如 [{"trigger_type": "opportunity_spike_trigger", "avg_replacements": 3}]。"""
    policies_associated_higher_excess_return: list[dict[str, Any]] = field(default_factory=list)
    """与较高超额收益相关的政策特征，如 [{"policy_band": "min_gap_0.3-0.5", "avg_excess": 0.02}]。"""
    risk_events_correlation: list[dict[str, Any]] = field(default_factory=list)
    """风险事件与表现相关性，如 [{"trigger_type": "concentration_risk_trigger", "weeks_count": 2, "avg_excess": -0.01}]。"""
    strategy_adjustment_suggested: bool = False
    """是否建议根据本次洞察进行策略/政策微调。"""

    def to_dict(self) -> dict[str, Any]:
        return {
            "frequent_replacement_failures": self.frequent_replacement_failures,
            "triggers_excessive_turnover": self.triggers_excessive_turnover,
            "policies_associated_higher_excess_return": self.policies_associated_higher_excess_return,
            "risk_events_correlation": self.risk_events_correlation,
            "strategy_adjustment_suggested": self.strategy_adjustment_suggested,
        }


def analyze_experience_history(
    weekly_experiences: list[dict[str, Any]],
    health_adjustment_events: list[dict[str, Any]],
    opportunity_ranking_snapshots: list[list[dict[str, Any]]] | None = None,
    *,
    replacement_failure_threshold: int = 2,
    excessive_turnover_replacements: int = 3,
    min_weeks_for_policy_insight: int = 2,
) -> ExperienceInsights:
    """
    分析历史经验，产出 ExperienceInsights。
    weekly_experiences: 来自 read_weekly_portfolio_experience_history 的列表，每项含 period, policy_snapshot, replaced_positions, top_opportunity_scores 等。
    health_adjustment_events: 来自 read_health_trigger_events 或 weekly 内 health_adjustment_summary 展开。
    opportunity_ranking_snapshots: 可选，与 weekly 一一对应的 opportunity 快照（已有则在 weekly 的 top_opportunity_scores 中）。
    """
    insights = ExperienceInsights()
    if not weekly_experiences:
        return insights

    # 1. Frequent replacement failures: 从 policy_snapshot.rejected_due_to_threshold / replacements_skipped 及 why_candidates_rejected 归纳
    failure_reasons: list[str] = []
    for w in weekly_experiences:
        ps = w.get("policy_snapshot") or {}
        if isinstance(ps, str):
            try:
                ps = json.loads(ps) if ps else {}
            except Exception:
                ps = {}
        rej = ps.get("rejected_due_to_threshold") or 0
        skip = ps.get("replacements_skipped") or 0
        if rej > 0:
            failure_reasons.extend(["score_gap_below_threshold"] * int(rej))
        if skip > 0:
            failure_reasons.extend(["replacements_skipped_budget_or_cap"] * int(skip))
    if failure_reasons:
        counts = Counter(failure_reasons)
        insights.frequent_replacement_failures = [
            {"reason": r, "count": c}
            for r, c in counts.most_common(10)
            if c >= replacement_failure_threshold
        ]

    # 2. Triggers that caused excessive turnover: 按 period 关联 health/intraday 触发与当周 replacements_executed
    period_to_replacements: dict[str, int] = {}
    period_to_trigger_types: dict[str, list[str]] = {}
    for w in weekly_experiences:
        period = w.get("period") or w.get("id")
        key = str(period)
        ps = w.get("policy_snapshot") or {}
        if isinstance(ps, str):
            try:
                ps = json.loads(ps) if ps else {}
            except Exception:
                ps = {}
        period_to_replacements[key] = int(ps.get("replacements_executed") or 0)
        health_adj = w.get("health_adjustment_summary")
        if isinstance(health_adj, str):
            try:
                health_adj = json.loads(health_adj) if health_adj else []
            except Exception:
                health_adj = []
        trigger_types = [t.get("trigger_type") for t in (health_adj or []) if t.get("trigger_type")]
        period_to_trigger_types[key] = list(set(trigger_types))
    for ev in health_adjustment_events or []:
        period = ev.get("period") or ""
        if period not in period_to_trigger_types:
            period_to_trigger_types[period] = []
        t = ev.get("trigger_type")
        if t and t not in period_to_trigger_types[period]:
            period_to_trigger_types[period].append(t)
    # 高 turnover 周期：replacements >= excessive_turnover_replacements
    high_turnover_periods = {p for p, r in period_to_replacements.items() if r >= excessive_turnover_replacements}
    trigger_turnover: dict[str, list[int]] = {}
    for period, triggers in period_to_trigger_types.items():
        rep = period_to_replacements.get(period, 0)
        for t in triggers:
            if t not in trigger_turnover:
                trigger_turnover[t] = []
            trigger_turnover[t].append(rep)
    insights.triggers_excessive_turnover = [
        {"trigger_type": t, "avg_replacements": sum(v) / len(v) if v else 0, "high_turnover_weeks": sum(1 for r in v if r >= excessive_turnover_replacements)}
        for t, v in trigger_turnover.items()
    ]
    insights.triggers_excessive_turnover.sort(key=lambda x: -x.get("avg_replacements", 0))

    # 3. Policies associated with higher excess_return: policy_snapshot 含 min_gap, max_replacements, turnover_budget, excess_return
    policy_bands: dict[str, list[float]] = {}
    for w in weekly_experiences:
        ps = w.get("policy_snapshot") or {}
        if isinstance(ps, str):
            try:
                ps = json.loads(ps) if ps else {}
            except Exception:
                ps = {}
        excess = ps.get("excess_return")
        if excess is None:
            continue
        try:
            excess_f = float(excess)
        except (TypeError, ValueError):
            continue
        min_gap = ps.get("minimum_score_gap_for_replacement")
        max_rep = ps.get("max_replacements_per_rebalance")
        turn = ps.get("turnover_budget")
        band = f"min_gap_{min_gap}_max_rep_{max_rep}_turn_{turn}"
        if band not in policy_bands:
            policy_bands[band] = []
        policy_bands[band].append(excess_f)
    if policy_bands and min_weeks_for_policy_insight:
        insights.policies_associated_higher_excess_return = [
            {"policy_band": band, "avg_excess_return": sum(v) / len(v), "weeks_count": len(v)}
            for band, v in policy_bands.items()
            if len(v) >= min_weeks_for_policy_insight
        ]
        insights.policies_associated_higher_excess_return.sort(
            key=lambda x: -x.get("avg_excess_return", 0)
        )

    # 4. Risk events correlation: 有 health 触发的周期 vs 无触发的周期，对比 excess_return
    periods_with_risk: set[str] = set()
    for ev in health_adjustment_events or []:
        periods_with_risk.add(str(ev.get("period") or ""))
    for period, triggers in period_to_trigger_types.items():
        if triggers:
            periods_with_risk.add(period)
    excess_by_period = {}
    for w in weekly_experiences:
        key = str(w.get("period") or w.get("id"))
        ps = w.get("policy_snapshot") or {}
        if isinstance(ps, str):
            try:
                ps = json.loads(ps) if ps else {}
            except Exception:
                ps = {}
        ex = ps.get("excess_return")
        if ex is not None:
            try:
                excess_by_period[key] = float(ex)
            except (TypeError, ValueError):
                pass
    trigger_to_excess: dict[str, list[float]] = {}
    for ev in health_adjustment_events or []:
        t = ev.get("trigger_type")
        period = str(ev.get("period") or "")
        ex = excess_by_period.get(period)
        if t and ex is not None:
            if t not in trigger_to_excess:
                trigger_to_excess[t] = []
            trigger_to_excess[t].append(ex)
    insights.risk_events_correlation = [
        {"trigger_type": t, "weeks_count": len(v), "avg_excess_return": sum(v) / len(v)}
        for t, v in trigger_to_excess.items()
    ]
    insights.risk_events_correlation.sort(key=lambda x: x.get("avg_excess_return", 0))

    # 是否建议调整：有显著失败模式、或高 turnover 触发、或风险事件与负超额相关
    insights.strategy_adjustment_suggested = (
        len(insights.frequent_replacement_failures) > 0
        or len([x for x in insights.triggers_excessive_turnover if x.get("high_turnover_weeks", 0) > 0]) > 0
        or any(x.get("avg_excess_return", 0) < -0.01 for x in insights.risk_events_correlation)
    )
    return insights


def analyze_experience_from_store(
    mandate_id: str | None = None,
    limit_weeks: int = 20,
    limit_health_events: int = 100,
    db_path: Any = None,
) -> ExperienceInsights:
    """
    从 Experience Store 读取最近数据并运行 analyze_experience_history，返回 ExperienceInsights。
    供 finish_week 或报告生成时调用。
    """
    from ai_trading_research_system.experience.store import (
        read_weekly_portfolio_experience_history,
        read_health_trigger_events,
    )
    weekly = read_weekly_portfolio_experience_history(
        limit=limit_weeks,
        mandate_id=mandate_id,
        db_path=db_path,
    )
    health_events = read_health_trigger_events(
        limit=limit_health_events,
        mandate_id=mandate_id,
        db_path=db_path,
    )
    health_expanded = []
    for w in weekly:
        period = w.get("period") or ""
        adj = w.get("health_adjustment_summary") or []
        if isinstance(adj, dict):
            adj = [adj]
        for a in adj:
            health_expanded.append({**a, "period": period})
    return analyze_experience_history(
        weekly_experiences=weekly,
        health_adjustment_events=health_expanded + health_events,
        opportunity_ranking_snapshots=None,
    )
