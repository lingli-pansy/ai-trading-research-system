"""
BacktestRunner: run NautilusTrader backtest with AISignalStrategy and yfinance history.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pandas as pd

from ai_trading_research_system.strategy.translator import AISignal


@dataclass
class BacktestMetrics:
    sharpe: float
    max_drawdown: float
    win_rate: float
    pnl: float
    trade_count: int


def _default_date_range() -> tuple[str, str]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=90)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _symbol_to_venue(symbol: str) -> str:
    """Backtest uses simulated venue SIM so BacktestVenueConfig(name='SIM') matches."""
    return "SIM"


def _build_equity(symbol: str, venue: str):
    from nautilus_trader.model.instruments import Equity
    from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
    from nautilus_trader.model.currencies import USD
    from nautilus_trader.model.objects import Price, Quantity

    inst_id = InstrumentId(Symbol(symbol), Venue(venue))
    return Equity(
        instrument_id=inst_id,
        raw_symbol=Symbol(symbol),
        currency=USD,
        price_precision=2,
        price_increment=Price.from_str("0.01"),
        lot_size=Quantity.from_int(1),
        ts_event=0,
        ts_init=0,
    )


def _yfinance_history(symbol: str, start: str, end: str) -> pd.DataFrame:
    import yfinance as yf
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end, auto_adjust=True)
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    df = df[["open", "high", "low", "close", "volume"]]
    df.index = pd.to_datetime(df.index)
    df.index.name = "timestamp"
    return df


def _bars_to_catalog(
    catalog_path: Path,
    equity,
    bar_type,
    bars: list,
) -> None:
    from nautilus_trader.persistence.catalog import ParquetDataCatalog

    if catalog_path.exists():
        shutil.rmtree(catalog_path)
    catalog_path.mkdir(parents=True)
    catalog = ParquetDataCatalog(str(catalog_path))
    catalog.write_data([equity])
    catalog.write_data(bars)


def run_backtest(
    symbol: str,
    signal: AISignal,
    start_date: str | None = None,
    end_date: str | None = None,
    catalog_dir: Path | None = None,
) -> BacktestMetrics:
    """
    Run backtest for symbol with given signal. Uses yfinance for history.
    Returns sharpe, max_drawdown, win_rate, pnl, trade_count.
    """
    from nautilus_trader.model.data import BarType, BarSpecification
    from nautilus_trader.model.enums import BarAggregation, PriceType
    from nautilus_trader.persistence.wranglers import BarDataWrangler
    from nautilus_trader.backtest.node import (
        BacktestNode,
        BacktestRunConfig,
        BacktestEngineConfig,
        BacktestVenueConfig,
        BacktestDataConfig,
    )
    from nautilus_trader.config import ImportableStrategyConfig, LoggingConfig
    from nautilus_trader.model.data import Bar

    start_date = start_date or _default_date_range()[0]
    end_date = end_date or _default_date_range()[1]
    venue = _symbol_to_venue(symbol)
    equity = _build_equity(symbol, venue)
    inst_id = equity.id
    bar_spec = BarSpecification(1, BarAggregation.DAY, PriceType.LAST)
    bar_type = BarType(inst_id, bar_spec)
    wrangler = BarDataWrangler(bar_type, equity)

    df = _yfinance_history(symbol, start_date, end_date)
    if df.empty:
        return BacktestMetrics(sharpe=0.0, max_drawdown=0.0, win_rate=0.0, pnl=0.0, trade_count=0)

    bars = wrangler.process(df)
    if not bars:
        return BacktestMetrics(sharpe=0.0, max_drawdown=0.0, win_rate=0.0, pnl=0.0, trade_count=0)

    catalog_path = catalog_dir or Path.cwd() / ".backtest_catalog"
    _bars_to_catalog(catalog_path, equity, bar_type, bars)

    start_time = df.index.min().isoformat()
    end_time = df.index.max().isoformat()

    venue_config = BacktestVenueConfig(
        name="SIM",
        oms_type="NETTING",
        account_type="MARGIN",
        base_currency="USD",
        starting_balances=["1_000_000 USD"],
    )
    data_config = BacktestDataConfig(
        catalog_path=str(catalog_path),
        data_cls=Bar,
        instrument_id=inst_id,
        start_time=start_time,
        end_time=end_time,
    )
    strategy_config = ImportableStrategyConfig(
        strategy_path="ai_trading_research_system.strategy.ai_signal:AISignalStrategy",
        config_path="ai_trading_research_system.strategy.ai_signal:AISignalStrategyConfig",
        config={
            "instrument_id": inst_id,
            "bar_type": bar_type,
            "size_fraction": signal.allowed_position_size,
            "action": signal.action,
            "notional_per_trade": "10000",
        },
    )
    engine_config = BacktestEngineConfig(
        strategies=[strategy_config],
        logging=LoggingConfig(log_level="ERROR"),
    )
    run_config = BacktestRunConfig(
        engine=engine_config,
        venues=[venue_config],
        data=[data_config],
    )
    node = BacktestNode(configs=[run_config])
    results = node.run()
    node.dispose()

    if not results:
        return BacktestMetrics(sharpe=0.0, max_drawdown=0.0, win_rate=0.0, pnl=0.0, trade_count=0)
    r = results[0]
    stats_returns = getattr(r, "stats_returns", {}) or {}
    stats_pnls = getattr(r, "stats_pnls", {}) or {}
    total_orders = getattr(r, "total_orders", 0) or 0
    total_positions = getattr(r, "total_positions", 0) or 0
    pnl = 0.0
    for venue_currency, values in stats_pnls.items():
        if isinstance(values, dict) and "total" in values:
            pnl += float(values["total"])
        elif isinstance(values, (int, float)):
            pnl += float(values)
    sharpe = float(stats_returns.get("sharpe_ratio", 0.0)) if isinstance(stats_returns.get("sharpe_ratio"), (int, float)) else 0.0
    max_dd = float(stats_returns.get("max_drawdown", 0.0)) if isinstance(stats_returns.get("max_drawdown"), (int, float)) else 0.0
    win_rate = float(stats_returns.get("win_rate", 0.0)) if isinstance(stats_returns.get("win_rate"), (int, float)) else 0.0
    return BacktestMetrics(
        sharpe=sharpe,
        max_drawdown=max_dd,
        win_rate=win_rate,
        pnl=pnl,
        trade_count=max(total_orders, total_positions),
    )
