"""
IBKR 单连接复用（根治频繁 connect/disconnect 导致 Error 1100 / 超时）。
一次 connect，整轮流程内复用同一连接；仅在本模块或 pipeline 显式 set 时生效。
"""
from __future__ import annotations

import asyncio
import os
import threading
from contextvars import ContextVar
from typing import Any

from ai_trading_research_system.execution.ibkr_client import (
    IBKRAccountSnapshotRaw,
    _connect_timeout,
    _host_port_client_id,
)

# 当前运行时的 IB 会话；由 weekly_paper 等 pipeline 在开始时 set、结束时 clear
_current_session: ContextVar["IBKRSession | None"] = ContextVar("ibkr_session", default=None)


def get_ibkr_session() -> "IBKRSession | None":
    """获取当前上下文中的 IB 会话；无则返回 None，调用方回退到「每次建连」。"""
    return _current_session.get()


def set_ibkr_session(session: "IBKRSession | None") -> None:
    """设置当前上下文的 IB 会话；pipeline 开始时 set(session)，结束时 set(None)。"""
    _current_session.set(session)


class IBKRSession:
    """
    单连接复用：connect 一次，在整轮运行内用同一 IB 连接拉 account、bars，最后 disconnect。
    内部在单独线程跑事件循环，同步接口通过 submit 到该 loop 实现。
    """

    def __init__(self, *, client_id: int = 1) -> None:
        self._client_id = client_id
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ib: Any = None

    def connect(self) -> bool:
        """同步连接；成功返回 True。"""
        h, p, cid = _host_port_client_id(None, None, self._client_id)
        timeout = _connect_timeout()
        result: list[bool] = []

        def run_in_thread():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            async def do_connect():
                from ib_insync import IB
                self._ib = IB()
                await self._ib.connectAsync(h, p, clientId=cid, timeout=timeout)
                return True

            try:
                ok = self._loop.run_until_complete(do_connect())
                result.append(ok)
            except Exception:
                result.append(False)

        self._thread = threading.Thread(target=run_in_thread, daemon=True)
        self._thread.start()
        self._thread.join()
        return bool(result and result[0])

    def disconnect(self) -> None:
        """同步断开并结束后台 loop。"""
        if self._loop is None or self._ib is None:
            return
        fut: asyncio.Future[None] = asyncio.run_coroutine_threadsafe(
            self._disconnect_async(), self._loop
        )
        try:
            fut.result(timeout=10)
        except Exception:
            pass
        self._ib = None
        self._loop = None
        self._thread = None

    async def _disconnect_async(self) -> None:
        if self._ib and getattr(self._ib, "client", None) and self._ib.client.isConnected():
            self._ib.disconnect()

    def get_account_snapshot_raw(self) -> IBKRAccountSnapshotRaw | None:
        """在已连接状态下拉取账户快照，不断开连接。"""
        if self._loop is None or self._ib is None:
            return None
        fut = asyncio.run_coroutine_threadsafe(
            self._get_account_snapshot_async(), self._loop
        )
        try:
            return fut.result(timeout=int(_connect_timeout()) + 10)
        except Exception:
            return None

    async def _get_account_snapshot_async(self) -> IBKRAccountSnapshotRaw | None:
        try:
            try:
                summary = await self._ib.accountSummaryAsync()
            except AttributeError:
                loop = asyncio.get_event_loop()
                summary = await loop.run_in_executor(None, lambda: self._ib.accountSummary())
            await asyncio.sleep(0.2)
            cash = equity = buying_power = 0.0
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
            positions = []
            for pos in self._ib.positions():
                sym = getattr(pos.contract, "symbol", None) or ""
                qty = float(pos.position)
                avg_cost = float(pos.avgCost) if pos.avgCost else 0.0
                market_value = qty * avg_cost if avg_cost else 0.0
                positions.append({"symbol": sym, "quantity": qty, "market_value": market_value})
            open_orders = []
            for t in self._ib.openTrades():
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

    def fetch_bars(
        self,
        symbol: str,
        duration_days: int,
        bar_size: str = "1 day",
        *,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """在已连接状态下拉取历史 K 线，不断开连接。"""
        if self._loop is None or self._ib is None:
            return []
        fut = asyncio.run_coroutine_threadsafe(
            self._fetch_bars_async(symbol, duration_days, bar_size, end_date),
            self._loop,
        )
        try:
            return fut.result(timeout=60)
        except Exception:
            return []

    async def _fetch_bars_async(
        self,
        symbol: str,
        duration_days: int,
        bar_size: str,
        end_date: str | None,
    ) -> list[dict[str, Any]]:
        from ib_insync import Stock, Index
        if symbol.startswith("^") or symbol.upper() == "VIX":
            sym = symbol.lstrip("^")
            contract = Index(sym, "CBOE", "USD") if sym == "VIX" else Stock(symbol, "SMART", "USD")
        else:
            contract = Stock(symbol, "SMART", "USD")
        end = end_date or ""
        duration_str = f"{max(1, duration_days)} D"
        bars = await self._ib.reqHistoricalDataAsync(
            contract,
            endDateTime=end,
            durationStr=duration_str,
            barSizeSetting=bar_size,
            whatToShow="TRADES",
            useRTH=True,
            formatDate=1,
            timeout=30,
        )
        if not bars:
            return []
        out = []
        for b in bars:
            out.append({
                "date": getattr(b, "date", None),
                "open": float(getattr(b, "open", 0) or 0),
                "high": float(getattr(b, "high", 0) or 0),
                "low": float(getattr(b, "low", 0) or 0),
                "close": float(getattr(b, "close", 0) or 0),
                "volume": float(getattr(b, "volume", 0) or 0),
            })
        return out


def _ibkr_configured() -> bool:
    return bool((os.environ.get("IBKR_HOST") or "").strip() and (os.environ.get("IBKR_PORT") or "").strip())
