"""
Command: weekly_report — read existing weekly report or return summary. No execution.
UC-09 execution (weekly_autonomous_paper) is separate; this is report-only.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class WeeklyReportCommandResult:
    ok: bool
    report_path: str
    mandate_id: str
    summary: dict


def run_weekly_report(
    *,
    report_dir: Path | None = None,
) -> WeeklyReportCommandResult:
    """
    Read latest weekly report JSON from report_dir. Returns summary; no pipeline execution.
    """
    report_dir = report_dir or Path.cwd() / "reports"
    report_dir = Path(report_dir)
    if not report_dir.exists():
        return WeeklyReportCommandResult(ok=False, report_path="", mandate_id="", summary={})
    files = sorted(report_dir.glob("weekly_report_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return WeeklyReportCommandResult(ok=False, report_path="", mandate_id="", summary={})
    path = files[0]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return WeeklyReportCommandResult(ok=False, report_path=str(path), mandate_id="", summary={})
    mandate_id = data.get("mandate_id", "") or path.stem.replace("weekly_report_", "")
    summary = data.get("summary", data) if isinstance(data.get("summary"), dict) else dict(data)
    return WeeklyReportCommandResult(
        ok=True,
        report_path=str(path),
        mandate_id=mandate_id,
        summary=summary,
    )
