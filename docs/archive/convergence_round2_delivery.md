# 第二轮收敛交付说明（Convergence Round 2）

## 1. 修改文件列表

### 新增
- `src/ai_trading_research_system/state/schemas.py` — RebalancePlanItem、RebalancePlan、PortfolioSnapshot、PaperExecutionResult、action_type_from_weights
- `docs/current-path.md` — 当前开发者导航（主入口、OpenClaw、paper 命令、结果位置、replay、兼容层）
- `docs/convergence_round2_delivery.md` — 本说明

### 修改
- `src/ai_trading_research_system/state/run_store.py` — state-aware：write_snapshot/write_artifact/write_execution/read_snapshot、get_latest_portfolio_state、get_previous_research_snapshot、get_latest_run_summary、replay_run、path_for_*、write_rebalance_plan/read_rebalance_plan
- `src/ai_trading_research_system/state/__init__.py` — 导出 schemas
- `src/ai_trading_research_system/pipeline/autonomous_paper_cycle.py` — 拆分为 load_state、build_research_bundle、evaluate_trigger_and_allocate、build_rebalance_plan、execute_paper_orders、finalize_run；引入 RebalancePlan；portfolio_after 落盘；CycleOutput 增加 rebalance_plan
- `src/ai_trading_research_system/openclaw/adapter.py` — format_result 增加 rebalance_plan
- `src/ai_trading_research_system/presentation/renderers.py` — paper-cycle 输出 rebalance_plan
- `src/ai_trading_research_system/application/commands/run_paper.py` — 注释标明 deprecated compatibility layer
- `README.md` — 顶部“当前目标与主路径”、指向 current-path.md、CLI 表增加 paper-cycle
- `docs/system_architecture.md` — 主入口描述（分阶段、RebalancePlan、portfolio_after）、Replay 能力
- `docs/openclaw_autonomous_paper_convergence.md` — 第二轮收敛说明与 current-path 引用
- `tests/test_run_store.py` — replay_run、get_latest_run_summary、get_latest_portfolio_state、get_previous_research_snapshot 测试

---

## 2. 新的 autonomous_paper_cycle 结构说明

```
run_autonomous_paper_cycle
    ├─ load_state(run_id, input_, store)
    │      → portfolio_before (AccountSnapshot), run_metadata, symbols
    │      写: meta, snapshots/portfolio_before.json
    ├─ build_research_bundle(run_id, symbols, use_mock, use_llm, store)
    │      → contracts_for_cycle, research_snapshot, ranked (OpportunityScore)
    │      写: snapshots/research.json, artifacts/candidate_decision.json
    ├─ evaluate_trigger_and_allocate(...)
    │      → trigger, trigger_trace, allocator_result
    │      写: audit (trigger)
    ├─ build_rebalance_plan(snap, alloc_result, signals)
    │      → RebalancePlan, order_intents（由 plan 生成）
    │      写: artifacts/final_decision.json, rebalance_plan.json, order_intents.json
    ├─ execute_paper_orders(...)
    │      → paper_execution_results
    ├─ finalize_run(run_id, store, portfolio_before, rebalance_plan, paper_results, paths)
    │      写: snapshots/portfolio_after.json, execution/paper_result.json, meta.ended_at
```

每阶段输入/输出明确，对应 artifact 写入 RunStore；debug / agent / replay 可逐阶段定位。

---

## 3. RebalancePlan 示例

```json
{
  "items": [
    {
      "symbol": "NVDA",
      "current_position": 0.0,
      "target_position": 0.25,
      "delta": 0.25,
      "action_type": "OPEN",
      "reason": "Small probe allowed.",
      "confidence": "medium"
    }
  ],
  "no_trade_reason": ""
}
```

action_type 枚举：OPEN（0→正）、ADD（增仓）、TRIM（减仓）、CLOSE（清仓）、REPLACE、HOLD（不变）。order_intents 由 rebalance_plan 生成，含 symbol、side、size_fraction、delta、action_type、rationale。

---

## 4. portfolio_after 示例

**有执行时**（由 rebalance_plan 推导新 positions）：

```json
{
  "timestamp": "2026-03-08T12:10:46.959902+00:00",
  "positions": [
    {"symbol": "NVDA", "weight_pct": 0.25, "market_value_estimate": 2500.0, "action_type": "OPEN"}
  ],
  "cash_estimate": 7500.0,
  "equity_estimate": 10000.0,
  "run_id": "conv2_demo",
  "source": "derived"
}
```

**无执行时**：portfolio_after = portfolio_before（并写入 run_id、_kind: after）。

---

## 5. 最小运行命令

```bash
# 单周期（mock，不执行 paper）
python -m ai_trading_research_system.presentation.cli paper-cycle --symbols SPY,QQQ,NVDA --mock --no-execute

# 单周期（mock，执行 paper，落盘 runs/）
python -m ai_trading_research_system.presentation.cli paper-cycle --symbols NVDA --mock --run_id my_run

# OpenClaw
python scripts/run_for_openclaw.py autonomous_paper_cycle NVDA --mock --run_id openclaw_run
```

（无 `--mode research`；当前 registry 未区分 mode=research 仅研究不执行，如需可后续加。）

---

## 6. 测试运行结果

- `uv run pytest tests/ -q --tb=line`：**145 passed, 1 skipped**（test_cycle_e2e_mock 占位跳过）。
- `paper-cycle --mock --symbols NVDA --run_id conv2_demo --no-execute` 已跑通，rebalance_plan、portfolio_after、write_paths 正常落盘。

---

## 7. 尚未解决但已暴露的问题

- **REPLACE**：action_type 已定义，当前 build_rebalance_plan 仅从 current/target 权重推导 OPEN/ADD/TRIM/CLOSE/HOLD；若 allocator 有“替换 A 为 B”的语义，需在 plan 中显式表达 REPLACE（例如一条 CLOSE A、一条 OPEN B）。
- **get_latest_portfolio_state** fallback：无 runs 时调 get_account_snapshot(mock=True)；生产可改为可配置或仅读本地。
- **weekly_paper_pipe** 未改为“多日循环调用 autonomous_paper_cycle”，仍为独立 pipe；状态与 runs/ 未统一。
- **order_intents 的 side**：当前仅从 delta 正负写 buy/sell；若需与交易所 side 严格一致，可再与 execution 层对齐。

---

## 任务七：文档与入口收敛

- **精简**：README 顶部改为“当前目标与主路径”，指向 docs/current-path.md；CLI 表增加 paper-cycle、paper 标为兼容。
- **新增**：docs/current-path.md（当前开发者导航：主入口、OpenClaw、paper 命令、结果位置、replay、兼容层）。
- **未移动**：历史文档仍在 docs/ 与 docs/archive/；仅在 README 与 convergence 中注明“历史阶段说明已下沉至 archive”。
- **标记**：run_paper 注释为 deprecated compatibility layer；新开发使用 autonomous_paper_cycle / paper-cycle。
- **开发者优先看**：**docs/current-path.md**、**docs/system_architecture.md**。
- **当前唯一推荐运行路径**：**paper-cycle**（CLI）或 **autonomous_paper_cycle**（OpenClaw/编程），状态与 artifact 落在 **runs/<run_id>/**，replay 用 **RunStore.replay_run(run_id)**。
