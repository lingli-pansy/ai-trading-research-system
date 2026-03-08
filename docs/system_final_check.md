# 系统最终一致性检查（Final Stabilization）

**检查日期**：2026-03-08  
**范围**：Experiment Metadata 完整化 + 系统级 Stability / Consistency  
**约束**：无新增 agent / trading logic；未修改 allocator、policy、LLMResearchAgent、架构。

---

## 1. Experiment Metadata Schema

### 1.1 目标字段（规范）

| 字段 | 类型 | 说明 |
|------|------|------|
| `experiment_id` | str | 实验唯一标识 |
| `policy_version` | str | 策略/政策版本 |
| `strategy_version` | str | 策略版本（可与 policy 区分） |
| `dataset_range` | str | 数据区间（如 start_date–end_date） |
| `seed` | int/str | 可复现种子（可选） |
| `experiment_tag` | str | 实验标签（可选） |
| `created_at` | str | 创建时间（ISO） |

### 1.2 当前各模块覆盖情况

- **ExperimentCycle（内存 + 持久化）**
  - **已有**：`experiment_id`、`policy_version`；`start_time` 可视为周期开始时间。
  - **缺失**：`strategy_version`、`dataset_range`、`seed`、`experiment_tag`。
  - **Store**：表 `experiment_cycles` 含 `created_at`，但 `read_latest_experiment_cycle()` 的 SELECT 未包含 `created_at`，故当前读取路径未暴露该字段。
  - **结论**：Cycle 层具备基础 metadata（experiment_id、policy_version），其余为可选扩展；若需 `created_at`，需在 read 中增加该列。

- **WeeklyReport**
  - **已有**：`experiment_id`、`policy_version`、`evolution_guardrail_summary`。
  - **缺失**：`strategy_version`、`dataset_range`、`seed`、`experiment_tag`、`created_at`（均为可选）。
  - **结论**：与实验身份和策略版本相关的核心字段已具备；与 Report 写入时机对应的 `created_at` 可由调用方或报告生成时间推断。

- **ReplayResult（ExperimentReplay + replay_result 字典）**
  - **已有**：`ExperimentReplay` 含 `source_experiment_id`、`policy_version`、`strategy_version`；`replay_start`/`replay_end` 可表示重放区间。
  - **replay_result** 为 `WeeklyPaperResult.summary`，内含 `decision_traces_summary`、`decision_diff_summary` 等，身份通过容器 `ExperimentReplay` 表达。
  - **结论**：Replay 结果已具备完整可追溯的 metadata（含 strategy_version）。

- **Experience Store**
  - **experiment_cycles 表**：含 `experiment_id`、`policy_version`、`created_at`（表中存在，未在 read 中返回）；无 `strategy_version`、`dataset_range`、`seed`、`experiment_tag` 列。
  - **replay_comparison 表**：含 `source_experiment_id`、`replay_experiment_id`、`result_comparison_json`、`decision_diff_json`、`created_at`。
  - **结论**：Store 与 Report 在 `experiment_id`、`policy_version` 上一致；更完整的 metadata 需在表与 read/write 路径扩展（当前为可选）。

### 1.3 命名与类型统一情况

- `experiment_id`、`policy_version` 在 ExperimentCycle、WeeklyReport、report_service、weekly_finish_service、replay_service、store 中命名与用法一致。
- Replay 侧使用 `source_experiment_id` 表示源实验、`replay_experiment_id` 表示重放实验，与主实验的 `experiment_id` 区分清晰，无需改名。
- 未发现同义异名或类型不一致（如同一概念一处 str 一处 int）需要在本轮修正的问题。

---

## 2. Replay Determinism Verification

- **是否调用 LLMResearchAgent / 研究编排**  
  **结论：否。**  
  - `run_experiment_replay` 从 `read_latest_decision_traces_snapshot(source_experiment_id)` 读取 trace，构建 `recorded_research_by_symbol`（含 `research_thesis`、`research_key_drivers`、`research_risk_factors`），并传入 `run_weekly_autonomous_paper(..., recorded_research_by_symbol=recorded_research_by_symbol)`。
  - `weekly_paper_pipe` 中当 `recorded_research_by_symbol` 存在且当前 symbol 在其中有记录时，直接使用该记录构造 `DecisionContract`，不调用 `orchestrator.run_with_context()`，因此 **replay 不触发 LLM**。

- **是否 deterministic**  
  **结论：是（在相同输入下）。**  
  - 数据侧：replay 默认 `use_mock=True`，同一 mandate/watchlist 下 mock 数据确定。
  - 决策侧：研究结论来自 recorded trace，分配逻辑使用同一 `PortfolioDecisionPolicy`（从源 experiment 的 `applied_policies` 恢复），无随机分支。
  - 因此相同 `source_experiment_id`、相同 `policy_version`/`strategy_version` 与相同时间区间下，replay 结果可复现。

