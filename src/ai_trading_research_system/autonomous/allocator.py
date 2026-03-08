"""PortfolioAllocator: snapshot + mandate + signals -> target_positions, replacement_decisions. No direct order."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_trading_research_system.autonomous.schemas import AccountSnapshot, WeeklyTradingMandate


@dataclass
class AllocationResult:
    target_positions: list[dict[str, Any]]
    cash_reserve: float
    allocation_rationale: str
    no_trade: bool = False
    no_trade_reason: str = ""
    replacement_decisions: list[dict[str, Any]] = field(default_factory=list)


class PortfolioAllocator:
    """
    比较 current positions 与 new opportunities；若新机会更优可替换旧仓位。
    输出 target_positions、replacement_decisions、allocation_rationale。
    """

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
        current_positions = {p.get("symbol"): p for p in (account_snapshot.positions or []) if p.get("symbol")}
        # 新信号按 size_fraction 降序（更优机会优先）
        sorted_signals = sorted(
            signals,
            key=lambda s: float(s.get("size_fraction", s.get("allowed_position_size", 0))),
            reverse=True,
        )
        targets: list[dict[str, Any]] = []
        replacement_decisions: list[dict[str, Any]] = []
        taken = 0.0
        slots = mandate.max_positions
        used_symbols: set[str] = set()

        for s in sorted_signals[: slots * 2]:
            if taken >= 1.0:
                break
            symbol = s.get("symbol", "")
            size_fraction = float(s.get("size_fraction", s.get("allowed_position_size", 0)))
            weight = min(size_fraction, self.max_position_pct)
            if weight <= 0 or not symbol:
                continue
            rationale = s.get("rationale", "signal")
            if symbol in current_positions:
                targets.append({"symbol": symbol, "weight_pct": weight, "rationale": rationale})
                used_symbols.add(symbol)
                taken += weight
                continue
            if len(targets) >= slots:
                # 替换：从 current 中选一个不在 targets 的仓位换出，或从 targets 中换出最弱
                replaced = False
                for pos_sym in list(current_positions.keys()):
                    if pos_sym in used_symbols:
                        continue
                    replacement_decisions.append({
                        "symbol_out": pos_sym,
                        "symbol_in": symbol,
                        "reason": f"replace_with_{rationale[:30]}",
                    })
                    targets.append({"symbol": symbol, "weight_pct": weight, "rationale": rationale})
                    used_symbols.add(symbol)
                    taken += weight
                    replaced = True
                    break
                if not replaced:
                    worst = min(targets, key=lambda t: t["weight_pct"])
                    replacement_decisions.append({
                        "symbol_out": worst["symbol"],
                        "symbol_in": symbol,
                        "reason": f"replace_weaker_with_{rationale[:30]}",
                    })
                    targets.remove(worst)
                    targets.append({"symbol": symbol, "weight_pct": weight, "rationale": rationale})
                    used_symbols.discard(worst["symbol"])
                    used_symbols.add(symbol)
                    taken = sum(t["weight_pct"] for t in targets)
                break
            targets.append({"symbol": symbol, "weight_pct": weight, "rationale": rationale})
            used_symbols.add(symbol)
            taken += weight
            if taken >= 1.0:
                break

        rationale_parts = [f"positions={len(targets)}", f"cash_reserve_pct={mandate.cash_reserve_pct}"]
        if replacement_decisions:
            rationale_parts.append(f"replacements={len(replacement_decisions)}")
        return AllocationResult(
            target_positions=targets,
            cash_reserve=cash_reserve,
            allocation_rationale=" ".join(rationale_parts),
            no_trade=len(targets) == 0,
            no_trade_reason="no_valid_signals" if len(targets) == 0 else "",
            replacement_decisions=replacement_decisions,
        )
