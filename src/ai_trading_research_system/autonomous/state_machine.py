"""
AutonomousExecutionStateMachine：管理一周自治运行状态。
状态可记录、可观察，供 E2E 与 OpenClaw/scheduler 使用。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

State = Literal[
    "pending_start",
    "active",
    "paused_by_risk",
    "stopped_by_user",
    "completed_week",
    "errored",
]


@dataclass
class StateTransition:
    """单次状态切换记录。"""
    from_state: State
    to_state: State
    at: str  # ISO
    reason: str = ""


class AutonomousExecutionStateMachine:
    """
    至少支持：pending_start, active, paused_by_risk, stopped_by_user, completed_week, errored。
    状态切换可记录，E2E 可观察。
    """

    def __init__(self) -> None:
        self._state: State = "pending_start"
        self._transitions: list[StateTransition] = []

    @property
    def state(self) -> State:
        return self._state

    @property
    def transitions(self) -> list[StateTransition]:
        return list(self._transitions)

    def transition(self, to: State, reason: str = "") -> None:
        from_state = self._state
        self._state = to
        self._transitions.append(StateTransition(
            from_state=from_state,
            to_state=to,
            at=datetime.now(timezone.utc).isoformat(),
            reason=reason,
        ))

    def start(self) -> None:
        self.transition("active", "started")

    def pause_by_risk(self) -> None:
        self.transition("paused_by_risk", "risk_triggered")

    def stop_by_user(self) -> None:
        self.transition("stopped_by_user", "user_stop")

    def complete_week(self) -> None:
        self.transition("completed_week", "week_finished")

    def set_errored(self, reason: str = "") -> None:
        self.transition("errored", reason or "error")
