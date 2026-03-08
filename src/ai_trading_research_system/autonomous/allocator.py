"""PortfolioAllocator: snapshot + mandate + signals -> target_positions. No direct order."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_trading_research_system.autonomous.schemas import AccountSnapshot, WeeklyTradingMandate


@dataclass
class AllocationResult:
    target_positions: list[dict[str, Any]]
    cash_reserve: float
    allocation_rationale: str
    no_trade: bool = False
    no_trade_reason: str = ""


class PortfolioAllocator:
    def __init__(self, max_position_pct: float = 0.25):
        self.max_position_pct = max_position_pct

    def allocate(
        self,
        account_snapshot: AccountSnapshot,
        mandate: WeeklyTradingMandate,
        signals: list[dict[str, Any]] | None = None,
        wait_confirmation: bool = False,
    ) -> AllocationResult:
        if wait_confirmation:
            return AllocationResult(
                target_positions=[],
                cash_reserve=account_snapshot.cash * mandate.cash_reserve_pct,
                allocation_rationale="wait_confirmation",
                no_trade=True,
                no_trade_reason="wait_confirmation",
            )
        signals = signals or []
        if not signals:
            return AllocationResult(
                target_positions=[],
                cash_reserve=account_snapshot.cash * mandate.cash_reserve_pct,
                allocation_rationale="no_signals",
                no_trade=True,
                no_trade_reason="no_signals",
            )
        cash_reserve = account_snapshot.total_equity() * mandate.cash_reserve_pct
        targets = []
        taken = 0.0
        for s in signals[: mandate.max_positions]:
            symbol = s.get("symbol", "")
            size_fraction = float(s.get("size_fraction", s.get("allowed_position_size", 0)))
            weight = min(size_fraction, self.max_position_pct)
            if weight <= 0 or not symbol:
                continue
            targets.append({"symbol": symbol, "weight_pct": weight, "rationale": s.get("rationale", "signal")})
            taken += weight
            if taken >= 1.0:
                break
        return AllocationResult(
            target_positions=targets,
            cash_reserve=cash_reserve,
            allocation_rationale=f"positions={len(targets)} cash_reserve_pct={mandate.cash_reserve_pct}",
            no_trade=len(targets) == 0,
            no_trade_reason="no_valid_signals" if len(targets) == 0 else "",
        )
