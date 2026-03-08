"""
RunStore: 统一负责 paper run 的路径、命名、读写与版本字段。
所有 run / snapshot / decision / execution / audit 落盘必须经此接口，禁止各 service 直接写文件。
目录布局（可配置根目录，默认 runs/）：
  runs/
    <run_id>/
      meta.json           # 本轮 run metadata
      snapshots/
        portfolio_before.json
        portfolio_after.json
        research.json     # 本轮用到的研究/市场输入快照（精简）
      artifacts/
        candidate_decision.json
        final_decision.json
        order_intents.json
      execution/
        paper_result.json
      audit.json          # 追加型审计日志（列表）
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 默认根目录；可通过环境变量 PAPER_RUNS_ROOT 覆盖
DEFAULT_RUNS_ROOT = Path("runs")


def _runs_root() -> Path:
    root = os.environ.get("PAPER_RUNS_ROOT")
    if root:
        return Path(root).resolve()
    return Path.cwd() / DEFAULT_RUNS_ROOT


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunStore:
    """
    统一数据访问：run metadata、portfolio/research snapshot、decision artifact、
    order intent、paper execution、audit。所有落盘结构可读、可回放、可排查。
    """

    def __init__(self, root: Path | None = None):
        self._root = (root or _runs_root()).resolve()

    def _run_dir(self, run_id: str) -> Path:
        return self._root / run_id

    def _snapshots_dir(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "snapshots"

    def _artifacts_dir(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "artifacts"

    def _execution_dir(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "execution"

    def create_run(
        self,
        run_id: str,
        mode: str = "paper",
        symbols: list[str] | None = None,
        config: dict[str, Any] | None = None,
    ) -> Path:
        """创建本轮 run 目录结构；若已存在则复用。返回 run 目录。"""
        run_dir = self._run_dir(run_id)
        _ensure_dir(run_dir)
        _ensure_dir(self._snapshots_dir(run_id))
        _ensure_dir(self._artifacts_dir(run_id))
        _ensure_dir(self._execution_dir(run_id))
        meta = self.read_meta(run_id)
        if not meta:
            self.write_meta(
                run_id,
                {
                    "run_id": run_id,
                    "mode": mode,
                    "symbols": symbols or [],
                    "config": config or {},
                    "started_at": _iso_now(),
                    "ended_at": None,
                },
            )
        return run_dir

    def write_meta(self, run_id: str, meta: dict[str, Any]) -> None:
        """写入/覆盖本轮 run metadata。"""
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / "meta.json"
        payload = dict(meta)
        if "updated_at" not in payload:
            payload["updated_at"] = _iso_now()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def read_meta(self, run_id: str) -> dict[str, Any] | None:
        """读取本轮 run metadata；不存在返回 None。"""
        path = self._run_dir(run_id) / "meta.json"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def write_portfolio_snapshot(
        self, run_id: str, kind: str, data: dict[str, Any]
    ) -> None:
        """kind: 'before' | 'after'。写入 snapshots/portfolio_<kind>.json。"""
        self.create_run(run_id, **({"symbols": data.get("symbols", [])} if data else {}))
        path = self._snapshots_dir(run_id) / f"portfolio_{kind}.json"
        payload = dict(data)
        payload["_written_at"] = _iso_now()
        payload["_kind"] = kind
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def read_portfolio_snapshot(
        self, run_id: str, kind: str
    ) -> dict[str, Any] | None:
        """kind: 'before' | 'after'。"""
        path = self._snapshots_dir(run_id) / f"portfolio_{kind}.json"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def write_research_snapshot(self, run_id: str, data: dict[str, Any]) -> None:
        """写入 snapshots/research.json（本轮用到的研究/市场输入快照，精简版）。"""
        self.create_run(run_id)
        path = self._snapshots_dir(run_id) / "research.json"
        payload = dict(data)
        payload["_written_at"] = _iso_now()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def read_research_snapshot(self, run_id: str) -> dict[str, Any] | None:
        path = self._snapshots_dir(run_id) / "research.json"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def write_candidate_decision(self, run_id: str, data: dict[str, Any]) -> None:
        """写入 artifacts/candidate_decision.json。"""
        self.create_run(run_id)
        path = self._artifacts_dir(run_id) / "candidate_decision.json"
        payload = dict(data)
        payload["_written_at"] = _iso_now()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def write_final_decision(self, run_id: str, data: dict[str, Any]) -> None:
        """写入 artifacts/final_decision.json。"""
        self.create_run(run_id)
        path = self._artifacts_dir(run_id) / "final_decision.json"
        payload = dict(data)
        payload["_written_at"] = _iso_now()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def write_order_intents(self, run_id: str, data: list[dict[str, Any]]) -> None:
        """写入 artifacts/order_intents.json。"""
        self.create_run(run_id)
        path = self._artifacts_dir(run_id) / "order_intents.json"
        payload = {"intents": data, "_written_at": _iso_now()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def write_paper_execution(self, run_id: str, data: dict[str, Any]) -> None:
        """写入 execution/paper_result.json。"""
        self.create_run(run_id)
        path = self._execution_dir(run_id) / "paper_result.json"
        payload = dict(data)
        payload["_written_at"] = _iso_now()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def append_audit(self, run_id: str, entry: dict[str, Any]) -> None:
        """追加一条审计记录到 audit.json（文件内为 list）。"""
        self.create_run(run_id)
        path = self._run_dir(run_id) / "audit.json"
        entry = dict(entry)
        entry["_at"] = _iso_now()
        if path.exists():
            with open(path, encoding="utf-8") as f:
                entries = json.load(f)
        else:
            entries = []
        entries.append(entry)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)

    def read_audit(self, run_id: str) -> list[dict[str, Any]]:
        path = self._run_dir(run_id) / "audit.json"
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def list_runs(self, limit: int = 50) -> list[str]:
        """按目录 mtime 倒序返回 run_id 列表。"""
        if not self._root.exists():
            return []
        run_ids = [
            d.name
            for d in self._root.iterdir()
            if d.is_dir() and (d / "meta.json").exists()
        ]
        run_ids.sort(
            key=lambda rid: (self._run_dir(rid) / "meta.json").stat().st_mtime,
            reverse=True,
        )
        return run_ids[:limit]

    def read_latest_run_id(self) -> str | None:
        """最近一次 run 的 run_id；无则 None。"""
        runs = self.list_runs(limit=1)
        return runs[0] if runs else None

    def run_dir(self, run_id: str) -> Path:
        """返回本轮 run 的根目录 Path（供调用方拼写 report 等）。"""
        return self._run_dir(run_id)

    def read_run_summary(self, run_id: str) -> dict[str, Any] | None:
        """
        基于某次 run 的落盘结果做一次复盘/重建 summary（最小 replay 能力）。
        返回可读的 summary dict，便于排查与展示。
        """
        meta = self.read_meta(run_id)
        if not meta:
            return None
        before = self.read_portfolio_snapshot(run_id, "before")
        after = self.read_portfolio_snapshot(run_id, "after")
        final = None
        path = self._artifacts_dir(run_id) / "final_decision.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                final = json.load(f)
        audit_entries = self.read_audit(run_id)
        paper_path = self._execution_dir(run_id) / "paper_result.json"
        paper_result = None
        if paper_path.exists():
            with open(paper_path, encoding="utf-8") as f:
                paper_result = json.load(f)
        return {
            "run_id": run_id,
            "mode": meta.get("mode", ""),
            "symbols": meta.get("symbols", []),
            "started_at": meta.get("started_at"),
            "ended_at": meta.get("ended_at"),
            "error": meta.get("error"),
            "portfolio_before": before,
            "portfolio_after": after,
            "final_decision": final,
            "audit_count": len(audit_entries),
            "audit_tail": audit_entries[-5:] if len(audit_entries) > 5 else audit_entries,
            "paper_result": paper_result,
        }


def get_run_store(root: Path | None = None) -> RunStore:
    """获取全局 RunStore 实例（每次新建，无单例）。"""
    return RunStore(root=root)
