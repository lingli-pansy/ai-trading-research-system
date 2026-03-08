"""
ExperienceStore: 只读查询 runs/experience.jsonl。
写由 RunStore.append_experience 负责；本模块仅负责读取与查询，供 decision context / debug。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_trading_research_system.state.run_store import get_runs_root


class ExperienceStore:
    """
    从 runs/experience.jsonl 读取经验记录；不写文件。
    可与 RunStore 共用同一 root（默认 get_runs_root()）。
    """

    def __init__(self, root: Path | None = None):
        self._root = get_runs_root(override=root)

    def _experience_path(self) -> Path:
        return self._root / "experience.jsonl"

    def _read_all_records(self) -> list[dict[str, Any]]:
        path = self._experience_path()
        if not path.exists():
            return []
        records: list[dict[str, Any]] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return records

    def get_recent_runs(self, n: int) -> list[dict[str, Any]]:
        """返回最近 n 条经验记录（从新到旧）。"""
        records = self._read_all_records()
        return list(records[-n:][::-1]) if records else []

    def get_symbol_history(self, symbol: str) -> list[dict[str, Any]]:
        """返回包含该 symbol 的所有经验记录（从旧到新）。"""
        records = self._read_all_records()
        return [r for r in records if symbol in (r.get("symbols") or [])]

    def get_recent_rebalances(self, symbol: str, limit: int = 20) -> list[dict[str, Any]]:
        """返回该 symbol 最近 limit 条与 rebalance 相关的记录（run_id, timestamp, rebalance_plan, decision_summary）。"""
        history = self.get_symbol_history(symbol)
        out: list[dict[str, Any]] = []
        for r in history[-limit:]:
            out.append({
                "run_id": r.get("run_id", ""),
                "timestamp": r.get("timestamp", ""),
                "symbols": r.get("symbols", []),
                "rebalance_plan": r.get("rebalance_plan", {}),
                "decision_summary": r.get("decision_summary", ""),
            })
        return out[::-1]


def get_experience_store(root: Path | None = None) -> ExperienceStore:
    return ExperienceStore(root=root)
