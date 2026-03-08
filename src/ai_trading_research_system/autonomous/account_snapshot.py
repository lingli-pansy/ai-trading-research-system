"""
AccountSnapshot：paper 模式下统一账户快照。默认优先 IBKR paper 账户，仅显式 --mock 或连接失败且允许 fallback 时用 mock。
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from ai_trading_research_system.autonomous.schemas import AccountSnapshot


def _ibkr_configured() -> bool:
    return bool((os.environ.get("IBKR_HOST") or "").strip() and (os.environ.get("IBKR_PORT") or "").strip())


def get_account_snapshot(
    *,
    paper: bool = True,
    mock: bool = False,
    initial_cash: float = 10_000.0,
    allow_fallback: bool = True,
) -> AccountSnapshot:
    """
    获取统一账户快照。默认优先 IBKR paper（需配置 IBKR_HOST/IBKR_PORT）。
    - mock=True：强制 mock，snapshot_source=mock。
    - mock=False：先尝试 IBKR，成功则 snapshot_source=ibkr；失败且 allow_fallback 则 mock 且 source=mock。
    """
    if mock:
        return _mock_account_snapshot(initial_cash=initial_cash)

    if paper and _ibkr_configured():
        from ai_trading_research_system.execution.ibkr_client import get_ibkr_account_snapshot_raw

        raw = get_ibkr_account_snapshot_raw()
        if raw is not None:
            risk_budget = raw.equity * 0.02 if raw.equity else (raw.cash * 0.02)
            return AccountSnapshot(
                cash=raw.cash,
                equity=raw.equity,
                positions=raw.positions,
                open_orders=raw.open_orders,
                risk_budget=risk_budget,
                timestamp=datetime.now(timezone.utc).isoformat(),
                buying_power=raw.buying_power,
                source="ibkr",
            )

    if allow_fallback:
        return _mock_account_snapshot(initial_cash=initial_cash)

    return _mock_account_snapshot(initial_cash=initial_cash)


def _mock_account_snapshot(initial_cash: float = 10_000.0) -> AccountSnapshot:
    """无 broker 或 fallback 时的本地 mock：现金=initial_cash，无持仓、无挂单。"""
    return AccountSnapshot(
        cash=initial_cash,
        equity=initial_cash,
        positions=[],
        open_orders=[],
        risk_budget=initial_cash * 0.02,
        timestamp=datetime.now(timezone.utc).isoformat(),
        buying_power=initial_cash,
        source="mock",
    )
