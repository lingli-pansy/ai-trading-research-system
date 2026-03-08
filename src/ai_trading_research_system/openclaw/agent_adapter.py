"""
OpenClaw Agent Adapter: 稳定门面，将 OpenClaw 映射到 AutonomousTradingAgent。
不暴露 pipeline 细节；输入为 OpenClawAgentConfig，输出为结构化 summary。
OpenClaw agent 作为 proposal approver：approve_proposal(proposal, context) -> ApprovalDecision。
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_trading_research_system.agent.health import get_health
from ai_trading_research_system.agent.runtime import AutonomousTradingAgent, format_run_observability
from ai_trading_research_system.openclaw.config import OpenClawAgentConfig
from ai_trading_research_system.runtime.proposal import Proposal, ApprovalDecision
from ai_trading_research_system.state.experience_store import ExperienceStore, get_experience_store
from ai_trading_research_system.state.run_store import RunStore, get_run_store


def approve_proposal(
    proposal: Proposal | dict[str, Any],
    context: dict[str, Any],
    *,
    approver: Callable[[dict[str, Any], dict[str, Any]], ApprovalDecision | dict[str, Any]] | None = None,
) -> ApprovalDecision:
    """
    OpenClaw agent 作为 proposal approver：根据 proposal 与 context 返回结构化 decision。
    context 至少包含：proposal_summary, risk_flags, recent_runs, portfolio_exposure（及可选 symbol 历史）。
    返回必须是 approve | reject | defer。
    approver 可选：若提供则调用 approver(proposal.to_dict(), context)，否则默认 approve。
    """
    prop_dict = proposal.to_dict() if isinstance(proposal, Proposal) else proposal
    run_id = str(prop_dict.get("run_id", ""))
    ts = datetime.now(timezone.utc).isoformat()
    if approver is not None:
        out = approver(prop_dict, context)
        if isinstance(out, ApprovalDecision):
            return out
        return ApprovalDecision.from_dict(out) or ApprovalDecision(
            run_id=run_id, decision="defer", reviewer="openclaw", reason="invalid_decision", timestamp=ts,
        )
    return ApprovalDecision(
        run_id=run_id,
        decision="approve",
        reviewer="openclaw_default",
        reason="no_approver",
        timestamp=ts,
    )


def load_agent_context(run_id: str, runs_root: Path | None = None) -> dict[str, Any] | None:
    """
    读取 runs/<run_id>/artifacts/agent_context.json，供 OpenClaw/LLM 审批时作为 prompt context。
    在调用 approval decision 前可调用此函数获取完整上下文。
    """
    store = get_run_store(root=runs_root)
    ctx = store.read_artifact(run_id, "agent_context")
    return ctx if isinstance(ctx, dict) else None


def create_openclaw_agent(config: OpenClawAgentConfig) -> AutonomousTradingAgent:
    """
    根据 OpenClawAgentConfig 创建 AutonomousTradingAgent 实例。
    OpenClaw 仅通过此接口与 config 使用 runtime，不直接依赖 pipeline。
    """
    return AutonomousTradingAgent(
        symbols=config.symbols,
        capital=config.capital,
        benchmark=config.benchmark,
        use_mock=config.use_mock,
        use_llm=config.use_llm,
        execute_paper=config.paper_enabled,
        runs_root=config.runs_root,
    )


def run_openclaw_agent_once(config: OpenClawAgentConfig) -> dict[str, Any]:
    """
    使用给定配置执行一次 autonomous trading run。
    返回结构化 summary，供 OpenClaw / CLI / 调试使用。
    """
    agent = create_openclaw_agent(config)
    summary = agent.run_once()
    store = get_run_store(root=config.runs_root)
    run_id = summary.get("run_id", "")
    run_path = str(store.run_dir(run_id)) if run_id else ""
    agent_context = load_agent_context(run_id, config.runs_root)

    # 结构化输出
    portfolio_before_summary: dict[str, Any] = {
        "value": summary.get("portfolio_before_value"),
    }
    portfolio_after_summary: dict[str, Any] = {
        "value": summary.get("portfolio_after_value"),
    }

    return {
        "run_id": summary.get("run_id", ""),
        "ok": summary.get("ok", False),
        "error": "" if summary.get("ok") else (summary.get("decision_summary") or "run_not_ok"),
        "decision_summary": summary.get("decision_summary", ""),
        "risk_flags": summary.get("risk_flags") or [],
        "order_intents_count": summary.get("order_intents_count", 0),
        "orders_executed": summary.get("executed_orders_count", 0),
        "trade_count": summary.get("trade_count", 0),
        "execution_status": summary.get("execution_status", ""),
        "portfolio_after_source": summary.get("portfolio_after_source", ""),
        "rebalance_summary": summary.get("rebalance_summary") or [],
        "portfolio_before": portfolio_before_summary,
        "portfolio_after": portfolio_after_summary,
        "write_paths": {"run_path": run_path},
        "run_path": run_path,
        "agent_name": config.name,
        "symbols": config.symbols,
        "approval_decision": summary.get("approval_decision", "") or "approve",
        "agent_context": agent_context,
    }


def build_openclaw_context_summary(
    *,
    runs_root: Path | None = None,
    recent_runs_n: int = 5,
    symbol_for_rebalance: str | None = None,
    rebalance_limit: int = 5,
) -> dict[str, Any]:
    """
    构建供 OpenClaw 使用的轻量上下文摘要：health + 最近 experience。
    不返回完整 experience.jsonl，仅 summary 级别信息。
    """
    store = get_run_store(root=runs_root)
    health = get_health(store)
    health_summary = {
        "last_success_run": health.last_success_run,
        "consecutive_failures": health.consecutive_failures,
        "current_state": health.current_state,
        "last_error": health.last_error[:200] if health.last_error else "",
    }

    exp_store: ExperienceStore = get_experience_store(root=runs_root)
    recent = exp_store.get_recent_runs(recent_runs_n)
    recent_summary = [
        {
            "run_id": r.get("run_id", ""),
            "timestamp": r.get("timestamp", ""),
            "symbols": r.get("symbols", []),
            "decision_summary": (r.get("decision_summary") or "")[:100],
        }
        for r in recent
    ]

    symbol_rebalance_summary: list[dict[str, Any]] = []
    if symbol_for_rebalance:
        rebalances = exp_store.get_recent_rebalances(symbol_for_rebalance, limit=rebalance_limit)
        symbol_rebalance_summary = [
            {
                "run_id": r.get("run_id", ""),
                "decision_summary": (r.get("decision_summary") or "")[:80],
            }
            for r in rebalances
        ]

    return {
        "health": health_summary,
        "recent_runs": recent_summary,
        "symbol_rebalance_summary": symbol_rebalance_summary,
    }


def format_openclaw_run_output(summary: dict[str, Any], *, include_context: bool = False) -> str:
    """
    将 run_openclaw_agent_once 的返回格式化为可读文本，供 CLI 打印。
    """
    lines = [
        f"AGENT {summary.get('agent_name', '')}",
        f"RUN {summary.get('run_id', '')}",
        f"SYMBOLS {summary.get('symbols', [])}",
        f"OK {summary.get('ok', False)}",
        f"DECISION {summary.get('decision_summary', '')}",
        f"RISK_FLAGS {summary.get('risk_flags', [])}",
        f"APPROVAL {summary.get('approval_decision', '') or 'approve'}",
        f"ORDER_INTENTS {summary.get('order_intents_count', 0)}",
        f"EXECUTED_ORDERS {summary.get('orders_executed', 0)}",
        f"TRADE_COUNT {summary.get('trade_count', 0)}",
        f"EXECUTION_STATUS {summary.get('execution_status', '')}",
        f"PORTFOLIO {summary.get('portfolio_before', {}).get('value')} -> {summary.get('portfolio_after', {}).get('value')} (after.source={summary.get('portfolio_after_source', '')})",
        f"RUN_PATH {summary.get('run_path', '')}",
    ]
    if summary.get("rebalance_summary"):
        lines.insert(4, "PROPOSAL " + " | ".join(str(x) for x in summary["rebalance_summary"]))
    if include_context:
        ctx = summary.get("context_summary")
        if ctx:
            lines.append("HEALTH " + str(ctx.get("health", {})))
            lines.append("RECENT_RUNS " + str(len(ctx.get("recent_runs", []))))
    return "\n".join(lines)
