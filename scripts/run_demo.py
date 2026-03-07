from pprint import pprint

from ai_trading_research_system.utils.logging import setup_logging
from ai_trading_research_system.research.orchestrator import ResearchOrchestrator
from ai_trading_research_system.decision.rules import RuleEngine
from ai_trading_research_system.portfolio.engine import PortfolioEngine
from ai_trading_research_system.execution.paper import PaperTradingEngine

def main() -> None:
    setup_logging()

    symbol = "NVDA"
    orchestrator = ResearchOrchestrator()
    rule_engine = RuleEngine()
    portfolio = PortfolioEngine(initial_cash=100000.0)
    paper = PaperTradingEngine(portfolio)

    contract = orchestrator.run(symbol)
    print("\n=== DECISION CONTRACT ===")
    pprint(contract.model_dump())

    signal = rule_engine.evaluate(contract)
    print("\n=== RULE ENGINE OUTPUT ===")
    pprint(signal)

    if signal.action == "paper_buy" and signal.allowed_position_size > 0:
        result = paper.buy(symbol=symbol, price=122.5, size_fraction=signal.allowed_position_size)
        print("\n=== PAPER ORDER RESULT ===")
        pprint(result)

    print("\n=== PORTFOLIO STATE ===")
    pprint(portfolio.state)

if __name__ == "__main__":
    main()
