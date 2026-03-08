"""Command: research symbol. Calls ResearchOrchestrator only."""
from __future__ import annotations

from ai_trading_research_system.research.orchestrator import ResearchOrchestrator
from ai_trading_research_system.research.schemas import DecisionContract


def run_research_symbol(
    symbol: str,
    *,
    use_mock: bool = False,
    use_llm: bool = False,
) -> DecisionContract:
    """Run research for symbol; returns DecisionContract. No side effects beyond orchestrator."""
    orchestrator = ResearchOrchestrator(use_mock=use_mock, use_llm=use_llm)
    return orchestrator.run(symbol)
