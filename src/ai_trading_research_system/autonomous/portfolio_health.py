"""
Portfolio Health Monitoring: 组合健康快照与评估。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class PortfolioHealthSnapshot:
    portfolio_return: float
    benchmark_return: float
    excess_return: float
    volatility: float
    beta_vs_spy: float
    concentration_index: float
    max_drawdown: float
    current_positions: list[dict[str, Any]] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_return": self.portfolio_return,
            "benchmark_return": self.benchmark_return,
            "excess_return": self.excess_return,
            "volatility": self.volatility,
            "beta_vs_spy": self.beta_vs_spy,
            "concentration_index": self.concentration_index,
            "max_drawdown": self.max_drawdown,
            "current_positions": self.current_positions,
            "timestamp": self.timestamp,
        }


def _concentration_index(positions: list[dict[str, Any]], total_equity: float) -> float:
    """Herfindahl: sum of (weight_i)^2. 单标的 100% 为 1，均匀 N 标为 1/N。"""
    if not total_equity or total_equity <= 0:
        return 0.0
    total = 0.0
    for p in positions:
        mv = float(p.get("market_value", 0) or 0)
        total += (mv / total_equity) ** 2
    return round(total, 6)


def _beta_from_returns(portfolio_returns: list[float], spy_returns: list[float]) -> float:
    """Beta = cov(portfolio, spy) / var(spy)."""
    if not spy_returns or len(portfolio_returns) != len(spy_returns) or len(spy_returns) < 2:
        return 0.0
    n = len(spy_returns)
    mean_p = sum(portfolio_returns) / n
    mean_s = sum(spy_returns) / n
    cov = sum((portfolio_returns[i] - mean_p) * (spy_returns[i] - mean_s) for i in range(n)) / (n - 1)
    var_s = sum((spy_returns[i] - mean_s) ** 2 for i in range(n)) / (n - 1)
    if var_s <= 0:
        return 0.0
    return round(cov / var_s, 4)


def _volatility_from_returns(returns: list[float]) -> float:
    """Annualized volatility (sqrt(252) * std)."""
    if not returns or len(returns) < 2:
        return 0.0
    n = len(returns)
    mean = sum(returns) / n
    var = sum((r - mean) ** 2 for r in returns) / (n - 1)
    import math
    return round(math.sqrt(var * 252) if var > 0 else 0.0, 6)


def evaluate_portfolio_health(
    account_snapshot: Any,
    benchmark_data: dict[str, Any],
    positions: list[dict[str, Any]] | None = None,
    *,
    initial_equity: float | None = None,
) -> PortfolioHealthSnapshot:
    """
    评估组合健康，输出 PortfolioHealthSnapshot。
    benchmark_data: benchmark_return (float), optional: volatility, max_drawdown, portfolio_returns, spy_returns.
    positions: 若为 None 则用 account_snapshot.positions。
    """
    positions = positions if positions is not None else (getattr(account_snapshot, "positions", None) or [])
    if hasattr(account_snapshot, "total_equity") and callable(account_snapshot.total_equity):
        equity = float(account_snapshot.total_equity() or 0)
    else:
        equity = float(getattr(account_snapshot, "equity", 0) or 0)
    init = float(initial_equity or equity or 1)
    benchmark_return = float(benchmark_data.get("benchmark_return", 0) or 0)
    portfolio_return = (equity - init) / init if init > 0 else 0.0
    excess_return = portfolio_return - benchmark_return

    volatility = float(benchmark_data.get("volatility", 0) or 0)
    if benchmark_data.get("portfolio_returns"):
        volatility = _volatility_from_returns(benchmark_data["portfolio_returns"])

    beta = 0.0
    if benchmark_data.get("portfolio_returns") and benchmark_data.get("spy_returns"):
        beta = _beta_from_returns(benchmark_data["portfolio_returns"], benchmark_data["spy_returns"])
    elif benchmark_data.get("beta_vs_spy") is not None:
        beta = float(benchmark_data["beta_vs_spy"])

    concentration = _concentration_index(positions, equity if equity > 0 else 1.0)
    max_drawdown = float(benchmark_data.get("max_drawdown", 0) or 0)
    timestamp = getattr(account_snapshot, "timestamp", None) or datetime.now(timezone.utc).isoformat()

    return PortfolioHealthSnapshot(
        portfolio_return=portfolio_return,
        benchmark_return=benchmark_return,
        excess_return=excess_return,
        volatility=volatility,
        beta_vs_spy=beta,
        concentration_index=concentration,
        max_drawdown=max_drawdown,
        current_positions=list(positions),
        timestamp=timestamp,
    )
