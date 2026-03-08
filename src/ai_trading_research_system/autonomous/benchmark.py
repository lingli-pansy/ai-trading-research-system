"""
BenchmarkComparator：自动对比组合收益与 benchmark（默认 SPY）。
主路径使用 MarketDataService（IB Gateway）；取数失败时 return=0、source=mock。
"""
from __future__ import annotations

from dataclasses import dataclass

from ai_trading_research_system.data.market_data_service import get_market_data_service


def get_benchmark_return_for_period(
    symbol: str = "SPY",
    start_date: str | None = None,
    end_date: str | None = None,
    lookback_days: int = 5,
) -> tuple[float, str]:
    """
    用 MarketDataService（IB Gateway）计算 benchmark 在给定区间的收益率。
    返回 (return_pct_as_decimal, source)，source 为 "ib" 或 "mock"（取数失败时 return=0）。
    """
    mds = get_market_data_service(for_research=False)
    returns, total_return, _, _ = mds.get_benchmark_series(
        symbol=symbol,
        lookback_days=lookback_days,
        start_date=start_date,
        end_date=end_date,
        use_cache=True,
    )
    source = "ib" if returns else "mock"
    return total_return, source


def get_benchmark_series(
    symbol: str = "SPY",
    start_date: str | None = None,
    end_date: str | None = None,
    lookback_days: int = 5,
) -> tuple[list[float], float, float, float]:
    """
    获取 benchmark 日收益率序列及衍生指标。数据来自 MarketDataService（IB），带缓存。
    返回 (daily_returns, total_return, volatility_annualized, max_drawdown)。
    取数失败时返回 ([], 0.0, 0.0, 0.0)。
    """
    mds = get_market_data_service(for_research=False)
    return mds.get_benchmark_series(
        symbol=symbol,
        lookback_days=lookback_days,
        start_date=start_date,
        end_date=end_date,
        use_cache=True,
    )


@dataclass
class BenchmarkResult:
    """对比结果。"""
    portfolio_return: float  # 组合区间收益率
    benchmark_return: float  # 基准区间收益率
    excess_return: float     # 超额
    max_drawdown: float
    trade_count: int
    period: str  # e.g. "2024-01-01 to 2024-01-05"
    benchmark_source: str = "mock"  # "ib" | "yfinance" | "mock"


class BenchmarkComparator:
    """
    组合 vs benchmark（默认 SPY）。主路径使用 MarketDataService（IB）拉真实收益。
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
