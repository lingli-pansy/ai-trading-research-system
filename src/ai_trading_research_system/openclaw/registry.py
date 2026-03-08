"""
Command/skill metadata single source of truth.
All command info: canonical name, aliases, description, input/output schema, example, handler_target, needs_report_dir, expose_for_openclaw.
Alias → canonical resolution is implemented only here; command_registry and CLI use resolve() from this module.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_trading_research_system.openclaw.contract import (
    ResearchSymbolInput,
    BacktestSymbolInput,
    RunDemoInput,
    RunPaperInput,
    WeeklyAutonomousPaperInput,
    WeeklyReportInput,
    AutonomousPaperCycleInput,
    ResearchSymbolOutput,
    BacktestSymbolOutput,
    RunDemoOutput,
    RunPaperOutput,
    WeeklyAutonomousPaperOutput,
    WeeklyReportOutput,
    AutonomousPaperCycleOutput,
)

# Full metadata per command. handler_target = application.commands function name.
_COMMAND_METADATA: list[dict[str, Any]] = [
    {
        "canonical": "research_symbol",
        "aliases": ["research"],
        "description": "对标的做研究，返回 DecisionContract",
        "input_schema": ResearchSymbolInput.model_json_schema(),
        "output_schema": ResearchSymbolOutput.model_json_schema(),
        "example": {"command": "research_symbol", "symbol": "NVDA"},
        "handler_target": "run_research_symbol",
        "needs_report_dir": False,
        "expose_for_openclaw": True,
    },
    {
        "canonical": "backtest_symbol",
        "aliases": ["backtest"],
        "description": "对标的做研究 + 回测 + 写入 Experience Store",
        "input_schema": BacktestSymbolInput.model_json_schema(),
        "output_schema": BacktestSymbolOutput.model_json_schema(),
        "example": {"command": "backtest_symbol", "symbol": "NVDA", "start_date": None, "end_date": None},
        "handler_target": "run_backtest_symbol",
        "needs_report_dir": False,
        "expose_for_openclaw": True,
    },
    {
        "canonical": "run_demo",
        "aliases": ["demo"],
        "description": "E2E 演示：研究 → 策略 → 回测 → 总结",
        "input_schema": RunDemoInput.model_json_schema(),
        "output_schema": RunDemoOutput.model_json_schema(),
        "example": {"command": "run_demo", "symbol": "NVDA"},
        "handler_target": "run_demo",
        "needs_report_dir": False,
        "expose_for_openclaw": True,
    },
    {
        "canonical": "run_paper",
        "aliases": ["paper"],
        "description": "Research → Contract → Paper inject (once or runner). Deprecated for agent: use autonomous_paper_cycle.",
        "input_schema": RunPaperInput.model_json_schema(),
        "output_schema": RunPaperOutput.model_json_schema(),
        "example": {"command": "run_paper", "symbol": "NVDA", "once": False},
        "handler_target": "run_paper",
        "needs_report_dir": False,
        "expose_for_openclaw": False,
    },
    {
        "canonical": "autonomous_paper_cycle",
        "aliases": ["paper_cycle", "paper-cycle"],
        "description": "OpenClaw agent 主入口：单周期 autonomous paper（读组合→研究→规则/风控→决策→订单意图/执行→落盘）",
        "input_schema": AutonomousPaperCycleInput.model_json_schema(),
        "output_schema": AutonomousPaperCycleOutput.model_json_schema(),
        "example": {"command": "autonomous_paper_cycle", "run_id": "run_001", "symbol_universe": ["NVDA"], "use_mock": True},
        "handler_target": "run_autonomous_paper_cycle",
        "needs_report_dir": False,
        "expose_for_openclaw": True,
    },
    {
        "canonical": "weekly_autonomous_paper",
        "aliases": ["weekly-paper"],
        "description": "UC-09 一周自治 Paper：mandate → snapshot → 多轮 research/allocator/paper → benchmark → 周报",
        "input_schema": WeeklyAutonomousPaperInput.model_json_schema(),
        "output_schema": WeeklyAutonomousPaperOutput.model_json_schema(),
        "example": {"command": "weekly_autonomous_paper", "capital": 10000, "benchmark": "SPY", "duration": 5},
        "handler_target": "run_weekly_autonomous_paper",
        "needs_report_dir": True,
        "expose_for_openclaw": True,
    },
    {
        "canonical": "weekly_report",
        "aliases": [],
        "description": "读取已有周报或生成报告摘要；与 UC-09 execution 分离，仅报告",
        "input_schema": WeeklyReportInput.model_json_schema(),
        "output_schema": WeeklyReportOutput.model_json_schema(),
        "example": {"command": "weekly_report", "report_dir": None},
        "handler_target": "run_weekly_report",
        "needs_report_dir": True,
        "expose_for_openclaw": True,
    },
]

# Built once: alias -> canonical (only place that defines alias resolution)
_ALIAS_MAP: dict[str, str] = {}
for _m in _COMMAND_METADATA:
    for _a in _m["aliases"]:
        _ALIAS_MAP[_a] = _m["canonical"]

_CANONICAL_BY_TARGET: dict[str, dict[str, Any]] = {_m["canonical"]: _m for _m in _COMMAND_METADATA}


def resolve(command: str) -> str:
    """Resolve alias to canonical. Single implementation; CLI and run_for_openclaw must not duplicate."""
    return _ALIAS_MAP.get(command, command)


def get_all_metadata() -> list[dict[str, Any]]:
    """All command metadata (single source of truth)."""
    return list(_COMMAND_METADATA)


def get_canonical_commands() -> list[str]:
    """All canonical command names in registry order."""
    return [_m["canonical"] for _m in _COMMAND_METADATA]


def get_canonical_commands_for_openclaw() -> list[str]:
    """Canonical commands exposed to OpenClaw (expose_for_openclaw=True)."""
    return [_m["canonical"] for _m in _COMMAND_METADATA if _m.get("expose_for_openclaw", True)]


def get_aliases() -> dict[str, str]:
    """Alias -> canonical mapping (read-only)."""
    return dict(_ALIAS_MAP)


def get_metadata(canonical: str) -> dict[str, Any] | None:
    """Metadata for one canonical command, or None."""
    return _CANONICAL_BY_TARGET.get(canonical)


def get_cli_subcommand_names() -> list[str]:
    """Names to use as CLI subcommands: primary alias if any, else canonical."""
    out: list[str] = []
    for _m in _COMMAND_METADATA:
        out.append(_m["aliases"][0] if _m["aliases"] else _m["canonical"])
    return out


# --- Backward compatibility ---

def list_skills() -> list[dict[str, Any]]:
    """Return skill view: canonical, description, input_schema, output_schema, example (for OpenClaw)."""
    return [
        {
            "name": _m["canonical"],
            "canonical_command": _m["canonical"],
            "description": _m["description"],
            "input_schema": _m["input_schema"],
            "output_schema": _m["output_schema"],
            "example": _m["example"],
        }
        for _m in _COMMAND_METADATA if _m.get("expose_for_openclaw", True)
    ]


def get_skill_names() -> list[str]:
    """Canonical commands exposed to OpenClaw (same as get_canonical_commands_for_openclaw)."""
    return get_canonical_commands_for_openclaw()


def kwargs_for_task(task: str, args: Any) -> dict[str, Any]:
    """Build kwargs for command_registry.run(task, **kwargs). task must be canonical."""
    base = {"use_mock": getattr(args, "mock", False), "use_llm": getattr(args, "llm", False)}
    if task == "research_symbol":
        return {**base, "symbol": getattr(args, "symbol", "NVDA")}
    if task == "backtest_symbol":
        return {
            **base,
            "symbol": getattr(args, "symbol", "NVDA"),
            "start_date": getattr(args, "start", None),
            "end_date": getattr(args, "end", None),
        }
    if task == "run_demo":
        return {**base, "symbol": getattr(args, "symbol", "NVDA")}
    if task == "run_paper":
        return {
            **base,
            "symbol": getattr(args, "symbol", "NVDA"),
            "once": getattr(args, "once", False),
            "project_root": Path.cwd(),
        }
    if task == "autonomous_paper_cycle":
        syms = getattr(args, "symbol_universe", None) or getattr(args, "symbols", None)
        if isinstance(syms, str):
            syms = [s.strip() for s in syms.split(",") if s.strip()]
        if not syms:
            syms = ["NVDA"]
        return {
            **base,
            "run_id": getattr(args, "run_id", "") or "",
            "symbol_universe": syms,
            "mode": getattr(args, "mode", "paper"),
            "capital": getattr(args, "capital", 10000),
            "benchmark": getattr(args, "benchmark", "SPY"),
            "execute_paper": getattr(args, "execute_paper", True),
        }
    if task == "weekly_autonomous_paper":
        syms = getattr(args, "symbols", None)
        if isinstance(syms, str):
            syms = [s.strip() for s in syms.split(",") if s.strip()]
        return {
            **base,
            "capital": getattr(args, "capital", 10000),
            "benchmark": getattr(args, "benchmark", "SPY"),
            "duration_days": getattr(args, "days", 5),
            "auto_confirm": getattr(args, "auto_confirm", True),
            "report_dir": Path.cwd() / "reports",
            "symbols": syms if syms else None,
        }
    if task == "weekly_report":
        return {"report_dir": Path.cwd() / "reports"}
    return base
