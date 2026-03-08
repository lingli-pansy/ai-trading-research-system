"""
RunStore: state-aware 统一数据访问。
所有 run / snapshot / decision / execution / audit / index / experience 落盘必须经此接口。
Public API: write_snapshot, write_artifact, write_execution, read_snapshot, read_meta, read_audit,
get_latest_portfolio_state, get_previous_research_snapshot, get_latest_run_summary, replay_run,
append_run_index, get_recent_runs, get_last_run, append_experience.
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


def get_runs_root(override: Path | None = None) -> Path:
    """返回 runs 根目录；供 ExperienceStore 等与 RunStore 共用同一 root。"""
    return (override or _runs_root()).resolve()


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunStore:
    """
    State-aware 统一数据访问：run metadata、snapshot、artifact、execution、audit。
    优先读本地落盘状态，再决定是否请求外部 API。
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

    # ---------- create / meta ----------
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
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / "meta.json"
        payload = dict(meta)
        if "updated_at" not in payload:
            payload["updated_at"] = _iso_now()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def read_meta(self, run_id: str) -> dict[str, Any] | None:
        path = self._run_dir(run_id) / "meta.json"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    # ---------- Public: write_snapshot / read_snapshot ----------
    def write_snapshot(self, run_id: str, kind: str, data: dict[str, Any]) -> str:
        """
        kind: portfolio_before | portfolio_after | research.
        返回写入路径（用于 write_paths）。
        """
        self.create_run(run_id)
        if kind in ("portfolio_before", "portfolio_after"):
            kind_short = kind.replace("portfolio_", "")
            path = self._snapshots_dir(run_id) / f"portfolio_{kind_short}.json"
            payload = dict(data)
            payload["_written_at"] = _iso_now()
            payload["_kind"] = kind_short
        elif kind == "research":
            path = self._snapshots_dir(run_id) / "research.json"
            payload = dict(data)
            payload["_written_at"] = _iso_now()
        else:
            raise ValueError(f"unknown snapshot kind: {kind}")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return str(path)

    def read_snapshot(self, run_id: str, kind: str) -> dict[str, Any] | None:
        """kind: portfolio_before | portfolio_after | research."""
        if kind in ("portfolio_before", "portfolio_after"):
            k = kind.replace("portfolio_", "")
            path = self._snapshots_dir(run_id) / f"portfolio_{k}.json"
        elif kind == "research":
            path = self._snapshots_dir(run_id) / "research.json"
        else:
            return None
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def write_portfolio_snapshot(self, run_id: str, kind: str, data: dict[str, Any]) -> None:
        """kind: 'before' | 'after'。保留兼容。"""
        self.write_snapshot(run_id, f"portfolio_{kind}", data)

    def read_portfolio_snapshot(self, run_id: str, kind: str) -> dict[str, Any] | None:
        """kind: 'before' | 'after'。"""
        return self.read_snapshot(run_id, f"portfolio_{kind}")

    def write_research_snapshot(self, run_id: str, data: dict[str, Any]) -> None:
        self.write_snapshot(run_id, "research", data)

    def read_research_snapshot(self, run_id: str) -> dict[str, Any] | None:
        return self.read_snapshot(run_id, "research")

    # ---------- Public: write_artifact ----------
    def write_artifact(self, run_id: str, name: str, data: Any) -> str:
        """
        name: candidate_decision | final_decision | order_intents | rebalance_plan.
        data: dict 或 list（order_intents）。返回写入路径。
        """
        self.create_run(run_id)
        path = self._artifacts_dir(run_id) / f"{name}.json"
        if name == "order_intents":
            payload = {"intents": data if isinstance(data, list) else [], "_written_at": _iso_now()}
        else:
            payload = dict(data) if isinstance(data, dict) else {"data": data}
            payload["_written_at"] = _iso_now()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return str(path)

    def write_candidate_decision(self, run_id: str, data: dict[str, Any]) -> None:
        self.write_artifact(run_id, "candidate_decision", data)

    def write_final_decision(self, run_id: str, data: dict[str, Any]) -> None:
        self.write_artifact(run_id, "final_decision", data)

    def write_order_intents(self, run_id: str, data: list[dict[str, Any]]) -> None:
        self.write_artifact(run_id, "order_intents", data)

    def write_rebalance_plan(self, run_id: str, data: dict[str, Any]) -> str:
        return self.write_artifact(run_id, "rebalance_plan", data)

    def read_artifact(self, run_id: str, name: str) -> dict[str, Any] | list | None:
        """name: candidate_decision | final_decision | order_intents | rebalance_plan."""
        path = self._artifacts_dir(run_id) / f"{name}.json"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            out = json.load(f)
        if name == "order_intents" and isinstance(out, dict):
            return out.get("intents", [])
        return out

    def read_rebalance_plan(self, run_id: str) -> dict[str, Any] | None:
        out = self.read_artifact(run_id, "rebalance_plan")
        return out if isinstance(out, dict) else None

    # ---------- Public: write_execution ----------
    def write_execution(self, run_id: str, data: dict[str, Any]) -> str:
        """写入 execution/paper_result.json。返回路径。"""
        self.create_run(run_id)
        path = self._execution_dir(run_id) / "paper_result.json"
        payload = dict(data)
        payload["_written_at"] = _iso_now()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return str(path)

    def write_paper_execution(self, run_id: str, data: dict[str, Any]) -> None:
        self.write_execution(run_id, data)

    def read_execution(self, run_id: str) -> dict[str, Any] | None:
        path = self._execution_dir(run_id) / "paper_result.json"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    # ---------- audit ----------
    def append_audit(self, run_id: str, entry: dict[str, Any]) -> None:
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

    # ---------- paths for write_paths (public，不暴露内部 dir) ----------
    def path_for_snapshot(self, run_id: str, kind: str) -> str:
        """kind: portfolio_before | portfolio_after | research。返回用于展示的路径字符串。"""
        if kind in ("portfolio_before", "portfolio_after"):
            k = kind.replace("portfolio_", "")
            return str(self._snapshots_dir(run_id) / f"portfolio_{k}.json")
        if kind == "research":
            return str(self._snapshots_dir(run_id) / "research.json")
        return ""

    def path_for_artifact(self, run_id: str, name: str) -> str:
        return str(self._artifacts_dir(run_id) / f"{name}.json")

    def path_for_execution(self, run_id: str) -> str:
        return str(self._execution_dir(run_id) / "paper_result.json")

    def list_runs(self, limit: int = 50) -> list[str]:
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
        runs = self.list_runs(limit=1)
        return runs[0] if runs else None

    # ---------- Run Index (runs/index.json) ----------
    def _index_path(self) -> Path:
        return self._root / "index.json"

    def append_run_index(self, run_metadata: dict[str, Any]) -> None:
        """追加一条运行索引到 runs/index.json。CLI/agent 仅通过此 API 写 index。"""
        _ensure_dir(self._root)
        path = self._index_path()
        entries: list[dict[str, Any]] = []
        if path.exists():
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
                entries = raw if isinstance(raw, list) else []
        entries.append(dict(run_metadata))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)

    def get_recent_runs(self, n: int) -> list[dict[str, Any]]:
        """返回最近 n 条索引（从新到旧）。"""
        path = self._index_path()
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            entries = json.load(f)
        if not isinstance(entries, list):
            return []
        return list(entries)[-n:][::-1]

    def get_last_run(self) -> dict[str, Any] | None:
        """返回最近一条索引，无则 None。"""
        recent = self.get_recent_runs(1)
        return recent[0] if recent else None

    # ---------- Experience Log (runs/experience.jsonl) ----------
    def _experience_path(self) -> Path:
        return self._root / "experience.jsonl"

    def append_experience(self, record: dict[str, Any]) -> None:
        """追加一条经验记录到 runs/experience.jsonl。CLI/agent 仅通过此 API 写 experience。"""
        _ensure_dir(self._root)
        path = self._experience_path()
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)

    # ---------- Agent Health (runs/agent_health.json) ----------
    def _agent_health_path(self) -> Path:
        return self._root / "agent_health.json"

    def write_agent_health(self, data: dict[str, Any]) -> None:
        """写入 runs/agent_health.json。仅通过 RunStore 写，agent 不直接写 runs/。"""
        _ensure_dir(self._root)
        path = self._agent_health_path()
        payload = dict(data)
        if "updated_at" not in payload:
            payload["updated_at"] = _iso_now()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def read_agent_health(self) -> dict[str, Any] | None:
        """读取 runs/agent_health.json。"""
        path = self._agent_health_path()
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def run_dir(self, run_id: str) -> Path:
        return self._run_dir(run_id)

    # ---------- State-aware: get_latest_portfolio_state ----------
    def get_latest_portfolio_state(self) -> dict[str, Any] | None:
        """
        优先：runs/<latest_run>/snapshots/portfolio_after.json；
        否则 fallback：account snapshot API。
        """
        rid = self.read_latest_run_id()
        if rid:
            after = self.read_snapshot(rid, "portfolio_after")
            if after:
                return after
        try:
            from ai_trading_research_system.autonomous import get_account_snapshot
            snap = get_account_snapshot(paper=True, mock=True, initial_cash=10_000.0, allow_fallback=True)
            return {
                "cash": snap.cash,
                "equity": snap.equity,
                "positions": list(snap.positions or []),
                "source": snap.source,
                "timestamp": snap.timestamp,
                "risk_budget": getattr(snap, "risk_budget", 0),
            }
        except Exception:
            return None

    # ---------- State-aware: get_previous_research_snapshot(symbol) ----------
    def get_previous_research_snapshot(self, symbol: str) -> dict[str, Any] | None:
        """若上一轮 run 存在 research snapshot，返回该 symbol 的条目。"""
        rid = self.read_latest_run_id()
        if not rid:
            return None
        data = self.read_snapshot(rid, "research")
        if not data or "by_symbol" not in data:
            return None
        for entry in data.get("by_symbol", []):
            if entry.get("symbol") == symbol:
                return entry
        return None

    # ---------- get_latest_run_summary ----------
    def get_latest_run_summary(self) -> dict[str, Any] | None:
        """快速返回：run_id, final_decision, order_intents, portfolio_after。"""
        rid = self.read_latest_run_id()
        if not rid:
            return None
        final = self.read_artifact(rid, "final_decision")
        intents = self.read_artifact(rid, "order_intents")
        if isinstance(intents, dict) and "intents" in intents:
            intents = intents["intents"]
        after = self.read_snapshot(rid, "portfolio_after")
        return {
            "run_id": rid,
            "final_decision": final,
            "order_intents": intents if isinstance(intents, list) else [],
            "portfolio_after": after,
        }

    # ---------- replay_run ----------
    def replay_run(self, run_id: str) -> dict[str, Any] | None:
        """
        完整 replay summary：symbols, ranking, trigger, decision, rebalance_plan, execution, portfolio_after。
        用于 debug、agent introspection、CLI replay。
        """
        meta = self.read_meta(run_id)
        if not meta:
            return None
        research = self.read_snapshot(run_id, "research")
        candidate = self.read_artifact(run_id, "candidate_decision")
        final = self.read_artifact(run_id, "final_decision")
        rebalance_plan = self.read_artifact(run_id, "rebalance_plan")
        execution = self.read_execution(run_id)
        before = self.read_snapshot(run_id, "portfolio_before")
        after = self.read_snapshot(run_id, "portfolio_after")
        audit_entries = self.read_audit(run_id)
        ranking = research.get("opportunity_ranking", []) if research else []
        if research and "by_symbol" in research:
            ranking = ranking or [{"symbol": e.get("symbol"), "action": e.get("suggested_action"), "confidence": e.get("confidence")} for e in research["by_symbol"]]
        trigger = None
        for e in audit_entries:
            if "trigger" in e:
                trigger = e.get("trigger")
                break
        return {
            "run_id": run_id,
            "symbols": meta.get("symbols", []),
            "ranking": ranking,
            "trigger": trigger,
            "decision": final,
            "final_decision": final,
            "rebalance_plan": rebalance_plan,
            "execution": execution,
            "portfolio_before": before,
            "portfolio_after": after,
            "started_at": meta.get("started_at"),
            "ended_at": meta.get("ended_at"),
            "error": meta.get("error"),
            "audit_count": len(audit_entries),
        }

    def read_run_summary(self, run_id: str) -> dict[str, Any] | None:
        """兼容旧名：等同于 replay_run 的简化版。"""
        return self.replay_run(run_id)


def get_run_store(root: Path | None = None) -> RunStore:
    return RunStore(root=root)
