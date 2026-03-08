# 当前状态（Current State）

面向新协作者：**现在能跑通什么、哪些是 mock、哪些是过渡实现、下一步会换什么**。

---

## 1. 能跑通什么

- **最短一条命令**：`python cli.py demo NVDA`（或 `--mock` 免网络），四块输出。
- **Research**：`python cli.py research [SYMBOL] [--mock] [--llm]`，输出 DecisionContract JSON。
- **Backtest**：`python cli.py backtest [SYMBOL] [--start] [--end] [--mock] [--llm]`，Research → 回测 → ExperienceStore。
- **Paper**：`python cli.py paper [--symbol SYMBOL] [--once] [--mock] [--llm]`，默认 Nautilus 短窗口回测；或配置 IBKR_* 走 TWS。
- **OpenClaw**：`python cli.py research NVDA --mock` 或 `scripts/run_for_openclaw.py`，stdout 单条 JSON。
- **UC-09 Weekly Autonomous Paper**：**默认走真实路径**。`python cli.py weekly-paper --capital 10000 --benchmark SPY` 或 `python scripts/run_weekly_autonomous_paper.py --capital 10000 --benchmark SPY`；stdout 单条 JSON（含 snapshot_source、market_data_source、benchmark_source）。仅加 `--mock` 时走 mock（CI/回归用）。Nautilus 主线；周报落盘 `reports/weekly_report_<mandate_id>.json`。
- **UC-09 验证**：mock 回归 `.venv/bin/python scripts/verify_uc09_mock.py`；真实联调 `.venv/bin/python scripts/verify_uc09_real.py`。
- **E2E**：`python scripts/run_e2e_check.py NVDA --mock`；**调度**：`python scripts/run_scheduled.py [--once]`。

---

## 2. Mock 与过渡

- **Mock**：仅用于 CI 与最小回归；主入口默认 **real**。详见 [mock_vs_real.md](mock_vs_real.md)。
- **过渡层**：RuleEngine/PortfolioEngine/PaperTradingEngine（use_nautilus=False 时保留）；默认已走 Nautilus。
- **UC-09 主路径**：AccountSnapshot 默认优先 IBKR paper；失败则 mock 并标记 snapshot_source=mock。市场数据默认 yfinance；benchmark 默认 SPY；输出含 snapshot_source、market_data_source、benchmark_source。
- **降级**：IBKR 未配置或连接失败 → snapshot 自动 mock；yfinance 不可用时 Research/benchmark 可退化为 mock 并显式标记。

---

## 3. 真实 UC-09 调试与降级

- **最短真实调试命令**：`python scripts/run_weekly_autonomous_paper.py --capital 10000 --benchmark SPY`（不加 `--mock`）。
- **降级**：仅做回归时加 `--mock` 或运行 `verify_uc09_mock.py`。

---

## 4. 下一步

- 实盘前 L1–L7：见 [live_readiness_checklist.md](live_readiness_checklist.md)。
- Post-MVP 与实盘对接：见 [restructuring_plan.md](restructuring_plan.md)、[deferred_authorization.md](deferred_authorization.md)。

Mock 盘点与 real 切换说明：[UC09_REAL_PATH_MOCK_INVENTORY.md](UC09_REAL_PATH_MOCK_INVENTORY.md)。精简版当前状态见 [../operations.md](../operations.md)。
