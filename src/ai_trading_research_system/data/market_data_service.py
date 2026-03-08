"""
MarketDataService: 主市场数据源。
优先级 1：IB Gateway / IBKR API；
优先级 2：yfinance 仅作为 research 可选补充（allow_yf_fallback=True 时）。
Benchmark 数据使用缓存，避免重复请求。
"""
from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Cache for benchmark series: (symbol, lookback_days) -> (ts, (returns, total_ret, vol, max_dd))
_BENCHMARK_CACHE: dict[tuple[str, int], tuple[float, tuple[list[float], float, float, float]]] = {}
_BENCHMARK_CACHE_TTL_SEC = 300.0


def _ib_configured() -> bool:
    return bool((os.environ.get("IBKR_HOST") or "").strip() and (os.environ.get("IBKR_PORT") or "").strip())


# 与 ibkr_client 区分：账户用 IBKR_CLIENT_ID(默认 1)，行情用 IBKR_MARKET_DATA_CLIENT_ID(默认 2)，避免同一 id 频繁重连导致 Gateway 报错
def _host_port_client_id(host: str | None = None, port: int | None = None, client_id: int = 2) -> tuple[str, int, int]:
    h = host or (os.environ.get("IBKR_HOST") or "127.0.0.1").strip()
    p = port if port is not None else int((os.environ.get("IBKR_PORT") or "4002").strip())
    cid = int(os.environ.get("IBKR_MARKET_DATA_CLIENT_ID") or str(client_id))
    return h, p, cid


def _ib_connect_timeout() -> float:
    try:
        return float(os.environ.get("IBKR_CONNECT_TIMEOUT", "60"))
    except (ValueError, TypeError):
        return 60.0


def _ib_disconnect_delay() -> float:
    try:
        return float(os.environ.get("IBKR_DISCONNECT_DELAY", "1"))
    except (ValueError, TypeError):
        return 1.0


def _ib_end_datetime(end_date: str | None) -> str:
    """IB 要求 endDateTime 为空或 UTC 格式 yyyymmdd-HH:mm:ss（见 TWS API Historical Bar Data）。空表示当前。"""
    if not end_date or not end_date.strip():
        return ""
    s = end_date.strip()
    if len(s) == 8 and s.isdigit():
        return f"{s}-23:59:59"
    if "-" in s:
        parts = s.split(" ")[0].split("-")
        if len(parts) >= 3:
            try:
                y, m, d = parts[0], parts[1].zfill(2), parts[2].zfill(2)
                return f"{y}{m}{d}-23:59:59"
            except Exception:
                pass
    return ""


