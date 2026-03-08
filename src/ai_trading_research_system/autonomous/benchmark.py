"""
BenchmarkComparator：自动对比组合收益与 benchmark（默认 SPY）。主路径使用真实行情计算 benchmark 收益。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


def get_benchmark_return_for_period(
    symbol: str = "SPY",
    start_date: str | None = None,
    end_date: str | None = None,
    lookback_days: int = 5,
) -> tuple[float, str]:
    """
    用 yfinance 计算 benchmark 在给定区间的收益率。
    返回 (return_pct_as_decimal, source)，source 为 "yfinance" 或 "mock"（取数失败时 return=0）。
    """
    try:
        import yfinance as yf
    except Exception:
        return 0.0, "mock"

    end = end_date
    start = start_date
    if not end or not start:
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=max(1, lookback_days))
        if not end:
            end = end_dt.strftime("%Y-%m-%d")
        if not start:
            start = start_dt.strftime("%Y-%m-%d")

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start, end=end, auto_adjust=True)
        if hist is None or len(hist) < 2:
            return 0.0, "mock"
        p0 = float(hist["Close"].iloc[0])
        p1 = float(hist["Close"].iloc[-1])
        if p0 <= 0:
            return 0.0, "mock"
        return (p1 - p0) / p0, "yfinance"
    except Exception:
        return 0.0, "mock"


@dataclass
class BenchmarkResult:
    """对比结果。"""
    portfolio_return: float  # 组合区间收益率
    benchmark_return: float  # 基准区间收益率
    excess_return: float     # 超额
    max_drawdown: float
    trade_count: int
    period: str  # e.g. "2024-01-01 to 2024-01-05"
    benchmark_source: str = "mock"  # "yfinance" | "mock"


class BenchmarkComparator:
    """
    组合 vs benchmark（默认 SPY）。主路径使用 get_benchmark_return_for_period 拉真实收益。
    """

    def compare(
        self,
        portfolio_return: float,
        benchmark_return: float,
        max_drawdown: float = 0.0,
        trade_count: int = 0,
        period: str = "",
        benchmark_source: str = "mock",
    ) -> BenchmarkResult:
        """输入组合与基准收益率等，输出对比结果。"""
        excess = portfolio_return - benchmark_return
        return BenchmarkResult(
            portfolio_return=portfolio_return,
            benchmark_return=benchmark_return,
            excess_return=excess,
            max_drawdown=max_drawdown,
            trade_count=trade_count,
            period=period or "week",
            benchmark_source=benchmark_source,
        )
