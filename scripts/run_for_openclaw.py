#!/usr/bin/env python3
"""
OpenClaw-callable entry: run skills from registry; print single JSON to stdout.
Task list from openclaw.registry; no hardcoded skill names.
"""
from __future__ import annotations

import argparse
import json
import sys

from ai_trading_research_system.application.command_registry import run as command_run
from ai_trading_research_system.openclaw.adapter import format_result
from ai_trading_research_system.openclaw.contract import error_to_dict
from ai_trading_research_system.openclaw.registry import get_skill_names, kwargs_for_task


def main() -> int:
    skill_names = get_skill_names()
    parser = argparse.ArgumentParser(
        description="OpenClaw: run research/backtest/demo/weekly_autonomous_paper/weekly_report, output JSON to stdout"
    )
    parser.add_argument("task", choices=skill_names, help="Task to run")
    parser.add_argument("symbol", nargs="?", default="NVDA", help="Symbol (default: NVDA; not used for weekly_*)")
    parser.add_argument("--start", default=None, help="Backtest start YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="Backtest end YYYY-MM-DD")
    parser.add_argument("--capital", type=float, default=10000, help="Weekly: capital limit (default 10000)")
    parser.add_argument("--benchmark", default="SPY", help="Weekly: benchmark symbol (default SPY)")
    parser.add_argument("--days", type=int, default=5, help="Weekly: trading days (default 5)")
    parser.add_argument("--mock", action="store_true", help="Use mock research data")
    parser.add_argument("--llm", action="store_true", help="Use LLM agent (requires OPENAI_API_KEY)")
    args = parser.parse_args()

    try:
        kwargs = kwargs_for_task(args.task, args)
        result = command_run(args.task, **kwargs)
        out = format_result(args.task, result, **kwargs)
        if args.task in ("research_symbol", "backtest_symbol", "run_demo"):
            out["ok"] = True
            out["command"] = args.task
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        err = error_to_dict(args.task, 1, str(e))
        print(json.dumps(err, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
