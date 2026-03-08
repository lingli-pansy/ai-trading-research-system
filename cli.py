#!/usr/bin/env python3
"""
Unified CLI entry: delegates to presentation.cli.
Usage:
  python cli.py research SYMBOL [--mock] [--llm]
  python cli.py backtest SYMBOL [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--mock] [--llm]
  python cli.py paper [--symbol SYMBOL] [--once] [--mock] [--llm]
  python cli.py demo SYMBOL [--mock] [--llm]
  python cli.py weekly-paper [--capital 10000] [--benchmark SPY] [--days 5] [--mock] [--llm]
"""
from __future__ import annotations

import sys

# Ensure package is importable when run from repo root
def _main() -> int:
    from ai_trading_research_system.presentation.cli import main
    return main()


if __name__ == "__main__":
    sys.exit(_main())
