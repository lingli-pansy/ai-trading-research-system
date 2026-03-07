from datetime import datetime, timedelta
from .models import NewsItem, FundamentalSnapshot, PriceSnapshot


class YFinanceProvider:
    """Real-time price from yfinance; fundamentals and news fall back to mock for now.
    On rate limit or request error, falls back to mock price so the pipeline still outputs a Contract.
    """

    def get_price(self, symbol: str) -> PriceSnapshot:
        import sys
        try:
            import yfinance as yf
        except Exception as e:
            print(f"Warning: yfinance import failed ({e}), using mock price for {symbol}.", file=sys.stderr)
            return _fallback_price(symbol)

        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
        except Exception as e:
            print(f"Warning: yfinance request failed ({e}), using mock price for {symbol}.", file=sys.stderr)
            return _fallback_price(symbol)

        if hist is None or hist.empty:
            return _fallback_price(symbol)
        try:
            last = hist.iloc[-1]
            last_price = float(last["Close"])
            if len(hist) >= 2:
                prev = hist.iloc[-2]["Close"]
                change_pct = (last_price - prev) / prev * 100.0 if prev else 0.0
            else:
                change_pct = 0.0
            volume_ratio = None
            if "Volume" in hist.columns and hist["Volume"].iloc[-1] and hist["Volume"].iloc[:-1].mean():
                volume_ratio = float(hist["Volume"].iloc[-1] / hist["Volume"].iloc[:-1].mean())
            return PriceSnapshot(
                symbol=symbol,
                last_price=last_price,
                change_pct=round(change_pct, 2),
                volume_ratio=round(volume_ratio, 2) if volume_ratio is not None else None,
            )
        except Exception as e:
            print(f"Warning: yfinance parse failed ({e}), using mock price for {symbol}.", file=sys.stderr)
            return _fallback_price(symbol)

    def get_fundamentals(self, symbol: str) -> FundamentalSnapshot:
        import sys
        try:
            import yfinance as yf
        except Exception:
            return _mock_fundamentals(symbol)
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            rev_growth = info.get("revenueGrowth")
            if rev_growth is not None and not isinstance(rev_growth, (int, float)):
                rev_growth = None
            gross = info.get("grossMargins")
            if gross is not None and not isinstance(gross, (int, float)):
                gross = None
            pe = info.get("trailingPE")
            if pe is not None and not isinstance(pe, (int, float)):
                pe = None
            notes = info.get("longBusinessSummary") or ""
            if notes and len(notes) > 200:
                notes = notes[:197] + "..."
            return FundamentalSnapshot(
                symbol=symbol,
                revenue_growth=float(rev_growth) if rev_growth is not None else None,
                gross_margin=float(gross) if gross is not None else None,
                pe_ttm=float(pe) if pe is not None else None,
                notes=notes or None,
            )
        except Exception as e:
            print(f"Warning: yfinance fundamentals failed ({e}), using mock for {symbol}.", file=sys.stderr)
            return _mock_fundamentals(symbol)

    def get_news(self, symbol: str) -> list[NewsItem]:
        import sys
        try:
            import yfinance as yf
        except Exception:
            return _mock_news(symbol)
        try:
            ticker = yf.Ticker(symbol)
            raw = getattr(ticker, "news", None) or []
            out: list[NewsItem] = []
            now = datetime.utcnow()
            for i, item in enumerate(raw[:10]):
                if not isinstance(item, dict):
                    continue
                title = item.get("title") or "No title"
                summary = item.get("summary") or item.get("title") or title
                provider = item.get("publisher") or item.get("source") or "yfinance"
                pub_ts = item.get("providerPublishTime") or item.get("published_at")
                if isinstance(pub_ts, (int, float)):
                    published_at = datetime.utcfromtimestamp(pub_ts)
                else:
                    published_at = now - timedelta(hours=i)
                out.append(
                    NewsItem(
                        title=title[:200] if len(title) > 200 else title,
                        source=provider[:64] if isinstance(provider, str) else "yfinance",
                        published_at=published_at,
                        summary=(summary[:500] if len(summary) > 500 else summary) if isinstance(summary, str) else title,
                    )
                )
            if not out:
                return _mock_news(symbol)
            return out
        except Exception as e:
            print(f"Warning: yfinance news failed ({e}), using mock for {symbol}.", file=sys.stderr)
            return _mock_news(symbol)


def _fallback_price(symbol: str) -> PriceSnapshot:
    """Fallback when yfinance is unavailable (rate limit, network, etc.)."""
    return PriceSnapshot(symbol=symbol, last_price=122.5, change_pct=2.1, volume_ratio=1.3)


def _mock_fundamentals(symbol: str) -> FundamentalSnapshot:
    return FundamentalSnapshot(
        symbol=symbol,
        revenue_growth=0.28,
        gross_margin=0.63,
        pe_ttm=31.0,
        notes="Growth remains solid; valuation is elevated but not extreme.",
    )


def _mock_news(symbol: str) -> list[NewsItem]:
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


class MockDataProvider:
    """Minimal mock provider for local development."""

    def get_price(self, symbol: str) -> PriceSnapshot:
        return PriceSnapshot(symbol=symbol, last_price=122.5, change_pct=2.1, volume_ratio=1.3)

    def get_fundamentals(self, symbol: str) -> FundamentalSnapshot:
        return _mock_fundamentals(symbol)

    def get_news(self, symbol: str) -> list[NewsItem]:
        return _mock_news(symbol)
