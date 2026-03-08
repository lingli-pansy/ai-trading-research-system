"""
Command routing only: read metadata from openclaw.registry, resolve alias -> canonical, bind handler.
No duplicate command list or alias map; single source of truth is registry.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from ai_trading_research_system.openclaw.registry import (
    resolve,
    get_metadata,
    get_canonical_commands,
    get_aliases,
    get_cli_subcommand_names,
    kwargs_for_task as registry_kwargs_for_task,
)

from ai_trading_research_system.application.commands import (
    run_research_symbol,
    run_backtest_symbol,
    run_demo,
    run_paper,
    run_autonomous_paper_cycle,
    run_weekly_autonomous_paper,
    run_weekly_report,
)

# Handler target name -> callable (only binding; command list lives in registry)
# autonomous_paper_cycle = OpenClaw agent 主入口
_HANDLERS: dict[str, Callable[..., Any]] = {
    "run_research_symbol": run_research_symbol,
    "run_backtest_symbol": run_backtest_symbol,
    "run_demo": run_demo,
    "run_paper": run_paper,
    "run_autonomous_paper_cycle": run_autonomous_paper_cycle,
    "run_weekly_autonomous_paper": run_weekly_autonomous_paper,
    "run_weekly_report": run_weekly_report,
}


def run(command: str, **kwargs: Any) -> Any:
    """
    Resolve alias -> canonical via registry (only place), then dispatch to application.commands.
    report_dir injected here when metadata.needs_report_dir and not in kwargs.
    """
    canonical = resolve(command)
    meta = get_metadata(canonical)
    if not meta:
        raise ValueError(f"unknown command: {command!r} (resolved: {canonical!r})")
    handler = _HANDLERS.get(meta["handler_target"])
    if not handler:
        raise ValueError(f"no handler for canonical: {canonical!r} (target: {meta['handler_target']!r})")
    if meta.get("needs_report_dir") and "report_dir" not in kwargs:
        kwargs["report_dir"] = Path.cwd() / "reports"
    return handler(**kwargs)


def command_names() -> list[str]:
    """All names that can be passed to run() (canonical + aliases)."""
    canonicals = get_canonical_commands()
    aliases = list(get_aliases().keys())
    return canonicals + aliases


def cli_command_names() -> list[str]:
    """CLI subcommand names (from registry)."""
    return get_cli_subcommand_names()


def kwargs_from_cli_args(command: str, args: Any) -> dict[str, Any]:
    """Build kwargs from args; resolution and per-command logic in registry only."""
    canonical = resolve(command)
    return registry_kwargs_for_task(canonical, args)


# Re-export so callers that only need resolve don't need to import registry
__all__ = ["run", "resolve", "command_names", "cli_command_names", "kwargs_from_cli_args"]
