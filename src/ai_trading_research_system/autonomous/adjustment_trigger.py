"""
Intraday Opportunistic Adjustment Trigger: 日内机会性调整触发。
支持 drawdown_trigger / opportunity_spike_trigger / risk_event_trigger。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


TRIGGER_DRAWDOWN = "drawdown_trigger"
TRIGGER_OPPORTUNITY_SPIKE = "opportunity_spike_trigger"
TRIGGER_RISK_EVENT = "risk_event_trigger"
TRIGGER_CONCENTRATION_RISK = "concentration_risk_trigger"
TRIGGER_BETA_SPIKE = "beta_spike_trigger"
TRIGGER_EXCESS_DRAWDOWN = "excess_drawdown_trigger"


@dataclass
class AdjustmentTrigger:
    trigger_type: str  # drawdown_trigger | opportunity_spike_trigger | risk_event_trigger
    trigger_reason: str
    severity: str  # low | medium | high
    timestamp: str  # ISO format

    def to_dict(self) -> dict:
        return {
            "trigger_type": self.trigger_type,
            "trigger_reason": self.trigger_reason,
            "severity": self.severity,
            "timestamp": self.timestamp,
        }
