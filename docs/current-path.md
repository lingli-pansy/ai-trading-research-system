# 当前开发者导航（Current Path）

**几分钟内回答：今天该跑什么、结果在哪、replay 看哪。**

---

## 1. 当前系统主入口是什么？

**Canonical path**：`autonomous_paper_cycle`。  
- 应用层：`application.commands.run_autonomous_paper_cycle`  
- 编排层：`pipeline.autonomous_paper_cycle.run_autonomous_paper_cycle`  
- 分阶段：load_state → build_research_bundle → evaluate_trigger_and_allocate → build_rebalance_plan → execute_paper_orders → finalize_run  

其他命令（research、backtest、demo、paper、weekly-paper）经 `application.command_registry` 派发；**paper trading 主路径**即 autonomous_paper_cycle。

---

## 2. OpenClaw 调哪个接口？

- **脚本**：`python scripts/run_for_openclaw.py autonomous_paper_cycle [SYMBOL] --run_id <id> [--mock]`  
- **编程**：`openclaw.adapter.run_autonomous_paper_cycle_report(...)` 或 `application.command_registry.run("autonomous_paper_cycle", ...)`  
- 契约：`openclaw/contract.py` 中 `AutonomousPaperCycleInput` / `AutonomousPaperCycleOutput`  

---

## 3. Paper trading 跑哪个命令？

- **推荐**：`python -m ai_trading_research_system.presentation.cli paper-cycle --symbols NVDA [--mock] [--run_id <id>]`  
- 单标的兼容：`python cli.py paper --symbol NVDA [--mock]`（内部复用 autonomous_paper_cycle，落盘 runs/）  
- 周自治：`python cli.py weekly-paper ...`（独立 pipe，非单周期）  

---

## 4. 运行结果写到哪里？

- **runs/**：每轮 `runs/<run_id>/` 下  
  - `snapshots/portfolio_before.json`, `portfolio_after.json`, `research.json`  
  - `artifacts/candidate_decision.json`, `final_decision.json`, `order_intents.json`, `rebalance_plan.json`  
  - `execution/paper_result.json`  
  - `audit.json`, `meta.json`  
- **reports/**：周报等报告（`weekly_report_*.json`）  
- 所有 run 读写经 **`state.RunStore`**，禁止各 service 直接写 run 目录。  

---

## 5. Replay 看哪里？

- **单 run 复盘**：`RunStore.replay_run(run_id)` → symbols, ranking, trigger, decision, rebalance_plan, execution, portfolio_before/after  
- **最近一次摘要**：`RunStore.get_latest_run_summary()` → run_id, final_decision, order_intents, portfolio_after  
- **最近组合状态**：`RunStore.get_latest_portfolio_state()`（优先读 runs 内 portfolio_after，否则 fallback API）  

---

## 6. 哪些入口是兼容层，不建议新开发依赖？

- **run_paper**（CLI `paper`）：已复用 autonomous_paper_cycle，保留 CLI 别名与 IBKR 分支；新逻辑应走 paper-cycle / autonomous_paper_cycle。  
- **scripts/run_*.py**：与 CLI 对应，多为兼容入口；主路径为 `cli paper-cycle` 与 `run_for_openclaw.py autonomous_paper_cycle`。  
- **pipeline/weekly_paper_pipe**：周自治专用，非单周期 agent 入口。  
- **control/**：已删除；不再使用。  

---

**更细的架构与数据层**：见 [system_architecture.md](system_architecture.md)、[operations.md](operations.md)。
