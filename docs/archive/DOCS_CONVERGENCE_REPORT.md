# docs 收敛变更报告

## 目标

收敛 docs，只保留核心文档；历史与长文档移至 archive。

---

## 1. 扫描结果（收敛前分类）

| 类型 | 文档 |
|------|------|
| architecture | architecture/system_architecture_overview.md, agent_loop.md, user_journey.md |
| concept | core_concepts/result_schema.md, decision_contract.md, strategy_spec.md |
| pipeline | execution/execution_flow.md, paper_trading.md, nautilus_migration.md；experience/experience_store.md, strategy_refiner.md |
| integration | integration/openclaw_integration.md, cli_usage.md |
| operations | operations/current_state.md, mock_vs_real.md, verify_scripts.md |
| historical | archive/*（已存在） |

---

## 2. 新 docs 结构（收敛后）

```
docs/
├── README.md                      # 仅文档入口
├── system_architecture.md         # 目标架构（由 system_architecture_overview 合并）
├── core_concepts.md               # ResultSchema + DecisionContract + StrategySpec + Experience 写入口
├── execution_pipeline.md          # 执行流水线（execution_flow + paper_trading + nautilus 要点）
├── uc09_weekly_autonomous_paper.md # UC-09 入口、OpenClaw、验证
├── operations.md                  # 当前状态 + 验证脚本 + Mock 与过渡
└── archive/                       # 历史与长文档（含下列移动与既有文档）
    ├── Agent_Loop_and_Interaction.md  # 由 architecture/agent_loop.md 覆盖
    ├── User_Journey.md                 # 由 architecture/user_journey.md 覆盖
    ├── CURRENT_STATE.md                 # 由 operations/current_state.md 覆盖
    ├── mock_vs_real.md                  # 由 operations/mock_vs_real.md 覆盖
    ├── nautilus_migration.md           # 由 execution/nautilus_migration.md 覆盖
    ├── UC09_IMPLEMENTATION_PLAN.md      # 已存在
    ├── next_phase_interface.md         # 已存在
    └── …（其余既有 archive 文档不变）
```

---

## 3. 合并与移动

| 操作 | 源 | 目标 |
|------|------|------|
| 合并 | architecture/system_architecture_overview.md | docs/system_architecture.md |
| 合并 | core_concepts/result_schema.md + decision_contract.md + strategy_spec.md + Experience 写入口 | docs/core_concepts.md |
| 合并 | execution/execution_flow.md + paper_trading.md + nautilus 要点 | docs/execution_pipeline.md |
| 合并 | operations/current_state.md + verify_scripts.md | docs/operations.md |
| 新增 | — | docs/uc09_weekly_autonomous_paper.md |
| 移动/覆盖 | architecture/agent_loop.md | archive/Agent_Loop_and_Interaction.md |
| 移动/覆盖 | architecture/user_journey.md | archive/User_Journey.md |
| 移动/覆盖 | operations/current_state.md | archive/CURRENT_STATE.md |
| 移动/覆盖 | operations/mock_vs_real.md | archive/mock_vs_real.md |
| 移动/覆盖 | execution/nautilus_migration.md | archive/nautilus_migration.md |
| — | UC09_IMPLEMENTATION_PLAN.md, next_phase_interface.md | 已在 archive |

已删除：architecture/*.md、core_concepts/*.md、execution/*.md、experience/*.md、integration/*.md、operations/*.md（内容已合并或迁至 archive）。

---

## 4. 链接更新

- **仓库根 README.md**：docs/operations/current_state.md → docs/operations.md；docs/architecture/system_architecture_overview.md → docs/system_architecture.md；docs/core_concepts/* → docs/core_concepts.md；docs/integration/openclaw_integration.md → docs/core_concepts.md / docs/uc09_weekly_autonomous_paper.md；文档表改为新结构。
- **docs/README.md**：仅保留上述 5 个核心文档入口 + archive。
- **archive 内文档**：Agent_Loop、User_Journey、CURRENT_STATE、mock_vs_real、nautilus_migration、UC09_* 等内部链接已改为相对路径指向 ../system_architecture.md、../operations.md、../core_concepts.md、../execution_pipeline.md 或 archive 内文档。

---

## 5. 最终 docs 目录列表（核心）

| 路径 | 说明 |
|------|------|
| docs/README.md | 文档入口 |
| docs/system_architecture.md | 目标架构 |
| docs/core_concepts.md | ResultSchema、DecisionContract、StrategySpec、Experience Store |
| docs/execution_pipeline.md | 执行流水线 |
| docs/uc09_weekly_autonomous_paper.md | UC-09 周自治 Paper |
| docs/operations.md | 当前状态与运维 |
| docs/archive/ | 历史与参考（含本报告） |
