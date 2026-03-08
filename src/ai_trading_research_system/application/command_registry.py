"""
Single command routing: canonical names + aliases. All routing resolves alias → canonical first.
registry = skill surface, contract = schema, command_registry = handler mapping only.
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
    run_weekly_report,
)

# Canonical command names (align with openclaw.contract)
CANONICAL_COMMANDS = [
    "research_symbol",
    "backtest_symbol",
    "run_demo",
    "weekly_autonomous_paper",
    "weekly_report",
]

# Alias → canonical (CLI / OpenClaw may use alias; routing resolves first)
ALIASES: dict[str, str] = {
    "research": "research_symbol",
    "backtest": "backtest_symbol",
    "demo": "run_demo",
    "weekly-paper": "weekly_autonomous_paper",
}

# canonical → (handler, needs_report_dir?)
_HANDLERS: dict[str, tuple[Callable[..., Any], bool]] = {
    "research_symbol": (run_research_symbol, False),
    "backtest_symbol": (run_backtest_symbol, False),
    "run_demo": (run_demo, False),
    "paper": (run_paper, False),
    "weekly_autonomous_paper": (run_weekly_autonomous_paper, True),
    "weekly_report": (run_weekly_report, True),
}


def resolve(command: str) -> str:
    """Resolve alias to canonical command name."""
    return ALIASES.get(command, command)


def run(command: str, **kwargs: Any) -> Any:
    """
    Dispatch by command name. Resolves alias → canonical, then calls application.commands.
    Returns raw result. report_dir / project_root come from kwargs (built by kwargs_from_*).
    """
    canonical = resolve(command)
    if canonical not in _HANDLERS:
        raise ValueError(f"unknown command: {command!r} (resolved: {canonical!r})")
    handler, needs_report_dir = _HANDLERS[canonical]
    if needs_report_dir and "report_dir" not in kwargs:
        kwargs["report_dir"] = Path.cwd() / "reports"
    return handler(**kwargs)


def command_names() -> list[str]:
    """All registered names (canonical + aliases) for routing."""
    return list(CANONICAL_COMMANDS) + list(ALIASES.keys())


def cli_command_names() -> list[str]:
    """CLI subcommand names: aliases (research, backtest, demo) + paper + weekly-paper + weekly_report."""
    return ["research", "backtest", "paper", "demo", "weekly-paper", "weekly_report"]


def kwargs_from_cli_args(command: str, args: Any) -> dict[str, Any]:
    """
    Build kwargs for run(resolve(command), **kwargs). CLI passes alias; we resolve and build.
    report_dir / project_root are set here so CLI does not construct business params.
    """
    canonical = resolve(command)
    base = {"use_mock": getattr(args, "mock", False), "use_llm": getattr(args, "llm", False)}
    if canonical == "research_symbol":
        return {**base, "symbol": getattr(args, "symbol", "NVDA")}
    if canonical == "backtest_symbol":
        return {
            **base,
            "symbol": getattr(args, "symbol", "NVDA"),
            "start_date": getattr(args, "start", None),
            "end_date": getattr(args, "end", None),
        }
    if canonical == "paper":
        return {
            **base,
            "symbol": getattr(args, "symbol", "NVDA"),
            "once": getattr(args, "once", False),
            "project_root": Path.cwd(),
        }
    if canonical == "run_demo":
        return {**base, "symbol": getattr(args, "symbol", "NVDA")}
    if canonical == "weekly_autonomous_paper":
        return {
            **base,
            "capital": getattr(args, "capital", 10000),
            "benchmark": getattr(args, "benchmark", "SPY"),
            "duration_days": getattr(args, "days", 5),
            "auto_confirm": getattr(args, "auto_confirm", True),
            "report_dir": Path.cwd() / "reports",
        }
    if canonical == "weekly_report":
        return {"report_dir": Path.cwd() / "reports"}
    return base
