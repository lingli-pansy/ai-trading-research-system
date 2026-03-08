# Commands: single-responsibility entry points; each calls existing pipeline only.
# 主入口：OpenClaw agent 调用 run_autonomous_paper_cycle 触发单周期 paper。
from ai_trading_research_system.application.commands.research_symbol import run_research_symbol
from ai_trading_research_system.application.commands.backtest_symbol import run_backtest_symbol
from ai_trading_research_system.application.commands.run_demo import run_demo
from ai_trading_research_system.application.commands.run_paper import run_paper
from ai_trading_research_system.application.commands.run_autonomous_paper_cycle import run_autonomous_paper_cycle
from ai_trading_research_system.application.commands.run_weekly_autonomous_paper import run_weekly_autonomous_paper
from ai_trading_research_system.application.commands.run_weekly_report import run_weekly_report
from ai_trading_research_system.application.commands.generate_weekly_report import generate_weekly_report

__all__ = [
    "run_research_symbol",
    "run_backtest_symbol",
    "run_demo",
    "run_paper",
    "run_autonomous_paper_cycle",
    "run_weekly_autonomous_paper",
    "run_weekly_report",
    "generate_weekly_report",
]
