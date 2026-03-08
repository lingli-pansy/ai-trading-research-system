"""
CLI renderers: turn command result objects into display lines or JSON dict.
No business logic; only formatting. CLI calls render(command, result, args) only.
"""
from __future__ import annotations

from typing import Any

# Return: list[str] for text output, dict for JSON output
RenderOutput = list[str] | dict[str, Any]


def render(command: str, result: Any, args: Any) -> RenderOutput:
    """Single entry: dispatch by command name. Returns lines or dict for JSON."""
    if command == "research":
        return result.model_dump()
    if command == "backtest":
        return render_backtest(result, getattr(args, "symbol", "NVDA"))
    if command == "paper":
        return render_paper(result)
    if command == "demo":
        return render_demo(result, getattr(args, "symbol", "NVDA"))
    if command == "weekly-paper":
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
    if command == "weekly_report":
        return {
            "ok": result.ok,
            "report_path": getattr(result, "report_path", ""),
            "mandate_id": getattr(result, "mandate_id", ""),
            "summary": getattr(result, "summary", {}),
        }
    return []


def render_backtest(result: Any, symbol: str) -> list[str]:
    """Format BacktestPipeResult as lines for CLI."""
    c = result.contract
    m = result.metrics
    return [
        "=== BACKTEST RESULT ===",
        f"symbol: {symbol}",
        f"contract action: {c.suggested_action} (confidence: {c.confidence})",
        f"sharpe: {m.sharpe:.4f}  max_drawdown: {m.max_drawdown:.4f}",
        f"win_rate: {m.win_rate:.4f}  pnl: {m.pnl:.2f}  trades: {m.trade_count}",
        f"strategy_run_id: {result.strategy_run_id}",
    ]


def render_paper(result: Any) -> list[str]:
    """Format PaperCommandResult as lines for CLI."""
    if result.paused:
        return ["Paper 已暂停：STOP_PAPER=1 或存在 .paper_stop（Kill Switch）"]
    header = "=== PAPER RESULT (IBKR) ===" if result.use_ibkr else "=== PAPER RESULT ==="
    lines = [
        header,
        f"symbol: {result.symbol}",
        f"contract: {result.contract_action} (confidence: {result.contract_confidence})",
        f"signal: {result.signal_action} size_fraction={result.allowed_position_size}",
        f"price: {result.price}",
    ]
    if result.order_done is not None:
        lines.append(f"order_done: {result.order_done} message: {result.message}")
        if result.order_result and hasattr(result.order_result, "status"):
            o = result.order_result
            lines.append(f"  order: {getattr(o, 'status', '')} qty={getattr(o, 'quantity', '')} price={getattr(o, 'price', '')}")
    return lines


def render_demo(result: Any, symbol: str) -> list[str]:
    """Format BacktestPipeResult as four-block demo output for CLI."""
    from ai_trading_research_system.strategy.translator import ContractTranslator

    contract = result.contract
    metrics = result.metrics
    signal = ContractTranslator().translate(contract)
    thesis = contract.thesis or ""
    thesis_preview = thesis[:400] + "..." if len(thesis) > 400 else thesis

    return [
        "=" * 60,
        "【1】研究结论",
        "=" * 60,
        f"thesis: {thesis_preview}",
        f"key_drivers: {contract.key_drivers}",
        f"confidence: {contract.confidence}  suggested_action: {contract.suggested_action}",
        f"time_horizon: {contract.time_horizon}",
        *([f"uncertainties: {contract.uncertainties}"] if contract.uncertainties else []),
        "",
        "=" * 60,
        "【2】策略生成",
        "=" * 60,
        f"action: {signal.action}  allowed_position_size: {signal.allowed_position_size}",
        f"rationale: {signal.rationale}",
        "",
        "=" * 60,
        "【3】回测结果",
        "=" * 60,
        f"sharpe: {metrics.sharpe:.4f}  max_drawdown: {metrics.max_drawdown:.4f}",
        f"win_rate: {metrics.win_rate:.4f}  pnl: {metrics.pnl:.2f}  trade_count: {metrics.trade_count}",
        "",
        "=" * 60,
        "【4】交易总结",
        "=" * 60,
        "执行引擎: NautilusTrader（回测 + Paper 默认主线）。",
        f"本轮研究+回测已写入 Experience Store，strategy_run_id={result.strategy_run_id}。",
        f"结论: {contract.suggested_action}（置信度 {contract.confidence}），策略信号 {signal.action}，回测 {metrics.trade_count} 笔，pnl={metrics.pnl:.2f}。",
    ]
