"""
Strategy Refiner：根据 strategy_run + backtest_result 或 ExperienceInsights 产出改进建议。
可读取 ExperienceInsights 以调整 entry filters、risk controls、signal thresholds 的建议（不直接改策略）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_trading_research_system.experience.store import get_connection, _get_db_path

from ai_trading_research_system.experience.analyzer import ExperienceInsights


def refiner_suggest(
    strategy_run_id: int,
    *,
    db_path: Path | None = None,
) -> str:
    """
    根据指定 strategy_run_id 读取 backtest_result 与 strategy_run.parameters（含 spec 快照），
    返回一句改进建议（占位实现：基于 sharpe、trade_count、max_drawdown 的简单规则）。
    """
    path = db_path or _get_db_path()
    if not path.exists():
        return "Experience Store 未初始化，暂无建议。"
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT s.parameters, b.sharpe, b.max_drawdown, b.win_rate, b.pnl, b.trade_count
            FROM strategy_run s
            JOIN backtest_result b ON s.id = b.strategy_run_id
            WHERE s.id = ?
            """,
            (strategy_run_id,),
        )
        row = cur.fetchone()
        if not row:
            return f"未找到 strategy_run id={strategy_run_id}，暂无建议。"
        parameters_json, sharpe, max_drawdown, win_rate, pnl, trade_count = row
        # 占位规则
        suggestions = []
        if trade_count == 0:
            suggestions.append("本次无成交，可考虑放宽入场条件或增加标的覆盖。")
        elif sharpe is not None and sharpe < 0:
            suggestions.append("Sharpe 为负，建议收紧入场或增加止损。")
        if max_drawdown is not None and max_drawdown > 0.2:
            suggestions.append("回撤较大，建议降低仓位或强化风控。")
        if win_rate is not None and 0 < win_rate < 0.4 and trade_count and trade_count >= 3:
            suggestions.append("胜率偏低，可回顾入场逻辑与止盈止损。")
        if not suggestions:
            suggestions.append("当前指标在可接受范围内，可继续观察或小幅优化。")
        return " ".join(suggestions)
    finally:
        conn.close()


def refiner_suggest_from_insights(insights: ExperienceInsights) -> dict[str, Any]:
    """
    根据 ExperienceInsights 产出策略层调整建议（entry filters、risk controls、signal thresholds）。
    返回结构化建议，不直接修改策略代码。
    """
    if not isinstance(insights, ExperienceInsights):
        return _empty_refiner_suggestions()
    entry_filters: list[str] = []
    risk_controls: list[str] = []
    signal_thresholds: list[str] = []

    # 替换失败多 → 建议提高入场/信号阈值或放宽 gap
    if insights.frequent_replacement_failures:
        top = insights.frequent_replacement_failures[0] if insights.frequent_replacement_failures else {}
        if "score_gap" in str(top.get("reason", "")).lower():
            signal_thresholds.append("历史中 score_gap 不足导致替换被拒较多，可考虑提高 minimum_score_gap 或放宽 replacement 阈值。")
        if "skipped" in str(top.get("reason", "")).lower() or "budget" in str(top.get("reason", "")).lower():
            risk_controls.append("替换常因 budget/cap 被跳过，可适当提高 turnover_budget 或 max_replacements。")

    # 高 turnover 触发 → 建议收紧触发条件或入场
    for t in insights.triggers_excessive_turnover:
        if (t.get("high_turnover_weeks") or 0) > 0:
            risk_controls.append(
                f"触发类型 {t.get('trigger_type', '')} 多次伴随高换手，建议收紧该触发阈值或入场条件。"
            )

    # 风险事件与负超额相关 → 建议强化风控
    for r in insights.risk_events_correlation:
        if (r.get("avg_excess_return") or 0) < -0.01:
            signal_thresholds.append(
                f"风险事件 {r.get('trigger_type', '')} 与负超额相关，建议强化风控或降低该情形下仓位。"
            )

    # 政策与超额关联 → 可作 entry/position 参考
    if insights.policies_associated_higher_excess_return:
        best = insights.policies_associated_higher_excess_return[0]
        entry_filters.append(
            f"历史中政策波段 {best.get('policy_band', '')} 对应较高超额（avg_excess={best.get('avg_excess_return', 0):.2%}），可作参数参考。"
        )

    if not entry_filters:
        entry_filters.append("暂无基于经验的入场过滤建议。")
    if not risk_controls:
        risk_controls.append("暂无基于经验的风控调整建议。")
    if not signal_thresholds:
        signal_thresholds.append("暂无基于经验的信号阈值建议。")

    return {
        "entry_filters_adjustment": entry_filters,
        "risk_controls_adjustment": risk_controls,
        "signal_thresholds_adjustment": signal_thresholds,
        "strategy_adjustment_suggested": insights.strategy_adjustment_suggested,
    }


def _empty_refiner_suggestions() -> dict[str, Any]:
    return {
        "entry_filters_adjustment": ["暂无经验数据。"],
        "risk_controls_adjustment": ["暂无经验数据。"],
        "signal_thresholds_adjustment": ["暂无经验数据。"],
        "strategy_adjustment_suggested": False,
    }
