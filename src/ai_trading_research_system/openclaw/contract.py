"""
OpenClaw command contract: machine-verifiable input/output schemas.
Used by run_for_openclaw.py and tests; persona/skills remain documentation.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# --- OpenClaw-exposed commands (must match registry.get_canonical_commands_for_openclaw()) ---
OPENCLAW_COMMANDS = [
    "research_symbol",
    "backtest_symbol",
    "run_demo",
    "weekly_autonomous_paper",
    "weekly_report",
]


# --- Input schemas (per command) ---

class CommandInputBase(BaseModel):
    """Base: command name."""
    command: str = Field(..., description="Command name")


class ResearchSymbolInput(CommandInputBase):
    command: str = "research_symbol"
    symbol: str = "NVDA"


class BacktestSymbolInput(CommandInputBase):
    command: str = "backtest_symbol"
    symbol: str = "NVDA"
    start_date: str | None = None
    end_date: str | None = None


class RunDemoInput(CommandInputBase):
    command: str = "run_demo"
    symbol: str = "NVDA"


class WeeklyAutonomousPaperInput(CommandInputBase):
    command: str = "weekly_autonomous_paper"
    capital: float = 10_000.0
    benchmark: str = "SPY"
    duration: int = 5
    auto_confirm: bool = True
    symbols: list[str] | None = None  # watchlist / universe；空则默认 ["NVDA"]


class WeeklyReportInput(CommandInputBase):
    command: str = "weekly_report"
    report_dir: str | None = None


class RunPaperInput(CommandInputBase):
    command: str = "run_paper"
    symbol: str = "NVDA"
    once: bool = False


# --- Output schemas: success ---

class OpenClawSuccessBase(BaseModel):
    """Unified success output base."""
    ok: bool = True
    command: str = Field(..., description="Command that was run")
    status: str = Field("ok", description="Status string")
    engine_type: str = Field("nautilus", description="Execution engine")
    used_nautilus: bool = True


class ResearchSymbolOutput(OpenClawSuccessBase):
    command: str = "research_symbol"
    symbol: str = ""
    contract_action: str = ""
    contract_confidence: str = ""
    thesis_snippet: str = ""
    raw_contract: dict[str, Any] = Field(default_factory=dict)


class BacktestSymbolOutput(OpenClawSuccessBase):
    command: str = "backtest_symbol"
    symbol: str = ""
    contract_action: str = ""
    contract_confidence: str = ""
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    pnl: float = 0.0
    trade_count: int = 0
    strategy_run_id: int = 0
    report_path: str | None = None


class RunDemoOutput(OpenClawSuccessBase):
    command: str = "run_demo"
    symbol: str = ""
    research: dict[str, Any] = Field(default_factory=dict)
    strategy: dict[str, Any] = Field(default_factory=dict)
    backtest: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    report_path: str | None = None


class WeeklyAutonomousPaperOutput(OpenClawSuccessBase):
    command: str = "weekly_autonomous_paper"
    mandate_id: str = ""
    report_path: str | None = None
    snapshot_source: str = ""
    benchmark_source: str = ""


class WeeklyReportOutput(OpenClawSuccessBase):
    command: str = "weekly_report"
    mandate_id: str = ""
    report_path: str | None = None
    summary: dict[str, Any] = Field(default_factory=dict)


class RunPaperOutput(OpenClawSuccessBase):
    command: str = "run_paper"
    symbol: str = ""
    paused: bool = False
    contract_action: str = ""
    contract_confidence: str = ""
    signal_action: str = ""
    message: str = ""


# --- Error schema (stderr / failure) ---

class OpenClawErrorOutput(BaseModel):
    """Unified error output; written to stderr only."""
    ok: bool = False
    command: str = Field(..., description="Command that failed")
    error_code: int = Field(1, description="Non-zero error code")
    error_message: str = Field("", description="Human-readable error")


def error_to_dict(command: str, error_code: int, error_message: str) -> dict[str, Any]:
    """Build error payload for stderr; machine-verifiable."""
    return OpenClawErrorOutput(
        ok=False,
        command=command,
        error_code=error_code,
        error_message=error_message,
    ).model_dump()


def validate_success_output(command: str, out: dict[str, Any]) -> bool:
    """Check that success output has required fields. Returns True if valid."""
    required = {"ok", "command", "status", "engine_type", "used_nautilus"}
    if not required.issubset(out.keys()):
        return False
    if out.get("ok") is not True or out.get("command") != command:
        return False
    return True


def validate_error_output(out: dict[str, Any]) -> bool:
    """Check that error output has required fields."""
    required = {"ok", "command", "error_code", "error_message"}
    if not required.issubset(out.keys()):
        return False
    return out.get("ok") is False
