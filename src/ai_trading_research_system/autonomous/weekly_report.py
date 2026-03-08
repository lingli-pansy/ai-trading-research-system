"""
WeeklyReportGenerator：生成用户可读的周报。
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from ai_trading_research_system.autonomous.benchmark import BenchmarkResult
from ai_trading_research_system.autonomous.schemas import WeeklyTradingMandate


@dataclass
class WeeklyReport:
    """周报结构。"""
    mandate_id: str
    period: str
    portfolio_return_pct: float
    benchmark_return_pct: float
    excess_return_pct: float
    max_drawdown_pct: float
    trade_count: int
    key_trades: list[str]  # 简要描述
    risk_events: list[str]
    no_trade_days: int
    no_trade_reasons: list[str]
    next_week_suggestion: str  # 规则化建议
    daily_research: list[dict[str, Any]]  # 每日/每轮 Research 产出
    benchmark_source: str = "mock"  # "yfinance" | "mock"


class WeeklyReportGenerator:
    """生成周报（用户可读 + 可序列化）。"""

    def generate(
        self,
        mandate: WeeklyTradingMandate,
        benchmark_result: BenchmarkResult,
        *,
        key_trades: list[str] | None = None,
        risk_events: list[str] | None = None,
        no_trade_days: int = 0,
        no_trade_reasons: list[str] | None = None,
        daily_research: list[dict[str, Any]] | None = None,
    ) -> WeeklyReport:
        key_trades = key_trades or []
        risk_events = risk_events or []
        no_trade_reasons = no_trade_reasons or []
        daily_research = daily_research or []
        # 规则化下周建议
        if benchmark_result.excess_return > 0.02:
            suggestion = "组合跑赢基准，可维持当前风险偏好。"
        elif benchmark_result.trade_count == 0:
            suggestion = "本周无成交，建议检查入场条件或放宽信号阈值。"
        else:
            suggestion = "建议下周继续观察，可微调仓位上限。"
        return WeeklyReport(
            mandate_id=mandate.mandate_id,
            period=benchmark_result.period,
            portfolio_return_pct=benchmark_result.portfolio_return * 100,
            benchmark_return_pct=benchmark_result.benchmark_return * 100,
            excess_return_pct=benchmark_result.excess_return * 100,
            max_drawdown_pct=benchmark_result.max_drawdown * 100,
            trade_count=benchmark_result.trade_count,
            key_trades=key_trades,
            risk_events=risk_events,
            no_trade_days=no_trade_days,
            no_trade_reasons=no_trade_reasons,
            next_week_suggestion=suggestion,
            daily_research=daily_research,
            benchmark_source=getattr(benchmark_result, "benchmark_source", "mock"),
        )

    def to_dict(self, report: WeeklyReport) -> dict[str, Any]:
        return asdict(report)
