"""唯一用户入口 handle_trading_intent_sync：4 个用户动作经统一入口返回 status/summary/details。"""
from __future__ import annotations

from pathlib import Path

import pytest

from ai_trading_research_system.openclaw.bridge import handle_trading_intent_sync


def _check_unified_shape(out: dict) -> None:
    assert "status" in out
    assert "summary" in out
    assert "details" in out
    assert out.get("bridge_invoked") is True
    assert out.get("bridge_mode") == "sync"
    assert out["status"] in ("ok", "pending_confirmation", "no_proposal", "error")


def test_sync_start_build_position() -> None:
    """开始建仓：经统一入口返回 pending_confirmation 或 error，含 summary/details。"""
    config_path = Path(__file__).resolve().parent.parent / "configs" / "openclaw_agent.paper.yaml"
    if not config_path.exists():
        config_path = None
    out = handle_trading_intent_sync("开始建仓", config_path=str(config_path) if config_path else None)
    _check_unified_shape(out)
    assert out["intent"] == "start_build_position"
    assert out["status"] in ("pending_confirmation", "error")
    assert "本次请求已完成。" in out["summary"]


def test_sync_show_portfolio() -> None:
    """查看投资组合：经统一入口返回 ok 或 error。"""
    out = handle_trading_intent_sync("当前投资情况")
    _check_unified_shape(out)
    assert out["intent"] == "show_portfolio"
    assert out["status"] in ("ok", "error")
    assert "本次请求已完成。" in out["summary"]


def test_sync_review_latest_proposal() -> None:
    """查看最新建议：经统一入口返回 pending_confirmation / no_proposal / error。"""
    out = handle_trading_intent_sync("调仓建议")
    _check_unified_shape(out)
    assert out["intent"] == "review_latest_proposal"
    assert out["status"] in ("pending_confirmation", "no_proposal", "error")
    assert "本次请求已完成。" in out["summary"]


def test_sync_approve_execution() -> None:
    """确认执行：经统一入口返回 ok 或 error。"""
    out = handle_trading_intent_sync("确认执行")
    _check_unified_shape(out)
    assert out["intent"] == "approve_execution"
    assert out["status"] in ("ok", "error")
    assert "本次请求已完成。" in out["summary"]


def test_sync_unknown_intent_returns_error() -> None:
    """未知指令返回 status=error，不抛异常。"""
    out = handle_trading_intent_sync("随便说一句")
    _check_unified_shape(out)
    assert out["status"] == "error"
    assert out["intent"] == "unknown"
