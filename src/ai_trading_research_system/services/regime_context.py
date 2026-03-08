"""
Regime context for Experience Store: spy_trend, vix_level.
使用 MarketDataService（IB Gateway）获取 SPY/VIX 数据；不再直接调用 yfinance。
"""
from __future__ import annotations

import logging
import time

from ai_trading_research_system.data.market_data_service import get_market_data_service

logger = logging.getLogger(__name__)


def get_regime_context(use_mock: bool = False) -> tuple[str, str]:
    """
    Returns (spy_trend, vix_level).
    spy_trend: "up" | "down" | "sideways"
    vix_level: "low" | "medium" | "high"
    数据来自 MarketDataService（IB）；use_mock 时返回默认值。
    """
    if use_mock:
        return "sideways", "medium"
    t0 = time.perf_counter()
    mds = get_market_data_service(for_research=False)
    # SPY
    spy_bars = mds.get_history("SPY", 5)
    if spy_bars and len(spy_bars) >= 2:
        p0 = spy_bars[0].get("close") or 0
        p1 = spy_bars[-1].get("close") or 0
        ret = (p1 - p0) / p0 if p0 else 0
        spy_trend = "up" if ret > 0.01 else ("down" if ret < -0.01 else "sideways")
    else:
        spy_trend = "sideways"
    # VIX（IB 指数 ^VIX 或 VIX）
    vix_bars = mds.get_history("^VIX", 5)
    if not vix_bars:
        vix_bars = mds.get_history("VIX", 5)
    if vix_bars and len(vix_bars) > 0:
        level = float(vix_bars[-1].get("close") or 0)
        vix_level = "high" if level > 25 else ("low" if level < 18 else "medium")
    else:
        vix_level = "medium"
    elapsed = time.perf_counter() - t0
    logger.info("[ib] regime context latency=%.2fs", elapsed)
    return spy_trend, vix_level
