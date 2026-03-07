from ..schemas import DecisionContract, ResearchContext

class SynthesisAgent:
    name = "synthesis"

    def run(self, context: ResearchContext, aggregated: dict) -> DecisionContract:
        support = aggregated.get("supporting_evidence", [])
        counter = aggregated.get("counter_evidence", [])
        uncertainties = aggregated.get("uncertainties", [])
        risk_flags = aggregated.get("risk_flags", [])
        key_drivers = aggregated.get("key_drivers", [])
        thesis = aggregated.get("thesis") or "Mixed but constructive setup with unresolved valuation and confirmation risk."

        if len(counter) >= 3 and len(uncertainties) >= 2:
            action = "wait_confirmation"
            confidence = "medium"
        elif support and len(counter) <= 2:
            action = "probe_small"
            confidence = "medium"
        else:
            action = "watch"
            confidence = "low"

        return DecisionContract(
            symbol=context.symbol,
            thesis=thesis,
            key_drivers=key_drivers,
            supporting_evidence=support,
            counter_evidence=counter,
            uncertainties=uncertainties,
            confidence=confidence,
            suggested_action=action,
            time_horizon="swing",
            risk_flags=risk_flags,
        )
