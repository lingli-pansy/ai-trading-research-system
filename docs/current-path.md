# 当前开发者导航（Current Path）

**几分钟内回答：今天该跑什么、结果在哪、replay 看哪。**

---

## 1. 当前系统主入口是什么？

**Canonical path**：`autonomous_paper_cycle`。  
- 应用层：`application.commands.run_autonomous_paper_cycle`  
- 编排层：`pipeline.autonomous_paper_cycle.run_autonomous_paper_cycle`  
- 分阶段：load_state → build_research_bundle → evaluate_trigger_and_allocate → build_rebalance_plan → (risk) → **generate_proposal** → **approval** → **execute_if_approved** → finalize_run  

其他命令（research、backtest、demo、paper、weekly-paper）经 `application.command_registry` 派发；**paper trading 主路径**即 autonomous_paper_cycle。**OpenClaw agent = proposal approver**（approve / reject / defer），不直接调用 execution。

---

## 2. OpenClaw 调哪个接口？

- **用户/对话唯一入口**：`openclaw.bridge.handle_trading_intent_sync(message)`，四类动作一次返回 status/summary/details。CLI smoke：`openclaw-trading-intent-sync --message-json '{"message":"开始建仓"}'`。  
- **开发/调试**：`openclaw-agent-once`、`openclaw-agent-loop`、`openclaw-approver-smoke`（见 AGENTS.md、openclaw-project-setup.md）。  
- **兼容（compat）**：`scripts/run_for_openclaw.py`、`openclaw.adapter.run_autonomous_paper_cycle_report(...)`；不作为官方入口。  
- 契约：`openclaw/contract.py` 中 `AutonomousPaperCycleInput` / `AutonomousPaperCycleOutput`。  

---

## 3. Paper trading 跑哪个命令？

- **推荐**：`python -m ai_trading_research_system.presentation.cli paper-cycle --symbols NVDA [--mock] [--run_id <id>]`  
- 单标的兼容：`python cli.py paper --symbol NVDA [--mock]`（内部复用 autonomous_paper_cycle，落盘 runs/）  
- 周自治：`python cli.py weekly-paper ...`（独立 pipe，非单周期）  

---

## 4. 运行结果写到哪里？

