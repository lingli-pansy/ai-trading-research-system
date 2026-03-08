"""
IBKR 单连接复用（根治频繁 connect/disconnect 导致 Error 1100 / 超时）。
一次 connect，整轮流程内复用同一连接；仅在本模块或 pipeline 显式 set 时生效。
Snapshot 拆分为 account_summary / positions / open_orders，单独超时与日志。
"""
from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from contextvars import ContextVar
from typing import Any

logger = logging.getLogger(__name__)

from ai_trading_research_system.execution.ibkr_client import (
    IBKRAccountSnapshotRaw,
    _connect_timeout,
    _host_port_client_id,
    _positions_timeout,
    _warmup_delay,
)

def _ib_end_datetime(end_date: str | None) -> str:
    """IB 要求 endDateTime 为空或 UTC 格式 yyyymmdd-HH:mm:ss（见 TWS API Historical Bar Data）。空表示当前。"""
    if not end_date or not end_date.strip():
        return ""
    s = end_date.strip()
    if len(s) == 8 and s.isdigit():
        return f"{s}-23:59:59"
    if "-" in s:
        parts = s.split(" ")[0].split("-")
        if len(parts) >= 3:
            try:
                y, m, d = parts[0], parts[1].zfill(2), parts[2].zfill(2)
                return f"{y}{m}{d}-23:59:59"
            except Exception:
                pass
    return ""


# 当前运行时的 IB 会话；由 weekly_paper 等 pipeline 在开始时 set、结束时 clear
_current_session: ContextVar["IBKRSession | None"] = ContextVar("ibkr_session", default=None)
# 供工作线程使用：ThreadPoolExecutor 内线程不继承 ContextVar，research 线程通过此处复用同一连接，避免 client_id=2 再建连导致 Error 326
_fallback_session: "IBKRSession | None" = None


class PositionCache:
    """订阅式 positions 结果缓存；读取 snapshot 时使用。"""
    __slots__ = ("positions", "ts")

    def __init__(self) -> None:
        self.positions: list[dict] = []
        self.ts: float = 0.0

    def set(self, positions: list[dict]) -> None:
        self.positions = list(positions)
        self.ts = time.monotonic()

    def get_valid(self, max_age_sec: float = 60.0) -> list[dict] | None:
        if not self.positions and self.ts == 0.0:
            return None
        if time.monotonic() - self.ts <= max_age_sec:
            return self.positions
        return None


def get_ibkr_session() -> "IBKRSession | None":
    """获取当前上下文中的 IB 会话；无则返回 fallback（供工作线程复用），再无则 None。"""
    try:
        ctx = _current_session.get()
        if ctx is not None:
            return ctx
    except LookupError:
        pass
    return _fallback_session


