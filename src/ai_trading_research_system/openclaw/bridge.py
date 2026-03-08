"""
薄桥：唯一用户入口。所有 4 个用户动作（开始建仓 / 查看投资组合 / 查看最新建议 / 确认执行）
均通过 handle_trading_intent_sync(message, config_path=None) 完成。
内部调用 dispatch_trading_intent，一次同步返回 { status, summary, details }。不经 shell，不拼命令。
summary 仅面向用户，禁止含 exec/poll/bridge/platform 等内部词；details 供调试。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_trading_research_system.openclaw.agent_adapter import (
    dispatch_trading_intent,
    route_user_intent,
    sanitize_summary_for_user,
)
from ai_trading_research_system.openclaw.config import OpenClawAgentConfig


def handle_trading_intent_sync(
    message: str,
    *,
    config_path: str | None = None,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """
    OpenClaw workspace 唯一推荐入口：同步桥接。
    - 内部直接调用 dispatch_trading_intent(...)，不经 shell，不拼命令字符串。
    - 返回统一格式：status / summary / details。summary 仅业务化用语，details 仅调试。
    - 异常或 bridge 不可用时，summary 只返回业务化失败提示，技术原因在 details。
    """
    intent = route_user_intent((message or "").strip())
    try:
        config = None
        if config_path:
            config = OpenClawAgentConfig.load(Path(config_path))
        result = dispatch_trading_intent(
            (message or "").strip(),
            config=config,
            runs_root=config.runs_root if config else None,
            timeout_seconds=timeout_seconds,
        )
    except Exception as e:
        return {
            "status": "error",
            "summary": "当前暂时无法完成该操作，请稍后再试。",
            "details": {"error": str(e)[:500], "intent": intent},
            "bridge_invoked": True,
            "bridge_mode": "sync",
            "intent": intent,
        }
    summary = result.get("summary") or ""
    status = result.get("status", "error")
    summary = sanitize_summary_for_user(summary, status)
    if status != "error" and summary and not summary.endswith("本次请求已完成。"):
        summary = summary.rstrip() + " 本次请求已完成。"
    result = {**result, "summary": summary}
    result["bridge_invoked"] = True
    result["bridge_mode"] = "sync"
    result["intent"] = intent
    return result