- **依据代码位置**  
  - `replay_service.run_experiment_replay`：构建 `recorded_research_by_symbol` 并传入 pipe。  
  - `weekly_paper_pipe.run_weekly_autonomous_paper`：存在 `recorded_research_by_symbol[sym]` 时使用 `rec` 构造 contract，否则才调用 `orchestrator.run_with_context(sym)`。

---

## 3. Evolution Guardrail Verification

- **Guardrail 结果是否写入报告与可回溯**  
  **结论：是。**  
  - `weekly_finish_service` 中根据 `decide_evolution(proposal, current_policy)` 得到 `decision`，并构造：
    - `evolution_guardrail_summary = { "guardrail_result": decision.guardrail_result, "guardrail_reason": decision.guardrail_reason }`
  - 该 summary 传入 `report_generate_and_write(..., evolution_guardrail_summary=...)`，最终进入 `WeeklyReport.evolution_guardrail_summary`。
  - Store 侧：`write_evolution_proposal_snapshot`、`write_evolution_decision_snapshot` 持久化 proposal 与 decision；`read_latest_evolution_proposal` 可读回，evolution proposal 可回溯。

- **与 Evolution Boundary 一致性**  
  - `evolution_boundary`（如 `PolicyDeltaLimit`、`validate_policy_adjustment`）产生的 `guardrail_result`/`guardrail_reason` 通过 `decide_evolution` 进入 decision，再进入上述 summary 与 snapshot，链路完整。

---

## 4. DecisionTrace Coverage

- **Replay 是否复用 recorded trace、是否不再调用 LLM**  
  **结论：是。**  
  - DecisionTrace 含 `research_thesis`、`research_key_drivers`、`research_risk_factors`（与 DecisionContract 对齐）。
  - 每次实验 run 时 allocator/pipe 将 trace 写入 store（`write_decision_traces_snapshot`）。
  - Replay 时从 `read_latest_decision_traces_snapshot(source_experiment_id)` 读取，仅当 trace 中已包含上述 research 字段时才填充 `recorded_research_by_symbol`，并传给 pipe；pipe 使用后不调用 LLM。
  - 因此 **replay 完全复用 recorded trace，不重新调用 LLM**。

- **Trace 内容覆盖**  
  - 单条 trace 包含：timestamp、symbol、opportunity_score、health_context、policy_constraints、trigger_context、allocator_reason、final_action、research_thesis、research_key_drivers、research_risk_factors。
  - 满足“决策可追溯 + 研究理由可复用于 replay”的设计目标。

---

## 5. SystemStatusSnapshot 与 Active Experiment

- **能否正确读取 active experiment**  
  **结论：能。**  
  - `get_system_status(experiment_id=None, ...)` 调用 `read_latest_experiment_cycle(experiment_id=experiment_id)`，当 `experiment_id` 为 `None` 时，SQL 按 `ORDER BY id DESC LIMIT 1` 取最新一条 experiment_cycles 记录。
  - 返回的 `cycle` 用于填充 `SystemStatusSnapshot.experiment_id`、`cycle_status`、`last_rebalance_time`、`active_policy`、`last_report_path` 等。
  - 因此 **SystemStatusSnapshot 能正确反映当前（最新）active experiment**。

---

## 6. Remaining Issues

- **无阻塞性问题**：Replay 不调 LLM、deterministic；DecisionTrace 覆盖 replay 复用；Evolution guardrail 写入报告且可回溯；SystemStatus 能读 active experiment；核心 metadata（experiment_id、policy_version）在 Cycle / Report / Replay / Store 间一致。

- **可选增强（非必须，可不改代码）**  
  1. **experiment_cycles 读取**：若需在 API/报告中暴露行的创建时间，可在 `read_latest_experiment_cycle` 的 SELECT 中增加 `created_at` 并在返回 dict 中带上。  
  2. **ExperimentCycle / WeeklyReport**：若需完整满足“目标 schema”中的 `strategy_version`、`dataset_range`、`seed`、`experiment_tag`，需在 ExperimentCycle、experiment_cycles 表、WeeklyReport 及对应 write/read 路径上增加字段并传参；当前 Replay 已在容器层具备 `strategy_version`。  
  3. **命名与类型**：当前无发现需强制统一的命名或类型问题；若未来增加 `seed`，建议统一为 `int` 或 `str` 之一并在全链路一致。

**总结**：系统满足本轮“工程收尾”的稳定性与一致性要求；未发现必须在本轮修复的缺陷。若仅需检查结果而不扩展功能，无需新增代码，以本文档为检查结果即可。
