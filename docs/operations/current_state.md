# 当前状态（Current State）

面向新协作者：**现在能跑通什么、哪些是 mock、哪些是过渡实现、下一步会换什么**。

---

## 1. 能跑通什么

- **最短一条命令**：`python cli.py demo NVDA`（或 `--mock` 免网络），四块输出。
- **Research**：`python cli.py research [SYMBOL] [--mock] [--llm]`，输出 DecisionContract JSON。
- **Backtest**：`python cli.py backtest [SYMBOL] [--start] [--end] [--mock] [--llm]`，Research → 回测 → ExperienceStore。
- **Paper**：`python cli.py paper [--symbol SYMBOL] [--once] [--mock] [--llm]`，默认 Nautilus 短窗口回测；或配置 IBKR_* 走 TWS。
- **OpenClaw**：`python cli.py research NVDA --mock` 或 `scripts/run_for_openclaw.py`，stdout 单条 JSON。
- **E2E**：`python scripts/run_e2e_check.py NVDA --mock`；**调度**：`python scripts/run_scheduled.py [--once]`。

---

## 2. Mock 与过渡

- **Mock**：use_mock=True 时数据与部分 Agent 为 mock；详见 [mock_vs_real.md](mock_vs_real.md)。
- **过渡层**：本仓 RuleEngine/PortfolioEngine/PaperTradingEngine（use_nautilus=False 时保留）；默认已走 Nautilus。
- **长期保留**：ResearchOrchestrator、DecisionContract、ContractTranslator、ExperienceStore 接口、CLI、control 层、openclaw 约定。

---

## 3. 下一步

- 实盘前 7 项与 L1–L7：见 [../archive/live_readiness_checklist.md](../archive/live_readiness_checklist.md)。
- Post-MVP 与实盘对接：见 [../archive/restructuring_plan.md](../archive/restructuring_plan.md)、[../archive/deferred_authorization.md](../archive/deferred_authorization.md)。

---

完整版（含优先级 P1–P3）：[../archive/CURRENT_STATE.md](../archive/CURRENT_STATE.md)。
