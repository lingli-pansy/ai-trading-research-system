"""
Strategy Refiner 占位：根据 strategy_run + backtest_result + spec 快照产出一句改进建议。
供后续「经验 → 策略优化」闭环注入；本阶段仅读 Store 做规则建议，不修改策略。
"""
from __future__ import annotations

import json
from pathlib import Path

from ai_trading_research_system.experience.store import get_connection, _get_db_path


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
