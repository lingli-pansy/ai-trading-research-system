# UC-09 验收审计报告

**审计日期**: 2026-03-08  
**审计范围**: weekly-paper 执行链、UC-09 成功标准、阻塞点定位。  
**原则**: 仅阅读/运行/分析/定位，不新增功能、不重构、不修改 trading logic / LLM / allocator / policy。

---

## 1. 实际执行链路

```
CLI (presentation/cli.py)
  main() → kwargs_from_cli_args("weekly-paper", args) → command_run("weekly-paper", **kwargs)
    ↓
command_registry.run (application/command_registry.py)
  resolve("weekly-paper") → "weekly_autonomous_paper"
  handler = _HANDLERS["run_weekly_autonomous_paper"]
  handler(**kwargs)  [report_dir 由 registry 注入]
    ↓
run_weekly_autonomous_paper (application/commands/run_weekly_autonomous_paper.py)
  _run_pipe(capital, benchmark, duration_days, auto_confirm, use_mock, use_llm, report_dir, symbols)
    ↓
weekly_paper_pipe.run_weekly_autonomous_paper (pipeline/weekly_paper_pipe.py)
  mandate_from_cli()  [若无 mandate]
  [非 mock] IBKRSession(client_id=1).connect() → set_ibkr_session(session)
  get_account_snapshot(paper=True, mock=use_mock, allow_fallback=not reject_mock)  ← ibkr_client.get_ibkr_account_snapshot_raw() / session.get_account_snapshot_raw()
  get_regime_context(use_mock)  ← MarketDataService.get_history(SPY/VIX)
  for day in range(duration_days):
    [并行] orchestrator.run_with_context(sym)  [research]
    get_benchmark_returns_and_volatility(benchmark, lookback_days)  [日内]
    ranker.rank / allocator / execution (NautilusPaperRunner)
  get_benchmark_returns_and_volatility(benchmark, max(duration_days,2))  [周级]
  finish_week(...)  ← 此处再次 get_benchmark_return(symbol, lookback_days=duration_days)
  [finally] set_ibkr_session(None); session.disconnect()
    ↓
weekly_finish_service.finish_week (services/weekly_finish_service.py)
  get_benchmark_return(symbol, lookback_days=duration_days, reject_mock=not use_mock)  ← 阻塞点
  compare_to_benchmark(...)
  report_generate_and_write(...)
  write_evolution_proposal_snapshot / write_evolution_decision_snapshot
  write_weekly_portfolio_experience / write_portfolio_health_snapshot / write_experience_insight_snapshot
  write_decision_traces_snapshot (若 experiment_id)
  build_weekly_result_summary(...)
  return WeeklyPaperResult
    ↓
render → JSON 输出
```

**数据获取链**:
- **Snapshot**: `account_snapshot.get_account_snapshot` → `ibkr_client.get_ibkr_account_snapshot_raw()`（有 session 则用 `ibkr_session.get_account_snapshot_raw()`）。
- **Benchmark**: `benchmark_service.get_benchmark_return` → `autonomous.benchmark.get_benchmark_return_for_period` → `MarketDataService.get_benchmark_series` → `_ib_fetch_bars`（有 session 则 `session.fetch_bars`）。
- **Regime**: `regime_context.get_regime_context` → `MarketDataService.get_history(SPY/VIX)`。

---

## 2. UC-09 成功标准检查表

| # | 标准 | 本次运行结果 | 结论 |
|---|------|--------------|------|
| 1 | IB session successfully connected | `[ib] IB connection latency=2.41s`，`IB session connected, reusing for account & market data` | ✅ 满足 |
| 2 | snapshot_source = ib（不能 fallback mock） | `Account snapshot: source=ibkr, equity=1000086`（ibkr 视为真实 IB） | ✅ 满足 |
| 3 | benchmark successfully loaded | 管程内 `[ib] benchmark latency=0.45s/0.52s` 成功；**finish_week 内**再次调用 `get_benchmark_return(lookback_days=1)` 返回空并因 reject_mock 抛错 | ❌ 不满足 |
| 4 | weekly report generated | 因 3 未通过，未执行到 `report_generate_and_write` | ❌ 未达成 |
| 5 | decision trace written | 因 3 未通过，未执行到 `write_decision_traces_snapshot` | ❌ 未达成 |
| 6 | experience store updated | 因 3 未通过，未执行到 `write_weekly_portfolio_experience` 等 | ❌ 未达成 |

---

## 3. 当前运行日志关键片段