def _ib_fetch_bars(
    symbol: str,
    duration_days: int,
    bar_size: str = "1 day",
    *,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """从 IB 拉取历史 K 线。若有 IBKRSession 复用则用单连接；否则每次建连。失败返回 []。"""
    try:
        from ai_trading_research_system.execution.ibkr_session import get_ibkr_session
        session = get_ibkr_session()
        if session is not None:
            return session.fetch_bars(symbol, duration_days, bar_size, end_date=end_date)
    except Exception:
        pass
    if not _ib_configured():
        return []
    try:
        import asyncio
        from ib_insync import IB, Stock, Index

        h, p, cid = _host_port_client_id()

        async def _fetch() -> list[dict[str, Any]]:
            ib = IB()
            try:
                await ib.connectAsync(h, p, clientId=cid, timeout=_ib_connect_timeout())
                # ^VIX -> Index; 其余按股票
                if symbol.startswith("^") or symbol.upper() == "VIX":
                    sym = symbol.lstrip("^")
                    contract = Index(sym, "CBOE", "USD") if sym == "VIX" else Stock(symbol, "SMART", "USD")
                else:
                    contract = Stock(symbol, "SMART", "USD")
                end = _ib_end_datetime(end_date)
                duration_str = f"{max(1, duration_days)} D"
                bars = await ib.reqHistoricalDataAsync(
                    contract,
                    endDateTime=end,
                    durationStr=duration_str,
                    barSizeSetting=bar_size,
                    whatToShow="TRADES",
                    useRTH=True,
                    formatDate=1,
                    timeout=30,
                )
                if not bars:
                    return []
                out = []
                for b in bars:
                    out.append({
                        "date": getattr(b, "date", None),
                        "open": float(getattr(b, "open", 0) or 0),
                        "high": float(getattr(b, "high", 0) or 0),
                        "low": float(getattr(b, "low", 0) or 0),
                        "close": float(getattr(b, "close", 0) or 0),
                        "volume": float(getattr(b, "volume", 0) or 0),
                    })
                return out
            finally:
                ib.disconnect()
                await asyncio.sleep(_ib_disconnect_delay())

        return asyncio.run(_fetch())
    except Exception:
        return []


def _yf_fetch_bars(symbol: str, start: str, end: str) -> list[dict[str, Any]]:
    """yfinance 拉取日线，仅用于 research fallback。返回同上格式。"""
    try:
        import yfinance as yf
        t = yf.Ticker(symbol)
        hist = t.history(start=start, end=end, auto_adjust=True)
        if hist is None or len(hist) < 2:
            return []
        out = []
        for idx in hist.index:
            row = hist.loc[idx]
            out.append({
                "date": idx,
                "open": float(row.get("Open", 0) or 0),
                "high": float(row.get("High", 0) or 0),
                "low": float(row.get("Low", 0) or 0),
                "close": float(row.get("Close", 0) or 0),
                "volume": float(row.get("Volume", 0) or 0),
            })
        return out
    except Exception:
        return []


@dataclass
class PriceSnapshot:
    """最新价快照，与 data.models.PriceSnapshot 字段兼容。"""
    symbol: str
    last_price: float
    change_pct: float = 0.0
    volume_ratio: float | None = None
    source: str = "ib"  # "ib" | "yfinance"


class MarketDataService:
    """
    主市场数据服务：IB Gateway 优先；allow_yf_fallback 时可用于 research 的 yfinance 补充。
    Benchmark 使用内存缓存，减少对 IB/yfinance 的重复请求。
    """

    def __init__(self, *, allow_yf_fallback: bool = False) -> None:
        self.allow_yf_fallback = allow_yf_fallback

    def get_latest_price(self, symbol: str) -> PriceSnapshot:
        """
        取最新价。优先 IB；若 allow_yf_fallback 且 IB 不可用/失败则用 yfinance（仅 research 场景）。
        """
        if _ib_configured():
            bars = _ib_fetch_bars(symbol, duration_days=3, bar_size="1 day")
            if bars:
                last = bars[-1]
                prev = bars[-2] if len(bars) >= 2 else last
                p0 = prev["close"] or 0.0001
                p1 = last["close"] or 0.0
                chg = (p1 - p0) / p0 * 100.0 if p0 else 0.0
                return PriceSnapshot(symbol=symbol, last_price=p1, change_pct=round(chg, 2), source="ib")
        if self.allow_yf_fallback:
            try:
                import yfinance as yf
                t = yf.Ticker(symbol)
                hist = t.history(period="5d")
                if hist is not None and len(hist) >= 2:
                    last = hist.iloc[-1]
                    prev = hist.iloc[-2]
                    p1 = float(last["Close"])
                    p0 = float(prev["Close"]) or 0.0001
                    chg = (p1 - p0) / p0 * 100.0 if p0 else 0.0
                    vol_ratio = None
                    if "Volume" in hist.columns and len(hist) > 1:
                        v_last = hist["Volume"].iloc[-1]
                        v_avg = hist["Volume"].iloc[:-1].mean()
                        if v_avg and v_avg > 0:
                            vol_ratio = round(float(v_last / v_avg), 2)
                    return PriceSnapshot(symbol=symbol, last_price=p1, change_pct=round(chg, 2), volume_ratio=vol_ratio, source="yfinance")
            except Exception:
                pass
        return PriceSnapshot(symbol=symbol, last_price=0.0, change_pct=0.0, source="none")

    def get_history(
        self,
        symbol: str,
        days: int,
        *,
        end_date: str | None = None,
        allow_yf_fallback: bool | None = None,
    ) -> list[dict[str, Any]]:
        """
        取 N 日日线。优先 IB；若 allow_yf_fallback 为 True 且 IB 不可用则用 yfinance。
        allow_yf_fallback 默认使用实例构造时的 self.allow_yf_fallback。
        """
        use_yf = allow_yf_fallback if allow_yf_fallback is not None else self.allow_yf_fallback
        if _ib_configured():
            bars = _ib_fetch_bars(symbol, duration_days=max(1, days), end_date=end_date or "")
            if bars:
                return bars
        if use_yf:
            end_dt = datetime.now(timezone.utc)
            start_dt = end_dt - timedelta(days=max(1, days))
            start = start_dt.strftime("%Y-%m-%d")
            end = end_dt.strftime("%Y-%m-%d")
            return _yf_fetch_bars(symbol, start, end)
        return []

    def get_benchmark_series(
        self,
        symbol: str = "SPY",
        lookback_days: int = 5,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        use_cache: bool = True,
    ) -> tuple[list[float], float, float, float]:
        """
        获取 benchmark 日收益率序列及衍生指标。仅使用 IB（不使用 yfinance fallback）。
        返回 (daily_returns, total_return, volatility_annualized, max_drawdown)。
        使用缓存避免重复请求。
        """
        cache_key = (symbol, lookback_days)
        now = time.monotonic()
        if use_cache and cache_key in _BENCHMARK_CACHE:
            ts, cached = _BENCHMARK_CACHE[cache_key]
            if now - ts <= _BENCHMARK_CACHE_TTL_SEC:
                return cached

        if not start_date or not end_date:
            end_dt = datetime.now(timezone.utc)
            start_dt = end_dt - timedelta(days=max(1, lookback_days))
            start_date = start_date or start_dt.strftime("%Y-%m-%d")
            end_date = end_date or end_dt.strftime("%Y-%m-%d")

        bars = _ib_fetch_bars(symbol, duration_days=max(1, lookback_days), end_date=end_date or "")
        if not bars or len(bars) < 2:
            result = ([], 0.0, 0.0, 0.0)
            if use_cache:
                _BENCHMARK_CACHE[cache_key] = (now, result)
            return result

        closes = [b["close"] for b in bars]
        returns = []
        for i in range(1, len(closes)):
            if closes[i - 1] and closes[i - 1] > 0:
                returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
        if not returns:
            result = ([], 0.0, 0.0, 0.0)
            if use_cache:
                _BENCHMARK_CACHE[cache_key] = (now, result)
            return result

        total_return = (closes[-1] - closes[0]) / closes[0] if closes[0] and closes[0] > 0 else 0.0
        n = len(returns)
        mean_r = sum(returns) / n
        var = sum((r - mean_r) ** 2 for r in returns) / (n - 1) if n >= 2 else 0.0
        vol = math.sqrt(var * 252) if var > 0 else 0.0
        peak = closes[0]
        max_dd = 0.0
        for c in closes:
            if c and peak and peak > 0:
                dd = (peak - c) / peak
                if dd > max_dd:
                    max_dd = dd
            if c and (not peak or c > peak):
                peak = c
        result = (returns, total_return, round(vol, 6), round(max_dd, 6))
        if use_cache:
            _BENCHMARK_CACHE[cache_key] = (now, result)
        return result


def get_market_data_service(*, for_research: bool = False) -> MarketDataService:
    """工厂：allocator/trigger/benchmark 用 for_research=False；research 用 for_research=True 以允许 yf 补充。"""
    return MarketDataService(allow_yf_fallback=for_research)
