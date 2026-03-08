"""PortfolioAllocator: snapshot + mandate + ranked opportunities/signals -> PortfolioTarget (target_positions, replacements, rationale)."""
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
    Compare current positions vs ranked opportunities; replace only when new opportunity score > weakest current holding.
    Input: signals may include "score" (from OpportunityRanking); sorted by score desc when present.
    Output: target_positions, replacement_decisions (why replaced), allocation_rationale.
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
        # Sort by score desc when present (opportunity ranking), else by size_fraction
        has_scores = any(s.get("score") is not None for s in signals)
        def sort_key(s: dict) -> tuple[float, float]:
            score = float(s.get("score", 0) or 0)
            size = float(s.get("size_fraction", s.get("allowed_position_size", 0)) or 0)
            if has_scores:
                return (-score, -size)
            return (-size, 0.0)
        sorted_signals = sorted(signals, key=sort_key)

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
            score = float(s.get("score", 0) or 0)
            target_entry = {"symbol": symbol, "weight_pct": weight, "rationale": rationale}
            if has_scores:
                target_entry["score"] = score

            if symbol in current_positions:
                targets.append(target_entry)
                used_symbols.add(symbol)
                taken += weight
                continue
            if len(targets) >= slots:
                # Replacement: only when new opportunity score > weakest current holding score
                weakest = min(
                    targets,
                    key=lambda t: (float(t.get("score", 0) or 0), t.get("weight_pct", 1.0)),
                )
                weakest_score = float(weakest.get("score", 0) or 0)
                if has_scores and score <= weakest_score:
                    continue
                replacement_decisions.append({
                    "symbol_out": weakest["symbol"],
                    "symbol_in": symbol,
                    "reason": f"new_score_{score:.2f}_gt_weakest_{weakest_score:.2f}_{rationale[:25]}",
                })
                targets.remove(weakest)
                used_symbols.discard(weakest["symbol"])
                targets.append(target_entry)
                used_symbols.add(symbol)
                taken = sum(t["weight_pct"] for t in targets)
                continue
            targets.append(target_entry)
            used_symbols.add(symbol)
            taken += weight
            if taken >= 1.0:
                break

        # Post-pass: record replacements when current positions were dropped for new opportunities
        target_symbols = {t["symbol"] for t in targets}
        out_set = set(current_positions) - target_symbols
        in_list = [t for t in targets if t["symbol"] not in current_positions]
        if not replacement_decisions and out_set and in_list and has_scores:
            # Pair each new position with a dropped current (by score order)
            out_list = sorted(out_set)
            for i, t in enumerate(in_list):
                if i < len(out_list):
                    symbol_in = t["symbol"]
                    symbol_out = out_list[i]
                    new_score = float(t.get("score", 0) or 0)
                    replacement_decisions.append({
                        "symbol_out": symbol_out,
                        "symbol_in": symbol_in,
                        "reason": f"new_score_{new_score:.2f}_replaced_{symbol_out}_{t.get('rationale', '')[:25]}",
                    })

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