def set_ibkr_session(session: "IBKRSession | None") -> None:
    """设置当前上下文的 IB 会话；pipeline 开始时 set(session)，结束时 set(None)。同时更新 fallback 供工作线程使用。"""
    global _fallback_session
    _fallback_session = session
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
        self._position_cache = PositionCache()

    def connect(self) -> bool:
        """同步连接；成功返回 True。冷启动：connect 后 sleep 1–2s 再允许请求。"""
        h, p, cid = _host_port_client_id(None, None, self._client_id)
        timeout = _connect_timeout()
        result: list[bool] = []
        loop_running = threading.Event()

        def run_in_thread():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            async def do_connect():
                from ib_insync import IB
                t0 = time.perf_counter()
                self._ib = IB()
                await self._ib.connectAsync(h, p, clientId=cid, timeout=timeout)
                warmup = _warmup_delay()
                if warmup > 0:
                    await asyncio.sleep(warmup)
                logger.info("[ib] IB connection latency=%.2fs", time.perf_counter() - t0)
                return True

            try:
                ok = self._loop.run_until_complete(do_connect())
                result.append(ok)
                if ok:
                    loop_running.set()  # 先通知「即将 run_forever」，再进入，避免主线程在 loop 未跑时就调 snapshot
                    self._loop.run_forever()
            except Exception:
                result.append(False)

        self._thread = threading.Thread(target=run_in_thread, daemon=True)
        self._thread.start()
        for _ in range(500):
            if result:
                if result[0]:
                    loop_running.wait(timeout=5.0)  # 确保事件循环已进入 run_forever
                return bool(result and result[0])
            time.sleep(0.05)
        return False

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
        if self._loop and self._loop.is_running():
            self._loop.stop()

    def _parse_positions_list(self, raw: list) -> list[dict]:
        out = []
        for pos in raw:
            sym = getattr(pos.contract, "symbol", None) or ""
            qty = float(pos.position)
            avg_cost = float(pos.avgCost) if pos.avgCost else 0.0
            market_value = qty * avg_cost if avg_cost else 0.0
            out.append({"symbol": sym, "quantity": qty, "market_value": market_value})
        return out

    async def _fetch_positions_session(self, pos_timeout: float) -> list[dict] | None:
        """订阅式：reqPositions() → 等待 positionEnd() → 解析并缓存。超时或异常返回 None。"""
        pos_timeout = max(10.0, pos_timeout)
        cached = self._position_cache.get_valid(max_age_sec=60.0)
        if cached is not None:
            return cached
        ev = getattr(self._ib, "positionEndEvent", None)
        if ev is not None:
            try:
                if hasattr(ev, "clear"):
                    ev.clear()
                self._ib.reqPositions()
                await asyncio.wait_for(ev.wait(), timeout=pos_timeout)
                raw = list(self._ib.positions())
                if getattr(self._ib, "cancelPositions", None):
                    self._ib.cancelPositions()
                return self._parse_positions_list(raw)
            except asyncio.TimeoutError:
                logger.warning("[ib] positions request timed out (timeout=%.0fs)", pos_timeout)
                if getattr(self._ib, "cancelPositions", None):
                    try:
                        self._ib.cancelPositions()
                    except Exception:
                        pass
                return None
            except Exception as e:
                logger.warning("[ib] positions failed: %s", e)
                return None
        # 无 positionEndEvent 时回退为同步 positions() + timeout
        try:
            loop = asyncio.get_event_loop()
            raw = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: list(self._ib.positions())),
                timeout=pos_timeout,
            )
            return self._parse_positions_list(raw)
        except asyncio.TimeoutError:
            logger.warning("[ib] positions request timed out (timeout=%.0fs)", pos_timeout)
            return None
        except Exception as e:
            logger.warning("[ib] positions failed: %s", e)
            return None

    def get_account_snapshot_raw(self) -> IBKRAccountSnapshotRaw | None:
        """在已连接状态下拉取账户快照，不断开连接。拆分为 account_summary/positions/open_orders。"""
        if self._loop is None or self._ib is None:
            logger.warning("[ib] session get_account_snapshot_raw: _loop or _ib is None")
            return None
        total_timeout = int(_connect_timeout()) + int(_positions_timeout()) + 20
        fut = asyncio.run_coroutine_threadsafe(
            self._get_account_snapshot_async(), self._loop
        )
        try:
            return fut.result(timeout=total_timeout)
        except Exception as e:
            logger.warning("[ib] session get_account_snapshot_raw failed: %s", e)
            return None

    async def _get_account_snapshot_async(self) -> IBKRAccountSnapshotRaw | None:
        t_snapshot_start = time.perf_counter()
        failed_steps: list[str] = []
        pos_timeout = _positions_timeout()
        open_orders_timeout = min(30, max(15, int(pos_timeout * 0.5)))
        loop = asyncio.get_event_loop()

        # --- account_summary ---
        t0 = time.perf_counter()
        logger.info("[ib] account_summary start")
        try:
            try:
                summary = await self._ib.accountSummaryAsync()
            except AttributeError:
                summary = await loop.run_in_executor(None, lambda: self._ib.accountSummary())
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning("[ib] account_summary failed: %s", e)
            failed_steps.append("account_summary")
            summary = []
        logger.info("[ib] account_summary end (latency=%.2fs)", time.perf_counter() - t0)

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

        # --- positions：订阅式 reqPositions() → positionEnd → 缓存；超时 retry 1 次 ---
        t1 = time.perf_counter()
        logger.info("[ib] positions start")
        positions = await self._fetch_positions_session(pos_timeout)
        if positions is None:
            logger.info("[ib] positions retry 1")
            positions = await self._fetch_positions_session(pos_timeout)
        if positions is None:
            failed_steps.append("positions")
            positions = []
        else:
            self._position_cache.set(positions)
        logger.info("[ib] positions end (latency=%.2fs)", time.perf_counter() - t1)

        # --- open_orders ---
        open_orders: list[dict] = []
        t2 = time.perf_counter()
        logger.info("[ib] open_orders start")
        try:
            raw_trades = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: list(self._ib.openTrades())),
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
        end = _ib_end_datetime(end_date)
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
