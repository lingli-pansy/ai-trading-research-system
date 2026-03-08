"""
IBKR Paper 客户端：连接 TWS/Gateway，下单（实盘前 L5）。
依赖 ib_insync；仅当 IBKR_HOST/IBKR_PORT 配置且 run_paper 走 IBKR 路径时使用。
ib_insync 为 asyncio，需在 asyncio.run() 内执行连接与下单。
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass


@dataclass
class IBKROrderResult:
    filled: bool
    order_id: int | None
    message: str
    placed: bool = False  # True 表示订单已被经纪商接受（含 PendingSubmit/Submitted/Filled）


def _host_port_client_id(host: str | None, port: int | None, client_id: int):
    h = host or (os.environ.get("IBKR_HOST") or "127.0.0.1").strip()
    p = port if port is not None else int((os.environ.get("IBKR_PORT") or "4002").strip())
    cid = int(os.environ.get("IBKR_CLIENT_ID") or str(client_id))
    return h, p, cid


async def _place_market_buy_async(
    symbol: str,
    quantity: float,
    *,
    host: str | None = None,
    port: int | None = None,
    client_id: int = 1,
) -> IBKROrderResult:
    from ib_insync import IB, Stock, MarketOrder

    h, p, cid = _host_port_client_id(host, port, client_id)
    ib = IB()
    try:
        await ib.connectAsync(h, p, clientId=cid)
        contract = Stock(symbol, "SMART", "USD")
        # 显式 TIF=DAY，避免 TWS order preset 导致 Error 10349 取消
        order = MarketOrder("BUY", round(quantity), tif="DAY")
        trade = ib.placeOrder(contract, order)
        await asyncio.sleep(3)
        status = trade.orderStatus.status
        placed = status in ("Filled", "Submitted", "PreSubmitted", "PendingSubmit")
        if placed:
            return IBKROrderResult(
                filled=(status == "Filled"),
                order_id=trade.order.orderId,
                message=status,
                placed=True,
            )
        return IBKROrderResult(
            filled=False,
            order_id=trade.order.orderId,
            message=status or str(trade.log),
            placed=False,
        )
    except Exception as e:
        return IBKROrderResult(filled=False, order_id=None, message=str(e), placed=False)
    finally:
        ib.disconnect()


def place_market_buy(
    symbol: str,
    quantity: float,
    *,
    host: str | None = None,
    port: int | None = None,
    client_id: int = 1,
) -> IBKROrderResult:
    """
    市价买入 quantity 股 symbol（美股，SMART 路由）。
    调用方需已确认 signal 为 paper_buy 且 quantity > 0。
    """
    return asyncio.run(_place_market_buy_async(symbol, quantity, host=host, port=port, client_id=client_id))


async def _check_connected_async(
    host: str | None = None,
    port: int | None = None,
    client_id: int = 1,
) -> bool:
    from ib_insync import IB

    h, p, cid = _host_port_client_id(host, port, client_id)
    ib = IB()
    try:
        await ib.connectAsync(h, p, clientId=cid)
        return True
    except Exception:
        return False
    finally:
        ib.disconnect()


def check_connected(host: str | None = None, port: int | None = None, client_id: int = 1) -> bool:
    """检测是否可连接 TWS/Gateway（用于 L7 深度验证，可选）。"""
    try:
        return asyncio.run(_check_connected_async(host=host, port=port, client_id=client_id))
    except Exception:
        return False


@dataclass
class IBKRAccountSnapshotRaw:
    """IBKR 账户原始快照，供 autonomous.account_snapshot 转为 AccountSnapshot。"""
    cash: float
    equity: float
    buying_power: float
    positions: list[dict]
    open_orders: list[dict]


async def _get_account_snapshot_async(
    host: str | None = None,
    port: int | None = None,
    client_id: int = 1,
) -> IBKRAccountSnapshotRaw | None:
    """从 TWS/Gateway 拉取 paper 账户快照。失败返回 None。"""
    from ib_insync import IB

    h, p, cid = _host_port_client_id(host, port, client_id)
    ib = IB()
    try:
        await ib.connectAsync(h, p, clientId=cid)
        # 兼容：部分 ib_insync 版本有 accountSummaryAsync，否则用 executor 跑同步 accountSummary
        try:
            summary = await ib.accountSummaryAsync()
        except AttributeError:
            loop = asyncio.get_event_loop()
            summary = await loop.run_in_executor(None, lambda: ib.accountSummary())
        await asyncio.sleep(0.3)
        cash = 0.0
        equity = 0.0
        buying_power = 0.0
        for acc in summary:
            if acc.tag == "TotalCashValue":
                try:
                    cash = float(acc.value)
                except (ValueError, TypeError):
                    pass
            elif acc.tag == "NetLiquidation":
                try:
                    equity = float(acc.value)
                except (ValueError, TypeError):
                    pass
            elif acc.tag == "BuyingPower":
                try:
                    buying_power = float(acc.value)
                except (ValueError, TypeError):
                    pass
            elif acc.tag == "EquityWithLoanValue" and equity == 0.0:
                try:
                    equity = float(acc.value)
                except (ValueError, TypeError):
                    pass
        if equity == 0.0 and cash != 0.0:
            equity = cash
        # Positions
        positions: list[dict] = []
        for pos in ib.positions():
            sym = getattr(pos.contract, "symbol", None) or ""
            qty = float(pos.position)
            avg_cost = float(pos.avgCost) if pos.avgCost else 0.0
            market_value = qty * avg_cost if avg_cost else 0.0
            positions.append({"symbol": sym, "quantity": qty, "market_value": market_value})
        # Open orders
        open_orders: list[dict] = []
        for t in ib.openTrades():
            if t.orderStatus.status in ("PendingSubmit", "PreSubmitted", "Submitted", "ApiPending"):
                open_orders.append({
                    "symbol": getattr(t.contract, "symbol", ""),
                    "side": "BUY" if "BUY" in str(t.order.action) else "SELL",
                    "quantity": float(t.order.totalQuantity or 0),
                    "status": t.orderStatus.status,
                })
        return IBKRAccountSnapshotRaw(
            cash=cash,
            equity=equity,
            buying_power=buying_power,
            positions=positions,
            open_orders=open_orders,
        )
    except Exception:
        return None
    finally:
        ib.disconnect()


def get_ibkr_account_snapshot_raw(
    host: str | None = None,
    port: int | None = None,
    client_id: int = 1,
) -> IBKRAccountSnapshotRaw | None:
    """同步封装：拉取 IBKR 账户快照，失败返回 None。"""
    try:
        return asyncio.run(_get_account_snapshot_async(host=host, port=port, client_id=client_id))
    except Exception:
        return None
