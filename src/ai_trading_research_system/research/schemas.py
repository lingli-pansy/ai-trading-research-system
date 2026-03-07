from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

Confidence = Literal["low", "medium", "high"]
SuggestedAction = Literal[
    "forbid_trade",
    "watch",
    "wait_confirmation",
    "probe_small",
    "allow_entry",
]
TimeHorizon = Literal["intraday", "swing", "position"]

class DecisionContract(BaseModel):
    symbol: str
    analysis_time: datetime = Field(default_factory=datetime.utcnow)

    thesis: str
    key_drivers: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    counter_evidence: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)

    confidence: Confidence
    suggested_action: SuggestedAction
    time_horizon: TimeHorizon = "swing"
    risk_flags: list[str] = Field(default_factory=list)

class ResearchContext(BaseModel):
    symbol: str
    price_summary: str
    fundamentals_summary: str
    news_summaries: list[str]
