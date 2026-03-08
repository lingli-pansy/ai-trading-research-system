"""
Deprecated: prefer openclaw.adapter. Re-export for backward compatibility.
"""
from __future__ import annotations

from ai_trading_research_system.openclaw.adapter import (
    run_research_report,
    run_backtest_report,
    run_demo_report,
    run_weekly_paper_report,
)

__all__ = [
    "run_research_report",
    "run_backtest_report",
    "run_demo_report",
    "run_weekly_paper_report",
]
