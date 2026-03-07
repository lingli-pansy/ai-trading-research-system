"""
统一执行结果模型：backtest / paper / demo / OpenClaw 输出字段对齐。
CLI、E2E、OpenClaw 消费的核心字段一致；wait_confirmation 等 0 笔交易规范为 status=no_trade。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_trading_research_system.research.schemas import DecisionContract
from ai_trading_research_system.backtest.runner import BacktestMetrics


@dataclass
class UnifiedRunOutput:
    """
    CLI / OpenClaw / E2E 统一读到的核心字段。
    symbol, action, confidence, suggested_action, trade_count, pnl, max_drawdown,
    engine_type, used_nautilus, status, reason 保持一致。
    """
    symbol: str
    action: str
    confidence: str
    suggested_action: str
    trade_count: int
    pnl: float
    max_drawdown: float
    engine_type: str  # "nautilus"
    used_nautilus: bool
    status: str  # "ok" | "no_trade"
    reason: str = ""
    # 可选扩展
    strategy_run_id: int | None = None
    sharpe: float = 0.0
    win_rate: float = 0.0


def from_backtest_pipe(
    symbol: str,
    contract: DecisionContract,
    metrics: BacktestMetrics,
    strategy_run_id: int,
) -> UnifiedRunOutput:
    """从 BacktestPipeResult 的 contract + metrics 构建统一输出。"""
    status = "no_trade" if metrics.trade_count == 0 else "ok"
    reason = "wait_confirmation" if metrics.trade_count == 0 else ""
    from ai_trading_research_system.strategy.translator import ContractTranslator
    signal = ContractTranslator().translate(contract)
    return UnifiedRunOutput(
        symbol=symbol,
        action=signal.action,
        confidence=contract.confidence,
        suggested_action=contract.suggested_action,
        trade_count=metrics.trade_count,
        pnl=metrics.pnl,
        max_drawdown=metrics.max_drawdown,
        engine_type="nautilus",
        used_nautilus=True,
        status=status,
        reason=reason,
        strategy_run_id=strategy_run_id,
        sharpe=metrics.sharpe,
        win_rate=metrics.win_rate,
    )


def from_paper_pipe(
    symbol: str,
    contract: DecisionContract,
    runner_result: Any,
) -> UnifiedRunOutput:
    """从 PaperPipeResult (contract + runner_result) 构建统一输出。"""
    if runner_result is None:
        from ai_trading_research_system.strategy.translator import ContractTranslator
        signal = ContractTranslator().translate(contract)
        return UnifiedRunOutput(
            symbol=symbol,
            action=signal.action,
            confidence=contract.confidence,
            suggested_action=contract.suggested_action,
            trade_count=0,
            pnl=0.0,
            max_drawdown=0.0,
            engine_type="nautilus",
            used_nautilus=True,
            status="no_trade",
            reason="no_runner_result",
        )
    return UnifiedRunOutput(
        symbol=symbol,
        action=runner_result.signal_action,
        confidence=contract.confidence,
        suggested_action=contract.suggested_action,
        trade_count=getattr(runner_result, "trade_count", 0),
        pnl=getattr(runner_result, "pnl", 0.0),
        max_drawdown=0.0,
        engine_type="nautilus" if getattr(runner_result, "used_nautilus", False) else "legacy",
        used_nautilus=getattr(runner_result, "used_nautilus", False),
        status=getattr(runner_result, "status", "ok"),
        reason=getattr(runner_result, "reason", ""),
    )


def to_plain_dict(out: UnifiedRunOutput) -> dict[str, Any]:
    """用于 JSON 输出（OpenClaw / --json）。"""
    return {
        "symbol": out.symbol,
        "action": out.action,
        "confidence": out.confidence,
        "suggested_action": out.suggested_action,
        "trade_count": out.trade_count,
        "pnl": out.pnl,
        "max_drawdown": out.max_drawdown,
        "engine_type": out.engine_type,
        "used_nautilus": out.used_nautilus,
        "status": out.status,
        "reason": out.reason,
        "strategy_run_id": out.strategy_run_id,
        "sharpe": out.sharpe,
        "win_rate": out.win_rate,
    }
