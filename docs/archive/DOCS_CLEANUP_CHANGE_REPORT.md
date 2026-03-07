# docs 系统性清理与收敛 — 变更报告

## 1. 新的 docs 结构

```text
docs/
├── README.md                    # 统一入口（Project Overview / Architecture / Core Concepts / Execution / Experience / Integrations / Operations / 术语 / Archive）
├── architecture/
│   ├── system_architecture_overview.md   # 目标架构总览、Mermaid、核心术语
│   ├── agent_loop.md                     # Agent Loop 与五层交互（目标态）
│   └── user_journey.md                   # User Journey 与 UC 摘要（目标态）
├── core_concepts/
│   ├── decision_contract.md
│   ├── strategy_spec.md
│   └── result_schema.md
├── execution/
│   ├── nautilus_migration.md
│   ├── paper_trading.md
│   └── execution_flow.md
├── experience/
│   ├── experience_store.md
│   └── strategy_refiner.md
├── integration/
│   ├── openclaw_integration.md
│   └── cli_usage.md
├── operations/
│   ├── current_state.md
│   ├── mock_vs_real.md
│   └── verify_scripts.md
└── archive/
    ├── DOCS_CLEANUP_STEP1_CLASSIFICATION.md
    ├── DOCS_CLEANUP_CHANGE_REPORT.md
    ├── README.md（旧文档索引）
    ├── Agent_Loop_and_Interaction.md
    ├── User_Journey.md
    ├── architecture.md
    ├── CURRENT_STATE.md
    ├── decision_contract.md
    ├── strategy_spec.md
    ├── result_schema.md
    ├── experience_schema.md
    ├── next_phase_interface.md
    ├── nautilus_migration.md
    ├── openclaw_integration.md
    ├── mock_vs_real.md
    ├── restructuring_plan.md
    ├── mvp_plan.md
    ├── PRD.md
    ├── AGENT_WORK_GUIDE.md
    ├── live_readiness_checklist.md
    ├── dev_prerequisites.md
    ├── deferred_authorization.md
    ├── scheduling.md
    ├── PRIVACY_AND_GIT.md
    └── system_architecture_overview.md
```

## 2. 被移动到 archive 的文档

- Agent_Loop_and_Interaction.md  
- User_Journey.md  
- architecture.md  
- CURRENT_STATE.md  
- decision_contract.md  
- strategy_spec.md  
- result_schema.md  
- experience_schema.md  
- next_phase_interface.md  
- nautilus_migration.md  
- openclaw_integration.md  
- mock_vs_real.md  
- system_architecture_overview.md  
- restructuring_plan.md  
- mvp_plan.md  
- PRD.md  
- AGENT_WORK_GUIDE.md  
- live_readiness_checklist.md  
- dev_prerequisites.md  
- deferred_authorization.md  
- scheduling.md  
- PRIVACY_AND_GIT.md  
- README.md（旧索引）

以上全部保留在 `docs/archive/`，不删除，仅作历史参考。

## 3. 被合并的文档

- **experience_schema.md + next_phase_interface.md** → **experience/experience_store.md**（表结构 + 写入口 write_run_result、TradingAgents 预留）
- **architecture 与 Agent Loop / User Journey**：目标架构保留在 architecture/ 三份独立文档，旧 architecture.md（混合当前/目标）移入 archive
- **dev_prerequisites + 旧 README 入口** → **integration/cli_usage.md**（CLI 子命令 + 开发前准备引用 archive）

## 4. 新增文档

- **architecture/system_architecture_overview.md** — 重写，仅目标架构 + Mermaid + 统一术语表  
- **architecture/agent_loop.md** — 精简自 Agent_Loop_and_Interaction，仅目标态 + Mermaid  
- **architecture/user_journey.md** — 精简自 User_Journey，UC 摘要 + 指向 archive 完整版  
- **execution/paper_trading.md** — 新建，Paper 入口与流程  
- **execution/execution_flow.md** — 新建，执行流 Mermaid + 简要说明  
- **experience/experience_store.md** — 新建，合并 experience_schema + next_phase 要点  
- **experience/strategy_refiner.md** — 新建，Refiner 职责与当前占位  
- **integration/cli_usage.md** — 新建，CLI 子命令表 + 开发前准备指向 archive  
- **operations/verify_scripts.md** — 新建，验证脚本列表  
- **operations/current_state.md** — 新建，精简当前状态（指向 archive 完整版）  
- **operations/mock_vs_real.md** — 新建，精简（指向 archive 完整版）  
- **docs/README.md** — 新建，统一入口（Project Overview / Architecture / Core Concepts / Execution / Experience / Integrations / Operations / 术语 / Archive）  
- **archive/DOCS_CLEANUP_STEP1_CLASSIFICATION.md** — 第一步分类结果  
- **archive/DOCS_CLEANUP_CHANGE_REPORT.md** — 本变更报告  

## 5. 更新的链接

- **仓库根 README.md**：所有 `docs/xxx.md` 改为 `docs/operations/current_state.md`、`docs/architecture/`、`docs/core_concepts/`、`docs/experience/`、`docs/integration/`、`docs/archive/` 下对应路径；文档表改为新结构；入口统一为 docs/README.md。  
- **docs/README.md**：仅链接新结构下文档及 archive，无旧平铺链接。  
- **各子目录内文档**：相对链接指向同目录或 `../archive/`、`../core_concepts/` 等，无指向已移除的根级 md。  

## 6. 确保项

- **文档没有丢失**：原根目录下 md 均移入 `docs/archive/`，可查完整版。  
- **架构说明只有一份权威版本**：目标架构以 **architecture/system_architecture_overview.md** 与 **architecture/agent_loop.md**、**architecture/user_journey.md** 为准；当前实现以 **operations/current_state.md** 为准。  
- **docs 目录结构清晰**：architecture（仅目标）、core_concepts、execution、experience、integration、operations（仅当前与运维）、archive（历史参考）。
