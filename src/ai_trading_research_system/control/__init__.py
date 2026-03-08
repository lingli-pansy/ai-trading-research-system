"""
COMPATIBILITY LAYER — Do not use for new code.

Control layer: legacy command routing and Skill interface.
New control surface: OpenClaw / CLI → application.commands only.
Use openclaw.adapter / openclaw.commands for OpenClaw; use presentation.cli for CLI.
"""
from __future__ import annotations

from ai_trading_research_system.control.command_router import route_intent
from ai_trading_research_system.control.skill_interface import execute

__all__ = ["route_intent", "execute"]
