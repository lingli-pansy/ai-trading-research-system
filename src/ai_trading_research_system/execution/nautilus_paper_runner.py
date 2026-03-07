"""
NautilusPaperRunner: Paper 路径由 NautilusTrader 短窗口回测执行，与 backtest 链同一套 AISignalStrategy。
"""
from __future__ import annotations

from ai_trading_research_system.strategy.translator import AISignal
from ai_trading_research_system.backtest.runner import run_paper_simulation, BacktestMetrics
from ai_trading_research_system.execution.paper import PaperRunnerResult


def _metrics_to_result(
    symbol: str,
    signal: AISignal,
    metrics: BacktestMetrics,
) -> PaperRunnerResult:
    status = "no_trade" if metrics.trade_count == 0 else "ok"
    reason = "wait_confirmation" if metrics.trade_count == 0 else ""
    return PaperRunnerResult(
        symbol=symbol,
        signal_action=signal.action,
        size_fraction=signal.allowed_position_size,
        order_done=metrics.trade_count > 0,
        order_result=None,
        message=f"nautilus paper: trades={metrics.trade_count} pnl={metrics.pnl:.2f} sharpe={metrics.sharpe:.4f}",
        trade_count=metrics.trade_count,
        pnl=metrics.pnl,
        status=status,
        reason=reason,
        used_nautilus=True,
    )


class NautilusPaperRunner:
    """
    Paper 执行由 NautilusTrader 短窗口回测完成，与 Strategy → Backtest 链同一套策略语义。
    接口与 PaperRunner 一致：inject(signal), start(), run_once(price), stop()。
    """

    def __init__(self, symbol: str, *, lookback_days: int = 5):
        self.symbol = symbol
        self._signal: AISignal | None = None
        self._started = False
        self._lookback_days = lookback_days

    def inject(self, signal: AISignal) -> None:
        self._signal = signal

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def run_once(
        self,
        price: float,
        *,
        use_mock: bool = False,
        daily_pnl_pct: float | None = None,
    ) -> PaperRunnerResult:
        """
        执行一次 Paper：用 NautilusTrader 对最近 lookback_days 天跑回测，信号已由 inject 注入。
        price 在本实现中未用于下单（由 Nautilus 使用历史 bar）；保留参数以兼容 PaperRunner 接口。
        """
        if not self._started:
            return PaperRunnerResult(
                symbol=self.symbol,
                signal_action="",
                size_fraction=0.0,
                order_done=False,
                message="Runner not started",
                status="no_trade",
                reason="runner_not_started",
                used_nautilus=True,
            )
        signal = self._signal
        if signal is None:
            return PaperRunnerResult(
                symbol=self.symbol,
                signal_action="",
                size_fraction=0.0,
                order_done=False,
                message="No signal injected",
                status="no_trade",
                reason="no_signal",
                used_nautilus=True,
            )
        metrics = run_paper_simulation(
            self.symbol,
            signal,
            lookback_days=self._lookback_days,
        )
        return _metrics_to_result(self.symbol, signal, metrics)
