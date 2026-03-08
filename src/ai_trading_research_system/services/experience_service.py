"""
Experience service: write weekly paper run result to Experience Store.
Used by UC-09 weekly controller for each symbol/day run.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ai_trading_research_system.experience.writer import write_run_result, RunResultPayload


def write_weekly_run(
    symbol: str,
    pnl: float,
    trade_count: int,
    extra: dict[str, Any],
    *,
    regime_tag: str = "weekly_paper",
) -> int:
    """Write one weekly paper run to Experience Store. Returns strategy_run id."""
    start_d = datetime.now(timezone.utc).date().isoformat()
    payload = RunResultPayload(
        symbol=symbol,
        start_date=start_d,
        end_date=start_d,
        sharpe=0.0,
        max_drawdown=0.0,
        win_rate=0.0,
        pnl=pnl,
        trade_count=trade_count,
        extra=extra,
        regime_tag=regime_tag,
    )
    return write_run_result(payload)
