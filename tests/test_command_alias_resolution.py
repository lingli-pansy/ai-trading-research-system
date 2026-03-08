"""
Verify command_registry: alias → canonical resolution and dispatch.
All alias/canonical data comes from registry (single source); command_registry only uses resolve/run.
"""
from __future__ import annotations

import pytest

from ai_trading_research_system.application.command_registry import resolve, run
from ai_trading_research_system.openclaw.registry import get_aliases, get_canonical_commands


def test_resolve_research_alias_to_canonical():
    assert resolve("research") == "research_symbol"


def test_resolve_backtest_alias_to_canonical():
    assert resolve("backtest") == "backtest_symbol"


def test_resolve_demo_alias_to_canonical():
    assert resolve("demo") == "run_demo"


def test_resolve_weekly_paper_alias_to_canonical():
    assert resolve("weekly-paper") == "weekly_autonomous_paper"


def test_resolve_paper_alias_to_run_paper():
    assert resolve("paper") == "run_paper"


def test_resolve_canonical_unchanged():
    assert resolve("research_symbol") == "research_symbol"
    assert resolve("weekly_report") == "weekly_report"
    assert resolve("run_paper") == "run_paper"


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
    aliases = get_aliases()
    assert aliases["research"] == "research_symbol"
    assert aliases["backtest"] == "backtest_symbol"
    assert aliases["demo"] == "run_demo"
    assert aliases["weekly-paper"] == "weekly_autonomous_paper"
    assert aliases["paper"] == "run_paper"


def test_canonical_commands_include_run_paper():
    canonicals = get_canonical_commands()
    assert set(canonicals) >= {
        "research_symbol",
        "backtest_symbol",
        "run_demo",
        "run_paper",
        "weekly_autonomous_paper",
        "weekly_report",
    }
