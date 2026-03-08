"""
MarketDataService: IB 主数据源、yfinance research fallback、benchmark 缓存。
"""
from __future__ import annotations

import os
import time

import pytest

from ai_trading_research_system.data.market_data_service import (
    MarketDataService,
    get_market_data_service,
    _ib_configured,
    _BENCHMARK_CACHE,
)


def test_get_market_data_service_factory():
    """get_market_data_service(for_research=False) 不启用 yf fallback；for_research=True 启用。"""
    mds_main = get_market_data_service(for_research=False)
    assert mds_main.allow_yf_fallback is False
    mds_research = get_market_data_service(for_research=True)
    assert mds_research.allow_yf_fallback is True


def test_get_latest_price_without_ib_returns_snapshot():
    """无 IB 配置时 get_latest_price 仍返回 PriceSnapshot（source=none 或 yfinance 若 fallback）。"""
    # 确保测试环境无 IB（或临时清除）
    orig_host = os.environ.pop("IBKR_HOST", None)
    orig_port = os.environ.pop("IBKR_PORT", None)
    try:
        mds = MarketDataService(allow_yf_fallback=False)
        snap = mds.get_latest_price("SPY")
        assert snap.symbol == "SPY"
        assert hasattr(snap, "last_price")
        assert hasattr(snap, "change_pct")
        assert snap.source in ("none", "ib", "yfinance")
        # 无 IB 且不 fallback 时应为 none 或 last_price=0
        if not _ib_configured():
            assert snap.source in ("none", "yfinance")
    finally:
        if orig_host is not None:
            os.environ["IBKR_HOST"] = orig_host
        if orig_port is not None:
            os.environ["IBKR_PORT"] = orig_port


def test_fallback_to_yfinance_when_allowed():
    """allow_yf_fallback=True 且无 IB 时，get_latest_price 可回退到 yfinance（research 场景）。"""
    orig_host = os.environ.pop("IBKR_HOST", None)
    orig_port = os.environ.pop("IBKR_PORT", None)
    try:
        mds = MarketDataService(allow_yf_fallback=True)
        snap = mds.get_latest_price("SPY")
        assert snap.symbol == "SPY"
        # 可能 source=none（网络/限流）或 yfinance
        assert snap.source in ("none", "ib", "yfinance")
        if snap.source == "yfinance":
            assert snap.last_price > 0
    finally:
        if orig_host is not None:
            os.environ["IBKR_HOST"] = orig_host
        if orig_port is not None:
            os.environ["IBKR_PORT"] = orig_port


def test_benchmark_series_uses_cache():
    """get_benchmark_series 使用缓存，相同 (symbol, lookback_days) 在 TTL 内应命中。"""
    # 清空缓存以便观察
    _BENCHMARK_CACHE.clear()
    mds = get_market_data_service(for_research=False)
    key = ("SPY", 5)
    returns1, tr1, vol1, dd1 = mds.get_benchmark_series("SPY", lookback_days=5, use_cache=True)
    assert key in _BENCHMARK_CACHE
    ts_first, _ = _BENCHMARK_CACHE[key]
    returns2, tr2, vol2, dd2 = mds.get_benchmark_series("SPY", lookback_days=5, use_cache=True)
    ts_second, _ = _BENCHMARK_CACHE[key]
    assert ts_first == ts_second
    assert returns1 == returns2 and tr1 == tr2 and vol1 == vol2 and dd1 == dd2


@pytest.mark.skipif(not _ib_configured(), reason="IBKR_HOST/PORT not set")
def test_ib_data_read_when_configured():
    """当配置了 IB 时，应能读取到数据（SPY 至少应有 bars 或明确失败）。"""
    mds = get_market_data_service(for_research=False)
    bars = mds.get_history("SPY", 5)
    # 可能因 Gateway 未开而为空，或成功拿到数据
    if bars:
        assert len(bars) >= 1
        assert all("close" in b and "date" in b for b in bars)
    series_returns, total_ret, vol, max_dd = mds.get_benchmark_series("SPY", lookback_days=5, use_cache=False)
    # 有数据时应有 returns；无数据时为 ([], 0, 0, 0)
    if series_returns:
        assert total_ret != 0.0 or len(series_returns) == 0
        assert isinstance(vol, (int, float)) and isinstance(max_dd, (int, float))
