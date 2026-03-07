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
