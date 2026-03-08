"""OpenClaw agent adapter: config 加载、run_once 结构化输出、context summary。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_trading_research_system.openclaw.config import OpenClawAgentConfig, export_example_config_yaml
from ai_trading_research_system.openclaw.agent_adapter import (
    create_openclaw_agent,
    run_openclaw_agent_once,
    build_openclaw_context_summary,
    build_approver_prompt_input,
    parse_approval_decision,
)


def test_parse_approval_decision() -> None:
    """自然语言与变体均解析为 approve | reject | defer，默认 fallback defer。"""
    assert parse_approval_decision("approve") == "approve"
    assert parse_approval_decision("approved") == "approve"
    assert parse_approval_decision("yes approve") == "approve"
    assert parse_approval_decision("decision: approve") == "approve"
    assert parse_approval_decision("I recommend approving this trade") == "approve"
    assert parse_approval_decision("reject") == "reject"
    assert parse_approval_decision("rejected") == "reject"
    assert parse_approval_decision("decision: reject") == "reject"
    assert parse_approval_decision("defer") == "defer"
    assert parse_approval_decision("hold") == "defer"
    assert parse_approval_decision("wait") == "defer"
    assert parse_approval_decision("") == "defer"
    assert parse_approval_decision("unknown text") == "defer"


def test_approver_integration_smoke_prompt_input_to_normalized_decision() -> None:
    """
    联调 smoke：给定最小 agent_context + recommendation，当 approver 输出自然语言时，
    系统能稳定得到 normalized decision。不调 LLM，只测 prompt input -> parser -> normalized。
    """
    minimal_agent_context = {
        "portfolio_summary": {"equity": 100000, "cash": 5000, "positions": {"SPY": 0.5}},
        "risk_flags": [],
        "proposal_summary": ["NVDA ADD 0.05"],
        "approval_focus": [{"symbol": "NVDA", "score": 0.88, "allocator": "probe", "one_line_reason": "score high"}],
        "recommendation": "approve",
        "recommendation_reasons": ["no risk flags", "approval_focus available"],
    }
    prompt_input = build_approver_prompt_input(minimal_agent_context)
    assert "portfolio_summary" in prompt_input
    assert "risk_flags" in prompt_input
    assert "proposal_summary" in prompt_input
    assert "approval_focus" in prompt_input
    assert "recommendation" in prompt_input
    assert "recommendation_reasons" in prompt_input
    assert prompt_input["recommendation"] == "approve"

    raw_outputs = [
        "I recommend approving this trade",
        "approve",
        "We should reject due to risk",
        "reject",
        "hold for now",
        "defer",
    ]
    expected = ["approve", "approve", "reject", "reject", "defer", "defer"]
    for raw, exp in zip(raw_outputs, expected):
        normalized = parse_approval_decision(raw)
        assert normalized == exp, f"raw={raw!r} -> {normalized}, expected {exp}"


def test_config_from_dict_defaults() -> None:
    c = OpenClawAgentConfig.from_dict({})
    assert c.name == "openclaw-paper"
    assert c.symbols == ["NVDA"]
    assert c.capital == 10_000.0
    assert c.paper_enabled is True
    assert c.use_mock is True


def test_config_from_dict_custom() -> None:
    c = OpenClawAgentConfig.from_dict({
        "name": "my-agent",
        "symbols": ["SPY", "NVDA"],
        "capital": 20_000,
        "interval_seconds": 60,
        "stop_after_consecutive_failures": 3,
    })
    assert c.name == "my-agent"
    assert c.symbols == ["SPY", "NVDA"]
    assert c.capital == 20_000.0
    assert c.interval_seconds == 60.0
    assert c.stop_after_consecutive_failures == 3


def test_config_load_yaml(tmp_path: Path) -> None:
    yaml_path = tmp_path / "agent.yaml"
    yaml_path.write_text("""
name: test-agent
symbols: [SPY, QQQ]
capital: 5000
""", encoding="utf-8")
    c = OpenClawAgentConfig.load(yaml_path)
    assert c.name == "test-agent"
    assert c.symbols == ["SPY", "QQQ"]
    assert c.capital == 5000.0


def test_config_load_json(tmp_path: Path) -> None:
    json_path = tmp_path / "agent.json"
    json.dump({"name": "json-agent", "symbols": ["NVDA"], "capital": 15000}, open(json_path, "w", encoding="utf-8"))
    c = OpenClawAgentConfig.load(json_path)
    assert c.name == "json-agent"
    assert c.capital == 15000.0


def test_create_openclaw_agent() -> None:
    config = OpenClawAgentConfig(symbols=["SPY"], capital=5000.0)
    agent = create_openclaw_agent(config)
    assert agent.symbols == ["SPY"]
    assert agent.capital == 5000.0
    assert agent.use_mock is True


def test_run_openclaw_agent_once_returns_structured_summary(tmp_path: Path) -> None:
    config = OpenClawAgentConfig(
        name="smoke",
        symbols=["NVDA"],
        capital=10_000.0,
        use_mock=True,
        paper_enabled=True,
        runs_root=tmp_path,
    )
    summary = run_openclaw_agent_once(config)
    assert "run_id" in summary
    assert "ok" in summary
    assert "decision_summary" in summary
    assert "risk_flags" in summary
    assert "orders_executed" in summary
    assert "portfolio_before" in summary
    assert "portfolio_after" in summary
    assert "write_paths" in summary
    assert "run_path" in summary
    assert "agent_name" in summary
    assert summary["agent_name"] == "smoke"
    assert isinstance(summary["risk_flags"], list)


def test_build_openclaw_context_summary(tmp_path: Path) -> None:
    ctx = build_openclaw_context_summary(runs_root=tmp_path, recent_runs_n=3)
    assert "health" in ctx
    assert "last_success_run" in ctx["health"] or "consecutive_failures" in ctx["health"]
    assert "recent_runs" in ctx
    assert "symbol_rebalance_summary" in ctx
    assert isinstance(ctx["recent_runs"], list)


def test_example_config_yaml_loadable_from_repo() -> None:
    """示例配置文件 configs/openclaw_agent.paper.yaml 可被加载。"""
    root = Path(__file__).resolve().parent.parent
    path = root / "configs" / "openclaw_agent.paper.yaml"
    if not path.exists():
        pytest.skip("configs/openclaw_agent.paper.yaml not found")
    c = OpenClawAgentConfig.load(path)
    assert c.name
    assert len(c.symbols) >= 1
    assert c.capital > 0
    assert c.paper_enabled is True
