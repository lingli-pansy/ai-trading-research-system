"""Command: run paper (research → contract → paper inject).
主路径：非 IBKR 时复用 run_autonomous_paper_cycle，状态与审计落盘。IBKR 路径为兼容层，仍走 paper_pipe + place_market_buy。
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# PROJECT_ROOT for .paper_stop; caller can pass or we use cwd
def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


@dataclass
class PaperCommandResult:
    """Result of paper command for CLI to print."""
    paused: bool = False
    symbol: str = ""
    contract_action: str = ""
    contract_confidence: str = ""
    signal_action: str = ""
    allowed_position_size: float = 0.0
    price: float = 0.0
    order_done: bool | None = None
    message: str = ""
    order_result: Any = None  # optional order detail
    use_ibkr: bool = False


def run_paper(
    symbol: str,
    once: bool = False,
    use_mock: bool = False,
    use_llm: bool = False,
    project_root: Path | None = None,
) -> PaperCommandResult:
    """
    Run paper: kill switch check → get price → IBKR or Nautilus path → return result for CLI to print.
    """
    root = project_root or _project_root()
    if os.environ.get("STOP_PAPER", "").strip() == "1" or (root / ".paper_stop").exists():
        return PaperCommandResult(paused=True, symbol=symbol)

    if use_mock:
        price = 122.5
    else:
        try:
            from ai_trading_research_system.data.market_data_service import get_market_data_service
            snap = get_market_data_service(for_research=False).get_latest_price(symbol)
            price = snap.last_price if snap.last_price > 0 else 122.5
        except Exception:
            price = 122.5

    use_ibkr = bool((os.environ.get("IBKR_HOST") or "").strip() and (os.environ.get("IBKR_PORT") or "").strip())

    from ai_trading_research_system.pipeline.paper_pipe import run

    if use_ibkr:
        res = run(symbol, use_mock=use_mock, use_llm=use_llm)
        out = PaperCommandResult(
            symbol=symbol,
            contract_action=res.contract.suggested_action,
            contract_confidence=res.contract.confidence,
            signal_action=res.signal.action,
            allowed_position_size=res.signal.allowed_position_size,
            price=price,
            use_ibkr=True,
        )
        if res.signal.action != "paper_buy" or res.signal.allowed_position_size <= 0:
            out.order_done = False
            out.message = "no buy signal"
            return out
        raw = os.environ.get("PAPER_INITIAL_CASH")
        initial_cash = float(raw.strip()) if raw else 100_000.0
        quantity = (initial_cash * res.signal.allowed_position_size) / price if price > 0 else 0
        if quantity <= 0:
            out.order_done = False
            out.message = "quantity=0"
            return out
        try:
            from ai_trading_research_system.execution.ibkr_client import place_market_buy
            ibkr_out = place_market_buy(symbol, quantity)
            out.order_done = ibkr_out.placed
            out.message = ibkr_out.message or ""
            out.order_result = ibkr_out
        except Exception as e:
            out.order_done = False
            out.message = str(e)
        return out

    # 主路径：复用 autonomous_paper_cycle，状态与审计落盘（runs/<run_id>/）
    from ai_trading_research_system.application.commands.run_autonomous_paper_cycle import run_autonomous_paper_cycle
    run_id = f"paper_{symbol}_{int(time.time())}"
    cycle_out = run_autonomous_paper_cycle(
        run_id=run_id,
        symbol_universe=[symbol],
        use_mock=use_mock,
        use_llm=use_llm,
        execute_paper=True,
    )
    # 从 cycle 输出转成 PaperCommandResult（单 symbol 时取第一个）
    r = None
    if cycle_out.paper_execution_results:
        r = cycle_out.paper_execution_results[0]
    return PaperCommandResult(
        symbol=symbol,
        contract_action=cycle_out.candidate_decision[0].get("action", "") if cycle_out.candidate_decision else "",
        contract_confidence=cycle_out.candidate_decision[0].get("confidence", "") if cycle_out.candidate_decision else "",
        signal_action="paper_buy" if (cycle_out.order_intents and not cycle_out.no_trade_reason) else "no_trade",
        allowed_position_size=cycle_out.order_intents[0].get("size_fraction", 0) if cycle_out.order_intents else 0,
        price=price,
        order_done=r.get("order_done", None) if r else None,
        message=r.get("message", cycle_out.no_trade_reason or "") if r else (cycle_out.no_trade_reason or ""),
        order_result=r,
        use_ibkr=False,
    )
