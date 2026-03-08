"""
Registry as single source of truth: command metadata, alias resolution, OpenClaw vs command_registry consistency.
"""
from __future__ import annotations

from ai_trading_research_system.openclaw.registry import (
    get_all_metadata,
    get_canonical_commands,
    get_canonical_commands_for_openclaw,
    get_aliases,
    resolve,
    get_metadata,
    get_cli_subcommand_names,
)
from ai_trading_research_system.application.command_registry import (
    command_names,
    cli_command_names,
    run,
)


def test_registry_single_source_of_truth():
    """All command metadata lives in registry: canonical, aliases, handler_target, expose_for_openclaw."""
    meta = get_all_metadata()
    assert len(meta) >= 6
    required_keys = {"canonical", "aliases", "description", "input_schema", "output_schema", "example", "handler_target", "needs_report_dir", "expose_for_openclaw"}
    for m in meta:
        assert required_keys.issubset(m.keys()), f"missing keys in {m.get('canonical')}"
    canonicals = [m["canonical"] for m in meta]
    assert "run_paper" in canonicals
    assert "research_symbol" in canonicals
    assert "weekly_report" in canonicals


def test_alias_resolution_for_all_commands():
    """Every alias resolves to its canonical; every canonical resolves to itself."""
    aliases = get_aliases()
    canonicals = get_canonical_commands()
    for alias, canonical in aliases.items():
        assert resolve(alias) == canonical
    for c in canonicals:
        assert resolve(c) == c
    # All CLI names (alias or canonical) must resolve to a known canonical
    for name in get_cli_subcommand_names():
        resolved = resolve(name)
        assert resolved in canonicals


def test_paper_command_is_canonicalized():
    """paper is alias for canonical run_paper; run_paper is in registry with expose_for_openclaw=False."""
    assert resolve("paper") == "run_paper"
    meta = get_metadata("run_paper")
    assert meta is not None
    assert meta["canonical"] == "run_paper"
    assert "paper" in meta["aliases"]
    assert meta.get("expose_for_openclaw") is False
    # Dispatch works
    result = run("paper", symbol="NVDA", use_mock=True, project_root=None)
    assert hasattr(result, "paused")
    assert hasattr(result, "symbol")


def test_openclaw_registry_matches_command_registry():
    """OpenClaw skill list is subset of full canonical list; command_registry can run any canonical."""
    openclaw_commands = set(get_canonical_commands_for_openclaw())
    all_canonicals = set(get_canonical_commands())
    assert openclaw_commands <= all_canonicals
    assert "run_paper" not in openclaw_commands
    assert "run_paper" in all_canonicals
    # Every name command_registry accepts (command_names()) is either canonical or alias from registry
    registry_accepts = set(command_names())
    for c in all_canonicals:
        assert c in registry_accepts
    for alias in get_aliases():
        assert alias in registry_accepts
    # CLI subcommand names match what we expect (aliases + canonical for no-alias commands)
    cli_names = set(cli_command_names())
    assert "paper" in cli_names
    assert "research" in cli_names
    assert "weekly_report" in cli_names
