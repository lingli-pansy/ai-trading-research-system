"""
Skill interface: execute research / backtest / paper / demo for OpenClaw Skill.
Skill can call execute() (Python API) or invoke cli.py via subprocess; this module provides the API path
so that output format matches openclaw_integration.md and is JSON-serializable for Agent.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from ai_trading_research_system.control.command_router import RoutedCommand
from ai_trading_research_system.pipeline.openclaw_adapter import (
    run_research_report,
    run_backtest_report,
    run_demo_report,
)


def execute(
    cmd: RoutedCommand,
    *,
    as_json: bool = True,
) -> dict[str, Any] | str:
    """
    Execute a routed command and return result.
    If as_json=True (default), returns a dict (for Skill/OpenClaw); otherwise returns stdout string from CLI.
    Uses Python API (openclaw_adapter) so output format matches run_for_openclaw.py / openclaw_integration.md.
    """
    subcommand = cmd.subcommand
    kwargs = cmd.to_kwargs()
    symbol = kwargs["symbol"]
    use_mock = kwargs.get("use_mock", False)
    use_llm = kwargs.get("use_llm", False)

    if as_json:
        if subcommand == "research":
            return run_research_report(symbol, use_mock=use_mock, use_llm=use_llm)
        if subcommand == "backtest":
            return run_backtest_report(
                symbol,
                start_date=kwargs.get("start_date"),
                end_date=kwargs.get("end_date"),
                use_mock=use_mock,
                use_llm=use_llm,
            )
        if subcommand == "demo":
            return run_demo_report(symbol, use_mock=use_mock, use_llm=use_llm)
        if subcommand == "paper":
            # Paper does not have a report in openclaw_adapter; return minimal status
            from ai_trading_research_system.pipeline.paper_pipe import run
            res = run(symbol, use_mock=use_mock, use_llm=use_llm)
            return {
                "task": "paper",
                "symbol": symbol,
                "contract_action": res.contract.suggested_action,
                "contract_confidence": res.contract.confidence,
                "signal_action": res.signal.action,
                "allowed_position_size": res.signal.allowed_position_size,
            }
        return {"error": f"unknown subcommand: {subcommand}"}

    # Invoke CLI via subprocess and return stdout (project root = .../src/.../control -> parents[3])
    root = Path(__file__).resolve().parents[3]
    cli = root / "cli.py"
    if not cli.exists():
        cli = root / "scripts" / "cli.py"
    argv = [sys.executable, str(cli), subcommand, symbol]
    if use_mock:
        argv.append("--mock")
    if use_llm:
        argv.append("--llm")
    if subcommand == "backtest":
        if kwargs.get("start_date"):
            argv.extend(["--start", kwargs["start_date"]])
        if kwargs.get("end_date"):
            argv.extend(["--end", kwargs["end_date"]])
    if subcommand == "paper" and kwargs.get("once"):
        argv.append("--once")
    result = subprocess.run(argv, capture_output=True, text=True, cwd=str(root))
    if result.returncode != 0:
        return result.stderr or f"exit code {result.returncode}"
    return result.stdout
