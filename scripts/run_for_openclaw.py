#!/usr/bin/env python3
"""
OpenClaw-callable entry: run research or research+backtest and print a JSON report to stdout.
Usage:
  python scripts/run_for_openclaw.py research SYMBOL [--mock] [--llm]
  python scripts/run_for_openclaw.py backtest SYMBOL [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--mock] [--llm]
Output: single JSON object (report) to stdout; errors to stderr and non-zero exit.
"""
from __future__ import annotations

import argparse
import json
import sys

from ai_trading_research_system.pipeline.openclaw_adapter import (
    run_research_report,
    run_backtest_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenClaw: run research or backtest, output JSON report")
    parser.add_argument("task", choices=["research", "backtest"], help="Task: research or backtest")
    parser.add_argument("symbol", nargs="?", default="NVDA", help="Symbol (default: NVDA)")
    parser.add_argument("--start", default=None, help="Backtest start YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="Backtest end YYYY-MM-DD")
    parser.add_argument("--mock", action="store_true", help="Use mock research data")
    parser.add_argument("--llm", action="store_true", help="Use LLM agent (requires OPENAI_API_KEY)")
    args = parser.parse_args()

    try:
        if args.task == "research":
            report = run_research_report(args.symbol, use_mock=args.mock, use_llm=args.llm)
        else:
            report = run_backtest_report(
                args.symbol,
                start_date=args.start,
                end_date=args.end,
                use_mock=args.mock,
                use_llm=args.llm,
            )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
