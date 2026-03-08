"""
OpenClaw workspace 唯一推荐入口：同步完成式桥接。
不经 shell，不拼命令；内部直接调用 dispatch_trading_intent，一次调用同步返回。
供 OpenClaw Agent 通过 Python API 调用，禁止 agent 输出 exec / process:poll / shell command。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_trading_research_system.openclaw.agent_adapter import dispatch_trading_intent
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
    - 返回统一格式：status / summary / details，并带 bridge_invoked、bridge_mode 便于确认走桥接。
    - summary 末尾统一追加「本次请求已完成。」作为完成信号。
    """
    config = None
    if config_path:
        config = OpenClawAgentConfig.load(Path(config_path))
    result = dispatch_trading_intent(
        (message or "").strip(),
        config=config,
        runs_root=config.runs_root if config else None,
        timeout_seconds=timeout_seconds,
    )
    summary = result.get("summary") or ""
    if summary and not summary.endswith("本次请求已完成。"):
        result = {**result, "summary": summary.rstrip() + " 本次请求已完成。"}
    result["bridge_invoked"] = True
    result["bridge_mode"] = "sync"
    from ai_trading_research_system.openclaw.agent_adapter import route_user_intent
    result["intent"] = route_user_intent(message)
    return result
