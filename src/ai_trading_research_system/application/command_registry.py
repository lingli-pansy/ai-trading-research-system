"""
Single command routing: map command name -> application.commands function.
CLI and OpenClaw must use this only; no if command == ... elsewhere.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from ai_trading_research_system.application.commands import (
    run_research_symbol,
    run_backtest_symbol,
    run_demo,
    run_paper,
    run_weekly_autonomous_paper,
)

# CLI subcommand names and OpenClaw task names -> (handler, takes_report_dir?)
_HANDLERS: dict[str, tuple[Callable[..., Any], bool]] = {
    "research": (run_research_symbol, False),
    "backtest": (run_backtest_symbol, False),
    "demo": (run_demo, False),
    "paper": (run_paper, False),
    "weekly-paper": (run_weekly_autonomous_paper, True),
    "weekly_autonomous_paper": (run_weekly_autonomous_paper, True),
    "weekly_report": (run_weekly_autonomous_paper, True),
}


def run(command: str, report_dir: Path | None = None, project_root: Path | None = None, **kwargs: Any) -> Any:
    """
    Dispatch by command name to application.commands. Returns raw result (contract, BacktestPipeResult, etc).
    """
    if command not in _HANDLERS:
        raise ValueError(f"unknown command: {command}")
    handler, needs_report_dir = _HANDLERS[command]
    if needs_report_dir and report_dir is not None:
        kwargs["report_dir"] = report_dir
    if command == "paper" and project_root is not None:
        kwargs["project_root"] = project_root
    return handler(**kwargs)


def command_names() -> list[str]:
    """Return all registered command names (CLI + OpenClaw names)."""
    return list(_HANDLERS.keys())


def cli_command_names() -> list[str]:
    """Return CLI subcommand names only (research, backtest, paper, demo, weekly-paper)."""
    return ["research", "backtest", "paper", "demo", "weekly-paper"]


def kwargs_from_cli_args(command: str, args: Any) -> dict[str, Any]:
    """Build kwargs for run(command, **kwargs) from argparse.Namespace (CLI)."""
    base = {"use_mock": getattr(args, "mock", False), "use_llm": getattr(args, "llm", False)}
    if command == "research":
        return {**base, "symbol": getattr(args, "symbol", "NVDA")}
    if command == "backtest":
        return {
            **base,
            "symbol": getattr(args, "symbol", "NVDA"),
            "start_date": getattr(args, "start", None),
            "end_date": getattr(args, "end", None),
        }
    if command == "paper":
        return {
            **base,
            "symbol": getattr(args, "symbol", "NVDA"),
            "once": getattr(args, "once", False),
        }
    if command == "demo":
        return {**base, "symbol": getattr(args, "symbol", "NVDA")}
    if command == "weekly-paper":
        return {
            **base,
            "capital": getattr(args, "capital", 10000),
            "benchmark": getattr(args, "benchmark", "SPY"),
            "duration_days": getattr(args, "days", 5),
            "auto_confirm": getattr(args, "auto_confirm", True),
        }
    return base
