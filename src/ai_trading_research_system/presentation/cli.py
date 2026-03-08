"""
Unified CLI: parse args -> command_registry.run -> renderer. No business logic, no pipeline calls.
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


def _project_root() -> Path:
    p = Path(__file__).resolve()
    for _ in range(4):
        p = p.parent
    return p


PROJECT_ROOT = _project_root()
if load_dotenv:
    load_dotenv(PROJECT_ROOT / ".env")


def _json_serial(obj: object) -> str | float | int | None:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AI Trading Research System — unified CLI (research / backtest / paper / demo / weekly-paper)"
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

    args = parser.parse_args()

    kwargs = kwargs_from_cli_args(args.command, args)
    report_dir = PROJECT_ROOT / "reports" if args.command == "weekly-paper" else None
    if report_dir is not None:
        report_dir.mkdir(parents=True, exist_ok=True)
    project_root = PROJECT_ROOT if args.command == "paper" else None
    result = command_run(args.command, report_dir=report_dir, project_root=project_root, **kwargs)

    output = render(args.command, result, args)
    if isinstance(output, dict):
        print(json.dumps(output, indent=2, default=_json_serial))
    else:
        for line in output:
            print(line)

    if args.command == "paper" and getattr(result, "paused", False):
        return 1
    if args.command == "weekly-paper" and not getattr(result, "ok", True):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
