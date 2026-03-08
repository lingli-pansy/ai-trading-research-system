"""
OpenClaw Agent Adapter: 稳定门面，将 OpenClaw 映射到 AutonomousTradingAgent。
不暴露 pipeline 细节；输入为 OpenClawAgentConfig，输出为结构化 summary。
OpenClaw agent 作为 proposal approver：approve_proposal(proposal, context) -> ApprovalDecision。
支持同步完成式用户交互：handle_trading_intent(message) -> 统一 { status, summary, details }，无 exec/poll。
"""
from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from ai_trading_research_system.agent.health import get_health
from ai_trading_research_system.agent.runtime import AutonomousTradingAgent, format_run_observability
from ai_trading_research_system.openclaw.config import OpenClawAgentConfig
from ai_trading_research_system.runtime.proposal import Proposal, ApprovalDecision
from ai_trading_research_system.state.experience_store import ExperienceStore, get_experience_store
from ai_trading_research_system.state.run_store import RunStore, get_run_store
from ai_trading_research_system.openclaw.prompts import build_approver_user_message


def build_approver_prompt_input(agent_context: dict[str, Any] | None) -> dict[str, Any]:
    """
    从 agent_context 构造 approver 联调用 prompt 输入，结构稳定，调用方无需再拼凑。
    仅包含审批所需字段，适合第一阶段联调。
    """
    ctx = agent_context or {}
    return {
        "portfolio_summary": ctx.get("portfolio_summary") or {},
        "risk_flags": list(ctx.get("risk_flags") or []),
        "proposal_summary": list(ctx.get("proposal_summary") or []),
        "approval_focus": list(ctx.get("approval_focus") or []),
        "recommendation": (ctx.get("recommendation") or "defer").lower(),
        "recommendation_reasons": list(ctx.get("recommendation_reasons") or []),
    }


def parse_approval_decision(text: str) -> str:
    """
    从 agent 原始输出解析出规范决策：approve | reject | defer。
    支持自然语言如 "I recommend approving this trade" -> "approve"。
    默认 fallback: "defer"。
    """
    if not text or not isinstance(text, str):
        return "defer"
    t = text.strip().lower()
    if not t:
        return "defer"
    # reject 优先（避免 "approve but reject risk" 被误判为 approve）
    if re.search(r"\breject(e[d])?\b", t) or "reject" in t:
        return "reject"
    if re.search(r"\bapprov(e|ed|ing)?\b", t) or "approve" in t or "approved" in t:
        return "approve"
    if re.search(r"\b(defer|hold|wait)\b", t) or "defer" in t or "hold" in t or "wait" in t:
        return "defer"
    return "defer"


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
        if isinstance(out, dict):
            raw = out.get("raw_agent_output") or out.get("decision") or ""
            parsed = parse_approval_decision(str(raw))
            out = dict(out)
            out["decision"] = parsed
            out["parsed_decision"] = parsed
            out["raw_agent_output"] = out.get("raw_agent_output") or raw
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
        "approval_focus": (agent_context or {}).get("approval_focus") or [],
        "top_opportunities": (agent_context or {}).get("top_opportunities") or [],
        "recommendation": (agent_context or {}).get("recommendation") or "defer",
        "recommendation_reasons": (agent_context or {}).get("recommendation_reasons") or [],
    }


def write_approver_prompt_artifacts(
    store: RunStore,
    run_id: str,
    prompt_input: dict[str, Any],
    user_message_text: str,
) -> dict[str, str]:
    """
    将联调用 prompt 输入与 user message 写入 runs/<run_id>/artifacts/，
    返回路径供 summary 展示。不修改 pipeline。
    """
    store.create_run(run_id)
    store.write_artifact(run_id, "approver_prompt_input", prompt_input)
    path_txt = store.run_dir(run_id) / "artifacts" / "approver_user_message.txt"
    path_txt.write_text(user_message_text, encoding="utf-8")
    return {
        "prompt_input_path": store.path_for_artifact(run_id, "approver_prompt_input"),
        "user_message_path": str(path_txt),
    }


