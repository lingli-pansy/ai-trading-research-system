# 第一步：docs 扫描与分类结果

## 分类结果

### Architecture（目标架构）
| 文档 | 说明 |
|------|------|
| system_architecture_overview.md | 目标架构总览（英文，含 Mandate/PortfolioController/AccountSnapshot） |
| Agent_Loop_and_Interaction.md | 系统交互与 Agent 循环（目标态） |
| User_Journey.md | 用户旅程与用例（目标态） |
| architecture.md | 混合：分层原则 + 当前/目标模块，与 restructuring_plan 重叠 |

### Design / Core Concepts
| 文档 | 说明 |
|------|------|
| decision_contract.md | DecisionContract 规范 |
| strategy_spec.md | StrategySpec 定义 |
| result_schema.md | 统一结果模型 |
| experience_schema.md | Experience Store 表结构 |
| next_phase_interface.md | 下一阶段接口（Experience 写入口、TradingAgents 预留） |

### Current State（当前实现）
| 文档 | 说明 |
|------|------|
| CURRENT_STATE.md | 当前状态总表 |
| mock_vs_real.md | Mock vs 真实实现对照 |

### Migration
| 文档 | 说明 |
|------|------|
| nautilus_migration.md | NautilusTrader 迁移规划与现状 |
| restructuring_plan.md | 重构方案与目标架构、阶段实施 |

### Integration
| 文档 | 说明 |
|------|------|
| openclaw_integration.md | OpenClaw 集成与 Skill 打通 |

### Schemas
| 文档 | 说明 |
|------|------|
| result_schema.md | 已列入 Core Concepts |
| experience_schema.md | 已列入 Core Concepts |
| next_phase_interface.md | 已列入 Design |

### Operations（运维/上线/开发入口）
| 文档 | 说明 |
|------|------|
| live_readiness_checklist.md | 实盘前工作清单 |
| dev_prerequisites.md | 开发前准备 |
| deferred_authorization.md | 实盘与生产对接 |
| scheduling.md | 研究任务自动运行 |
| PRIVACY_AND_GIT.md | 隐私与 Git |
| AGENT_WORK_GUIDE.md | Agent 工作规范（长文档） |

### Product / Roadmap
| 文档 | 说明 |
|------|------|
| PRD.md | 产品需求 |
| mvp_plan.md | MVP 与后续路线 |

### 入口
| 文档 | 说明 |
|------|------|
| README.md | 当前文档索引 |

### Local Alignment（不在此次重构的 docs 根下）
- docs/local/agent_loop_alignment.md、user_journey_alignment.md 等保留在 local，不移动。

---

## 与目标结构的对应

- **architecture/**：system_architecture_overview, agent_loop, user_journey（仅目标架构）
- **core_concepts/**：decision_contract, strategy_spec, result_schema
- **execution/**：nautilus_migration, paper_trading（新建或从 nautilus 拆出）, execution_flow（新建）
- **experience/**：experience_store（experience_schema + next_phase 合并）, strategy_refiner（新建简短）
- **integration/**：openclaw_integration, cli_usage（新建，从 dev_prerequisites + README 提炼）
- **operations/**：current_state, mock_vs_real, verify_scripts（新建）
- **archive/**：restructuring_plan, architecture.md（旧混合）, next_phase_interface, mvp_plan, PRD, AGENT_WORK_GUIDE, live_readiness_checklist, dev_prerequisites, deferred_authorization, scheduling, PRIVACY_AND_GIT（部分保留在 operations 或归档）
