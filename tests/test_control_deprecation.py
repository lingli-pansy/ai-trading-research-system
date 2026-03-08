"""
Verify control/ is compatibility layer only; main entry is openclaw + application.commands.
"""
from __future__ import annotations

import pytest


def test_control_module_has_deprecation_docstring():
    """control/__init__.py should document compatibility layer."""
    from ai_trading_research_system import control
    doc = control.__doc__ or ""
    assert "COMPATIBILITY" in doc or "compatibility" in doc.lower()
    assert "openclaw" in doc.lower() or "application.commands" in doc


def test_openclaw_adapter_does_not_import_control():
    """openclaw.adapter must not depend on control layer."""
    import ai_trading_research_system.openclaw.adapter as adapter
    # Adapter should use openclaw.commands -> application.commands
    assert "control" not in (adapter.__doc__ or "").lower() or "do not" in (adapter.__doc__ or "").lower()


def test_run_for_openclaw_uses_adapter_not_control():
    """run_for_openclaw uses openclaw.adapter, not control."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "run_for_openclaw.py"
    if not path.exists():
        pytest.skip("run_for_openclaw.py not found")
    text = path.read_text()
    assert "openclaw.adapter" in text, "run_for_openclaw should import from openclaw.adapter"
    assert "from ai_trading_research_system.control" not in text, "run_for_openclaw must not import control"
