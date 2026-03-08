"""
IBKR Paper 客户端：连接 TWS/Gateway，下单（实盘前 L5）。
依赖 ib_insync；仅当 IBKR_HOST/IBKR_PORT 配置且 run_paper 走 IBKR 路径时使用。
连接稳定性：使用 IBKR_CONNECT_TIMEOUT、断开后延迟 IBKR_DISCONNECT_DELAY，避免 Gateway 未释放 client id 即重连。
Snapshot 拆分为 account_summary / positions / open_orders，单独超时与日志，支持部分成功。
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Gateway 在 disconnect 后不会立即释放 client id，短时间用同一 id 重连易导致 Error 1100 / socket closing
_DEFAULT_CONNECT_TIMEOUT = 60
_DEFAULT_DISCONNECT_DELAY = 1.0  # 断开后等待秒数再返回，便于 Gateway 释放
_DEFAULT_POSITIONS_TIMEOUT = 45   # positions 请求单独超时（秒），≥10
_DEFAULT_WARMUP_DELAY = 2.0       # connect 后 1–2s 再请求 snapshot，避免冷启动 timeout
_POSITIONS_RETRIES = 1           # positions 超时后重试次数


def _host_port_client_id(host: str | None, port: int | None, client_id: int):
    h = host or (os.environ.get("IBKR_HOST") or "127.0.0.1").strip()
    p = port if port is not None else int((os.environ.get("IBKR_PORT") or "4002").strip())
    cid = int(os.environ.get("IBKR_CLIENT_ID") or str(client_id))
    return h, p, cid


def _connect_timeout() -> float:
    try:
        return float(os.environ.get("IBKR_CONNECT_TIMEOUT", _DEFAULT_CONNECT_TIMEOUT))
    except (ValueError, TypeError):
        return _DEFAULT_CONNECT_TIMEOUT


def _disconnect_delay() -> float:
    try:
        return float(os.environ.get("IBKR_DISCONNECT_DELAY", _DEFAULT_DISCONNECT_DELAY))
    except (ValueError, TypeError):
        return _DEFAULT_DISCONNECT_DELAY


def _positions_timeout() -> float:
    try:
        return float(os.environ.get("IBKR_POSITIONS_TIMEOUT", _DEFAULT_POSITIONS_TIMEOUT))
    except (ValueError, TypeError):
        return _DEFAULT_POSITIONS_TIMEOUT


def _warmup_delay() -> float:
    try:
        return float(os.environ.get("IBKR_WARMUP_DELAY", _DEFAULT_WARMUP_DELAY))
    except (ValueError, TypeError):
        return _DEFAULT_WARMUP_DELAY


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
        await ib.connectAsync(h, p, clientId=cid, timeout=_connect_timeout())
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
        await asyncio.sleep(_disconnect_delay())


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
        await ib.connectAsync(h, p, clientId=cid, timeout=_connect_timeout())
        return True
    except Exception:
        return False
    finally:
        ib.disconnect()
        await asyncio.sleep(_disconnect_delay())


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
    failed_steps: list[str] = field(default_factory=list)  # 子步骤失败时记录，如 ["positions"]


async def _get_account_snapshot_async(
    host: str | None = None,
    port: int | None = None,
    client_id: int = 1,
) -> IBKRAccountSnapshotRaw | None:
    """从 TWS/Gateway 拉取 paper 账户快照。拆分为 account_summary / positions / open_orders，支持部分成功。"""
    from ib_insync import IB

    h, p, cid = _host_port_client_id(host, port, client_id)
    ib = IB()
    failed_steps: list[str] = []
    try:
        t_connect_start = time.perf_counter()
        await ib.connectAsync(h, p, clientId=cid, timeout=_connect_timeout())
        warmup = _warmup_delay()
        if warmup > 0:
            await asyncio.sleep(warmup)
        logger.info("[ib] IB connection latency=%.2fs", time.perf_counter() - t_connect_start)
        t_snapshot_start = time.perf_counter()
        loop = asyncio.get_event_loop()
        pos_timeout = _positions_timeout()
        open_orders_timeout = min(30, max(15, int(pos_timeout * 0.5)))

        # --- account_summary ---
        t0 = time.perf_counter()
        logger.info("[ib] account_summary start")
        try:
            try:
                summary = await ib.accountSummaryAsync()
            except AttributeError:
                summary = await loop.run_in_executor(None, lambda: ib.accountSummary())
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning("[ib] account_summary failed: %s", e)
            failed_steps.append("account_summary")
            summary = []
        elapsed = time.perf_counter() - t0
        logger.info("[ib] account_summary end (latency=%.2fs)", elapsed)

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

        # --- positions（timeout≥10s，超时 retry 1 次）---
        t1 = time.perf_counter()
        logger.info("[ib] positions start")
        positions = await _fetch_positions_client(ib, loop, pos_timeout)
        if positions is None:
            logger.info("[ib] positions retry 1")
            positions = await _fetch_positions_client(ib, loop, pos_timeout)
        if positions is None:
            failed_steps.append("positions")
        logger.info("[ib] positions end (latency=%.2fs)", time.perf_counter() - t1)
        positions = positions if positions is not None else []

        # --- open_orders ---
        open_orders: list[dict] = []
        t2 = time.perf_counter()
        logger.info("[ib] open_orders start")
        try:
            raw_trades = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: list(ib.openTrades())),
                timeout=open_orders_timeout,
            )
            for t in raw_trades:
                if t.orderStatus.status in ("PendingSubmit", "PreSubmitted", "Submitted", "ApiPending"):
                    open_orders.append({
                        "symbol": getattr(t.contract, "symbol", ""),
                        "side": "BUY" if "BUY" in str(t.order.action) else "SELL",
                        "quantity": float(t.order.totalQuantity or 0),
                        "status": t.orderStatus.status,
                    })
        except asyncio.TimeoutError:
            logger.warning("[ib] open_orders timed out (timeout=%.0fs)", open_orders_timeout)
            failed_steps.append("open_orders")
        except Exception as e:
            logger.warning("[ib] open_orders failed: %s", e)
            failed_steps.append("open_orders")
        logger.info("[ib] open_orders end (latency=%.2fs)", time.perf_counter() - t2)

        # 至少 account_summary 成功即返回；positions 失败时 partial_real，不 fallback mock
        if "account_summary" in failed_steps and equity == 0.0 and cash == 0.0:
            return None
        logger.info("[ib] account snapshot total latency=%.2fs", time.perf_counter() - t_snapshot_start)
        return IBKRAccountSnapshotRaw(
            cash=cash,
            equity=equity,
            buying_power=buying_power,
            positions=positions,
            open_orders=open_orders,
            failed_steps=failed_steps,
        )
    except Exception as e:
        logger.warning("IB snapshot: connect or overall failed: %s", e)
        return None
    finally:
        ib.disconnect()
        await asyncio.sleep(_disconnect_delay())


async def _fetch_positions_client(ib: Any, loop: asyncio.AbstractEventLoop, pos_timeout: float) -> list[dict] | None:
    """拉取 positions，超时或异常返回 None。timeout 至少 10s。"""
    try:
        raw = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: list(ib.positions())),
            timeout=max(10.0, pos_timeout),
        )
        out = []
        for pos in raw:
            sym = getattr(pos.contract, "symbol", None) or ""
            qty = float(pos.position)
            avg_cost = float(pos.avgCost) if pos.avgCost else 0.0
            market_value = qty * avg_cost if avg_cost else 0.0
            out.append({"symbol": sym, "quantity": qty, "market_value": market_value})
        return out
    except asyncio.TimeoutError:
        logger.warning("[ib] positions request timed out (timeout=%.0fs)", max(10.0, pos_timeout))
        return None
    except Exception as e:
        logger.warning("[ib] positions failed: %s", e)
        return None


def get_ibkr_account_snapshot_raw(
    host: str | None = None,
    port: int | None = None,
    client_id: int = 1,
    retries: int = 2,
) -> IBKRAccountSnapshotRaw | None:
    """同步封装：拉取 IBKR 账户快照。若有 IBKRSession 复用则仅用该连接，绝不再用同一 clientId 建第二连接。"""
    try:
        from ai_trading_research_system.execution.ibkr_session import get_ibkr_session
        session = get_ibkr_session()
        if session is None:
            logger.warning("[ib] no session in context, snapshot will try standalone connect or fallback")
        if session is not None:
            out = session.get_account_snapshot_raw()
            if out is None:
                logger.warning("[ib] session snapshot returned None (timeout or failure), snapshot will use fallback")
            return out  # 有 session 时只走这一条路，返回 None 也不 fallback，避免 clientId 重复连接
    except Exception as e:
        logger.debug("get_ibkr_account_snapshot_raw (session): %s", e)
        try:
            from ai_trading_research_system.execution.ibkr_session import get_ibkr_session
            if get_ibkr_session() is not None:
                return None  # session 存在但调用失败，不尝试新连接，否则会触发 Error 326
        except Exception:
            pass
    last_err: Exception | None = None
    for attempt in range(max(1, retries + 1)):
        try:
            out = asyncio.run(_get_account_snapshot_async(host=host, port=port, client_id=client_id))
            if out is not None:
                return out
        except Exception as e:
            last_err = e
            logger.debug("get_ibkr_account_snapshot_raw attempt %s: %s", attempt + 1, e)
        if attempt < retries:
            time.sleep(2.0)
    return None
