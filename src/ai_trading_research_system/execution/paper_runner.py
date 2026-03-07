"""
PaperRunner: 封装 Paper 引擎与策略挂载，支持一次注入或持续运行。
默认使用 NautilusTrader 短窗口回测（NautilusPaperRunner）；use_nautilus=False 时使用本仓 PaperTradingEngine（过渡层，将废弃）。
"""
from __future__ import annotations

from dataclasses import dataclass

from ai_trading_research_system.strategy.translator import AISignal
from ai_trading_research_system.portfolio.engine import PortfolioEngine
from ai_trading_research_system.execution.paper import (
    PaperTradingEngine,
    PaperOrderResult,
    PaperRunnerResult,
)
from ai_trading_research_system.execution.nautilus_paper_runner import NautilusPaperRunner


def _check_position_limit(
    engine: PaperTradingEngine,
    symbol: str,
    price: float,
    size_fraction: float,
    max_position_pct: float | None,
) -> bool:
    """仓位上限：下单后该标的市值占组合权益比例不得超过 max_position_pct（0~100）。"""
    if max_position_pct is None or max_position_pct <= 0:
        return True
    state = engine.portfolio.state
    cash = state.cash
    positions = state.positions
    current_qty = positions[symbol].quantity if symbol in positions else 0.0
    current_sym_value = current_qty * price
    new_qty = engine.portfolio.target_quantity(symbol, price, size_fraction)
    new_value = new_qty * price
    total_equity = cash + sum(
        p.quantity * (price if p.symbol == symbol else p.avg_price)
        for p in positions.values()
    )
    if total_equity <= 0:
        return True
    position_pct_after = (current_sym_value + new_value) / total_equity * 100.0
    return position_pct_after <= max_position_pct


def _check_daily_stop(daily_pnl_pct: float | None, daily_stop_loss_pct: float | None) -> bool:
    """单日止损：若当日已实现+未实现亏损达到 daily_stop_loss_pct（如 -2 表示 -2%），则禁止新开仓。"""
    if daily_stop_loss_pct is None or daily_stop_loss_pct <= 0:
        return True
    if daily_pnl_pct is None:
        return True
    return daily_pnl_pct > -daily_stop_loss_pct


class PaperRunner:
    """
    封装 Paper 引擎，支持注入 Contract 派生信号并执行一次或持续运行。
    默认 use_nautilus=True：由 NautilusTrader 短窗口回测执行（与 backtest 链同一套策略）。
    use_nautilus=False：使用本仓 PaperTradingEngine（过渡层，将废弃）。
    """

    def __init__(
        self,
        symbol: str,
        *,
        initial_cash: float = 100_000.0,
        max_position_pct: float | None = None,
        daily_stop_loss_pct: float | None = None,
        use_nautilus: bool = True,
        paper_lookback_days: int = 5,
    ):
        self.symbol = symbol
        self._use_nautilus = use_nautilus
        self._nautilus: NautilusPaperRunner | None = (
            NautilusPaperRunner(symbol, lookback_days=paper_lookback_days) if use_nautilus else None
        )
        self._engine: PaperTradingEngine | None = (
            PaperTradingEngine(PortfolioEngine(initial_cash=initial_cash)) if not use_nautilus else None
        )
        self._signal: AISignal | None = None
        self._started = False
        self._max_position_pct = max_position_pct
        self._daily_stop_loss_pct = daily_stop_loss_pct

    def inject(self, signal: AISignal) -> None:
        """注入 Research → Translator 产出的信号，完成策略挂载。"""
        self._signal = signal
        if self._nautilus is not None:
            self._nautilus.inject(signal)

    def start(self) -> None:
        """启动 Runner，策略已挂载后可调用 run_once。"""
        self._started = True
        if self._nautilus is not None:
            self._nautilus.start()

    def stop(self) -> None:
        """停止 Runner。"""
        self._started = False
        if self._nautilus is not None:
            self._nautilus.stop()

    def run_once(
        self,
        price: float,
        *,
        use_mock: bool = False,
        daily_pnl_pct: float | None = None,
    ) -> PaperRunnerResult:
        """
        执行一次 Paper 周期。
        use_nautilus=True：NautilusTrader 短窗口回测，与 backtest 链同一套策略。
        use_nautilus=False：本仓 PaperTradingEngine 按当前价下单（过渡层）。
        """
        if self._nautilus is not None:
            return self._nautilus.run_once(price, use_mock=use_mock, daily_pnl_pct=daily_pnl_pct)
        return self._run_once_legacy(price, daily_pnl_pct)

    def _run_once_legacy(self, price: float, daily_pnl_pct: float | None) -> PaperRunnerResult:
        """Legacy path: PaperTradingEngine (use_nautilus=False)."""
        def _legacy_result(
            signal_action: str = "",
            size_fraction: float = 0.0,
            order_done: bool = False,
            order_result: PaperOrderResult | None = None,
            message: str = "",
        ) -> PaperRunnerResult:
            return PaperRunnerResult(
                symbol=self.symbol,
                signal_action=signal_action,
                size_fraction=size_fraction,
                order_done=order_done,
                order_result=order_result,
                message=message,
                trade_count=1 if order_done else 0,
                pnl=0.0,
                status="ok" if order_done else "no_trade",
                reason=message if not order_done else "",
                used_nautilus=False,
            )

        if self._engine is None:
            return _legacy_result(message="Legacy engine not initialized")
        if not self._started:
            return _legacy_result(message="Runner not started")
        signal = self._signal
        if signal is None:
            return _legacy_result(message="No signal injected")
        if signal.action != "paper_buy" or signal.allowed_position_size <= 0:
            return _legacy_result(
                signal_action=signal.action,
                size_fraction=signal.allowed_position_size,
                message=f"Signal does not allow buy: {signal.rationale}",
            )
        if price <= 0:
            return _legacy_result(
                signal_action=signal.action,
                size_fraction=signal.allowed_position_size,
                message="Invalid price",
            )
        if not _check_position_limit(
            self._engine,
            self.symbol,
            price,
            signal.allowed_position_size,
            self._max_position_pct,
        ):
            return _legacy_result(
                signal_action=signal.action,
                size_fraction=signal.allowed_position_size,
                message="Position limit exceeded",
            )
        if not _check_daily_stop(daily_pnl_pct, self._daily_stop_loss_pct):
            return _legacy_result(
                signal_action=signal.action,
                size_fraction=signal.allowed_position_size,
                message="Daily stop loss triggered",
            )
        try:
            result = self._engine.buy(
                self.symbol,
                price=price,
                size_fraction=signal.allowed_position_size,
            )
            return _legacy_result(
                signal_action=signal.action,
                size_fraction=signal.allowed_position_size,
                order_done=result.status == "filled",
                order_result=result,
                message=result.status,
            )
        except Exception as e:
            return _legacy_result(
                signal_action=signal.action,
                size_fraction=signal.allowed_position_size,
                message=str(e),
            )
