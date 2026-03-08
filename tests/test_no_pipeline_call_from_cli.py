"""
Structure constraint: CLI must not import or call pipeline.
"""
from __future__ import annotations

import ast
from pathlib import Path


def test_cli_does_not_import_pipeline():
    """presentation/cli.py must not import pipeline."""
    root = Path(__file__).resolve().parents[1]
    cli_path = root / "src" / "ai_trading_research_system" / "presentation" / "cli.py"
    assert cli_path.exists()
    tree = ast.parse(cli_path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and "pipeline" in node.module:
                raise AssertionError(f"CLI must not import pipeline, found: {node.module}")
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "pipeline" in alias.name:
                    raise AssertionError(f"CLI must not import pipeline, found: {alias.name}")


def test_cli_imports_command_registry():
    """CLI must use command_registry for dispatch."""
    root = Path(__file__).resolve().parents[1]
    cli_path = root / "src" / "ai_trading_research_system" / "presentation" / "cli.py"
    text = cli_path.read_text()
    assert "command_registry" in text
    assert "application.command_registry" in text or "command_registry" in text