- **runs/**：每轮 `runs/<run_id>/` 下  
  - `snapshots/portfolio_before.json`, `portfolio_after.json`, `research.json`  
  - `artifacts/candidate_decision.json`, `final_decision.json`, `order_intents.json`, `rebalance_plan.json`, **`approval_request.json`**（proposal）, **`approval_decision.json`**  
  - `execution/paper_result.json`  
  - `audit.json`, `meta.json`  
- **runs/index.json**：运行索引（run_id, timestamp, symbols, decision_summary, portfolio_value, orders），经 `RunStore.append_run_index` / `get_recent_runs` / `get_last_run` 读写。  
- **runs/experience.jsonl**：经验记录（每行一条 JSON：run_id, timestamp, symbols, rebalance_plan, decision_summary, portfolio_before, portfolio_after, **approval_decision**），经 `RunStore.append_experience` 追加；只读查询经 **`state.ExperienceStore`**（get_recent_runs, get_symbol_history, get_recent_rebalances）。  
- **runs/agent_health.json**：Agent 健康状态（last_success_run, last_error, consecutive_failures, agent_uptime, current_state），经 `RunStore.write_agent_health` / `read_agent_health` 读写。  
- **reports/**：周报等报告（`weekly_report_*.json`）  
- 所有 run 读写经 **`state.RunStore`**，禁止 CLI/agent 直接写 runs/ 下文件。  

---

## 5. Replay 看哪里？

- **单 run 复盘**：`RunStore.replay_run(run_id)` → symbols, ranking, trigger, decision, rebalance_plan, **proposal**, **approval_decision**, execution, portfolio_before/after  
- **最近一次摘要**：`RunStore.get_latest_run_summary()` → run_id, final_decision, order_intents, portfolio_after  
- **最近组合状态**：`RunStore.get_latest_portfolio_state()`（优先读 runs 内 portfolio_after，否则 fallback API）  
- **历史运行索引**：`RunStore.get_recent_runs(n)` / `RunStore.get_last_run()` → 快速查看最近 n 条或最后一条 run 索引。  

---

## 6. Agent Runtime（自治交易循环）

- **用途**：让 OpenClaw agent 持续跑 **observe → decide → act → record** 循环，不扩展复杂策略，只提供 runtime 能力。  
- **模块**：`agent.runtime.AutonomousTradingAgent`  
  - **run_once()**：加载最新 portfolio state → 调用 `autonomous_paper_cycle` → 更新 run index 与 experience log → 返回 run summary。  
  - **run_loop(interval_seconds=300)**：`while True: run_once(); sleep(interval)`。  
- **Run Index**：`runs/index.json`，由 `RunStore.append_run_index` 写入；agent 通过 `get_recent_runs(n)` / `get_last_run()` 快速查历史。  
- **Experience Log**：`runs/experience.jsonl`，由 `RunStore.append_experience` 追加；每 run 一条记录（run_id, timestamp, symbols, rebalance_plan, decision_summary, portfolio_before, portfolio_after），仅记录不学习。  
- **CLI**：  
  - 单次：`python -m ai_trading_research_system.presentation.cli agent-run-once [--symbols NVDA,SPY] [--capital 10000]`  
  - 循环：`python -m ai_trading_research_system.presentation.cli agent-loop --interval 300 [--max-consecutive-failures 5] [--symbols NVDA,SPY]`（内部使用 run_loop，含错误守卫与健康停止）。  
- **可观测输出**：每次 run 打印 RUN id、**PROPOSAL**、**RISK FLAGS**、**APPROVAL**、EXECUTION、PORTFOLIO（value before → after）。

---

## 7. Approval Workflow（提案 → 审批 → 执行）

- **Proposal**（`runtime.proposal.Proposal`）：runtime 提交给 approver 的交易提案；写入 `runs/<run_id>/approval_request.json`（经 `RunStore.write_proposal`）。  
- **ApprovalDecision**（`runtime.proposal.ApprovalDecision`）：decision 为 **approve | reject | defer**；写入 `runs/<run_id>/approval_decision.json`（经 `RunStore.write_approval_decision`）。  
- **执行**：仅当 decision == approve 时执行 execution engine；reject/defer 不执行，但可落盘 proposal 与 decision。  
- **OpenClaw agent = proposal approver**：通过 `openclaw.agent_adapter.approve_proposal(proposal, context)` 返回结构化 decision；不直接调用 execution。  
- **CLI**：`proposal-run --symbols SPY,QQQ,NVDA` 仅生成 proposal（不等待 approval、不执行），输出 proposal summary 与 proposal path。

---

## 8. Runtime Stability（运行时安全与稳定性）

- **RiskPolicyEngine**（`risk.policy_engine`）：在 rebalance_plan 执行前做风险检查；约束：max_position_size、max_turnover、max_orders_per_run、min_cash_buffer。输入 portfolio_before + rebalance_plan，输出 filtered_rebalance_plan + risk_flags；违反时自动 trim 或 skip order，并写入 audit。  
- **Agent Health**（`agent.health`）：状态持久化于 `runs/agent_health.json`（经 RunStore）。run 成功 → 重置 consecutive_failures；run 失败 → consecutive_failures += 1。若连续失败超过阈值（默认 5），agent loop 自动停止（current_state=stopped）。  
- **Experience Query**：`ExperienceStore.get_recent_runs(n)`、`get_symbol_history(symbol)`、`get_recent_rebalances(symbol)` 供 decision context 与 debug 使用。  
- **Runtime Error Guard**：`run_loop()` 内 try/except 包裹 `run_once()`；单次异常不终止 agent，记录错误并更新 health 后继续下一轮。

---

## 9. 哪些入口是兼容层，不建议新开发依赖？

- **run_paper**（CLI `paper`）：已复用 autonomous_paper_cycle，保留 CLI 别名与 IBKR 分支；新逻辑应走 paper-cycle / openclaw-agent-once。  
- **scripts/run_*.py**：与 CLI 对应，多为兼容入口；**OpenClaw 主路径**为 `openclaw-agent-once` / `openclaw-agent-loop` + 配置文件。  
- **pipeline/weekly_paper_pipe**：周自治专用，非单周期 agent 入口。  
- **control/**：已删除；不再使用。  

---

**更细的架构与数据层**：见 [system_architecture.md](system_architecture.md)、[operations.md](operations.md)。
