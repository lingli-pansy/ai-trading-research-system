"""Command: run paper (research → contract → paper inject). Calls paper_pipe; handles kill switch and IBKR vs Nautilus."""
from __future__ import annotations

import os
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

    from ai_trading_research_system.pipeline.paper_pipe import run, run_and_inject
    from ai_trading_research_system.execution.paper_runner import PaperRunner

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

    def _float_env(name: str, default: float | None) -> float | None:
        raw = os.environ.get(name)
        if not raw:
            return default
        try:
            return float(raw.strip())
        except ValueError:
            return default

    max_pct = _float_env("PAPER_MAX_POSITION_PCT", None)
    daily_stop = _float_env("PAPER_DAILY_STOP_LOSS_PCT", None)
    runner = PaperRunner(symbol, max_position_pct=max_pct, daily_stop_loss_pct=daily_stop)
    result = run_and_inject(symbol, runner, price, use_mock=use_mock, use_llm=use_llm)
    r = result.runner_result
    return PaperCommandResult(
        symbol=symbol,
        contract_action=result.contract.suggested_action,
        contract_confidence=result.contract.confidence,
        signal_action=result.signal.action,
        allowed_position_size=result.signal.allowed_position_size,
        price=price,
        order_done=r.order_done if r else None,
        message=r.message if r else "",
        order_result=r.order_result if r else None,
        use_ibkr=False,
    )
