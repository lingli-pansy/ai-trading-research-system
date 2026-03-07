#!/usr/bin/env python3
"""
OpenClaw-callable entry: run research / backtest / demo and print a single JSON report to stdout.
Usage:
  python scripts/run_for_openclaw.py research SYMBOL [--mock] [--llm]
  python scripts/run_for_openclaw.py backtest SYMBOL [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--mock] [--llm]
  python scripts/run_for_openclaw.py demo SYMBOL [--mock] [--llm]
Output: single JSON object to stdout only; errors to stderr as JSON line + non-zero exit.
Error format (stderr): {"ok": false, "command": "research", "error_code": 1, "error_message": "..."}
"""
from __future__ import annotations

import argparse
import json
import sys

from ai_trading_research_system.pipeline.openclaw_adapter import (
    run_research_report,
    run_backtest_report,
    run_demo_report,
)


def _err_json(command: str, error_code: int, error_message: str) -> str:
    return json.dumps({
        "ok": False,
        "command": command,
        "error_code": error_code,
        "error_message": error_message,
    }, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenClaw: run research/backtest/demo, output JSON to stdout")
    parser.add_argument("task", choices=["research", "backtest", "demo"], help="Task: research, backtest, or demo")
    parser.add_argument("symbol", nargs="?", default="NVDA", help="Symbol (default: NVDA)")
    parser.add_argument("--start", default=None, help="Backtest start YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="Backtest end YYYY-MM-DD")
    parser.add_argument("--mock", action="store_true", help="Use mock research data")
    parser.add_argument("--llm", action="store_true", help="Use LLM agent (requires OPENAI_API_KEY)")
    args = parser.parse_args()

    try:
        if args.task == "research":
            report = run_research_report(args.symbol, use_mock=args.mock, use_llm=args.llm)
        elif args.task == "backtest":
            report = run_backtest_report(
                args.symbol,
                start_date=args.start,
                end_date=args.end,
                use_mock=args.mock,
                use_llm=args.llm,
            )
        else:
            report = run_demo_report(args.symbol, use_mock=args.mock, use_llm=args.llm)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(_err_json(args.task, 1, str(e)), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
