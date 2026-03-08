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
    TRIGGER_CONCENTRATION_RISK,
    TRIGGER_BETA_SPIKE,
    TRIGGER_EXCESS_DRAWDOWN,
)
from ai_trading_research_system.autonomous.schemas import AccountSnapshot
from ai_trading_research_system.autonomous.portfolio_policy import PortfolioDecisionPolicy

DRAWDOWN_THRESHOLD_PCT = 5.0
OPPORTUNITY_SPIKE_MULTIPLIER = 2.0
CONCENTRATION_RISK_THRESHOLD = 0.6
BETA_SPIKE_THRESHOLD = 1.5
EXCESS_DRAWDOWN_THRESHOLD = 0.05


def evaluate_intraday_triggers(
    account_snapshot: AccountSnapshot,
    opportunity_ranking: list[dict[str, Any]],
    current_positions: dict[str, Any],
    policy: PortfolioDecisionPolicy,
    *,
    drawdown_pct: float | None = None,
    initial_equity: float | None = None,
    portfolio_health: Any = None,
) -> AdjustmentTrigger | None:
    """
    评估是否应触发日内调整。返回第一个满足条件的 trigger，否则 None。
    优先级: risk_event > health (concentration/beta/excess_drawdown) > drawdown > opportunity_spike。
    portfolio_health: PortfolioHealthSnapshot 或 to_dict()，用于 health-based triggers。
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

    # health-based triggers (需 portfolio_health)
    if portfolio_health is not None:
        h = portfolio_health
        conc = getattr(h, "concentration_index", None) or (h.get("concentration_index") if isinstance(h, dict) else None)
        if conc is not None and float(conc) >= CONCENTRATION_RISK_THRESHOLD:
            return AdjustmentTrigger(
                trigger_type=TRIGGER_CONCENTRATION_RISK,
                trigger_reason=f"concentration_index_{float(conc):.2f}_gte_{CONCENTRATION_RISK_THRESHOLD}",
                severity="medium",
                timestamp=now,
            )
        beta = getattr(h, "beta_vs_spy", None) if not isinstance(h, dict) else h.get("beta_vs_spy")
        if beta is not None and float(beta) >= BETA_SPIKE_THRESHOLD:
            return AdjustmentTrigger(
                trigger_type=TRIGGER_BETA_SPIKE,
                trigger_reason=f"beta_vs_spy_{float(beta):.2f}_gte_{BETA_SPIKE_THRESHOLD}",
                severity="high",
                timestamp=now,
            )
        md = getattr(h, "max_drawdown", None) if not isinstance(h, dict) else h.get("max_drawdown")
        if md is not None and float(md) >= EXCESS_DRAWDOWN_THRESHOLD:
            return AdjustmentTrigger(
                trigger_type=TRIGGER_EXCESS_DRAWDOWN,
                trigger_reason=f"max_drawdown_{float(md):.2f}_gte_{EXCESS_DRAWDOWN_THRESHOLD}",
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
