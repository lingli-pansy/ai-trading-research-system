# UC-09 主路径切 Real 交付说明

## 1. 修改过的文件列表

| 文件 | 变更概要 |
|------|----------|
| `docs/archive/UC09_REAL_PATH_MOCK_INVENTORY.md` | 新增：mock 入口盘点与替换优先级 |
| `src/.../autonomous/schemas.py` | AccountSnapshot 增加 buying_power、source |
| `src/.../autonomous/account_snapshot.py` | 真实优先：mock=False 时先试 IBKR，fallback 时 source=mock |
| `src/.../execution/ibkr_client.py` | 新增 get_ibkr_account_snapshot_raw、IBKRAccountSnapshotRaw；accountSummaryAsync + positions + openTrades |
| `src/.../autonomous/benchmark.py` | get_benchmark_return_for_period(symbol, lookback_days) 用 yfinance；BenchmarkResult.benchmark_source |
| `src/.../autonomous/weekly_report.py` | WeeklyReport 增加 benchmark_source；generate 传入 daily_research/benchmark_source |
| `src/.../pipeline/weekly_paper_pipe.py` | use_mock=False 默认；snapshot(mock=use_mock)；真实 benchmark；summary 含 snapshot/market_data/benchmark_source |
| `src/.../pipeline/openclaw_adapter.py` | run_weekly_paper_report use_mock=False |
| `scripts/run_weekly_autonomous_paper.py` | 默认不加 mock（real）；--mock 时 mock |
| `scripts/verify_uc09_mock.py` | 新增：mock 回归验证 |
| `scripts/verify_uc09_real.py` | 新增：真实联调验证 |
| `docs/operations.md` | 默认 real、验证脚本、调试与降级说明 |
| `docs/uc09_weekly_autonomous_paper.md` | weekly-paper 默认真实、JSON 含 source 字段 |
| `docs/core_concepts.md` | benchmark_source、snapshot/market_data_source 说明 |
| `docs/archive/UC09_IMPLEMENTATION_PLAN.md` | 第 6 节 Real 路径切换与验证 |

## 2. 每一步的验收方式

- **第一步**：查看 `docs/archive/UC09_REAL_PATH_MOCK_INVENTORY.md`，确认主路径 mock 与测试专用 mock 已区分。
- **第二步**：配置 IBKR_HOST/IBKR_PORT 后运行 weekly-paper（不加 --mock），输出 `snapshot_source: ibkr`；未配置时应为 `snapshot_source: mock`。
- **第三步**：不加 --mock 时 Research 用 YFinanceProvider，Nautilus 用 yfinance 历史数据；summary 中 `market_data_source: yfinance`。
- **第四步**：不加 --mock 时周报与 summary 中 `benchmark_return` 非固定 0，`benchmark_source: yfinance`（或取数失败时为 mock）。
- **第五步**：`python scripts/run_weekly_autonomous_paper.py --capital 10000 --benchmark SPY` 输出 JSON 含 snapshot_source、market_data_source、benchmark_source。
- **第六步**：在项目 venv 下运行（如 `.venv/bin/python scripts/verify_uc09_mock.py`）或 `pip install -e .` 后运行；`verify_uc09_real.py` 需网络（yfinance）。
- **第七步**：operations.md、uc09_weekly_autonomous_paper.md、core_concepts.md、UC09_IMPLEMENTATION_PLAN 已更新。

## 3. 已从 mock 切到 real 的路径

- **CLI weekly-paper**：默认不加 --mock，即 real。
- **run_weekly_autonomous_paper.py**：默认 real；仅加 --mock 时 mock。
- **OpenClaw run_weekly_paper_report**：默认 use_mock=False。
- **weekly_paper_pipe**：默认 use_mock=False；get_account_snapshot(mock=use_mock)；benchmark 用 get_benchmark_return_for_period。
- **AccountSnapshot**：mock=False 时优先 IBKR，失败则 fallback mock 并标记 source。

## 4. 保留 mock fallback 的能力

- **AccountSnapshot**：IBKR 未配置或连接失败时 fallback mock，snapshot_source=mock。
- **Research**：YFinanceProvider 失败时价格/新闻/基本面 fallback mock（providers 内已有逻辑）。
- **Benchmark**：get_benchmark_return_for_period 取数失败时返回 (0.0, "mock")。
- **显式 --mock**：所有主入口支持 --mock，用于 CI 与回归。

## 5. 最短真实调试命令示例

```bash
# 环境：pip install -e .（可选配置 IBKR_HOST/IBKR_PORT 以用真实 paper 账户）
python scripts/run_weekly_autonomous_paper.py --capital 10000 --benchmark SPY
# 或
python cli.py weekly-paper --capital 10000 --benchmark SPY
```

期望 stdout JSON 中含：`"snapshot_source": "ibkr"` 或 `"mock"`，`"market_data_source": "yfinance"`，`"benchmark_source": "yfinance"`（或取数失败时为 "mock"）。
