"""
Experience 写入口：为下一阶段 Experience Store 增强与 TradingAgents 接入预留统一写入接口。
当前实现：write_backtest_result + 自动写 trade_experience（每 run 一条）+ 按 regime 写 experience_summary。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_trading_research_system.backtest.runner import BacktestMetrics
from ai_trading_research_system.experience.store import (
    write_backtest_result,
    write_trade_experience,
    aggregate_and_write_experience_summary,
)


@dataclass
class RunResultPayload:
    """一次运行结果的最小载荷，供 write_run_result 写入 Experience。"""
    symbol: str
    start_date: str
    end_date: str
    sharpe: float
    max_drawdown: float
    win_rate: float
    pnl: float
    trade_count: int
    # 可选：后续扩展 contract_snapshot、strategy_params 等
    extra: dict[str, Any] | None = None
    # 可选：用于 experience_summary 的 regime 标签
    regime_tag: str | None = None


def write_run_result(
    payload: RunResultPayload,
    *,
    db_path: Path | None = None,
) -> int:
    """
    将一次运行结果写入 Experience Store。
    写入 strategy_run + backtest_result，并自动写入一条 trade_experience 与 experience_summary。
    """
    metrics = BacktestMetrics(
        sharpe=payload.sharpe,
        max_drawdown=payload.max_drawdown,
        win_rate=payload.win_rate,
        pnl=payload.pnl,
        trade_count=payload.trade_count,
    )
    parameters = payload.extra if isinstance(payload.extra, dict) else None
    run_id = write_backtest_result(
        symbol=payload.symbol,
        start_date=payload.start_date,
        end_date=payload.end_date,
        metrics=metrics,
        parameters=parameters,
        regime_tag=payload.regime_tag,
        db_path=db_path,
    )
    # 自动写入 trade_experience：每 run 一条（当前回测仅返回聚合指标，无逐笔列表）
    signal_snapshot = json.dumps(payload.extra, ensure_ascii=False) if payload.extra else None
    outcome = json.dumps({
        "sharpe": payload.sharpe,
        "max_drawdown": payload.max_drawdown,
        "win_rate": payload.win_rate,
        "pnl": payload.pnl,
        "trade_count": payload.trade_count,
    }, ensure_ascii=False)
    failure_reason = "no_trade" if payload.trade_count == 0 else None
    write_trade_experience(
        trade_id=f"run_{run_id}",
        signal_snapshot=signal_snapshot,
        outcome=outcome,
        failure_reason=failure_reason,
        db_path=db_path,
    )
    # 按 regime 聚合 backtest_result 后写入 experience_summary（每个 regime 保留一条最新聚合）
    aggregate_and_write_experience_summary(db_path=db_path)
    return run_id
