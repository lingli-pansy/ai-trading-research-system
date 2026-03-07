from pydantic import BaseModel, Field
from datetime import datetime

class NewsItem(BaseModel):
    title: str
    source: str
    published_at: datetime
    summary: str

class FundamentalSnapshot(BaseModel):
    symbol: str
    revenue_growth: float | None = None
    gross_margin: float | None = None
    pe_ttm: float | None = None
    notes: str | None = None

class PriceSnapshot(BaseModel):
    symbol: str
    last_price: float
    change_pct: float = Field(description="Daily percent change")
    volume_ratio: float | None = None
