#!/usr/bin/env python3
"""
Research → Contract → 注入 Paper 节点并执行一次（或持续运行 stub）。
Usage: python scripts/run_paper.py --symbol NVDA [--once] [--mock]
风控（授权就绪后可配）：PAPER_MAX_POSITION_PCT、PAPER_DAILY_STOP_LOSS_PCT，见 .env.example / deferred_authorization.md。
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_PROJECT_ROOT / ".env")

from ai_trading_research_system.pipeline.paper_pipe import run, run_and_inject
from ai_trading_research_system.execution.paper_runner import PaperRunner
from ai_trading_research_system.data.providers import YFinanceProvider


def _float_env(name: str, default: float | None) -> float | None:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return float(raw.strip())
    except ValueError:
        return default


def _get_price(symbol: str, use_mock: bool) -> float:
    if use_mock:
        return 122.5
    try:
        snap = YFinanceProvider().get_price(symbol)
        return snap.last_price
    except Exception:
        return 122.5


def _kill_switch_active() -> bool:
    """Kill Switch：STOP_PAPER=1 或项目根 .paper_stop 存在时禁止执行（实盘前 L6）。"""
    if os.environ.get("STOP_PAPER", "").strip() == "1":
        return True
    return (_PROJECT_ROOT / ".paper_stop").exists()


def main() -> int:
    parser = argparse.ArgumentParser(description="Research -> Paper inject")
    parser.add_argument("--symbol", default="NVDA", help="Symbol (default: NVDA)")
    parser.add_argument("--once", action="store_true", help="Run one Research+inject cycle then exit")
    parser.add_argument("--mock", action="store_true", help="Use mock research data and mock price")
    parser.add_argument("--llm", action="store_true", help="Use LLM agent (requires OPENAI_API_KEY)")
    args = parser.parse_args()

    if _kill_switch_active():
        print("Paper 已暂停：STOP_PAPER=1 或存在 .paper_stop（Kill Switch）")
        return 1

    use_ibkr = (os.environ.get("IBKR_HOST") or "").strip() and (os.environ.get("IBKR_PORT") or "").strip()
    price = _get_price(args.symbol, args.mock)

    if use_ibkr:
        # L5: IBKR Paper 路径 — Research → Contract → Signal，再通过 ib_insync 向 TWS 下单
        res = run(args.symbol, use_mock=args.mock, use_llm=args.llm)
        print("=== PAPER RESULT (IBKR) ===")
        print(f"symbol: {args.symbol}")
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
            out = place_market_buy(args.symbol, quantity)
            print(f"order_done: {out.placed} message: {out.message}" + (f" order_id={out.order_id}" if out.order_id else ""))
        except Exception as e:
            print(f"order_done: False message: {e}")
            return 1
        print("IBKR Paper injection completed.")
        return 0

    max_pct = _float_env("PAPER_MAX_POSITION_PCT", None)
    daily_stop = _float_env("PAPER_DAILY_STOP_LOSS_PCT", None)
    runner = PaperRunner(
        args.symbol,
        max_position_pct=max_pct,
        daily_stop_loss_pct=daily_stop,
    )
    result = run_and_inject(args.symbol, runner, price, use_mock=args.mock, use_llm=args.llm)

    print("=== PAPER RESULT ===")
    print(f"symbol: {args.symbol}")
    print(f"contract: {result.contract.suggested_action} (confidence: {result.contract.confidence})")
    print(f"signal: {result.signal.action} size_fraction={result.signal.allowed_position_size}")
    print(f"price: {price}")
    if result.runner_result:
        r = result.runner_result
        print(f"order_done: {r.order_done} message: {r.message}")
        if r.order_result:
            print(f"  order: {r.order_result.status} qty={r.order_result.quantity} price={r.order_result.price}")
    print("Strategy mounted and injection completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
