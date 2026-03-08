"""
AccountSnapshot：paper 模式下统一账户快照；无真实 broker 时 mock/local fallback。
"""
from __future__ import annotations

from datetime import datetime, timezone

from ai_trading_research_system.autonomous.schemas import AccountSnapshot


def get_account_snapshot(
    *,
    paper: bool = True,
    mock: bool = True,
    initial_cash: float = 10_000.0,
) -> AccountSnapshot:
    """
    获取统一账户快照。paper 模式且无真实 broker 时返回 mock 快照（本地内存/配置）。
    输出结构稳定，供 mandate、allocator、report 使用。
    """
    if paper and mock:
        return _mock_account_snapshot(initial_cash=initial_cash)
    # 未来：从 IBKR / 其他 broker 拉取真实 snapshot
    return _mock_account_snapshot(initial_cash=initial_cash)


def _mock_account_snapshot(initial_cash: float = 10_000.0) -> AccountSnapshot:
    """无 broker 时的本地 fallback：现金=initial_cash，无持仓、无挂单。"""
    return AccountSnapshot(
        cash=initial_cash,
        equity=initial_cash,
        positions=[],
        open_orders=[],
        risk_budget=initial_cash * 0.02,  # 示例：2% 风险预算
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
