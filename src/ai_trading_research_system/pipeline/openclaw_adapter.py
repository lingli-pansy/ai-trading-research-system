"""
OpenClaw adapter: run research or research+backtest and return a structured report (JSON-serializable).
OpenClaw can invoke this via CLI (run_for_openclaw.py) or import and call run_research_report / run_backtest_report.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any


@dataclass
class ResearchReport:
    """Report for research-only task."""
    task: str  # "research"
    symbol: str
    completed_at: str  # ISO
    contract_action: str
    contract_confidence: str
    thesis_snippet: str
    raw_contract: dict[str, Any]
    engine_type: str = "nautilus"
    status: str = "ok"
    reason: str = ""


@dataclass
class BacktestReport:
    """Report for research + backtest task."""
    task: str  # "backtest"
    symbol: str
    completed_at: str
    contract_action: str
    contract_confidence: str
    thesis_snippet: str
    sharpe: float
    max_drawdown: float
    win_rate: float
    pnl: float
    trade_count: int
    strategy_run_id: int
    raw_contract: dict[str, Any]
    engine_type: str = "nautilus"
    used_nautilus: bool = True
    status: str = "ok"  # "ok" | "no_trade"
    reason: str = ""   # e.g. "wait_confirmation"


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
    from ai_trading_research_system.research.orchestrator import ResearchOrchestrator

    orchestrator = ResearchOrchestrator(use_mock=use_mock, use_llm=use_llm)
    contract = orchestrator.run(symbol)
    dump = _json_safe_contract_dump(contract)
    report = ResearchReport(
        task="research",
        symbol=symbol,
        completed_at=datetime.utcnow().isoformat() + "Z",
        contract_action=contract.suggested_action,
        contract_confidence=contract.confidence,
        thesis_snippet=(contract.thesis or "")[:200],
        raw_contract=dump,
        engine_type="nautilus",
        status="ok",
        reason="",
    )
    return asdict(report)


def run_backtest_report(
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    use_mock: bool = False,
    use_llm: bool = False,
) -> dict[str, Any]:
    """Run research + backtest + store; return report dict (JSON-serializable)."""
    from ai_trading_research_system.pipeline.backtest_pipe import run as run_pipe

    result = run_pipe(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        use_mock=use_mock,
        use_llm=use_llm,
    )
    dump = _json_safe_contract_dump(result.contract)
    status = "no_trade" if result.metrics.trade_count == 0 else "ok"
    reason = "wait_confirmation" if result.metrics.trade_count == 0 else ""
    report = BacktestReport(
        task="backtest",
        symbol=symbol,
        completed_at=datetime.utcnow().isoformat() + "Z",
        contract_action=result.contract.suggested_action,
        contract_confidence=result.contract.confidence,
        thesis_snippet=(result.contract.thesis or "")[:200],
        sharpe=result.metrics.sharpe,
        max_drawdown=result.metrics.max_drawdown,
        win_rate=result.metrics.win_rate,
        pnl=result.metrics.pnl,
        trade_count=result.metrics.trade_count,
        strategy_run_id=result.strategy_run_id,
        raw_contract=dump,
        engine_type="nautilus",
        used_nautilus=True,
        status=status,
        reason=reason,
    )
    return asdict(report)


def run_demo_report(
    symbol: str,
    *,
    use_mock: bool = False,
    use_llm: bool = False,
) -> dict[str, Any]:
    """Run E2E demo (research → strategy → backtest → store); return report dict with four blocks for Skill/OpenClaw."""
    from ai_trading_research_system.pipeline.backtest_pipe import run as run_pipe
    from ai_trading_research_system.strategy.translator import ContractTranslator

    result = run_pipe(symbol=symbol, start_date=None, end_date=None, use_mock=use_mock, use_llm=use_llm)
    contract = result.contract
    signal = ContractTranslator().translate(contract)
    dump = _json_safe_contract_dump(contract)
    status = "no_trade" if result.metrics.trade_count == 0 else "ok"
    reason = "wait_confirmation" if result.metrics.trade_count == 0 else ""
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
    use_mock: bool = True,
    use_llm: bool = False,
) -> dict[str, Any]:
    """UC-09: Weekly autonomous paper. Returns JSON for OpenClaw (ok, mandate_id, status, report_path, summary)."""
    from ai_trading_research_system.pipeline.weekly_paper_pipe import run_weekly_autonomous_paper
    from pathlib import Path
    report_dir = Path.cwd() / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    result = run_weekly_autonomous_paper(
        capital=capital,
        benchmark=benchmark,
        duration_days=duration_days,
        auto_confirm=auto_confirm,
        use_mock=use_mock,
        use_llm=use_llm,
        report_dir=report_dir,
    )
    return {
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
