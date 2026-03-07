from datetime import datetime, timedelta
from .models import NewsItem, FundamentalSnapshot, PriceSnapshot

class MockDataProvider:
    """Minimal mock provider for local development."""

    def get_price(self, symbol: str) -> PriceSnapshot:
        return PriceSnapshot(symbol=symbol, last_price=122.5, change_pct=2.1, volume_ratio=1.3)

    def get_fundamentals(self, symbol: str) -> FundamentalSnapshot:
        return FundamentalSnapshot(
            symbol=symbol,
            revenue_growth=0.28,
            gross_margin=0.63,
            pe_ttm=31.0,
            notes="Growth remains solid; valuation is elevated but not extreme.",
        )

    def get_news(self, symbol: str) -> list[NewsItem]:
        now = datetime.utcnow()
        return [
            NewsItem(
                title=f"{symbol} announces stronger-than-expected enterprise demand",
                source="MockWire",
                published_at=now - timedelta(hours=6),
                summary="Demand commentary implies continued revenue support over the next two quarters.",
            ),
            NewsItem(
                title=f"Analysts debate whether {symbol} valuation already prices in optimism",
                source="MockJournal",
                published_at=now - timedelta(hours=12),
                summary="Valuation concerns rise after a sharp rally, despite resilient fundamentals.",
            ),
        ]
