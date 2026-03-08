"""
OpenClaw adapter: format command result -> unified JSON. Calls application.command_registry only.
Used by run_for_openclaw.py and by OpenClaw persona/skills.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from ai_trading_research_system.application.command_registry import run as registry_run


def _json_safe_contract_dump(contract: Any) -> dict[str, Any]:
    dump = contract.model_dump()
    for key, val in list(dump.items()):
        if hasattr(val, "isoformat"):
            dump[key] = val.isoformat()
    return dump


def format_result(task: str, result: Any, *, command_override: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """
    Format raw command result to OpenClaw report dict (JSON-serializable).
    task: canonical command (research_symbol | backtest_symbol | run_demo | weekly_autonomous_paper | weekly_report).
    """
    if task == "research_symbol":
        contract = result
        dump = _json_safe_contract_dump(contract)
        symbol = kwargs.get("symbol", getattr(contract, "symbol", ""))
        return {
            "task": "research_symbol",
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
    if task == "backtest_symbol":
        dump = _json_safe_contract_dump(result.contract)
        symbol = kwargs.get("symbol", "")
        status = "no_trade" if result.metrics.trade_count == 0 else "ok"
        reason = "wait_confirmation" if result.metrics.trade_count == 0 else ""
        return {
            "task": "backtest_symbol",
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
    if task == "run_demo":
        contract = result.contract
        dump = _json_safe_contract_dump(contract)
        symbol = kwargs.get("symbol", "")
        status = "no_trade" if result.metrics.trade_count == 0 else "ok"
        reason = "wait_confirmation" if result.metrics.trade_count == 0 else ""
        from ai_trading_research_system.strategy.translator import ContractTranslator
        signal = ContractTranslator().translate(contract)
        return {
            "task": "run_demo",
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
    if task == "weekly_report":
        # WeeklyReportCommandResult: ok, report_path, mandate_id, summary (no execution)
        return {
            "ok": result.ok,
            "command": command_override or "weekly_report",
            "mandate_id": getattr(result, "mandate_id", "") or "",
            "report_path": getattr(result, "report_path", "") or "",
            "summary": getattr(result, "summary", {}) or {},
            "status": "ok",
            "engine_type": "nautilus",
            "used_nautilus": True,
        }
    if task == "weekly_autonomous_paper":
        summary = result.summary or {}
        out = {
            "ok": result.ok,
            "command": command_override or task,
            "mandate_id": result.mandate_id,
            "status": result.status,
            "report_path": result.report_path,
            "engine_type": result.engine_type,
            "used_nautilus": result.used_nautilus,
            "snapshot_source": summary.get("snapshot_source", ""),
            "benchmark_source": summary.get("benchmark_source", ""),
        }
        return out
    if task == "autonomous_paper_cycle":
        # CycleOutput: ok, run_id, candidate_decision, final_decision, order_intents, no_trade_reason, ...
        return {
            "ok": result.ok,
            "command": command_override or task,
            "run_id": result.run_id,
            "candidate_decision": result.candidate_decision,
            "final_decision": result.final_decision,
            "order_intents": result.order_intents,
            "no_trade_reason": result.no_trade_reason,
            "rejected_reason": result.rejected_reason,
            "skipped_reason": result.skipped_reason,
            "write_paths": result.write_paths,
            "error": result.error,
            "status": "ok" if result.ok else "error",
            "engine_type": "nautilus",
            "used_nautilus": True,
        }
    raise ValueError(f"unknown task for format_result: {task}")


def run_research_report(
    symbol: str,
    *,
    use_mock: bool = False,
    use_llm: bool = False,
) -> dict[str, Any]:
    """Run research via command_registry; return report dict."""
    result = registry_run("research_symbol", symbol=symbol, use_mock=use_mock, use_llm=use_llm)
    return format_result("research_symbol", result, symbol=symbol)


def run_backtest_report(
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    use_mock: bool = False,
    use_llm: bool = False,
) -> dict[str, Any]:
    """Run backtest via command_registry; return report dict."""
    result = registry_run(
        "backtest_symbol",
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        use_mock=use_mock,
        use_llm=use_llm,
    )
    return format_result("backtest_symbol", result, symbol=symbol)


def run_demo_report(
    symbol: str,
    *,
    use_mock: bool = False,
    use_llm: bool = False,
) -> dict[str, Any]:
    """Run demo via command_registry; return report dict."""
    result = registry_run("run_demo", symbol=symbol, use_mock=use_mock, use_llm=use_llm)
    return format_result("run_demo", result, symbol=symbol)


def run_autonomous_paper_cycle_report(
    *,
    run_id: str = "",
    symbol_universe: list[str] | None = None,
    use_mock: bool = False,
    use_llm: bool = False,
    capital: float = 10_000.0,
    benchmark: str = "SPY",
    execute_paper: bool = True,
) -> dict[str, Any]:
    """OpenClaw agent 主入口：触发单周期 autonomous paper，返回结构化 JSON。"""
    result = registry_run(
        "autonomous_paper_cycle",
        run_id=run_id,
        symbol_universe=symbol_universe or ["NVDA"],
        use_mock=use_mock,
        use_llm=use_llm,
        capital=capital,
        benchmark=benchmark,
        execute_paper=execute_paper,
    )
    return format_result("autonomous_paper_cycle", result)


def run_weekly_paper_report(
    *,
    capital: float = 10_000.0,
    benchmark: str = "SPY",
    duration_days: int = 5,
    auto_confirm: bool = True,
    use_mock: bool = False,
    use_llm: bool = False,
    report_dir: Path | None = None,
) -> dict[str, Any]:
    """Run weekly autonomous paper via command_registry; return report dict."""
    if report_dir is None:
        report_dir = Path.cwd() / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    result = registry_run(
        "weekly_autonomous_paper",
        capital=capital,
        benchmark=benchmark,
        duration_days=duration_days,
        auto_confirm=auto_confirm,
        use_mock=use_mock,
        use_llm=use_llm,
        report_dir=report_dir,
    )
    return format_result("weekly_autonomous_paper", result)


def run_weekly_report_report(
    *,
    report_dir: Path | None = None,
) -> dict[str, Any]:
    """Read latest weekly report via command_registry; return report dict (no execution)."""
    result = registry_run("weekly_report", report_dir=report_dir or Path.cwd() / "reports")
    return format_result("weekly_report", result)
