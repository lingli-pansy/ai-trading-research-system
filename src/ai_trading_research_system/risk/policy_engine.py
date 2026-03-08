"""
RiskPolicyEngine: 在 rebalance_plan 执行前进行风险检查。
约束：max_position_size, max_turnover, max_orders_per_run, min_cash_buffer。
违反时自动 trim 或 skip order，并输出 risk_flags 供 audit。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RiskPolicy:
    """风险策略约束。"""
    max_position_size: float = 0.20   # 单标的最大权重
    max_turnover: float = 0.30       # 单次 run 最大换手（abs(delta) 之和）
    max_orders_per_run: int = 10     # 单次 run 最大订单数
    min_cash_buffer: float = 0.05    # 最低现金占比（equity 的占比）


@dataclass
class RiskCheckResult:
    """风险检查结果。"""
    filtered_rebalance_plan: dict[str, Any]  # 过滤后的 plan（与 RebalancePlan.to_dict() 结构一致）
    risk_flags: list[str] = field(default_factory=list)


def _equity(portfolio: dict[str, Any]) -> float:
    return float(portfolio.get("equity_estimate", portfolio.get("equity", 0)) or 0)


def _cash(portfolio: dict[str, Any]) -> float:
    return float(portfolio.get("cash_estimate", portfolio.get("cash", 0)) or 0)


class RiskPolicyEngine:
    """
    在 rebalance_plan 执行前做风险检查；违反则 trim/skip，并写 risk_flags 供 audit。
    """

    def __init__(self, policy: RiskPolicy | None = None):
        self.policy = policy or RiskPolicy()

    def check(
        self,
        portfolio_before: dict[str, Any],
        rebalance_plan: dict[str, Any],
    ) -> RiskCheckResult:
        """
        输入：portfolio_before, rebalance_plan（dict，含 items / no_trade_reason）。
        输出：filtered_rebalance_plan, risk_flags。
        """
        flags: list[str] = []
        if rebalance_plan.get("no_trade_reason"):
            return RiskCheckResult(
                filtered_rebalance_plan=dict(rebalance_plan),
                risk_flags=[],
            )
        items = list(rebalance_plan.get("items") or [])
        if not items:
            return RiskCheckResult(
                filtered_rebalance_plan=dict(rebalance_plan),
                risk_flags=[],
            )
        equity = _equity(portfolio_before)
        cash_before = _cash(portfolio_before)
        if equity <= 0:
            return RiskCheckResult(
                filtered_rebalance_plan={"items": [], "no_trade_reason": "no_equity"},
                risk_flags=["no_equity"],
            )
        min_cash = equity * self.policy.min_cash_buffer
        # 1) 单标的 cap max_position_size
        filtered: list[dict[str, Any]] = []
        for it in items:
            sym = it.get("symbol", "")
            target = float(it.get("target_position", 0) or 0)
            current = float(it.get("current_position", 0) or 0)
            delta = float(it.get("delta", 0) or 0)
            if target > self.policy.max_position_size:
                flags.append(f"trim_position_{sym}_{target:.2f}_to_{self.policy.max_position_size}")
                target = self.policy.max_position_size
                delta = target - current
            filtered.append({
                **dict(it),
                "symbol": sym,
                "target_position": target,
                "current_position": current,
                "delta": delta,
            })
        # 2) 总换手 cap max_turnover（按 |delta| 从大到小保留）
        total_turnover = sum(abs(x["delta"]) for x in filtered)
        if total_turnover > self.policy.max_turnover:
            flags.append(f"trim_turnover_{total_turnover:.2f}_to_{self.policy.max_turnover}")
            # 按 |delta| 降序，依次累加直到达到 max_turnover
            ordered = sorted(filtered, key=lambda x: -abs(x["delta"]))
            allowed = self.policy.max_turnover
            new_filtered: list[dict[str, Any]] = []
            for x in ordered:
                d = abs(x["delta"])
                if d <= 0:
                    new_filtered.append(x)
                    continue
                if allowed <= 0:
                    # 不再允许任何变动，改为 HOLD
                    new_filtered.append({
                        **x,
                        "delta": 0.0,
                        "target_position": x["current_position"],
                        "action_type": "HOLD",
                    })
                    continue
                if d <= allowed:
                    new_filtered.append(x)
                    allowed -= d
                else:
                    # 部分保留：按比例缩小 delta
                    scale = allowed / d
                    new_delta = x["delta"] * scale
                    new_filtered.append({
                        **x,
                        "delta": new_delta,
                        "target_position": x["current_position"] + new_delta,
                        "action_type": x.get("action_type", "HOLD"),
                    })
                    allowed = 0
            # 恢复原始顺序（按 symbol）
            by_sym = {x["symbol"]: x for x in new_filtered}
            filtered = [by_sym[it["symbol"]] for it in items if it["symbol"] in by_sym]
        # 3) 订单数 cap max_orders_per_run（只保留前 N 个非 HOLD，其余改为 HOLD）
        non_hold = [x for x in filtered if (x.get("action_type") or "HOLD") != "HOLD" and abs(x.get("delta", 0)) > 1e-9]
        if len(non_hold) > self.policy.max_orders_per_run:
            flags.append(f"trim_orders_{len(non_hold)}_to_{self.policy.max_orders_per_run}")
            keep_syms = {x["symbol"] for x in non_hold[: self.policy.max_orders_per_run]}
            filtered = [
                x if x["symbol"] in keep_syms else {**x, "delta": 0.0, "target_position": x.get("current_position", 0), "action_type": "HOLD"}
                for x in filtered
            ]
        # 4) min_cash_buffer：确保执行后现金 >= min_cash
        # 简化：若 (1 - sum(target)) * equity < min_cash，则 trim 部分 ADD
        total_target = sum(x.get("target_position", 0) for x in filtered)
        cash_after_estimate = equity * (1 - total_target) if total_target <= 1 else 0
        if cash_after_estimate < min_cash and cash_before >= min_cash:
            flags.append(f"trim_cash_buffer_{cash_after_estimate:.2f}_min_{min_cash:.2f}")
            # 对 ADD 类按 delta 从大到小减到满足 buffer
            need_reduce = min_cash - cash_after_estimate
            adds = [x for x in filtered if (x.get("delta") or 0) > 0]
            adds.sort(key=lambda x: -(x.get("delta") or 0))
            for x in adds:
                if need_reduce <= 0:
                    break
                d = x.get("delta") or 0
                if d <= 0:
                    continue
                reduce = min(d, need_reduce)
                x["delta"] = d - reduce
                x["target_position"] = (x.get("current_position") or 0) + x["delta"]
                need_reduce -= reduce

        return RiskCheckResult(
            filtered_rebalance_plan={"items": filtered, "no_trade_reason": rebalance_plan.get("no_trade_reason", "")},
            risk_flags=flags,
        )


def plan_to_target_positions(plan_dict: dict[str, Any]) -> list[dict[str, Any]]:
    """从 rebalance_plan dict 提取 target_positions 列表，供 execute_paper_orders 使用。"""
    items = plan_dict.get("items") or []
    return [
        {"symbol": x.get("symbol", ""), "weight_pct": x.get("target_position", 0), "rationale": x.get("reason", "")}
        for x in items
    ]
