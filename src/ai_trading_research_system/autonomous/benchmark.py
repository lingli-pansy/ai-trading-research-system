"""
BenchmarkComparator：自动对比组合收益与 benchmark（默认 SPY）。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BenchmarkResult:
    """对比结果。"""
    portfolio_return: float  # 组合区间收益率
    benchmark_return: float  # 基准区间收益率
    excess_return: float     # 超额
    max_drawdown: float
    trade_count: int
    period: str  # e.g. "2024-01-01 to 2024-01-05"


class BenchmarkComparator:
    """
    组合 vs benchmark（默认 SPY）。
    Paper 模式下可用 Nautilus 回测结果或 mock 数据。
    """

    def compare(
        self,
        portfolio_return: float,
        benchmark_return: float,
        max_drawdown: float = 0.0,
        trade_count: int = 0,
        period: str = "",
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
        )
