"""唯一用户入口 handle_trading_intent_sync：4 个用户动作经统一入口返回 status/summary/details。"""
from __future__ import annotations

from pathlib import Path

import pytest

from ai_trading_research_system.openclaw.bridge import handle_trading_intent_sync
from ai_trading_research_system.openclaw.agent_adapter import (
    FORBIDDEN_SUMMARY_TOKENS,
    route_user_intent,
)


def _check_unified_shape(out: dict) -> None:
    assert "status" in out
    assert "summary" in out
    assert "details" in out
    assert out.get("bridge_invoked") is True
    assert out.get("bridge_mode") == "sync"
    assert out["status"] in ("ok", "pending_confirmation", "no_proposal", "error")


def _assert_summary_no_internal_leak(summary: str) -> None:
    """summary 不得包含内部实现相关词。"""
    lower = (summary or "").lower()
    for token in FORBIDDEN_SUMMARY_TOKENS:
        assert token.lower() not in lower, f"summary 不得包含 {token!r}: {summary[:200]}"


def test_sync_start_build_position() -> None:
    """开始建仓：经统一入口返回 pending_confirmation 或 error，含 summary/details。"""
    config_path = Path(__file__).resolve().parent.parent / "configs" / "openclaw_agent.paper.yaml"
    if not config_path.exists():
        config_path = None
    out = handle_trading_intent_sync("开始建仓", config_path=str(config_path) if config_path else None)
    _check_unified_shape(out)
    assert out["intent"] == "start_build_position"
    assert out["status"] in ("pending_confirmation", "error")
    if out["status"] != "error":
        assert "本次请求已完成。" in out["summary"]
    _assert_summary_no_internal_leak(out["summary"])


def test_sync_show_portfolio() -> None:
    """查看投资组合：经统一入口返回 ok 或 error。"""
    out = handle_trading_intent_sync("当前投资情况")
    _check_unified_shape(out)
    assert out["intent"] == "show_portfolio"
    assert out["status"] in ("ok", "error")
    if out["status"] != "error":
        assert "本次请求已完成。" in out["summary"]
    _assert_summary_no_internal_leak(out["summary"])


def test_sync_review_latest_proposal() -> None:
    """查看最新建议：经统一入口返回 pending_confirmation / no_proposal / error。"""
    out = handle_trading_intent_sync("调仓建议")
    _check_unified_shape(out)
    assert out["intent"] == "review_latest_proposal"
    assert out["status"] in ("pending_confirmation", "no_proposal", "error")
    if out["status"] != "error":
        assert "本次请求已完成。" in out["summary"]
    _assert_summary_no_internal_leak(out["summary"])


def test_sync_approve_execution() -> None:
    """确认执行：经统一入口返回 ok 或 error。"""
    out = handle_trading_intent_sync("确认执行")
    _check_unified_shape(out)
    assert out["intent"] == "approve_execution"
    assert out["status"] in ("ok", "error")
    if out["status"] != "error":
        assert "本次请求已完成。" in out["summary"]
    _assert_summary_no_internal_leak(out["summary"])


def test_summary_never_contains_internal_tokens() -> None:
    """任意入口返回的 summary 均不包含 exec/poll/bridge/platform 等内部词。"""
    for msg in ("开始建仓", "当前投资情况", "调仓建议", "确认执行", "随便说一句"):
        out = handle_trading_intent_sync(msg)
        _assert_summary_no_internal_leak(out["summary"])


def test_sync_unknown_intent_returns_error() -> None:
    """未知指令返回 status=error，不抛异常；summary 不包含内部实现词。"""
    out = handle_trading_intent_sync("随便说一句")
    _check_unified_shape(out)
    assert out["status"] == "error"
    assert out["intent"] == "unknown"
    _assert_summary_no_internal_leak(out["summary"])


def test_bridge_exception_returns_business_summary() -> None:
    """bridge 不可用（如 config 加载失败）时，summary 仅业务化提示，技术原因在 details。"""
    out = handle_trading_intent_sync("开始建仓", config_path="/nonexistent/openclaw.yaml")
    _check_unified_shape(out)
    assert out["status"] == "error"
    _assert_summary_no_internal_leak(out["summary"])
    assert "请稍后再试" in out["summary"] or "无法" in out["summary"]
    assert "details" in out and ("error" in out["details"] or "intent" in out["details"])


def test_intent_router_natural_language() -> None:
    """自然语言稳定路由到 4 类意图。"""
    assert route_user_intent("开始建仓") == "start_build_position"
    assert route_user_intent("建仓") == "start_build_position"
    assert route_user_intent("账户建仓") == "start_build_position"
    assert route_user_intent("查看投资组合") == "show_portfolio"
    assert route_user_intent("查看持仓") == "show_portfolio"
    assert route_user_intent("当前投资情况") == "show_portfolio"
    assert route_user_intent("查看最新建议") == "review_latest_proposal"
    assert route_user_intent("调仓建议") == "review_latest_proposal"
    assert route_user_intent("最近有没有调仓建议") == "review_latest_proposal"
    assert route_user_intent("确认执行") == "approve_execution"
    assert route_user_intent("确认") == "approve_execution"
    assert route_user_intent("执行") == "approve_execution"
    assert route_user_intent("随便说一句") == "unknown"
    assert route_user_intent("") == "unknown"
