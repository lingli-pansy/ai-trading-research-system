"""
OpenClaw skill registry: list_skills() with name, description, input/output schema, example.
All commands must be registered; run_for_openclaw must not hardcode skill names.
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

_SKILLS: list[dict[str, Any]] = [
    {
        "name": "research",
        "description": "对标的做研究，返回 DecisionContract",
        "input_schema": ResearchSymbolInput.model_json_schema(),
        "output_schema": ResearchSymbolOutput.model_json_schema(),
        "example": {"command": "research", "symbol": "NVDA"},
    },
    {
        "name": "backtest",
        "description": "对标的做研究 + 回测 + 写入 Experience Store",
        "input_schema": BacktestSymbolInput.model_json_schema(),
        "output_schema": BacktestSymbolOutput.model_json_schema(),
        "example": {"command": "backtest", "symbol": "NVDA", "start_date": None, "end_date": None},
    },
    {
        "name": "demo",
        "description": "E2E 演示：研究 → 策略 → 回测 → 总结",
        "input_schema": RunDemoInput.model_json_schema(),
        "output_schema": RunDemoOutput.model_json_schema(),
        "example": {"command": "demo", "symbol": "NVDA"},
    },
    {
        "name": "weekly_autonomous_paper",
        "description": "UC-09 一周自治 Paper：mandate → snapshot → 多轮 research/allocator/paper → benchmark → 周报",
        "input_schema": WeeklyAutonomousPaperInput.model_json_schema(),
        "output_schema": WeeklyAutonomousPaperOutput.model_json_schema(),
        "example": {"command": "weekly_autonomous_paper", "capital": 10000, "benchmark": "SPY", "duration": 5},
    },
    {
        "name": "weekly_report",
        "description": "同 weekly_autonomous_paper，输出 command=weekly_report",
        "input_schema": WeeklyReportInput.model_json_schema(),
        "output_schema": WeeklyReportOutput.model_json_schema(),
        "example": {"command": "weekly_report", "capital": 10000, "benchmark": "SPY", "duration": 5},
    },
]


def list_skills() -> list[dict[str, Any]]:
    """Return all registered skills: name, description, input_schema, output_schema, example."""
    return list(_SKILLS)


def get_skill_names() -> list[str]:
    """Return skill names for argument choices / validation."""
    return [s["name"] for s in _SKILLS]


def kwargs_for_task(task: str, args: Any) -> dict[str, Any]:
    """Build kwargs for command_registry.run(task, **kwargs) from parsed args (e.g. argparse.Namespace)."""
    base = {"use_mock": getattr(args, "mock", False), "use_llm": getattr(args, "llm", False)}
    if task == "research":
        return {**base, "symbol": getattr(args, "symbol", "NVDA")}
    if task == "backtest":
        return {
            **base,
            "symbol": getattr(args, "symbol", "NVDA"),
            "start_date": getattr(args, "start", None),
            "end_date": getattr(args, "end", None),
        }
    if task == "demo":
        return {**base, "symbol": getattr(args, "symbol", "NVDA")}
    if task in ("weekly_autonomous_paper", "weekly_report"):
        return {
            **base,
            "capital": getattr(args, "capital", 10000),
            "benchmark": getattr(args, "benchmark", "SPY"),
            "duration_days": getattr(args, "days", 5),
            "auto_confirm": True,
        }
    return base
