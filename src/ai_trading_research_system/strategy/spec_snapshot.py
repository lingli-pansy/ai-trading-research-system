"""
StrategySpec 快照：从 DecisionContract + 回测结果产出可落库的 spec 结构（目标态 StrategySpec 的当前近似）。
不实现 StrategyCompiler；供 Experience 落库与后续 Refiner 消费。
Schema 对齐 docs/strategy_spec.md.
"""
from __future__ import annotations

from typing import Any

from ai_trading_research_system.backtest.runner import BacktestMetrics
from ai_trading_research_system.research.schemas import DecisionContract


def contract_to_spec_snapshot(
    contract: DecisionContract,
    metrics: BacktestMetrics,
    *,
    strategy_id: str = "AISignalStrategy",
) -> dict[str, Any]:
    """
    从 Contract + 本次回测指标产出 StrategySpec 形态的快照（dict）。
    用于落库到 strategy_run.parameters，供后续 Refiner 或分析使用。
    """
    entry_logic: list[str] = []
    if contract.suggested_action in ("probe_small", "allow_entry"):
        entry_logic.append(f"signal={contract.suggested_action}; confidence={contract.confidence}")
    else:
        entry_logic.append(f"signal={contract.suggested_action}; no entry")

    exit_logic: list[str] = []
    exit_logic.append("target or stop from strategy_params")

    risk_controls: dict[str, float] = {}
    if contract.strategy_params:
        if contract.strategy_params.stop_loss_pct is not None:
            risk_controls["stop_loss_pct"] = contract.strategy_params.stop_loss_pct
        if contract.strategy_params.take_profit_pct is not None:
            risk_controls["take_profit_pct"] = contract.strategy_params.take_profit_pct
        if contract.strategy_params.max_position_pct is not None:
            risk_controls["max_position_pct"] = contract.strategy_params.max_position_pct
    if not risk_controls:
        risk_controls = {"stop_loss_pct": 0.0, "take_profit_pct": 0.0, "max_position_pct": 1.0}

    return {
        "strategy_id": strategy_id,
        "symbol": contract.symbol,
        "thesis": contract.thesis,
        "entry_logic": entry_logic,
        "exit_logic": exit_logic,
        "filters": contract.risk_flags or [],
        "risk_controls": risk_controls,
        "time_horizon": contract.time_horizon,
        "regime_tag": None,
        "backtest_sharpe": metrics.sharpe,
        "backtest_max_drawdown": metrics.max_drawdown,
        "backtest_win_rate": metrics.win_rate,
        "backtest_pnl": metrics.pnl,
        "backtest_trade_count": metrics.trade_count,
    }
