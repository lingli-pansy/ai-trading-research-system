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
        print("=== BACKTEST RESULT ===")
        print(f"symbol: {args.symbol}")
        print(f"contract action: {result.contract.suggested_action} (confidence: {result.contract.confidence})")
        print(f"sharpe: {result.metrics.sharpe:.4f}  max_drawdown: {result.metrics.max_drawdown:.4f}")
        print(f"win_rate: {result.metrics.win_rate:.4f}  pnl: {result.metrics.pnl:.2f}  trades: {result.metrics.trade_count}")
        print(f"strategy_run_id: {result.strategy_run_id}")
        return 0

    if args.command == "paper":
        result = run_paper(args.symbol, once=args.once, use_mock=args.mock, use_llm=args.llm, project_root=PROJECT_ROOT)
        if result.paused:
            print("Paper 已暂停：STOP_PAPER=1 或存在 .paper_stop（Kill Switch）")
            return 1
        header = "=== PAPER RESULT (IBKR) ===" if result.use_ibkr else "=== PAPER RESULT ==="
        print(header)
        print(f"symbol: {result.symbol}")
        print(f"contract: {result.contract_action} (confidence: {result.contract_confidence})")
        print(f"signal: {result.signal_action} size_fraction={result.allowed_position_size}")
        print(f"price: {result.price}")
        if result.order_done is not None:
            print(f"order_done: {result.order_done} message: {result.message}")
            if result.order_result and hasattr(result.order_result, "status"):
                o = result.order_result
                print(f"  order: {getattr(o, 'status', '')} qty={getattr(o, 'quantity', '')} price={getattr(o, 'price', '')}")
        return 0

    if args.command == "demo":
        result = run_demo(args.symbol, use_mock=args.mock, use_llm=args.llm)
        contract = result.contract
        metrics = result.metrics
        run_id = result.strategy_run_id
        from ai_trading_research_system.strategy.translator import ContractTranslator
        signal = ContractTranslator().translate(contract)
        thesis_preview = (contract.thesis or "")[:400]
        if len(contract.thesis or "") > 400:
            thesis_preview += "..."
        print("=" * 60)
        print("【1】研究结论")
        print("=" * 60)
        print(f"thesis: {thesis_preview}")
        print(f"key_drivers: {contract.key_drivers}")
        print(f"confidence: {contract.confidence}  suggested_action: {contract.suggested_action}")
        print(f"time_horizon: {contract.time_horizon}")
        if contract.uncertainties:
            print(f"uncertainties: {contract.uncertainties}")
        print()
        print("=" * 60)
        print("【2】策略生成")
        print("=" * 60)
        print(f"action: {signal.action}  allowed_position_size: {signal.allowed_position_size}")
        print(f"rationale: {signal.rationale}")
        print()
        print("=" * 60)
        print("【3】回测结果")
        print("=" * 60)
        print(f"sharpe: {metrics.sharpe:.4f}  max_drawdown: {metrics.max_drawdown:.4f}")
        print(f"win_rate: {metrics.win_rate:.4f}  pnl: {metrics.pnl:.2f}  trade_count: {metrics.trade_count}")
        print()
        print("=" * 60)
        print("【4】交易总结")
        print("=" * 60)
        print("执行引擎: NautilusTrader（回测 + Paper 默认主线）。")
        print(f"本轮研究+回测已写入 Experience Store，strategy_run_id={run_id}。")
        print(f"结论: {contract.suggested_action}（置信度 {contract.confidence}），策略信号 {signal.action}，回测 {metrics.trade_count} 笔，pnl={metrics.pnl:.2f}。")
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
