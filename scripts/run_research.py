#!/usr/bin/env python3
"""
Run research pipeline for a symbol and print DecisionContract (JSON).
Usage: python scripts/run_research.py SYMBOL [--mock]
  SYMBOL   e.g. NVDA
  --mock   use mock data instead of yfinance (default: use yfinance)
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
# 固定从项目根加载 .env，不依赖当前工作目录
PROJECT_ROOT = Path(__file__).resolve().parents[1]
_load_env = PROJECT_ROOT / ".env"
load_dotenv(_load_env)

from ai_trading_research_system.research.orchestrator import ResearchOrchestrator


def _json_serial(obj: object) -> str | float | int | None:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run research and output DecisionContract")
    parser.add_argument("symbol", nargs="?", default="NVDA", help="Symbol to analyze (default: NVDA)")
    parser.add_argument("--mock", action="store_true", help="Use mock data instead of yfinance")
    parser.add_argument("--llm", action="store_true", help="Use LLM agent for research (requires OPENAI_API_KEY)")
    args = parser.parse_args()

    orchestrator = ResearchOrchestrator(use_mock=args.mock, use_llm=args.llm)
    contract = orchestrator.run(args.symbol)

    if args.llm and "LLM unavailable" in (contract.thesis or ""):
        import sys
        import os
        kimi = os.environ.get("KIMI_CODE_API_KEY") or os.environ.get("KIMI_API_KEY")
        openai = os.environ.get("OPENAI_API_KEY")
        print(
            f"[stderr] LLM 未就绪。已从 {_load_env} 加载 .env；\n"
            f"  KIMI_CODE_API_KEY 已设置: {bool(kimi and kimi.strip())}\n"
            f"  OPENAI_API_KEY 已设置: {bool(openai and openai.strip())}\n"
            f"  请确认 .env 中有且仅有一行: KIMI_CODE_API_KEY=你的key（等号两侧无空格，值不要加引号）",
            file=sys.stderr,
        )

    out = contract.model_dump()
    print(json.dumps(out, indent=2, default=_json_serial))


if __name__ == "__main__":
    main()
