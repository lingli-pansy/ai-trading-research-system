#!/usr/bin/env python3
"""
Scheduled run: execute research or research+backtest on an interval (or once) and write reports to disk.
Config via env: SCHEDULE_INTERVAL_MINUTES (0=once), DEFAULT_SYMBOL, RUN_BACKTEST (true|false), REPORT_DIR.
Usage: python scripts/run_scheduled.py [--once] [--symbol SYMBOL] [--backtest] [--mock] [--llm]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

from ai_trading_research_system.pipeline.openclaw_adapter import (
    run_research_report,
    run_backtest_report,
)


def _report_dir() -> Path:
    d = os.environ.get("REPORT_DIR", ".reports")
    path = Path(d)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run_one(symbol: str, backtest: bool, use_mock: bool, use_llm: bool) -> dict:
    if backtest:
        return run_backtest_report(symbol, use_mock=use_mock, use_llm=use_llm)
    return run_research_report(symbol, use_mock=use_mock, use_llm=use_llm)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scheduled research/backtest, write reports to REPORT_DIR")
    parser.add_argument("--once", action="store_true", help="Run once and exit (no loop)")
    parser.add_argument("--symbol", default=None, help="Symbol (default: DEFAULT_SYMBOL or NVDA)")
    parser.add_argument("--backtest", action="store_true", help="Run research+backtest instead of research only")
    parser.add_argument("--mock", action="store_true", help="Use mock research data")
    parser.add_argument("--llm", action="store_true", help="Use LLM agent")
    args = parser.parse_args()

    symbol = args.symbol or os.environ.get("DEFAULT_SYMBOL", "NVDA")
    interval_min = int(os.environ.get("SCHEDULE_INTERVAL_MINUTES", "0"))
    run_backtest_env = os.environ.get("RUN_BACKTEST", "false").lower() in ("1", "true", "yes")
    backtest = args.backtest or run_backtest_env

    report_dir = _report_dir()
    run_count = 0

    while True:
        run_count += 1
        try:
            report = _run_one(symbol, backtest=backtest, use_mock=args.mock, use_llm=args.llm)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            task = report.get("task", "research")
            path = report_dir / f"{task}_{symbol}_{ts}.json"
            path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[{ts}] Report written: {path}", file=sys.stderr)
            # Optional: notify hook (e.g. for OpenClaw or cron to tail)
            notify_file = os.environ.get("NOTIFY_FILE")
            if notify_file:
                try:
                    with open(notify_file, "a", encoding="utf-8") as f:
                        f.write(f"{ts}\t{path}\n")
                except Exception:
                    pass
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)

        if args.once or interval_min <= 0:
            break
        time.sleep(interval_min * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
