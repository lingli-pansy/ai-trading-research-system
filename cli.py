#!/usr/bin/env python3
"""
Unified CLI entry for AI Trading Research System (Phase 2).
Usage:
  python cli.py research SYMBOL [--mock] [--llm]
  python cli.py backtest SYMBOL [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--mock] [--llm]
  python cli.py paper [--symbol SYMBOL] [--once] [--mock] [--llm]
  python cli.py demo SYMBOL [--mock] [--llm]

Compatible with OpenClaw Skill: same subcommands and args; Skill can invoke this CLI or use control layer API.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")


def _json_serial(obj: object) -> str | float | int | None:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def cmd_research(symbol: str, mock: bool, llm: bool) -> int:
    from ai_trading_research_system.research.orchestrator import ResearchOrchestrator

    orchestrator = ResearchOrchestrator(use_mock=mock, use_llm=llm)
    contract = orchestrator.run(symbol)
    out = contract.model_dump()
    print(json.dumps(out, indent=2, default=_json_serial))
    return 0


def cmd_backtest(symbol: str, start: str | None, end: str | None, mock: bool, llm: bool) -> int:
    from ai_trading_research_system.pipeline.backtest_pipe import run as run_pipe

    result = run_pipe(
        symbol=symbol,
        start_date=start,
        end_date=end,
        use_mock=mock,
        use_llm=llm,
    )
    print("=== BACKTEST RESULT ===")
    print(f"symbol: {symbol}")
    print(f"contract action: {result.contract.suggested_action} (confidence: {result.contract.confidence})")
    print(f"sharpe: {result.metrics.sharpe:.4f}  max_drawdown: {result.metrics.max_drawdown:.4f}")
    print(f"win_rate: {result.metrics.win_rate:.4f}  pnl: {result.metrics.pnl:.2f}  trades: {result.metrics.trade_count}")
    print(f"strategy_run_id: {result.strategy_run_id}")
    return 0


def cmd_paper(symbol: str, once: bool, mock: bool, llm: bool) -> int:
    from ai_trading_research_system.pipeline.paper_pipe import run, run_and_inject
    from ai_trading_research_system.execution.paper_runner import PaperRunner
    from ai_trading_research_system.data.providers import YFinanceProvider

    def _kill_switch() -> bool:
        if os.environ.get("STOP_PAPER", "").strip() == "1":
            return True
        return (PROJECT_ROOT / ".paper_stop").exists()

    def _get_price(sym: str, use_mock: bool) -> float:
        if use_mock:
            return 122.5
        try:
            return YFinanceProvider().get_price(sym).last_price
        except Exception:
            return 122.5

    def _float_env(name: str, default: float | None) -> float | None:
        raw = os.environ.get(name)
        if not raw:
            return default
        try:
            return float(raw.strip())
        except ValueError:
            return default

    if _kill_switch():
        print("Paper 已暂停：STOP_PAPER=1 或存在 .paper_stop（Kill Switch）")
        return 1

    price = _get_price(symbol, mock)
    use_ibkr = (os.environ.get("IBKR_HOST") or "").strip() and (os.environ.get("IBKR_PORT") or "").strip()

    if use_ibkr:
        res = run(symbol, use_mock=mock, use_llm=llm)
        print("=== PAPER RESULT (IBKR) ===")
        print(f"symbol: {symbol}")
        print(f"contract: {res.contract.suggested_action} (confidence: {res.contract.confidence})")
        print(f"signal: {res.signal.action} size_fraction={res.signal.allowed_position_size}")
        print(f"price: {price}")
        if res.signal.action != "paper_buy" or res.signal.allowed_position_size <= 0:
            print("order_done: False (no buy signal)")
            return 0
        initial_cash = _float_env("PAPER_INITIAL_CASH", 100_000.0) or 100_000.0
        quantity = (initial_cash * res.signal.allowed_position_size) / price if price > 0 else 0
        if quantity <= 0:
            print("order_done: False (quantity=0)")
            return 0
        try:
            from ai_trading_research_system.execution.ibkr_client import place_market_buy
            out = place_market_buy(symbol, quantity)
            print(f"order_done: {out.placed} message: {out.message}" + (f" order_id={out.order_id}" if out.order_id else ""))
        except Exception as e:
            print(f"order_done: False message: {e}")
            return 1
        return 0

    max_pct = _float_env("PAPER_MAX_POSITION_PCT", None)
    daily_stop = _float_env("PAPER_DAILY_STOP_LOSS_PCT", None)
    runner = PaperRunner(symbol, max_position_pct=max_pct, daily_stop_loss_pct=daily_stop)
    result = run_and_inject(symbol, runner, price, use_mock=mock, use_llm=llm)

    print("=== PAPER RESULT ===")
    print(f"symbol: {symbol}")
    print(f"contract: {result.contract.suggested_action} (confidence: {result.contract.confidence})")
    print(f"signal: {result.signal.action} size_fraction={result.signal.allowed_position_size}")
    print(f"price: {price}")
    if result.runner_result:
        r = result.runner_result
        print(f"order_done: {r.order_done} message: {r.message}")
        if r.order_result:
            print(f"  order: {r.order_result.status} qty={r.order_result.quantity} price={r.order_result.price}")
    return 0


def cmd_demo(symbol: str, mock: bool, llm: bool) -> int:
    """E2E demo: research → strategy → backtest → summary (four blocks)."""
    from ai_trading_research_system.pipeline.backtest_pipe import run as run_pipe

    result = run_pipe(symbol=symbol, start_date=None, end_date=None, use_mock=mock, use_llm=llm)
    contract = result.contract
    metrics = result.metrics
    run_id = result.strategy_run_id

    # Block 1: 研究结论
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

    # Block 2: 策略生成 (Contract → Translator → signal)
    from ai_trading_research_system.strategy.translator import ContractTranslator
    signal = ContractTranslator().translate(contract)
    print("=" * 60)
    print("【2】策略生成")
    print("=" * 60)
    print(f"action: {signal.action}  allowed_position_size: {signal.allowed_position_size}")
    print(f"rationale: {signal.rationale}")
    print()

    # Block 3: 回测结果
    print("=" * 60)
    print("【3】回测结果")
    print("=" * 60)
    print(f"sharpe: {metrics.sharpe:.4f}  max_drawdown: {metrics.max_drawdown:.4f}")
    print(f"win_rate: {metrics.win_rate:.4f}  pnl: {metrics.pnl:.2f}  trade_count: {metrics.trade_count}")
    print()

    # Block 4: 交易总结
    print("=" * 60)
    print("【4】交易总结")
    print("=" * 60)
    print("执行引擎: NautilusTrader（回测 + Paper 默认主线）。")
    print(f"本轮研究+回测已写入 Experience Store，strategy_run_id={run_id}。")
    print(f"结论: {contract.suggested_action}（置信度 {contract.confidence}），策略信号 {signal.action}，回测 {metrics.trade_count} 笔，pnl={metrics.pnl:.2f}。")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AI Trading Research System — unified CLI (research / backtest / paper / demo)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def _add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--mock", action="store_true", help="Use mock research data")
        p.add_argument("--llm", action="store_true", help="Use LLM agent (requires OPENAI_API_KEY or KIMI_CODE_API_KEY)")

    # research SYMBOL [--mock] [--llm]
    p_research = subparsers.add_parser("research", help="Run research and output DecisionContract (JSON)")
    p_research.add_argument("symbol", nargs="?", default="NVDA", help="Symbol (default: NVDA)")
    _add_common(p_research)
    p_research.set_defaults(func=lambda ns: cmd_research(ns.symbol, ns.mock, ns.llm))

    # backtest SYMBOL [--start] [--end] [--mock] [--llm]
    p_backtest = subparsers.add_parser("backtest", help="Research → Backtest → Store, print metrics")
    p_backtest.add_argument("symbol", nargs="?", default="NVDA", help="Symbol (default: NVDA)")
    p_backtest.add_argument("--start", default=None, help="Backtest start YYYY-MM-DD")
    p_backtest.add_argument("--end", default=None, help="Backtest end YYYY-MM-DD")
    _add_common(p_backtest)
    p_backtest.set_defaults(
        func=lambda ns: cmd_backtest(ns.symbol, ns.start, ns.end, ns.mock, ns.llm)
    )

    # paper [--symbol SYMBOL] [--once] [--mock] [--llm]
    p_paper = subparsers.add_parser("paper", help="Research → Contract → Paper inject (once or runner)")
    p_paper.add_argument("--symbol", default="NVDA", help="Symbol (default: NVDA)")
    p_paper.add_argument("--once", action="store_true", help="Run one Research+inject cycle then exit")
    _add_common(p_paper)
    p_paper.set_defaults(func=lambda ns: cmd_paper(ns.symbol, ns.once, ns.mock, ns.llm))

    # demo SYMBOL [--mock] [--llm]
    p_demo = subparsers.add_parser("demo", help="E2E demo: research → strategy → backtest → summary (four blocks)")
    p_demo.add_argument("symbol", nargs="?", default="NVDA", help="Symbol (default: NVDA)")
    _add_common(p_demo)
    p_demo.set_defaults(func=lambda ns: cmd_demo(ns.symbol, ns.mock, ns.llm))

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