def run_openclaw_approver_smoke(
    config: OpenClawAgentConfig,
    *,
    raw_agent_output: str | None = None,
) -> dict[str, Any]:
    """
    单轮联调脚手架：运行一次 proposal/recommendation 生成 → 构造 prompt input/user message
    → 写入 approver_prompt_input.json、approver_user_message.txt → 模拟/接入 approver 输出
    → parser → normalized decision，返回完整联调 summary。可不接真实 OpenClaw，用默认 mock 输出。
    """
    summary = run_openclaw_agent_once(config)
    run_id = summary.get("run_id", "")
    store = get_run_store(root=config.runs_root)
    agent_context = load_agent_context(run_id, config.runs_root)
    prompt_input = build_approver_prompt_input(agent_context)
    user_message_text = build_approver_user_message(prompt_input)
    paths = write_approver_prompt_artifacts(store, run_id, prompt_input, user_message_text)
    raw = raw_agent_output if raw_agent_output is not None else "approve"
    parsed = parse_approval_decision(raw)
    normalized = parsed
    return {
        "run_id": run_id,
        "proposal": summary.get("rebalance_summary") or [],
        "approval_focus": (agent_context or {}).get("approval_focus") or [],
        "recommendation": (agent_context or {}).get("recommendation") or "defer",
        "recommendation_reasons": (agent_context or {}).get("recommendation_reasons") or [],
        "prompt_input_path": paths["prompt_input_path"],
        "user_message_path": paths["user_message_path"],
        "raw_agent_output": raw,
        "parsed_decision": parsed,
        "normalized_decision": normalized,
        "ok": summary.get("ok", False),
    }


def format_approver_smoke_summary(smoke_result: dict[str, Any]) -> str:
    """联调 summary：一眼看出 agent 看到什么、回了什么、系统如何解释。"""
    proposal_lines = [str(x) for x in (smoke_result.get("proposal") or [])]
    focus_lines = [f"  {a.get('symbol', '')} score={a.get('score')} {a.get('allocator')}" for a in (smoke_result.get("approval_focus") or [])]
    reason_lines = [f"  - {r}" for r in (smoke_result.get("recommendation_reasons") or [])]
    lines = [
        "RUN_ID",
        smoke_result.get("run_id", ""),
        "PROPOSAL",
        *(proposal_lines if proposal_lines else ["(no proposal)"]),
        "APPROVAL_FOCUS",
        *(focus_lines if focus_lines else ["(none)"]),
        "RECOMMENDATION",
        smoke_result.get("recommendation", "defer"),
        *(reason_lines if reason_lines else ["(none)"]),
        "PROMPT_INPUT_PATH",
        smoke_result.get("prompt_input_path", ""),
        "USER_MESSAGE_PATH",
        smoke_result.get("user_message_path", ""),
        "RAW_AGENT_OUTPUT",
        smoke_result.get("raw_agent_output", ""),
        "PARSED_DECISION",
        smoke_result.get("parsed_decision", ""),
        "NORMALIZED_DECISION",
        smoke_result.get("normalized_decision", ""),
    ]
    return "\n".join(lines)


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


# ---------- 同步完成式 Intent：统一 status/summary/details，无 exec/poll ----------

IntentType = Literal["start_build_position", "show_portfolio", "review_latest_proposal", "approve_execution", "unknown"]
IntentStatus = Literal["ok", "error", "no_proposal", "pending_confirmation"]
DEFAULT_INTENT_TIMEOUT_SECONDS = 30


def _append_intent_audit(store: RunStore, intent_run_id: str, event: str, detail: dict[str, Any] | None = None) -> None:
    """写入 runs/<intent_run_id>/audit.json，用于 intent_received / intent_routed / handler_start / handler_complete / handler_error。"""
    store.create_run(intent_run_id)
    store.append_audit(intent_run_id, {"event": event, **(detail or {})})


def route_user_intent(message: str) -> IntentType:
    """
    根据用户消息识别意图。关键词：
    - 开始建仓 / 建仓 / 账户建仓 / start position -> start_build_position
    - 当前投资 / 组合 / portfolio -> show_portfolio
    - 调仓 / 建议 / rebalance -> review_latest_proposal
    - 确认 / 执行 / approve -> approve_execution
    """
    if not message or not isinstance(message, str):
        return "unknown"
    t = message.strip().lower()
    if not t:
        return "unknown"
    if any(k in t for k in ("开始建仓", "建仓", "账户建仓", "start position", "startposition")):
        return "start_build_position"
    if any(k in t for k in ("当前投资", "投资情况", "组合", "portfolio")):
        return "show_portfolio"
    if any(k in t for k in ("调仓", "建议", "rebalance", "有没有调仓")):
        return "review_latest_proposal"
    if any(k in t for k in ("确认", "执行", "approve", "确认执行")):
        return "approve_execution"
    return "unknown"