```text
[weekly-paper] Start: 1 symbols, 1 days, use_llm=False, use_mock=False.
[weekly-paper] Connecting to IB (single session for this run)...
2026-03-08 16:56:05,978 | INFO | ai_trading_research_system.execution.ibkr_session | [ib] IB connection latency=2.41s
[weekly-paper] IB session connected, reusing for account & market data.
[weekly-paper] Getting account snapshot...
[weekly-paper] (IB session in context: True)
2026-03-08 16:56:06,385 | INFO | ... | [ib] account snapshot total latency=0.38s
[weekly-paper] Account snapshot: source=ibkr, equity=1000086.
[weekly-paper] Getting regime context (SPY/VIX)...
2026-03-08 16:56:07,277 | INFO | ... | [ib] regime context latency=0.89s
[weekly-paper] Day 1/1: researching 1 symbols...
[weekly-paper] Day 1/1: ranking & allocator...
2026-03-08 16:56:09,471 | INFO | ... | [ib] benchmark latency=0.45s
[weekly-paper] Computing benchmark & writing report...
2026-03-08 16:56:09,475 | INFO | ... | [ib] benchmark latency=0.00s
2026-03-08 16:56:09,998 | INFO | ... | [ib] benchmark latency=0.52s
2026-03-08 16:56:09,998 | INFO | ib_insync.ib | Disconnecting from 127.0.0.1:4002 ...
[weekly-paper] IB session disconnected.
RuntimeError: Reject mock: benchmark data from IB required. Check IB Gateway and historical data for SPY; or run with --mock for local testing.
```

**Latency 分布**:
- IB connection: 2.41s  
- account_summary: 0.38s（positions/open_orders 0.00s）  
- account snapshot total: 0.38s  
- regime context: 0.89s  
- benchmark（管程内）: 0.45s / 0.00s（cache）/ 0.52s  

---

## 4. 阻塞点定位

### 4.1 发生位置

- **函数**: `services/weekly_finish_service.finish_week` 第 75 行  
- **调用**: `get_benchmark_return(symbol=benchmark, lookback_days=duration_days, reject_mock=True)`  
- **参数**: `--days 1` → `duration_days=1` → `lookback_days=1`

### 4.2 调用链

1. `finish_week` → `get_benchmark_return(symbol="SPY", lookback_days=1, reject_mock=True)`  
2. `benchmark_service.get_benchmark_return` → `autonomous.benchmark.get_benchmark_return_for_period(symbol, lookback_days=1, reject_mock=True)`  
3. `get_benchmark_return_for_period` → `mds.get_benchmark_series(symbol, lookback_days=1, ...)`  
4. `market_data_service.get_benchmark_series` → `_ib_fetch_bars(symbol, duration_days=max(1, 1)=1, end_date=...)`  
5. IB 返回 **1 个 bar**（1 日仅 1 根日线）  
6. `get_benchmark_series` 中 `if not bars or len(bars) < 2: return ([], 0.0, 0.0, 0.0)`（需至少 2 根才能算收益率）  
7. `get_benchmark_return_for_period` 得到 `returns=[]`，`source="mock"`，`reject_mock=True` → **raise RuntimeError**

### 4.3 根因

- **不是** IB 断连、超时或未配置。  
- **是** 数据层语义：`lookback_days=1` 只请求 1 日 bars，得到 1 根 K 线，无法满足“至少 2 根才能算 return”的约束，返回空序列，再被 reject_mock 视为失败并抛错。

### 4.4 哪一步“fallback 到 mock”

- 逻辑上等价于“无有效 benchmark 数据”：`get_benchmark_series` 返回 `([], 0.0, 0.0, 0.0)`，在 `get_benchmark_return_for_period` 中 `source="ib" if returns else "mock"` → source 为 `"mock"`，随后 `reject_mock and not returns` 触发 raise，**未实际返回 mock 值**，而是直接报错。

---

## 5. 最小修复方案（仅允许修改数据获取层）

- **约束**: 只改数据获取/benchmark 调用方式，不改 trading logic、allocator、policy、LLM、不新增模块。

**建议（二选一或组合）**:

1. **在数据层保证至少 2 根 bar**  
   - 在 `MarketDataService.get_benchmark_series` 中，请求 bars 时使用 `duration_days = max(2, lookback_days)`（或等价地 `duration_days = max(2, max(1, lookback_days))`），这样 `--days 1` 时仍会拉 2 日数据，得到至少 2 根 bar，可计算 return，且不改变对外 `lookback_days` 语义（仅内部请求长度）。  
   - 或：在 `autonomous.benchmark.get_benchmark_return_for_period` 调用 `get_benchmark_series` 时传入 `lookback_days=max(2, lookback_days)`，效果同上。

2. **在 finish_week 调用处避免 lookback_days=1**  
   - 在 `weekly_finish_service.finish_week` 中，调用 `get_benchmark_return(symbol=benchmark, lookback_days=max(2, duration_days), reject_mock=reject_mock)`，这样 `--days 1` 时用 2 日做周级 benchmark，不触发“1 根 bar 无 return”的约束。  

两种方式都仅涉及“数据获取/参数”，不改变策略或执行逻辑；推荐 1 或 2 择一实施即可通过本次 UC-09 验收（在 IB 可用、reject_mock 开启的前提下）。

---

## 6. 结论

