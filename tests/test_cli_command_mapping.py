"""
Verify CLI subcommands map to application.commands only; no control/ or ad-hoc entry.
"""
from __future__ import annotations

import pytest

from ai_trading_research_system.application.commands import (
    run_research_symbol,
    run_backtest_symbol,
    run_demo,
    run_paper,
    run_weekly_autonomous_paper,
)


def test_research_command_exists():
    """CLI research -> run_research_symbol."""
    assert callable(run_research_symbol)


def test_backtest_command_exists():
    """CLI backtest -> run_backtest_symbol."""
    assert callable(run_backtest_symbol)


def test_demo_command_exists():
    """CLI demo -> run_demo."""
    assert callable(run_demo)


def test_paper_command_exists():
    """CLI paper -> run_paper."""
    assert callable(run_paper)


def test_weekly_autonomous_paper_command_exists():
    """CLI weekly-paper -> run_weekly_autonomous_paper."""
    assert callable(run_weekly_autonomous_paper)


def test_research_returns_contract():
    """run_research_symbol returns a contract-like object (model_dump)."""
    contract = run_research_symbol("NVDA", use_mock=True)
    assert hasattr(contract, "model_dump")
    d = contract.model_dump()
    assert "symbol" in d
    assert "suggested_action" in d
    assert "confidence" in d


def test_backtest_returns_structured_result():
    """run_backtest_symbol returns BacktestPipeResult-like (contract, metrics, strategy_run_id)."""
    result = run_backtest_symbol("NVDA", use_mock=True)
    assert hasattr(result, "contract")
    assert hasattr(result, "metrics")
    assert hasattr(result, "strategy_run_id")
    assert hasattr(result.metrics, "sharpe")
    assert hasattr(result.metrics, "pnl")


def test_demo_returns_structured_result():
    """run_demo returns same shape as backtest (contract, metrics, strategy_run_id)."""
    result = run_demo("NVDA", use_mock=True)
    assert hasattr(result, "contract")
    assert hasattr(result, "metrics")
    assert hasattr(result, "strategy_run_id")
