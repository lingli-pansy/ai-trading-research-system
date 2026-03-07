#!/usr/bin/env python3
"""
Run research -> contract -> translator -> backtest -> experience store, print metrics.
Usage: python scripts/run_backtest.py [SYMBOL] [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--mock]
实盘前 L3/L4：MIN_TRADE_COUNT、MAX_DRAWDOWN_PCT 可选校验（见 .env.example）。
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")

from ai_trading_research_system.research.orchestrator import ResearchOrchestrator
from ai_trading_research_system.strategy.translator import ContractTranslator
from ai_trading_research_system.backtest.runner import run_backtest
from ai_trading_research_system.experience.store import write_backtest_result


def _default_date_range() -> tuple[str, str]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=90)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def main() -> int:
    parser = argparse.ArgumentParser(description="Research -> Backtest -> Store -> Metrics")
    parser.add_argument("symbol", nargs="?", default="NVDA", help="Symbol (default: NVDA)")
    parser.add_argument("--start", default=None, help="Backtest start date YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="Backtest end date YYYY-MM-DD")
    parser.add_argument("--mock", action="store_true", help="Use mock data for research")
    parser.add_argument("--llm", action="store_true", help="Use LLM agent (requires OPENAI_API_KEY)")
    args = parser.parse_args()

    start_date, end_date = args.start, args.end
    if not start_date or not end_date:
        s, e = _default_date_range()
        start_date = start_date or s
        end_date = end_date or e

    orchestrator = ResearchOrchestrator(use_mock=args.mock, use_llm=args.llm)
    contract = orchestrator.run(args.symbol)
    translator = ContractTranslator()
    signal = translator.translate(contract)

    metrics = run_backtest(
        symbol=args.symbol,
        signal=signal,
        start_date=start_date,
        end_date=end_date,
    )

    run_id = write_backtest_result(
        symbol=args.symbol,
        start_date=start_date,
        end_date=end_date,
        metrics=metrics,
    )

    # 实盘前 L3/L4：可选阈值校验
    min_trades = os.environ.get("MIN_TRADE_COUNT")
    if min_trades is not None and min_trades.strip() != "":
        try:
            n = int(min_trades.strip())
            if metrics.trade_count < n:
                print(f"FAIL: trade_count {metrics.trade_count} < MIN_TRADE_COUNT {n}", file=sys.stderr)
                return 1
        except ValueError:
            pass
    max_dd_pct = os.environ.get("MAX_DRAWDOWN_PCT")
    if max_dd_pct is not None and max_dd_pct.strip() != "":
        try:
            dd = float(max_dd_pct.strip())
            if metrics.max_drawdown > dd / 100.0:
                print(f"FAIL: max_drawdown {metrics.max_drawdown:.4f} > MAX_DRAWDOWN_PCT {dd}%", file=sys.stderr)
                return 1
        except ValueError:
            pass

    print("=== BACKTEST METRICS ===")
    print(f"symbol: {args.symbol}")
    print(f"signal: {signal.action} (size_fraction={signal.allowed_position_size})")
    print(f"sharpe: {metrics.sharpe:.4f}")
    print(f"max_drawdown: {metrics.max_drawdown:.4f}")
    print(f"win_rate: {metrics.win_rate:.4f}")
    print(f"pnl: {metrics.pnl:.2f}")
    print(f"trade_count: {metrics.trade_count}")
    print(f"experience run_id: {run_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
