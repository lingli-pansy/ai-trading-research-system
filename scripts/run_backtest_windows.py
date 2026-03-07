#!/usr/bin/env python3
"""
多时间窗口回测并输出稳定性报告（实盘前 L1）。
Usage: python scripts/run_backtest_windows.py [SYMBOL] [--windows 90,180] [--mock] [--llm]
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")

from ai_trading_research_system.research.orchestrator import ResearchOrchestrator
from ai_trading_research_system.strategy.translator import ContractTranslator
from ai_trading_research_system.backtest.runner import run_backtest


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-window backtest stability report (L1)")
    parser.add_argument("symbol", nargs="?", default="NVDA", help="Symbol (default: NVDA)")
    parser.add_argument("--windows", default="90,180", help="Comma-separated window days (default: 90,180)")
    parser.add_argument("--oos-days", type=int, default=None, metavar="N", help="L2: 仅跑 OOS 窗口（最近 N 日）单窗口回测")
    parser.add_argument("--mock", action="store_true", help="Use mock research data")
    parser.add_argument("--llm", action="store_true", help="Use LLM agent")
    args = parser.parse_args()

    if args.oos_days is not None:
        window_days = [args.oos_days]
        print(f"OOS mode: single window last {args.oos_days} days (L2)")
    else:
        try:
            window_days = [int(x.strip()) for x in args.windows.split(",") if x.strip()]
        except ValueError:
            print("FAIL: --windows 应为逗号分隔的整数，如 90,180", file=sys.stderr)
            return 1
        if not window_days:
            print("FAIL: 至少指定一个窗口天数", file=sys.stderr)
            return 1

    orchestrator = ResearchOrchestrator(use_mock=args.mock, use_llm=args.llm)
    contract = orchestrator.run(args.symbol)
    signal = ContractTranslator().translate(contract)

    end = datetime.now(timezone.utc)
    rows = []
    for days in window_days:
        start = end - timedelta(days=days)
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")
        try:
            m = run_backtest(
                symbol=args.symbol,
                signal=signal,
                start_date=start_str,
                end_date=end_str,
            )
            rows.append((f"{days}d", start_str, end_str, m.sharpe, m.max_drawdown, m.win_rate, m.pnl, m.trade_count))
        except Exception as e:
            print(f"FAIL: window {days}d — {e}", file=sys.stderr)
            return 1

    print("=== MULTI-WINDOW BACKTEST (L1) ===")
    print(f"symbol: {args.symbol}  signal: {signal.action} (size={signal.allowed_position_size})")
    print(f"windows: {args.windows} days")
    print()
    print(f"{'window':<8} {'start':<12} {'end':<12} {'sharpe':<10} {'max_dd':<10} {'win_rate':<10} {'pnl':<12} {'trades':<8}")
    print("-" * 90)
    for r in rows:
        print(f"{r[0]:<8} {r[1]:<12} {r[2]:<12} {r[3]:<10.4f} {r[4]:<10.4f} {r[5]:<10.4f} {r[6]:<12.2f} {r[7]:<8}")
    print()
    print("Stability report done. Check sharpe/max_drawdown/trade_count across windows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
