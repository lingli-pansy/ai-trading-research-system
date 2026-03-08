"""
Structure constraint: control must not be used as entry by CLI, OpenClaw, or scripts.
"""
from __future__ import annotations

from pathlib import Path


def test_no_script_imports_control():
    """No script in scripts/ must import ai_trading_research_system.control."""
    root = Path(__file__).resolve().parents[1]
    scripts_dir = root / "scripts"
    if not scripts_dir.exists():
        return
    for path in scripts_dir.glob("*.py"):
        text = path.read_text()
        assert "ai_trading_research_system.control" not in text, f"{path.name} must not import control"


def test_cli_does_not_import_control():
    """presentation/cli.py must not import control."""
    root = Path(__file__).resolve().parents[1]
    cli_path = root / "src" / "ai_trading_research_system" / "presentation" / "cli.py"
    text = cli_path.read_text()
    assert "ai_trading_research_system.control" not in text