**UC-09 是否完成？**  
**NO**

**原因**：  
在 `weekly-paper --symbols SPY --days 1` 且不 fallback mock 的配置下，**finish_week** 内对 benchmark 的调用使用 `lookback_days=1`，导致只拉取 1 日 bars（1 根 K 线），数据层要求至少 2 根 bar 才返回有效收益，因此返回空并触发 reject_mock 抛出异常，进而未生成周报、未写入 decision trace 与 experience store。  

在实施上述**最小修复（仅数据获取层）**后，UC-09 可满足：IB 连接、snapshot_source=ibkr、benchmark 成功加载、周报生成、decision trace 与 experience store 写入。

---

## 7. 本次真实运行结果（UC-09 real mode 验收）

**验收时间**: 2026-03-08  
**提交**: 14c851b（IB snapshot/benchmark/reject_mock/并行 research/审计文档）

### 7.1 运行一：`weekly-paper --symbols SPY --days 1`

| 指标 | 值 |
|------|-----|
| IB connection latency | 2.41s |
| account_summary latency | 0.33s |
| positions latency | 0.00s |
| open_orders latency | 0.00s |
| account snapshot total | 0.34s |
| regime context latency | 0.99s |
| benchmark latency（管程内） | 0.44s / 0.00s / 0.51s |
| snapshot_source | ibkr |
| final status | exit 1，RuntimeError in finish_week |

### 7.2 运行二：`weekly-paper --symbols SPY,QQQ,NVDA --days 1 --llm`

| 指标 | 值 |
|------|-----|
| IB connection latency | 2.41s |
| account_summary latency | 0.27s |
| positions latency | 0.00s |
| open_orders latency | 0.00s |
| account snapshot total | 0.27s |
| regime context latency | 0.89s |
| benchmark latency（管程内） | 0.44s / 0.00s / 0.52s |
| snapshot_source | ibkr |
| final status | exit 1，RuntimeError in finish_week（同运行一） |

### 7.3 Real mode gate 结论

**是否通过 real mode gate？** **NO**

两轮均在 `finish_week` 内 `get_benchmark_return(symbol=SPY, lookback_days=1, reject_mock=True)` 处抛出 `RuntimeError: Reject mock: benchmark data from IB required...`，未生成周报、未写 decision trace、未写 experience store。

### 7.4 唯一阻塞点

- **阻塞点**: `finish_week` 调用 `get_benchmark_return(lookback_days=duration_days)`，当 `--days 1` 时 `lookback_days=1`，`get_benchmark_series` 仅请求 1 日 bars，得到 1 根 K 线，不满足 `len(bars) >= 2`，返回空序列，`reject_mock=True` 导致 raise。
- **最小修复所在函数**: `services/weekly_finish_service.finish_week`（调用处改为 `lookback_days=max(2, duration_days)`），或 `data/market_data_service.MarketDataService.get_benchmark_series`（请求 bars 时 `duration_days=max(2, lookback_days)`）。

---

## 8. 最新验证（仅运行、记录）

**验证时间**: 2026-03-08（本轮未改代码）

### 8.1 运行一：`weekly-paper --symbols SPY --days 1`

| 指标 | 值 |
|------|-----|
| IB connection latency | 2.51s |
| account_summary latency | 0.27s |
| positions latency | 0.00s |
| open_orders latency | 0.00s |
| benchmark latency（管程内） | 0.44s / 0.00s / 0.52s |
| snapshot_source | ibkr |
| report_path | —（未生成，finish_week 前抛错） |
| final status | exit 1，RuntimeError in finish_week |

**成功标准检查**: snapshot_source≠mock ✅；benchmark loaded（管程内）✅；weekly report generated ❌；decision trace written ❌；experience store updated ❌。

### 8.2 运行二：`weekly-paper --symbols SPY,QQQ,NVDA --days 1 --llm`

| 指标 | 值 |
|------|-----|
| IB connection latency | 首连 Error 326（clientId 1 占用），standalone snapshot 2.12s |
| account_summary latency | 0.33s |
| positions latency | 0.00s |
| open_orders latency | 0.00s |
| benchmark latency（管程内） | 1.55s / 0.00s / 1.84s |
| snapshot_source | ibkr |
| report_path | —（未生成） |
| final status | exit 1，RuntimeError in finish_week |

**成功标准检查**: snapshot_source≠mock ✅；benchmark loaded（管程内）✅；weekly report generated ❌；decision trace written ❌；experience store updated ❌。

### 8.3 结论

**UC-09 是否完成？** **NO**

两轮均在 `finish_week` 内 `get_benchmark_return(lookback_days=1)` 处因“1 日仅 1 根 bar、不满足至少 2 根”返回空并触发 reject_mock 抛错，未生成周报、未写 decision trace、未写 experience store。阻塞点与最小修复方案见第 4、5、7.4 节，未实施修复前 UC-09 real mode 不通过。
