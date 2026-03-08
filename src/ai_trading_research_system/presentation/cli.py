"""
Unified CLI: parse args -> command_registry.run -> renderer. No business logic, no pipeline calls.
report_dir / project_root come from command_registry.kwargs_from_cli_args only.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore[misc, assignment]

from ai_trading_research_system.application.command_registry import (
    run as command_run,
    kwargs_from_cli_args,
)
from ai_trading_research_system.presentation.renderers import render

if load_dotenv:
    load_dotenv(Path.cwd() / ".env")


def _json_serial(obj: object) -> str | float | int | None:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AI Trading Research System — unified CLI (research / backtest / paper / demo / weekly-paper / weekly_report)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def _add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--mock", action="store_true", help="Use mock research data")
        p.add_argument("--llm", action="store_true", help="Use LLM agent (requires OPENAI_API_KEY or KIMI_CODE_API_KEY)")

    p_research = subparsers.add_parser("research", help="Run research and output DecisionContract (JSON)")
    p_research.add_argument("symbol", nargs="?", default="NVDA", help="Symbol (default: NVDA)")
    _add_common(p_research)

    p_backtest = subparsers.add_parser("backtest", help="Research → Backtest → Store, print metrics")
    p_backtest.add_argument("symbol", nargs="?", default="NVDA", help="Symbol (default: NVDA)")
    p_backtest.add_argument("--start", default=None, help="Backtest start YYYY-MM-DD")
    p_backtest.add_argument("--end", default=None, help="Backtest end YYYY-MM-DD")
    _add_common(p_backtest)

    p_paper = subparsers.add_parser("paper", help="Research → Contract → Paper inject (once or runner)")
    p_paper.add_argument("--symbol", default="NVDA", help="Symbol (default: NVDA)")
    p_paper.add_argument("--once", action="store_true", help="Run one Research+inject cycle then exit")
    _add_common(p_paper)

    p_demo = subparsers.add_parser("demo", help="E2E demo: research → strategy → backtest → summary (four blocks)")
    p_demo.add_argument("symbol", nargs="?", default="NVDA", help="Symbol (default: NVDA)")
    _add_common(p_demo)

    p_weekly = subparsers.add_parser("weekly-paper", help="UC-09: Weekly autonomous paper portfolio")
    p_weekly.add_argument("--capital", type=float, default=10000, help="Capital limit (default 10000)")
    p_weekly.add_argument("--benchmark", default="SPY", help="Benchmark symbol (default SPY)")
    p_weekly.add_argument("--days", type=int, default=5, help="Trading days (default 5)")
    p_weekly.add_argument("--auto-confirm", action="store_true", default=True, dest="auto_confirm", help="Auto confirm trades (default True)")
    p_weekly.add_argument("--no-auto-confirm", action="store_false", dest="auto_confirm", help="Disable auto confirm")
    _add_common(p_weekly)

    p_weekly_report = subparsers.add_parser("weekly_report", help="Read latest weekly report or show summary (no execution)")
    _add_common(p_weekly_report)

    args = parser.parse_args()

    kwargs = kwargs_from_cli_args(args.command, args)
    result = command_run(args.command, **kwargs)

    output = render(args.command, result, args)
    if isinstance(output, dict):
        print(json.dumps(output, indent=2, default=_json_serial))
    else:
        for line in output:
            print(line)

    if getattr(result, "paused", False):
        return 1
    if getattr(result, "ok", True) is False:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
