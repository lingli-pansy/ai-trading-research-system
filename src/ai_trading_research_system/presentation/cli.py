"""
Unified CLI: argument parsing only; calls application.commands and prints stdout.
No business logic here.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore[misc, assignment]

# Resolve project root (cli.py may be at repo root or invoked as -m)
def _project_root() -> Path:
    p = Path(__file__).resolve()
    # presentation/cli.py -> src/ai_trading_research_system -> src -> repo root
    for _ in range(4):
        p = p.parent
    return p


PROJECT_ROOT = _project_root()
if load_dotenv:
    load_dotenv(PROJECT_ROOT / ".env")


def _json_serial(obj: object) -> str | float | int | None:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AI Trading Research System — unified CLI (research / backtest / paper / demo / weekly-paper)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def _add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--mock", action="store_true", help="Use mock research data")
        p.add_argument("--llm", action="store_true", help="Use LLM agent (requires OPENAI_API_KEY or KIMI_CODE_API_KEY)")

    # research
    p_research = subparsers.add_parser("research", help="Run research and output DecisionContract (JSON)")
    p_research.add_argument("symbol", nargs="?", default="NVDA", help="Symbol (default: NVDA)")
    _add_common(p_research)

    # backtest
    p_backtest = subparsers.add_parser("backtest", help="Research → Backtest → Store, print metrics")
    p_backtest.add_argument("symbol", nargs="?", default="NVDA", help="Symbol (default: NVDA)")
    p_backtest.add_argument("--start", default=None, help="Backtest start YYYY-MM-DD")
    p_backtest.add_argument("--end", default=None, help="Backtest end YYYY-MM-DD")
    _add_common(p_backtest)

    # paper
    p_paper = subparsers.add_parser("paper", help="Research → Contract → Paper inject (once or runner)")
    p_paper.add_argument("--symbol", default="NVDA", help="Symbol (default: NVDA)")
    p_paper.add_argument("--once", action="store_true", help="Run one Research+inject cycle then exit")
    _add_common(p_paper)

    # demo
    p_demo = subparsers.add_parser("demo", help="E2E demo: research → strategy → backtest → summary (four blocks)")
    p_demo.add_argument("symbol", nargs="?", default="NVDA", help="Symbol (default: NVDA)")
    _add_common(p_demo)

    # weekly-paper
    p_weekly = subparsers.add_parser("weekly-paper", help="UC-09: Weekly autonomous paper portfolio")
    p_weekly.add_argument("--capital", type=float, default=10000, help="Capital limit (default 10000)")
    p_weekly.add_argument("--benchmark", default="SPY", help="Benchmark symbol (default SPY)")
    p_weekly.add_argument("--days", type=int, default=5, help="Trading days (default 5)")
    p_weekly.add_argument("--auto-confirm", action="store_true", default=True, help="Auto confirm trades (default True)")
    p_weekly.add_argument("--no-auto-confirm", action="store_false", dest="auto_confirm", help="Disable auto confirm")
    _add_common(p_weekly)

    args = parser.parse_args()

    from ai_trading_research_system.application.commands import (
        run_research_symbol,
        run_backtest_symbol,
        run_demo,
        run_paper,
        run_weekly_autonomous_paper,
    )

    if args.command == "research":
        contract = run_research_symbol(args.symbol, use_mock=args.mock, use_llm=args.llm)
        print(json.dumps(contract.model_dump(), indent=2, default=_json_serial))
        return 0

    if args.command == "backtest":
        result = run_backtest_symbol(args.symbol, args.start, args.end, use_mock=args.mock, use_llm=args.llm)
        from ai_trading_research_system.presentation.renderers import render_backtest
        for line in render_backtest(result, args.symbol):
            print(line)
        return 0

    if args.command == "paper":
        result = run_paper(args.symbol, once=args.once, use_mock=args.mock, use_llm=args.llm, project_root=PROJECT_ROOT)
        from ai_trading_research_system.presentation.renderers import render_paper
        for line in render_paper(result):
            print(line)
        return 1 if result.paused else 0

    if args.command == "demo":
        result = run_demo(args.symbol, use_mock=args.mock, use_llm=args.llm)
        from ai_trading_research_system.presentation.renderers import render_demo
        for line in render_demo(result, args.symbol):
            print(line)
        return 0

    if args.command == "weekly-paper":
        report_dir = PROJECT_ROOT / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        result = run_weekly_autonomous_paper(
            capital=args.capital,
            benchmark=args.benchmark,
            duration_days=args.days,
            auto_confirm=args.auto_confirm,
            use_mock=args.mock,
            use_llm=args.llm,
            report_dir=report_dir,
        )
        out = {
            "ok": result.ok,
            "mandate_id": result.mandate_id,
            "status": result.status,
            "capital_limit": result.capital_limit,
            "benchmark": result.benchmark,
            "engine_type": result.engine_type,
            "used_nautilus": result.used_nautilus,
            "report_path": result.report_path,
            "summary": result.summary,
        }
        print(json.dumps(out, indent=2, default=_json_serial))
        return 0 if result.ok else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
