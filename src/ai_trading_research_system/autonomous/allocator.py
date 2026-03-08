"""PortfolioAllocator: snapshot + mandate + policy + ranked opportunities -> target_positions, replacements, retained, rejected, rationale."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_trading_research_system.autonomous.schemas import AccountSnapshot, WeeklyTradingMandate
from ai_trading_research_system.autonomous.portfolio_policy import PortfolioDecisionPolicy, default_policy


@dataclass
class AllocationResult:
    target_positions: list[dict[str, Any]]
    cash_reserve: float
    allocation_rationale: str
    no_trade: bool = False
    no_trade_reason: str = ""
    replacement_decisions: list[dict[str, Any]] = field(default_factory=list)
    retained_positions: list[dict[str, Any]] = field(default_factory=list)
    rejected_opportunities: list[dict[str, Any]] = field(default_factory=list)
    policy_summary: dict[str, Any] = field(default_factory=dict)


class PortfolioAllocator:
    """
    比较当前持仓与排序后的机会；仅在满足 policy（min_score_gap、max_replacements、turnover_budget）时允许替换。
    输出：target_positions, replacement_decisions, retained_positions, rejected_opportunities, policy_summary, allocation_rationale.
    """

    def __init__(self, max_position_pct: float = 0.25):
        self.max_position_pct = max_position_pct

    def allocate(
        self,
        account_snapshot: AccountSnapshot,
        mandate: WeeklyTradingMandate,
        signals: list[dict[str, Any]] | None = None,
        policy: PortfolioDecisionPolicy | None = None,
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
                cash_reserve=account_snapshot.total_equity() * mandate.cash_reserve_pct,
                allocation_rationale="no_signals",
                no_trade=True,
                no_trade_reason="no_signals",
            )

        policy = policy or default_policy()
        cash_reserve = account_snapshot.total_equity() * mandate.cash_reserve_pct
        current_positions = {p.get("symbol"): p for p in (account_snapshot.positions or []) if p.get("symbol")}
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
        rejected_opportunities: list[dict[str, Any]] = []
        replacements_skipped_threshold = 0
        replacements_skipped_budget = 0
        score_gap_used: float | None = None
        taken = 0.0
        slots = mandate.max_positions
        used_symbols: set[str] = set()
        turnover_used = 0.0

        for s in sorted_signals[: slots * 2]:
            if taken >= 1.0:
                break
            symbol = s.get("symbol", "")
            size_fraction = float(s.get("size_fraction", s.get("allowed_position_size", 0)) or 0)
            weight = min(size_fraction, self.max_position_pct)
            if weight <= 0 or not symbol:
                continue
            rationale = s.get("rationale", "signal")
            score = float(s.get("score", 0) or 0)
            target_entry = {"symbol": symbol, "weight_pct": weight, "rationale": rationale}
            if has_scores:
                target_entry["score"] = score

            if symbol in current_positions:
                if len(targets) < slots:
                    targets.append(target_entry)
                    used_symbols.add(symbol)
                    taken += weight
                continue

            if len(targets) >= slots:
                weakest = min(
                    targets,
                    key=lambda t: (float(t.get("score", 0) or 0), t.get("weight_pct", 1.0)),
                )
                weakest_score = float(weakest.get("score", 0) or 0)
                if has_scores:
                    gap = score - weakest_score
                    gap_required = policy.minimum_score_gap_for_replacement
                    if weakest_score >= policy.retain_threshold:
                        gap_required += max(0.0, weakest_score - policy.retain_threshold)
                    if gap < gap_required:
                        replacements_skipped_threshold += 1
                        rejected_opportunities.append({
                            "symbol": symbol,
                            "score": score,
                            "reason": f"score_gap_{gap:.2f}_below_required_{gap_required:.2f}",
                        })
                        continue
                else:
                    if score <= weakest_score:
                        continue
                if has_scores and len(replacement_decisions) >= policy.max_replacements_per_rebalance:
                    replacements_skipped_budget += 1
                    rejected_opportunities.append({
                        "symbol": symbol,
                        "score": score,
                        "reason": "max_replacements_per_rebalance_reached",
                    })
                    continue
                leg_turnover = (weakest.get("weight_pct", 0) or 0) + weight
                if has_scores and (turnover_used + leg_turnover) > policy.turnover_budget:
                    replacements_skipped_budget += 1
                    rejected_opportunities.append({
                        "symbol": symbol,
                        "score": score,
                        "reason": f"turnover_budget_exceeded_{turnover_used + leg_turnover:.2f}_gt_{policy.turnover_budget}",
                    })
                    continue
                if score_gap_used is None:
                    score_gap_used = gap
                replacement_decisions.append({
                    "symbol_out": weakest["symbol"],
                    "symbol_in": symbol,
                    "reason": f"new_score_{score:.2f}_gap_{gap:.2f}_gt_required_{gap_required:.2f}_{rationale[:25]}",
                    "score_gap": gap,
                })
                turnover_used += leg_turnover
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

        # Post-pass: 当前持仓被整体挤出时，配对 (out, in) 并受 policy 约束；若拒绝替换则保留 out、移除 in
        target_symbols = {t["symbol"] for t in targets}
        out_set = set(current_positions) - target_symbols
        in_list = [t for t in targets if t["symbol"] not in current_positions]
        rejected_pairs: list[tuple[str, str]] = []  # (symbol_in, symbol_out) 因 policy 未替换
        if not replacement_decisions and out_set and in_list and has_scores:
            out_list = sorted(out_set)
            for i, t in enumerate(in_list):
                if i >= len(out_list):
                    break
                if len(replacement_decisions) >= policy.max_replacements_per_rebalance:
                    replacements_skipped_budget += 1
                    rejected_opportunities.append({
                        "symbol": t["symbol"],
                        "score": float(t.get("score", 0) or 0),
                        "reason": "max_replacements_per_rebalance_reached",
                    })
                    rejected_pairs.append((t["symbol"], out_list[i]))
                    continue
                symbol_in = t["symbol"]
                symbol_out = out_list[i]
                new_score = float(t.get("score", 0) or 0)
                weakest_score = 0.0
                gap = new_score - weakest_score
                gap_required = policy.minimum_score_gap_for_replacement
                if gap < gap_required:
                    replacements_skipped_threshold += 1
                    rejected_opportunities.append({
                        "symbol": symbol_in,
                        "score": new_score,
                        "reason": f"score_gap_{gap:.2f}_below_required_{gap_required:.2f}",
                    })
                    rejected_pairs.append((symbol_in, symbol_out))
                    continue
                weight = t.get("weight_pct", 0) or 0
                leg_turnover = weight * 2
                if turnover_used + leg_turnover > policy.turnover_budget:
                    replacements_skipped_budget += 1
                    rejected_opportunities.append({
                        "symbol": symbol_in,
                        "score": new_score,
                        "reason": "turnover_budget_exceeded",
                    })
                    rejected_pairs.append((symbol_in, symbol_out))
                    continue
                if score_gap_used is None:
                    score_gap_used = gap
                replacement_decisions.append({
                    "symbol_out": symbol_out,
                    "symbol_in": symbol_in,
                    "reason": f"new_score_{new_score:.2f}_replaced_{symbol_out}_{t.get('rationale', '')[:25]}",
                    "score_gap": gap,
                })
                turnover_used += leg_turnover
        for symbol_in, symbol_out in rejected_pairs:
            targets[:] = [t for t in targets if t["symbol"] != symbol_in]
            targets.append({"symbol": symbol_out, "weight_pct": 0.2, "rationale": "retained_policy"})

        retained_positions = [t for t in targets if t["symbol"] in current_positions]
        rationale_parts = [f"positions={len(targets)}", f"cash_reserve_pct={mandate.cash_reserve_pct}"]
        if replacement_decisions:
            rationale_parts.append(f"replacements={len(replacement_decisions)}")
        if replacements_skipped_threshold:
            rationale_parts.append(f"skipped_threshold={replacements_skipped_threshold}")
        if replacements_skipped_budget:
            rationale_parts.append(f"skipped_budget={replacements_skipped_budget}")

        policy_summary: dict[str, Any] = {
            "score_gap_used": score_gap_used,
            "replacements_executed": len(replacement_decisions),
            "replacements_skipped_due_to_threshold": replacements_skipped_threshold,
            "replacements_skipped_due_to_budget": replacements_skipped_budget,
            "rejected_due_to_threshold": replacements_skipped_threshold,
        }

        return AllocationResult(
            target_positions=targets,
            cash_reserve=cash_reserve,
            allocation_rationale=" ".join(rationale_parts),
            no_trade=len(targets) == 0,
            no_trade_reason="no_valid_signals" if len(targets) == 0 else "",
            replacement_decisions=replacement_decisions,
            retained_positions=retained_positions,
            rejected_opportunities=rejected_opportunities,
            policy_summary=policy_summary,
        )
