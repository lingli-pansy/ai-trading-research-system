"""
AISignalStrategy: NautilusTrader Strategy that trades based on Contract-derived signal.
On first bar, if action is paper_buy and size_fraction > 0, submits one market buy.
"""
from __future__ import annotations

from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.objects import Quantity
from nautilus_trader.trading.strategy import Strategy


class AISignalStrategyConfig(StrategyConfig, frozen=True):
    """Config for AISignalStrategy: instrument, bar type, and signal (size_fraction)."""

    instrument_id: InstrumentId
    bar_type: BarType
    size_fraction: float = 0.0  # 0 = no trade, 0.25 = probe_small, 1.0 = full
    action: str = "wait"  # "paper_buy" | "no_trade" | "wait" | "watch_only"
    notional_per_trade: Decimal = Decimal("10000")  # base notional in USD for sizing


class AISignalStrategy(Strategy):
    """
    Submits at most one market buy on the first bar if action == "paper_buy" and size_fraction > 0.
    """

    def __init__(self, config: AISignalStrategyConfig) -> None:
        super().__init__(config)
        self._instrument: Instrument | None = None
        self._has_traded = False

    def on_start(self) -> None:
        self._instrument = self.cache.instrument(self.config.instrument_id)
        if self._instrument is None:
            self.log.error(f"Instrument not found: {self.config.instrument_id}")
            self.stop()
            return
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar) -> None:
        if self._instrument is None:
            return
        if self._has_traded:
            return
        if self.config.action != "paper_buy" or self.config.size_fraction <= 0:
            return
        price = float(bar.close)
        if price <= 0:
            return
        # notional = notional_per_trade * size_fraction, quantity = notional / price
        notional = float(self.config.notional_per_trade) * self.config.size_fraction
        qty = notional / price
        quantity = self._instrument.make_qty(qty)
        if quantity <= 0:
            return
        order = self.order_factory.market(
            instrument_id=self.config.instrument_id,
            order_side=OrderSide.BUY,
            quantity=quantity,
            time_in_force=TimeInForce.GTC,
        )
        self.submit_order(order)
        self._has_traded = True

    def on_stop(self) -> None:
        self.unsubscribe_bars(self.config.bar_type)