def _handler_start_build_position(
    *,
    config: OpenClawAgentConfig | None = None,
    runs_root: Path | None = None,
) -> dict[str, Any]:
    """同步：运行 autonomous_paper_cycle(proposal_only=True)，返回统一格式。"""
    from ai_trading_research_system.application.commands.run_autonomous_paper_cycle import run_autonomous_paper_cycle

    cfg = config or OpenClawAgentConfig()
    root = runs_root or cfg.runs_root
    run_id = f"run_{int(time.time())}"
    out = run_autonomous_paper_cycle(
        run_id=run_id,
        symbol_universe=cfg.symbols,
        use_mock=cfg.use_mock,
        use_llm=cfg.use_llm,
        capital=cfg.capital,
        benchmark=cfg.benchmark,
        execute_paper=False,
        runs_root=root,
        proposal_only=True,
    )
    store = get_run_store(root=root)
    agent_context = load_agent_context(run_id, runs_root=root)
    proposal = store.read_proposal(run_id) or {}
    return {
        "status": "pending_confirmation",
        "summary": "已生成投资组合方案",
        "details": {
            "run_id": run_id,
            "ok": out.ok,
            "proposal_summary": proposal.get("proposal_summary") or [],
            "rebalance_plan": proposal.get("rebalance_plan") or {},
            "recommendation": (agent_context or {}).get("recommendation") or "defer",
            "recommendation_reasons": (agent_context or {}).get("recommendation_reasons") or [],
            "approval_focus": (agent_context or {}).get("approval_focus") or [],
        },
    }


def _handler_show_portfolio(*, runs_root: Path | None = None) -> dict[str, Any]:
    """同步：读取最新 portfolio snapshot，返回统一格式。"""
    store = get_run_store(root=runs_root)
    state = store.get_latest_portfolio_state(use_mock=True)
    if not state:
        return {
            "status": "error",
            "summary": "无组合数据",
            "details": {"portfolio": {}},
        }
    return {
        "status": "ok",
        "summary": "当前组合",
        "details": {
            "portfolio": {
                "equity": state.get("equity"),
                "cash": state.get("cash"),
                "positions": state.get("positions") or [],
                "source": state.get("source", ""),
            },
        },
    }


def _handler_review_latest_proposal(*, runs_root: Path | None = None) -> dict[str, Any]:
    """同步：RunStore.get_latest_pending_approval_run()，返回统一格式。"""
    store = get_run_store(root=runs_root)
    pending = store.get_latest_pending_approval_run()
    if not pending:
        return {
            "status": "no_proposal",
            "summary": "暂无待审批的调仓建议",
            "details": {"proposal": None, "approval_focus": [], "recommendation": "defer"},
        }
    run_id = pending.get("run_id", "")
    proposal = pending.get("proposal") or {}
    agent_context = load_agent_context(run_id, runs_root=runs_root)
    return {
        "status": "pending_confirmation",
        "summary": "有待审批的调仓建议",
        "details": {
            "run_id": run_id,
            "proposal": proposal,
            "proposal_summary": proposal.get("proposal_summary") or [],
            "approval_focus": (agent_context or {}).get("approval_focus") or [],
            "recommendation": (agent_context or {}).get("recommendation") or "defer",
            "recommendation_reasons": (agent_context or {}).get("recommendation_reasons") or [],
        },
    }


def _handler_approve_execution(
    *,
    runs_root: Path | None = None,
    config: OpenClawAgentConfig | None = None,
) -> dict[str, Any]:
    """同步：写入 approval_decision(approve) 并执行 execution。"""
    from ai_trading_research_system.pipeline.autonomous_paper_cycle import run_execution_after_approval

    store = get_run_store(root=runs_root)
    pending = store.get_latest_pending_approval_run()
    if not pending:
        return {
            "status": "error",
            "summary": "暂无待确认的提案，请先「开始建仓」或查看「调仓建议」",
            "details": {},
        }
    run_id = pending.get("run_id", "")
    ts = datetime.now(timezone.utc).isoformat()
    store.write_approval_decision(run_id, {
        "run_id": run_id,
        "decision": "approve",
        "parsed_decision": "approve",
        "normalized_decision": "approve",
        "reviewer": "user_confirm",
        "reason": "user_confirm",
        "timestamp": ts,
        "raw_agent_output": "approve",
    })
    cfg = config or OpenClawAgentConfig()
    use_mock = cfg.use_mock if cfg else True
    results = run_execution_after_approval(run_id, store, use_mock=use_mock)
    executed = len([r for r in results if r.get("order_done")])
    trade_count = sum(int(r.get("trade_count", 0)) for r in results)
    return {
        "status": "ok",
        "summary": f"已执行，成交 {executed} 笔，共 {trade_count} 笔交易",
        "details": {"run_id": run_id, "executed_orders": executed, "trade_count": trade_count, "paper_results": results},
    }


