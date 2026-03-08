"""
OpenClaw skill registry: list_skills() with canonical name, description, input/output schema, example.
Single source for skill surface; get_skill_names() returns canonical commands only.
run_for_openclaw uses this only; no hardcoded skill names.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_trading_research_system.openclaw.contract import (
    ResearchSymbolInput,
    BacktestSymbolInput,
    RunDemoInput,
    WeeklyAutonomousPaperInput,
    WeeklyReportInput,
    ResearchSymbolOutput,
    BacktestSymbolOutput,
    RunDemoOutput,
    WeeklyAutonomousPaperOutput,
    WeeklyReportOutput,
)

# Each skill: canonical command = name; input/output from contract.
_SKILLS: list[dict[str, Any]] = [
    {
        "name": "research_symbol",
        "description": "对标的做研究，返回 DecisionContract",
        "canonical_command": "research_symbol",
        "input_schema": ResearchSymbolInput.model_json_schema(),
        "output_schema": ResearchSymbolOutput.model_json_schema(),
        "example": {"command": "research_symbol", "symbol": "NVDA"},
    },
    {
        "name": "backtest_symbol",
        "description": "对标的做研究 + 回测 + 写入 Experience Store",
        "canonical_command": "backtest_symbol",
        "input_schema": BacktestSymbolInput.model_json_schema(),
        "output_schema": BacktestSymbolOutput.model_json_schema(),
        "example": {"command": "backtest_symbol", "symbol": "NVDA", "start_date": None, "end_date": None},
    },
    {
        "name": "run_demo",
        "description": "E2E 演示：研究 → 策略 → 回测 → 总结",
        "canonical_command": "run_demo",
        "input_schema": RunDemoInput.model_json_schema(),
        "output_schema": RunDemoOutput.model_json_schema(),
        "example": {"command": "run_demo", "symbol": "NVDA"},
    },
    {
        "name": "weekly_autonomous_paper",
        "description": "UC-09 一周自治 Paper：mandate → snapshot → 多轮 research/allocator/paper → benchmark → 周报",
        "canonical_command": "weekly_autonomous_paper",
        "input_schema": WeeklyAutonomousPaperInput.model_json_schema(),
        "output_schema": WeeklyAutonomousPaperOutput.model_json_schema(),
        "example": {"command": "weekly_autonomous_paper", "capital": 10000, "benchmark": "SPY", "duration": 5},
    },
    {
        "name": "weekly_report",
        "description": "读取已有周报或生成报告摘要；与 UC-09 execution 分离，仅报告",
        "canonical_command": "weekly_report",
        "input_schema": WeeklyReportInput.model_json_schema(),
        "output_schema": WeeklyReportOutput.model_json_schema(),
        "example": {"command": "weekly_report", "report_dir": None},
    },
]


def list_skills() -> list[dict[str, Any]]:
    """Return all registered skills: name (= canonical), description, input_schema, output_schema, example."""
    return list(_SKILLS)


def get_skill_names() -> list[str]:
    """Return canonical command names only (single source for run_for_openclaw choices)."""
    return [s["canonical_command"] for s in _SKILLS]


def kwargs_for_task(task: str, args: Any) -> dict[str, Any]:
    """Build kwargs for command_registry.run(task, **kwargs). task is canonical. report_dir from cwd when needed."""
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
    if task == "weekly_autonomous_paper":
        return {
            **base,
            "capital": getattr(args, "capital", 10000),
            "benchmark": getattr(args, "benchmark", "SPY"),
            "duration_days": getattr(args, "days", 5),
            "auto_confirm": getattr(args, "auto_confirm", True),
            "report_dir": Path.cwd() / "reports",
        }
    if task == "weekly_report":
        return {"report_dir": Path.cwd() / "reports"}
    return base
