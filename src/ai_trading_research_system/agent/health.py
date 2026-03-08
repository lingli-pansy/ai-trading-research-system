"""
Agent Health Monitor: last_success_run, last_error, consecutive_failures, agent_uptime, current_state.
持久化于 runs/agent_health.json，经 RunStore 读写。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_trading_research_system.state.run_store import RunStore


@dataclass
class AgentHealthStatus:
    """Agent 健康状态，对应 runs/agent_health.json。"""
    last_success_run: str = ""
    last_error: str = ""
    consecutive_failures: int = 0
    agent_uptime: str = ""   # 启动时间或上次恢复时间
    current_state: str = "running"  # running | stopped
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_success_run": self.last_success_run,
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures,
            "agent_uptime": self.agent_uptime,
            "current_state": self.current_state,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AgentHealthStatus":
        if not data:
            return cls()
        return cls(
            last_success_run=data.get("last_success_run", ""),
            last_error=data.get("last_error", ""),
            consecutive_failures=int(data.get("consecutive_failures", 0)),
            agent_uptime=data.get("agent_uptime", ""),
            current_state=data.get("current_state", "running"),
            updated_at=data.get("updated_at", ""),
        )


def get_health(store: RunStore) -> AgentHealthStatus:
    """从 RunStore 读取 agent_health.json，返回 AgentHealthStatus。"""
    raw = store.read_agent_health()
    return AgentHealthStatus.from_dict(raw)


def update_health_success(store: RunStore, run_id: str) -> AgentHealthStatus:
    """run 成功：重置 consecutive_failures，更新 last_success_run；写入 runs/agent_health.json。"""
    from datetime import datetime, timezone
    health = get_health(store)
    health.last_success_run = run_id
    health.last_error = ""
    health.consecutive_failures = 0
    health.current_state = "running"
    health.updated_at = datetime.now(timezone.utc).isoformat()
    if not health.agent_uptime:
        health.agent_uptime = health.updated_at
    store.write_agent_health(health.to_dict())
    return health


def update_health_error(store: RunStore, error_message: str) -> AgentHealthStatus:
    """run 失败：consecutive_failures += 1，更新 last_error；写入 runs/agent_health.json。"""
    from datetime import datetime, timezone
    health = get_health(store)
    health.last_error = error_message
    health.consecutive_failures = health.consecutive_failures + 1
    health.updated_at = datetime.now(timezone.utc).isoformat()
    store.write_agent_health(health.to_dict())
    return health


def mark_agent_stopped(store: RunStore) -> None:
    """连续失败超阈值后标记 current_state=stopped。"""
    health = get_health(store)
    health.current_state = "stopped"
    from datetime import datetime, timezone
    health.updated_at = datetime.now(timezone.utc).isoformat()
    store.write_agent_health(health.to_dict())


def should_stop_loop(health: AgentHealthStatus, max_consecutive_failures: int = 5) -> bool:
    """连续失败超过阈值则返回 True，agent loop 应停止。"""
    return health.consecutive_failures >= max_consecutive_failures or health.current_state == "stopped"
