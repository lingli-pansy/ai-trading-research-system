"""
Regime context for Experience Store: spy_trend, vix_level.
Used by UC-09 to write regime_tag + spy_trend + vix_level into strategy_run.parameters.
"""
from __future__ import annotations


def get_regime_context(use_mock: bool = False) -> tuple[str, str]:
    """
    Returns (spy_trend, vix_level).
    spy_trend: "up" | "down" | "sideways"
    vix_level: "low" | "medium" | "high"
    """
    if use_mock:
        return "sideways", "medium"
    try:
        import yfinance as yf
        from datetime import datetime, timedelta, timezone
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=5)
        spy = yf.Ticker("SPY")
        hist = spy.history(start=start, end=end, auto_adjust=True)
        if hist is not None and len(hist) >= 2:
            p0 = float(hist["Close"].iloc[0])
            p1 = float(hist["Close"].iloc[-1])
            ret = (p1 - p0) / p0 if p0 else 0
            spy_trend = "up" if ret > 0.01 else ("down" if ret < -0.01 else "sideways")
        else:
            spy_trend = "sideways"
        vix = yf.Ticker("^VIX")
        vix_hist = vix.history(period="5d", auto_adjust=True)
        if vix_hist is not None and len(vix_hist) > 0:
            level = float(vix_hist["Close"].iloc[-1])
            vix_level = "high" if level > 25 else ("low" if level < 18 else "medium")
        else:
            vix_level = "medium"
        return spy_trend, vix_level
    except Exception:
        return "sideways", "medium"
