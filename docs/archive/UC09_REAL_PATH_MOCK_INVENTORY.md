# UC-09 主路径切 Real：Mock 入口盘点

## 主路径 Mock（需改为 real 优先）

| 文件 | 位置 | 说明 | 替换优先级 |
|------|------|------|------------|
| `scripts/run_weekly_autonomous_paper.py` | `--mock` default=True | 入口默认 mock | P0 |
| `src/.../pipeline/openclaw_adapter.py` | `run_weekly_paper_report(use_mock=True)` | OpenClaw 默认 mock | P0 |
| `src/.../pipeline/weekly_paper_pipe.py` | `use_mock: bool = True` | 管道默认 mock | P0 |
| `src/.../pipeline/weekly_paper_pipe.py` | `get_account_snapshot(..., mock=True)` 硬编码 | 账户快照强制 mock | P0 |
| `src/.../pipeline/weekly_paper_pipe.py` | `benchmark_return = 0.0` 占位 | 基准收益固定 0 | P0 |
| `src/.../research/orchestrator.py` | `use_mock: bool = True` | Research 默认 MockDataProvider | P1（主入口传 False 即可） |
| `src/.../autonomous/account_snapshot.py` | 仅实现 mock，无 IBKR | 无真实 snapshot 路径 | P0 |

## 测试专用 Mock（保留，仅 CI/回归）

| 文件 | 位置 | 说明 |
|------|------|------|
| `scripts/verify_uc09_weekly_autonomous_paper.py` | 全程 mock | 改为 verify_uc09_mock.py，仅做回归 |
| `src/.../data/providers.py` | MockDataProvider, _mock_* | 保留；YFinance 失败时 fallback |
| `src/.../research/agents/llm_agent.py` | LLM 不可用时的 mock 文案 | 保留 |

## 硬编码价格 / 占位

| 文件 | 位置 | 说明 |
|------|------|------|
| `weekly_paper_pipe.py` | `runner.run_once(122.5, ...)` | 122.5 为兼容参数；Nautilus 内部用 yfinance，可改为 real 取价 |
| `cli.py` / `run_paper.py` | 122.5 fallback 价 | mock 或取价失败时用；real 路径应从 yfinance 取价 |
| `data/providers.py` | _mock 返回 122.5 | 仅 fallback 时用 |

## 替换后约定

- 主入口默认 `use_mock=False`，`get_account_snapshot(mock=False)` 优先 IBKR，失败且允许 fallback 时才 mock。
- 所有产出显式标记：`snapshot_source`、`market_data_source`、`benchmark_source`。
- Benchmark 主路径接 yfinance 计算 SPY 周期收益，不再固定 0。
