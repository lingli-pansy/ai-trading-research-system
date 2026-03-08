"""
UC-09 自治控制层：AccountSnapshot、WeeklyTradingMandate 等数据结构。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AccountSnapshot:
    """统一账户快照，供 mandate、allocator、report 使用。"""
    cash: float
    equity: float
    positions: list[dict[str, Any]]  # [{"symbol": str, "quantity": float, "market_value": float}, ...]
    open_orders: list[dict[str, Any]]  # [{"symbol", "side", "quantity", "status"}, ...]
    risk_budget: float  # 剩余风险预算（如每日止损剩余）
    timestamp: str  # ISO format
    buying_power: float = 0.0  # 可用购买力（IBKR 等返回）
    source: str = "mock"  # "ibkr" | "mock"，用于显式记录数据来源

    def total_equity(self) -> float:
        return self.equity if self.equity > 0 else self.cash


@dataclass
class WeeklyTradingMandate:
    """用户目标的结构化表示（一周自治 Paper）。"""
    mandate_id: str
    mode: str = "paper"
    capital_limit: float = 10_000.0
    benchmark: str = "SPY"
    duration_trading_days: int = 5
    auto_confirm: bool = True
    rebalance_policy: str = "allow_rebalance"
    risk_profile: str = "moderate"
    max_positions: int = 5
    cash_reserve_pct: float = 0.1
    stop_conditions: list[str] = field(default_factory=list)  # e.g. ["max_drawdown_5pct", "kill_switch"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mandate_id": self.mandate_id,
            "mode": self.mode,
            "capital_limit": self.capital_limit,
            "benchmark": self.benchmark,
            "duration_trading_days": self.duration_trading_days,
            "auto_confirm": self.auto_confirm,
            "rebalance_policy": self.rebalance_policy,
            "risk_profile": self.risk_profile,
            "max_positions": self.max_positions,
            "cash_reserve_pct": self.cash_reserve_pct,
            "stop_conditions": self.stop_conditions,
        }
