"""
Verify control/ is not used as entry; entry is command_registry + openclaw.adapter.
"""
from __future__ import annotations

import pytest


def test_control_package_removed():
    """control package must be removed; no longer an entry."""
    with pytest.raises(ModuleNotFoundError):
        import ai_trading_research_system.control  # noqa: F401


def test_run_for_openclaw_uses_registry_and_command_registry():
    """run_for_openclaw must use registry (skill names) and command_registry, not control."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "run_for_openclaw.py"
    if not path.exists():
        pytest.skip("run_for_openclaw.py not found")
    text = path.read_text()
    assert "openclaw.registry" in text
    assert "command_registry" in text
    assert "from ai_trading_research_system.control" not in text
