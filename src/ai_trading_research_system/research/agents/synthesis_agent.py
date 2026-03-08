from ..schemas import DecisionContract, ResearchContext

class SynthesisAgent:
    name = "synthesis"

    def run(self, context: ResearchContext, aggregated: dict) -> DecisionContract:
        raw_sup = aggregated.get("supporting_evidence", [])
        support = raw_sup if isinstance(raw_sup, list) else [str(raw_sup)] if raw_sup else []
        raw_cnt = aggregated.get("counter_evidence", [])
        counter = raw_cnt if isinstance(raw_cnt, list) else [str(raw_cnt)] if raw_cnt else []
        raw_unc = aggregated.get("uncertainties", [])
        uncertainties = raw_unc if isinstance(raw_unc, list) else [str(raw_unc)] if raw_unc else []
        raw_risk = aggregated.get("risk_flags", [])
        risk_flags = raw_risk if isinstance(raw_risk, list) else [str(raw_risk)] if raw_risk else []
        raw_drivers = aggregated.get("key_drivers", [])
        key_drivers = raw_drivers if isinstance(raw_drivers, list) else [str(raw_drivers)] if raw_drivers else []
        thesis = (aggregated.get("thesis") or "Mixed but constructive setup with unresolved valuation and confirmation risk.")
        if isinstance(thesis, list):
            thesis = thesis[0] if thesis else ""

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
