"""
WeeklyTradingMandate：从自然语言或 CLI 参数构造结构化 mandate。
"""
from __future__ import annotations

import uuid
from ai_trading_research_system.autonomous.schemas import WeeklyTradingMandate


def mandate_from_cli(
    *,
    capital: float = 10_000.0,
    benchmark: str = "SPY",
    duration_days: int = 5,
    auto_confirm: bool = True,
    max_positions: int = 5,
    cash_reserve_pct: float = 0.1,
    watchlist: list[str] | None = None,
) -> WeeklyTradingMandate:
    """从 CLI 参数直接构造 mandate。watchlist 为空时使用默认单 symbol。"""
    return WeeklyTradingMandate(
        mandate_id=f"mandate_{uuid.uuid4().hex[:12]}",
        mode="paper",
        capital_limit=capital,
        benchmark=benchmark,
        duration_trading_days=duration_days,
        auto_confirm=auto_confirm,
        rebalance_policy="allow_rebalance",
        risk_profile="moderate",
        max_positions=max_positions,
        cash_reserve_pct=cash_reserve_pct,
        stop_conditions=["kill_switch"],
        watchlist=watchlist if watchlist else ["NVDA"],
    )


def mandate_from_nl(
    natural_language_goal: str,
    *,
    default_capital: float = 10_000.0,
    default_benchmark: str = "SPY",
) -> WeeklyTradingMandate:
    """
    把用户一句话目标转成结构化 mandate。
    当前为规则解析占位；后续可接 LLM。允许从自然语言入口生成。
    """
    # 占位：简单关键词映射
    capital = default_capital
    if "10k" in natural_language_goal.lower() or "10000" in natural_language_goal:
        capital = 10_000.0
    if "spy" in natural_language_goal.lower():
        benchmark = "SPY"
    else:
        benchmark = default_benchmark
    return mandate_from_cli(
        capital=capital,
        benchmark=benchmark,
        duration_days=5,
        auto_confirm=True,
        max_positions=5,
        cash_reserve_pct=0.1,
    )
