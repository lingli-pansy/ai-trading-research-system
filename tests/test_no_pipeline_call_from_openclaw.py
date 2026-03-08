"""
Structure constraint: OpenClaw adapter and run_for_openclaw must not import pipeline.
"""
from __future__ import annotations

import ast
from pathlib import Path


def _collect_imports(file_path: Path) -> list[str]:
    tree = ast.parse(file_path.read_text())
    mods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                mods.append(node.module)
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.append(alias.name)
    return mods


def test_openclaw_adapter_does_not_import_pipeline():
    """openclaw/adapter.py must not import pipeline."""
    root = Path(__file__).resolve().parents[1]
    path = root / "src" / "ai_trading_research_system" / "openclaw" / "adapter.py"
    assert path.exists()
    mods = _collect_imports(path)
    for m in mods:
        if "pipeline" in m:
            raise AssertionError(f"openclaw.adapter must not import pipeline, found: {m}")


def test_run_for_openclaw_does_not_import_pipeline():
    """scripts/run_for_openclaw.py must not import pipeline."""
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "run_for_openclaw.py"
    if not path.exists():
        return
    mods = _collect_imports(path)
    for m in mods:
        if "pipeline" in m:
            raise AssertionError(f"run_for_openclaw must not import pipeline, found: {m}")
