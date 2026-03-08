"""
Paper run 落盘与阶段产物的结构化类型。
用于 RunStore artifact、rebalance_plan、portfolio_after、replay 等。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# action_type: 由 current -> target 推导
ActionType = Literal["OPEN", "ADD", "TRIM", "CLOSE", "REPLACE", "HOLD"]


@dataclass
class RebalancePlanItem:
    """单标的调仓计划项。"""
    symbol: str
    current_position: float  # 当前权重 0..1
    target_position: float   # 目标权重 0..1
    delta: float             # target - current
    action_type: ActionType  # OPEN | ADD | TRIM | CLOSE | REPLACE | HOLD
    reason: str = ""
    confidence: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "current_position": self.current_position,
            "target_position": self.target_position,
            "delta": self.delta,
            "action_type": self.action_type,
            "reason": self.reason,
            "confidence": self.confidence,
        }


@dataclass
class RebalancePlan:
    """调仓计划：由 target_positions + portfolio_before 推导，用于生成 order_intents 与 portfolio_after。"""
    items: list[RebalancePlanItem] = field(default_factory=list)
    no_trade_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [x.to_dict() for x in self.items],
            "no_trade_reason": self.no_trade_reason,
        }


@dataclass
class PortfolioSnapshot:
    """组合快照（before/after）：可落盘、可 replay。"""
    timestamp: str
    positions: list[dict[str, Any]]  # [{"symbol", "quantity", "market_value", "weight_pct"?}, ...]
    cash_estimate: float
    equity_estimate: float
    run_id: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "positions": list(self.positions),
            "cash_estimate": self.cash_estimate,
            "equity_estimate": self.equity_estimate,
            "run_id": self.run_id,
            "source": self.source,
        }


@dataclass
class PaperExecutionResult:
    """单笔 paper 执行结果。"""
    symbol: str
    pnl: float
    trade_count: int
    order_done: bool
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "pnl": self.pnl,
            "trade_count": self.trade_count,
            "order_done": self.order_done,
            "message": self.message,
        }


def action_type_from_weights(current: float, target: float) -> ActionType:
    """由当前/目标权重推导 action_type。"""
    if current <= 0 and target > 0:
        return "OPEN"
    if current > 0 and target <= 0:
        return "CLOSE"
    if target > current:
        return "ADD"
    if target < current:
        return "TRIM"
    return "HOLD"


@dataclass
class RunIndexEntry:
    """运行索引单条：写入 runs/index.json，供 get_recent_runs / get_last_run 使用。"""
    run_id: str
    timestamp: str
    symbols: list[str]
    decision_summary: str
    portfolio_value: float
    orders: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "symbols": list(self.symbols),
            "decision_summary": self.decision_summary,
            "portfolio_value": self.portfolio_value,
            "orders": self.orders,
        }


@dataclass
class ExperienceRecord:
    """单次 run 经验记录：追加到 runs/experience.jsonl，非学习系统，仅记录。"""
    run_id: str
    timestamp: str
    symbols: list[str]
    rebalance_plan: dict[str, Any]
    decision_summary: str
    portfolio_before: dict[str, Any]
    portfolio_after: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "symbols": list(self.symbols),
            "rebalance_plan": dict(self.rebalance_plan),
            "decision_summary": self.decision_summary,
            "portfolio_before": dict(self.portfolio_before),
            "portfolio_after": dict(self.portfolio_after),
        }
