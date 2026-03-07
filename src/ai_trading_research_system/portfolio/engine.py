from dataclasses import dataclass, field

@dataclass
class Position:
    symbol: str
    quantity: float
    avg_price: float

@dataclass
class PortfolioState:
    cash: float = 100000.0
    positions: dict[str, Position] = field(default_factory=dict)

class PortfolioEngine:
    def __init__(self, initial_cash: float = 100000.0):
        self.state = PortfolioState(cash=initial_cash)

    def target_quantity(self, symbol: str, price: float, size_fraction: float) -> float:
        budget = self.state.cash * size_fraction
        if budget <= 0 or price <= 0:
            return 0.0
        return round(budget / price, 4)

    def buy(self, symbol: str, price: float, quantity: float) -> None:
        cost = price * quantity
        if cost > self.state.cash:
            raise ValueError("Insufficient cash.")
        self.state.cash -= cost
        self.state.positions[symbol] = Position(symbol=symbol, quantity=quantity, avg_price=price)
