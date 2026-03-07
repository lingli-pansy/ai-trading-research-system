from dataclasses import dataclass
from ai_trading_research_system.research.schemas import DecisionContract

@dataclass
class SignalDecision:
    action: str
    allowed_position_size: float
    rationale: str

class RuleEngine:
    def evaluate(self, contract: DecisionContract) -> SignalDecision:
        if contract.suggested_action == "forbid_trade":
            return SignalDecision("no_trade", 0.0, "Contract forbids trade.")
        if contract.confidence == "low":
            return SignalDecision("watch_only", 0.0, "Confidence too low.")
        if "liquidity_risk" in contract.risk_flags:
            return SignalDecision("watch_only", 0.0, "Liquidity risk present.")
        if contract.suggested_action == "probe_small":
            return SignalDecision("paper_buy", 0.25, "Small probe allowed.")
        if contract.suggested_action == "allow_entry" and contract.confidence == "high":
            return SignalDecision("paper_buy", 1.0, "Full entry allowed.")
        return SignalDecision("wait", 0.0, "Need further confirmation.")
