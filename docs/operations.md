# Operations（当前状态与运维）

面向新协作者：**能跑通什么、mock 与过渡、如何验证与降级**。

**控制面**：CLI 与 OpenClaw 统一走 `application.commands`；OpenClaw 契约见 `openclaw/contract.py`（persona、skills、command contract）。control/ 为兼容层，退场中。

---

## 1. 能跑通什么

- **最短一条命令**：`python cli.py demo NVDA`（或 `--mock` 免网络），四块输出。
- **Research**：`python cli.py research [SYMBOL] [--mock] [--llm]`，输出 DecisionContract JSON。
- **Backtest**：`python cli.py backtest [SYMBOL] [--start] [--end] [--mock] [--llm]`，Research → 回测 → ExperienceStore。
- **Paper**：`python cli.py paper [--symbol SYMBOL] [--once] [--mock] [--llm]`，默认 Nautilus 短窗口；或配置 IBKR_* 走 TWS。
- **OpenClaw**：`python cli.py research NVDA --mock` 或 `scripts/run_for_openclaw.py`，stdout 单条 JSON。
- **UC-09 Weekly Autonomous Paper**：默认走真实路径。`python cli.py weekly-paper --capital 10000 --benchmark SPY` 或 `python scripts/run_weekly_autonomous_paper.py --capital 10000 --benchmark SPY`；仅加 `--mock` 时走 mock。见 [uc09_weekly_autonomous_paper.md](uc09_weekly_autonomous_paper.md)。
- **UC-09 验证**：`.venv/bin/python scripts/verify_uc09_mock.py`（回归）、`.venv/bin/python scripts/verify_uc09_real.py`（真实联调）。
- **E2E**：`python scripts/run_e2e_check.py NVDA --mock`；**调度**：`python scripts/run_scheduled.py [--once]`。

---

## 2. Mock 与过渡

- **Mock**：仅用于 CI 与最小回归（`--mock` 或 `verify_uc09_mock.py`）；主入口默认 **real**。详见 [archive/mock_vs_real.md](archive/mock_vs_real.md)。
- **过渡层**：RuleEngine/PortfolioEngine/PaperTradingEngine（use_nautilus=False 时保留）；默认已走 Nautilus。
- **UC-09 主路径**：AccountSnapshot 默认优先 IBKR paper（需 IBKR_HOST/IBKR_PORT）；失败则 fallback mock 并标记 snapshot_source=mock。市场数据默认 yfinance；benchmark 默认 SPY 用 yfinance；输出含 snapshot_source、market_data_source、benchmark_source。
- **降级**：IBKR 未配置或连接失败 → snapshot 自动 mock；yfinance 不可用时 Research/benchmark 可退化为 mock 并显式标记。

---

## 3. 真实 UC-09 调试与降级

- **最短真实调试命令**：`python scripts/run_weekly_autonomous_paper.py --capital 10000 --benchmark SPY`（不加 `--mock`）。需网络（yfinance）；可选配置 IBKR_HOST/IBKR_PORT。
- **降级**：仅做回归时加 `--mock` 或运行 `verify_uc09_mock.py`。

---

## 4. 验证脚本

| 脚本 | 说明 |
|------|------|
| `python scripts/check_dev_prerequisites.py` | 开发前环境与权限核对 |
| `python scripts/run_e2e_check.py NVDA --mock` | E2E：Pipeline 与 ExperienceStore 有数据 |
| `python scripts/verify_experience_store.py` | 最新 strategy_run、backtest_result、trade_experience、experience_summary 等 |
| `.venv/bin/python scripts/verify_uc09_mock.py` | UC-09 mock 回归 |
| `.venv/bin/python scripts/verify_uc09_real.py` | UC-09 真实联调 |

---

## 5. 下一步

- 实盘前 L1–L7：见 [archive/live_readiness_checklist.md](archive/live_readiness_checklist.md)。
- Post-MVP 与实盘对接：见 [archive/restructuring_plan.md](archive/restructuring_plan.md)、[archive/deferred_authorization.md](archive/deferred_authorization.md)。

完整版（含优先级 P1–P3）：[archive/CURRENT_STATE.md](archive/CURRENT_STATE.md)。
