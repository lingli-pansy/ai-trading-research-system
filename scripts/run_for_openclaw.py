#!/usr/bin/env python3
"""
OpenClaw-callable entry: run research / backtest / demo / weekly_autonomous_paper / weekly_report; print single JSON to stdout.
Usage:
  python scripts/run_for_openclaw.py research SYMBOL [--mock] [--llm]
  python scripts/run_for_openclaw.py backtest SYMBOL [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--mock] [--llm]
  python scripts/run_for_openclaw.py demo SYMBOL [--mock] [--llm]
  python scripts/run_for_openclaw.py weekly_autonomous_paper [--capital 10000] [--benchmark SPY] [--days 5] [--mock] [--llm]
  python scripts/run_for_openclaw.py weekly_report [--capital 10000] [--benchmark SPY] [--days 5] [--mock] [--llm]

Output: single JSON object to stdout. Unified format for weekly commands:
  { "ok": true, "command": "...", "mandate_id": "...", "status": "...", "report_path": "...", "engine_type": "...", "used_nautilus": true, "snapshot_source": "...", "benchmark_source": "..." }
Errors: stderr JSON line + non-zero exit.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ai_trading_research_system.openclaw.adapter import (
    run_research_report,
    run_backtest_report,
    run_demo_report,
    run_weekly_paper_report,
)
from ai_trading_research_system.openclaw.contract import error_to_dict


def main() -> int:
    parser = argparse.ArgumentParser(
        description="OpenClaw: run research/backtest/demo/weekly_autonomous_paper/weekly_report, output JSON to stdout"
    )
    parser.add_argument(
        "task",
        choices=["research", "backtest", "demo", "weekly_autonomous_paper", "weekly_report"],
        help="Task to run",
    )
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
        if args.task == "research":
            report = run_research_report(args.symbol, use_mock=args.mock, use_llm=args.llm)
            out = {**report, "ok": True, "command": "research"}
        elif args.task == "backtest":
            report = run_backtest_report(
                args.symbol,
                start_date=args.start,
                end_date=args.end,
                use_mock=args.mock,
                use_llm=args.llm,
            )
            out = {**report, "ok": True, "command": "backtest"}
        elif args.task == "demo":
            report = run_demo_report(args.symbol, use_mock=args.mock, use_llm=args.llm)
            out = {**report, "ok": True, "command": "demo"}
        elif args.task == "weekly_autonomous_paper":
            out = run_weekly_paper_report(
                capital=args.capital,
                benchmark=args.benchmark,
                duration_days=args.days,
                auto_confirm=True,
                use_mock=args.mock,
                use_llm=args.llm,
            )
        elif args.task == "weekly_report":
            out = run_weekly_paper_report(
                capital=args.capital,
                benchmark=args.benchmark,
                duration_days=args.days,
                auto_confirm=True,
                use_mock=args.mock,
                use_llm=args.llm,
            )
            out = {**out, "command": "weekly_report"}
        else:
            err = error_to_dict(args.task, 1, f"unknown task: {args.task}")
            print(json.dumps(err, ensure_ascii=False), file=sys.stderr)
            return 1
        # stdout: result JSON only
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        # stderr: error JSON only
        err = error_to_dict(args.task, 1, str(e))
        print(json.dumps(err, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