def dispatch_trading_intent(
    message: str,
    *,
    config: OpenClawAgentConfig | None = None,
    runs_root: Path | None = None,
    timeout_seconds: float = DEFAULT_INTENT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    同步 intent dispatcher：解析 message -> route -> 调用 handler（带 timeout）-> 返回统一 { status, summary, details }。
    所有 handler 同步完成，不 spawn CLI。审计写入 runs/<intent_run_id>/audit.json。
    """
    cfg = config or OpenClawAgentConfig()
    root = runs_root or cfg.runs_root
    store = get_run_store(root=root)
    intent_run_id = f"intent_{int(time.time())}"
    _append_intent_audit(store, intent_run_id, "intent_received", {"message": message[:500]})

    intent = route_user_intent(message)
    _append_intent_audit(store, intent_run_id, "intent_routed", {"intent": intent})
    _append_intent_audit(store, intent_run_id, "handler_start", {"intent": intent})

    def run_handler() -> dict[str, Any]:
        if intent == "start_build_position":
            return _handler_start_build_position(config=cfg, runs_root=root)
        if intent == "show_portfolio":
            return _handler_show_portfolio(runs_root=root)
        if intent == "review_latest_proposal":
            return _handler_review_latest_proposal(runs_root=root)
        if intent == "approve_execution":
            return _handler_approve_execution(runs_root=root, config=cfg)
        return {
            "status": "error",
            "summary": "未识别的指令，请说：开始建仓 / 当前投资情况 / 调仓建议 / 确认执行",
            "details": {"intent": "unknown"},
        }

    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(run_handler)
            result = fut.result(timeout=timeout_seconds)
        _append_intent_audit(store, intent_run_id, "handler_complete", {"status": result.get("status"), "intent": intent})
        return {"intent_run_id": intent_run_id, **result}
    except FuturesTimeoutError:
        _append_intent_audit(store, intent_run_id, "handler_error", {"error": "operation timeout", "intent": intent})
        return {
            "status": "error",
            "summary": "operation timeout",
            "details": {"intent_run_id": intent_run_id, "intent": intent},
        }
    except Exception as e:
        _append_intent_audit(store, intent_run_id, "handler_error", {"error": str(e)[:200], "intent": intent})
        return {
            "status": "error",
            "summary": str(e)[:200] or "handler error",
            "details": {"intent_run_id": intent_run_id, "intent": intent},
        }


def handle_trading_intent(
    message: str,
    *,
    config: OpenClawAgentConfig | None = None,
    runs_root: Path | None = None,
    timeout_seconds: float = DEFAULT_INTENT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    单一 Python 入口：在 agent adapter 内直接调用 trading runtime，不构造 shell / exec / poll。
    返回统一格式 { status, summary, details }，供 agent 在一个响应内完成回复。
    """
    return dispatch_trading_intent(
        message,
        config=config,
        runs_root=runs_root,
        timeout_seconds=timeout_seconds,
    )


# 兼容旧调用方：保留同名函数，内部转调 _handler_* 并映射为旧格式（ok/message 等）
def handle_start_build_position(
    *,
    config: OpenClawAgentConfig | None = None,
    runs_root: Path | None = None,
) -> dict[str, Any]:
    r = _handler_start_build_position(config=config, runs_root=runs_root)
    return {"intent": "start_build_position", "ok": r["status"] == "pending_confirmation", "run_id": r["details"].get("run_id"), "proposal_summary": r["details"].get("proposal_summary", []), "rebalance_plan": r["details"].get("rebalance_plan", {}), "recommendation": r["details"].get("recommendation", "defer"), "recommendation_reasons": r["details"].get("recommendation_reasons", []), "approval_focus": r["details"].get("approval_focus", [])}


def handle_show_portfolio(*, runs_root: Path | None = None) -> dict[str, Any]:
    r = _handler_show_portfolio(runs_root=runs_root)
    return {"intent": "show_portfolio", "ok": r["status"] == "ok", "message": r["summary"] if r["status"] != "ok" else "", "portfolio": r["details"].get("portfolio", {})}


def handle_review_latest_proposal(*, runs_root: Path | None = None) -> dict[str, Any]:
    r = _handler_review_latest_proposal(runs_root=runs_root)
    d = r["details"]
    return {"intent": "review_latest_proposal", "ok": r["status"] in ("pending_confirmation", "ok"), "message": r["summary"] if r["status"] == "no_proposal" else "", "run_id": d.get("run_id"), "proposal": d.get("proposal"), "proposal_summary": d.get("proposal_summary", []), "approval_focus": d.get("approval_focus", []), "recommendation": d.get("recommendation", "defer"), "recommendation_reasons": d.get("recommendation_reasons", [])}


def handle_approve_execution(
    *,
    runs_root: Path | None = None,
    config: OpenClawAgentConfig | None = None,
) -> dict[str, Any]:
    r = _handler_approve_execution(runs_root=runs_root, config=config)
    d = r["details"]
    return {"intent": "approve_execution", "ok": r["status"] == "ok", "message": r["summary"] if r["status"] != "ok" else "", "run_id": d.get("run_id"), "executed_orders": d.get("executed_orders", 0), "trade_count": d.get("trade_count", 0), "paper_results": d.get("paper_results", [])}
