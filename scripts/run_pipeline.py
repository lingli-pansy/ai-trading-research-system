#!/usr/bin/env python3
"""
Single entry: Research -> Contract -> Backtest -> Experience Store.
Usage: python scripts/run_pipeline.py [SYMBOL] [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--mock]
"""
from __future__ import annotations

import argparse
import sys

from ai_trading_research_system.pipeline.backtest_pipe import run as run_pipe


def main() -> int:
    parser = argparse.ArgumentParser(description="Pipeline: Research -> Backtest -> Store")
    parser.add_argument("symbol", nargs="?", default="NVDA", help="Symbol (default: NVDA)")
    parser.add_argument("--start", default=None, help="Backtest start YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="Backtest end YYYY-MM-DD")
    parser.add_argument("--mock", action="store_true", help="Use mock research data")
    parser.add_argument("--llm", action="store_true", help="Use LLM agent (requires OPENAI_API_KEY)")
    args = parser.parse_args()

    result = run_pipe(
        symbol=args.symbol,
        start_date=args.start,
        end_date=args.end,
        use_mock=args.mock,
        use_llm=args.llm,
    )

    print("=== PIPELINE RESULT ===")
    print(f"symbol: {args.symbol}")
    print(f"contract action: {result.contract.suggested_action} (confidence: {result.contract.confidence})")
    print(f"sharpe: {result.metrics.sharpe:.4f}  max_drawdown: {result.metrics.max_drawdown:.4f}")
    print(f"win_rate: {result.metrics.win_rate:.4f}  pnl: {result.metrics.pnl:.2f}  trades: {result.metrics.trade_count}")
    print(f"strategy_run_id: {result.strategy_run_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
