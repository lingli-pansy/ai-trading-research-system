# 数据源架构（Data Source Architecture）

**目标**：IB Gateway / IBKR API 作为主市场数据源，yfinance 降级为 research 可选补充。

---

## 1. 主数据源：IB Gateway / IBKR API

- **用途**：最新价、历史 K 线、Benchmark（如 SPY）收益率序列。
- **配置**：环境变量 `IBKR_HOST`、`IBKR_PORT`（可选 `IBKR_CLIENT_ID`）。TWS 或 IB Gateway 需已启动并开启 API。
- **实现**：`data/market_data_service.py` 中的 `MarketDataService` 通过 `ib_insync` 连接 IB，使用 `reqHistoricalData` 拉取日线；`get_latest_price` 由最近几日 bar 的 close 推导。
- **Benchmark**：SPY 等 benchmark 历史数据来自 IB；`get_benchmark_series` 带内存缓存（TTL 5 分钟），避免重复请求。

---

## 2. 可选补充：yfinance（仅 Research）

- **允许出现位置**：
  - **research/news**：`data/providers.YFinanceProvider.get_news`
  - **research/fundamentals**：`data/providers.YFinanceProvider.get_fundamentals`
- **约束**：均为可选源；失败时可 fallback 或返回空/默认，不强制依赖。
- **Research 价格**：research 层价格优先使用 `MarketDataService.get_latest_price(symbol)`（IB 优先）；当 `allow_yf_fallback=True`（即 `for_research=True`）且 IB 不可用时，才使用 yfinance 作为价格补充。yfinance 不用于 benchmark、allocator、trigger、backtest 或 run_paper 的报价。

---

## 3. 数据流概览

| 模块 | 数据来源 | 说明 |
|------|----------|------|
| **Benchmark**（收益、波动率、最大回撤） | MarketDataService（IB） | `autonomous/benchmark.py` → `get_benchmark_series` / `get_benchmark_return_for_period`，带缓存 |
| **run_paper 最新价** | MarketDataService（IB） | `application/commands/run_paper.py` 使用 `get_market_data_service(for_research=False).get_latest_price` |
| **Regime context**（SPY/VIX） | MarketDataService（IB） | `services/regime_context.py` 使用 `get_history("SPY", 5)` / `get_history("^VIX", 5)` |
| **Backtest 历史数据** | MarketDataService（IB） | `backtest/runner.py` 使用 `_market_data_history` → `MarketDataService.get_history` |
| **Research 价格** | MarketDataService（IB，可选 yfinance） | `research/orchestrator.build_context` 使用 `get_market_data_service(for_research=True).get_latest_price` |
| **Research 基本面/新闻** | YFinanceProvider（可选） | `research/orchestrator` 仍通过 `data_provider.get_fundamentals` / `get_news`，仅在此处使用 yfinance |

---

## 4. MarketDataService API

- **get_latest_price(symbol)**  
  返回 `PriceSnapshot(symbol, last_price, change_pct, volume_ratio?, source)`。  
  IB 优先；`allow_yf_fallback=True` 时在 research 场景可回退到 yfinance。

- **get_history(symbol, days, end_date=..., allow_yf_fallback=...)**  
  返回 `list[dict]`，每项含 `date, open, high, low, close, volume`。  
  IB 优先；research 场景可设 `allow_yf_fallback=True`。

- **get_benchmark_series(symbol="SPY", lookback_days=..., use_cache=True)**  
  返回 `(daily_returns, total_return, volatility_annualized, max_drawdown)`。  
  **仅使用 IB**，不使用 yfinance；`use_cache=True` 时使用内存缓存减少重复请求。

---

## 5. 禁止与未改动

- **禁止**：修改 trading policy、allocator 逻辑、LLMResearchAgent、experiment lifecycle；仅做数据层改造。
- **未改动**：allocator / trigger 不直接调数据源，仍通过 pipeline 传入的 `benchmark_data` 等使用 benchmark；benchmark 数据现由 MarketDataService（IB）提供。

---

## 6. 测试与校验

- **tests/test_market_data_service.py**：
  - 工厂方法 `get_market_data_service(for_research=False/True)` 的 `allow_yf_fallback` 行为；
  - 无 IB 时 `get_latest_price` 仍返回合法 `PriceSnapshot`；
  - `allow_yf_fallback=True` 时可回退到 yfinance；
  - `get_benchmark_series` 缓存行为（同一 key 在 TTL 内命中）；
  - 在配置了 IB 时（`IBKR_HOST`/`IBKR_PORT` 已设）可读取 IB 数据（SPY history / benchmark series）。

---

## 7. 配置小结

- **主数据源**：配置 `IBKR_HOST`、`IBKR_PORT` 后，benchmark、run_paper 报价、regime、backtest、research 价格均优先走 IB。
- **Research 补充**：research 价格在 IB 不可用时可用 yfinance；research 基本面与新闻仍仅通过 `YFinanceProvider`（yfinance）可选获取。

---

## 8. 常见问题：weekly-paper 慢、超时、Error 1100

- **进度**：`weekly-paper` 会在 stderr 打印进度，例如 `[weekly-paper] Day 1/5: researching 8 symbols...`、`Day 1/5: done (trades=0, pnl=0.00).`，便于确认未卡死。
- **速度**：8 标的 × 5 天且 `--llm` 时，每天会对每个标的做一次 research（LLM 调用），整体可能需数分钟；可先用 `--symbols NVDA,SPY` 做短路径验证。

### 8.1 连接稳定性（不依赖 mock 时）

**原因简述**：ib_insync 每次请求都是「连接 → 请求 → 断开」。Gateway 在 `disconnect()` 后**不会立即释放 client id**，若马上用同一 client id 再连，易出现 “Error 1100 / Connectivity lost”“Can't write, socket client is closing” 或 positions/account 请求超时。

**已做改动**（无需 mock 即可提升稳定性）：

1. **区分 client id**  
   - 账户/下单：`IBKR_CLIENT_ID`（默认 **1**）。  
   - 行情（benchmark、regime、history）：`IBKR_MARKET_DATA_CLIENT_ID`（默认 **2**）。  
   避免账户与行情共用同一 id、频繁重连。

2. **连接与同步超时**  
   - `connectAsync` 建立连接后会同步 positions、open orders、account updates，**共用同一 timeout**。  
   - `ib_insync` 默认仅 **2 秒**，易出现 “positions request timed out”。  
   - 已改为默认 **60 秒**（`IBKR_CONNECT_TIMEOUT=60`）；若仍超时，可改为 90 或 120。

3. **断开后延迟**  
   - 每次 `disconnect()` 后等待 **`IBKR_DISCONNECT_DELAY`**（默认 **1** 秒）再返回，给 Gateway 时间释放 id，再发起下一次连接。

4. **账户快照重试**  
   - 拉取账户快照失败时自动重试（默认最多 2 次，间隔 2 秒），减少偶发超时导致整轮失败。

**推荐 .env（IB 连接）**：

```bash
IBKR_HOST=127.0.0.1
IBKR_PORT=4002
IBKR_CLIENT_ID=1
IBKR_MARKET_DATA_CLIENT_ID=2
IBKR_CONNECT_TIMEOUT=60
IBKR_DISCONNECT_DELAY=1
```

**Gateway 端建议**：

- **Settings → API → Settings**：启用 API，端口与 `IBKR_PORT` 一致（Gateway 多为 4002）。
- 若本机多进程/多实例，不要共用一个 client id；本仓库已用 1 和 2 区分账户与行情。
- 出现 “API Client: disconnected” 或大量 Error 1100 时，可重启 Gateway 后再跑一次。
