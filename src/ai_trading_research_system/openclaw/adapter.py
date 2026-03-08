"""
OpenClaw adapter: translate external requests into application.commands and return unified JSON.
Used by run_for_openclaw.py and by OpenClaw persona/skills.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from ai_trading_research_system.openclaw.commands import (
    research_symbol,
    backtest_symbol,
    run_demo_command,
    weekly_autonomous_paper,
)


def _json_safe_contract_dump(contract: Any) -> dict[str, Any]:
    dump = contract.model_dump()
    for key, val in list(dump.items()):
        if hasattr(val, "isoformat"):
            dump[key] = val.isoformat()
    return dump


def run_research_report(
    symbol: str,
    *,
    use_mock: bool = False,
    use_llm: bool = False,
) -> dict[str, Any]:
    """Run research only; return report dict (JSON-serializable)."""
    contract = research_symbol(symbol, use_mock=use_mock, use_llm=use_llm)
    dump = _json_safe_contract_dump(contract)
    return {
        "task": "research",
        "symbol": symbol,
        "completed_at": datetime.utcnow().isoformat() + "Z",
        "contract_action": contract.suggested_action,
        "contract_confidence": contract.confidence,
        "thesis_snippet": (contract.thesis or "")[:200],
        "raw_contract": dump,
        "engine_type": "nautilus",
        "status": "ok",
        "reason": "",
    }


def run_backtest_report(
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    use_mock: bool = False,
    use_llm: bool = False,
) -> dict[str, Any]:
    """Run research + backtest + store; return report dict."""
    result = backtest_symbol(
        symbol,
        start_date=start_date,
        end_date=end_date,
        use_mock=use_mock,
        use_llm=use_llm,
    )
    dump = _json_safe_contract_dump(result.contract)
    status = "no_trade" if result.metrics.trade_count == 0 else "ok"
    reason = "wait_confirmation" if result.metrics.trade_count == 0 else ""
    return {
        "task": "backtest",
        "symbol": symbol,
        "completed_at": datetime.utcnow().isoformat() + "Z",
        "contract_action": result.contract.suggested_action,
        "contract_confidence": result.contract.confidence,
        "thesis_snippet": (result.contract.thesis or "")[:200],
        "sharpe": result.metrics.sharpe,
        "max_drawdown": result.metrics.max_drawdown,
        "win_rate": result.metrics.win_rate,
        "pnl": result.metrics.pnl,
        "trade_count": result.metrics.trade_count,
        "strategy_run_id": result.strategy_run_id,
        "raw_contract": dump,
        "engine_type": "nautilus",
        "used_nautilus": True,
        "status": status,
        "reason": reason,
    }


def run_demo_report(
    symbol: str,
    *,
    use_mock: bool = False,
    use_llm: bool = False,
) -> dict[str, Any]:
    """Run E2E demo; return report dict with research/strategy/backtest/summary blocks."""
    result = run_demo_command(symbol, use_mock=use_mock, use_llm=use_llm)
    contract = result.contract
    dump = _json_safe_contract_dump(contract)
    status = "no_trade" if result.metrics.trade_count == 0 else "ok"
    reason = "wait_confirmation" if result.metrics.trade_count == 0 else ""
    from ai_trading_research_system.strategy.translator import ContractTranslator
    signal = ContractTranslator().translate(contract)
    return {
        "task": "demo",
        "symbol": symbol,
        "completed_at": datetime.utcnow().isoformat() + "Z",
        "engine_type": "nautilus",
        "used_nautilus": True,
        "status": status,
        "reason": reason,
        "research": {
            "thesis": (contract.thesis or "")[:400],
            "key_drivers": contract.key_drivers,
            "confidence": contract.confidence,
            "suggested_action": contract.suggested_action,
            "time_horizon": contract.time_horizon,
            "raw_contract": dump,
        },
        "strategy": {
            "action": signal.action,
            "allowed_position_size": signal.allowed_position_size,
            "rationale": signal.rationale,
        },
        "backtest": {
            "sharpe": result.metrics.sharpe,
            "max_drawdown": result.metrics.max_drawdown,
            "win_rate": result.metrics.win_rate,
            "pnl": result.metrics.pnl,
            "trade_count": result.metrics.trade_count,
        },
        "summary": {
            "strategy_run_id": result.strategy_run_id,
            "sentence": f"结论: {contract.suggested_action}（置信度 {contract.confidence}），策略信号 {signal.action}，回测 {result.metrics.trade_count} 笔，pnl={result.metrics.pnl:.2f}。",
        },
    }


def run_weekly_paper_report(
    *,
    capital: float = 10_000.0,
    benchmark: str = "SPY",
    duration_days: int = 5,
    auto_confirm: bool = True,
    use_mock: bool = False,
    use_llm: bool = False,
) -> dict[str, Any]:
    """UC-09: Weekly autonomous paper. Returns unified JSON (ok, command, mandate_id, status, report_path, ...)."""
    report_dir = Path.cwd() / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    result = weekly_autonomous_paper(
        capital=capital,
        benchmark=benchmark,
        duration_days=duration_days,
        auto_confirm=auto_confirm,
        use_mock=use_mock,
        use_llm=use_llm,
        report_dir=report_dir,
    )
    summary = result.summary or {}
    return {
        "ok": result.ok,
        "command": "weekly_autonomous_paper",
        "mandate_id": result.mandate_id,
        "status": result.status,
        "report_path": result.report_path,
        "engine_type": result.engine_type,
        "used_nautilus": result.used_nautilus,
        "snapshot_source": summary.get("snapshot_source", ""),
        "benchmark_source": summary.get("benchmark_source", ""),
    }
