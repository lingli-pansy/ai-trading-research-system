"""
Trigger Evaluator: 评估是否应触发日内调整。
仅当存在 trigger 时 pipeline 才执行 allocator，实现 event-driven。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ai_trading_research_system.autonomous.adjustment_trigger import (
    AdjustmentTrigger,
    TRIGGER_DRAWDOWN,
    TRIGGER_OPPORTUNITY_SPIKE,
    TRIGGER_RISK_EVENT,
)
from ai_trading_research_system.autonomous.schemas import AccountSnapshot
from ai_trading_research_system.autonomous.portfolio_policy import PortfolioDecisionPolicy


DRAWDOWN_THRESHOLD_PCT = 5.0
OPPORTUNITY_SPIKE_MULTIPLIER = 2.0


def evaluate_intraday_triggers(
    account_snapshot: AccountSnapshot,
    opportunity_ranking: list[dict[str, Any]],
    current_positions: dict[str, Any],
    policy: PortfolioDecisionPolicy,
    *,
    drawdown_pct: float | None = None,
    initial_equity: float | None = None,
) -> AdjustmentTrigger | None:
    """
    评估是否应触发日内调整。返回第一个满足条件的 trigger，否则 None。
    优先级: risk_event > drawdown > opportunity_spike。
    """
    now = datetime.now(timezone.utc).isoformat()

    # risk_event_trigger: 任一机会或持仓风险为 high
    for o in opportunity_ranking or []:
        if (o.get("risk") or "").lower() == "high":
            return AdjustmentTrigger(
                trigger_type=TRIGGER_RISK_EVENT,
                trigger_reason=f"opportunity_risk_high_{o.get('symbol', '')}",
                severity="high",
                timestamp=now,
            )

    # drawdown_trigger: 回撤超过阈值
    if drawdown_pct is not None and drawdown_pct >= DRAWDOWN_THRESHOLD_PCT:
        return AdjustmentTrigger(
            trigger_type=TRIGGER_DRAWDOWN,
            trigger_reason=f"drawdown_pct_{drawdown_pct:.1f}_gte_{DRAWDOWN_THRESHOLD_PCT}",
            severity="high" if drawdown_pct >= 10 else "medium",
            timestamp=now,
        )
    if initial_equity is not None and initial_equity > 0:
        equity = account_snapshot.total_equity()
        dd = (initial_equity - equity) / initial_equity * 100.0
        if dd >= DRAWDOWN_THRESHOLD_PCT:
            return AdjustmentTrigger(
                trigger_type=TRIGGER_DRAWDOWN,
                trigger_reason=f"drawdown_pct_{dd:.1f}_gte_{DRAWDOWN_THRESHOLD_PCT}",
                severity="high" if dd >= 10 else "medium",
                timestamp=now,
            )

    # opportunity_spike_trigger: 最优机会分数显著高于当前持仓
    if not opportunity_ranking:
        return None
    top_score = float(opportunity_ranking[0].get("score", 0) or 0)
    best_current = 0.0
    for p in (current_positions.values() if isinstance(current_positions, dict) else current_positions):
        if isinstance(p, dict):
            best_current = max(best_current, float(p.get("score", 0) or 0))
        else:
            break
    gap_required = policy.minimum_score_gap_for_replacement * OPPORTUNITY_SPIKE_MULTIPLIER
    if top_score - best_current >= gap_required:
        return AdjustmentTrigger(
            trigger_type=TRIGGER_OPPORTUNITY_SPIKE,
            trigger_reason=f"top_score_{top_score:.2f}_minus_best_{best_current:.2f}_gte_{gap_required:.2f}",
            severity="medium",
            timestamp=now,
        )
    return None
