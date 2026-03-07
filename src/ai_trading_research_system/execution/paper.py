from dataclasses import dataclass

from ai_trading_research_system.portfolio.engine import PortfolioEngine


@dataclass
class PaperOrderResult:
    symbol: str
    action: str
    quantity: float
    price: float
    status: str


@dataclass
class PaperRunnerResult:
    """单次 Paper 执行结果（runner.run_once 返回值）。"""
    symbol: str
    signal_action: str
    size_fraction: float
    order_done: bool
    order_result: PaperOrderResult | None = None
    message: str = ""

class PaperTradingEngine:
    def __init__(self, portfolio: PortfolioEngine):
        self.portfolio = portfolio

    def buy(self, symbol: str, price: float, size_fraction: float) -> PaperOrderResult:
        qty = self.portfolio.target_quantity(symbol, price, size_fraction)
        if qty <= 0:
            return PaperOrderResult(symbol, "buy", 0.0, price, "rejected")
        self.portfolio.buy(symbol, price, qty)
        return PaperOrderResult(symbol, "buy", qty, price, "filled")
