"""
Verify command_registry: alias → canonical resolution and dispatch.
"""
from __future__ import annotations

import pytest

from ai_trading_research_system.application.command_registry import (
    resolve,
    run,
    ALIASES,
    CANONICAL_COMMANDS,
)


def test_resolve_research_alias_to_canonical():
    assert resolve("research") == "research_symbol"


def test_resolve_backtest_alias_to_canonical():
    assert resolve("backtest") == "backtest_symbol"


def test_resolve_demo_alias_to_canonical():
    assert resolve("demo") == "run_demo"


def test_resolve_weekly_paper_alias_to_canonical():
    assert resolve("weekly-paper") == "weekly_autonomous_paper"


def test_resolve_canonical_unchanged():
    assert resolve("research_symbol") == "research_symbol"
    assert resolve("weekly_report") == "weekly_report"


def test_run_research_alias_dispatches_to_research_symbol():
    result = run("research", symbol="NVDA", use_mock=True)
    assert hasattr(result, "model_dump")
    d = result.model_dump()
    assert "suggested_action" in d
    assert "confidence" in d


def test_run_backtest_alias_dispatches_to_backtest_symbol():
    result = run("backtest", symbol="NVDA", use_mock=True)
    assert hasattr(result, "contract")
    assert hasattr(result, "metrics")


def test_unknown_command_raises():
    with pytest.raises(ValueError, match="unknown command"):
        run("unknown_cmd")


def test_aliases_mapping():
    assert ALIASES["research"] == "research_symbol"
    assert ALIASES["backtest"] == "backtest_symbol"
    assert ALIASES["demo"] == "run_demo"
    assert ALIASES["weekly-paper"] == "weekly_autonomous_paper"


def test_canonical_commands_include_all_five():
    assert set(CANONICAL_COMMANDS) >= {
        "research_symbol",
        "backtest_symbol",
        "run_demo",
        "weekly_autonomous_paper",
        "weekly_report",
    }
