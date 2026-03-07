from ai_trading_research_system.research.orchestrator import ResearchOrchestrator

def test_contract_generation():
    orchestrator = ResearchOrchestrator()
    contract = orchestrator.run("NVDA")
    assert contract.symbol == "NVDA"
    assert contract.suggested_action in {
        "forbid_trade", "watch", "wait_confirmation", "probe_small", "allow_entry"
    }
