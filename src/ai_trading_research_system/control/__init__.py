"""
Control layer: command routing and Skill/OpenClaw interface.
Unified entry for user intent (e.g. analyse NVDA, run backtest) and for OpenClaw Skill to invoke CLI or API.
"""
from __future__ import annotations

from ai_trading_research_system.control.command_router import route_intent
from ai_trading_research_system.control.skill_interface import execute

__all__ = ["route_intent", "execute"]
