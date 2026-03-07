# 文档索引

开发前建议按以下顺序阅读，便于直接进入开发阶段。

**MVP 已达成**；**Phase 2（Interactive Research System）** 已达成。实盘前工作见 [live_readiness_checklist.md](live_readiness_checklist.md)。  
**开发前准备**：权限、数据、IBKR Paper 等 → 见 [dev_prerequisites.md](dev_prerequisites.md)。  
**脚本用法**：见仓库根 [README.md](../README.md#统一-cliphase-2-推荐入口)。  
**过程文档**：开发过程/归档类文档可放在 `docs/local/`（已加入 .gitignore，不提交，仅本地维护）。

---

## 必读（开发入口）

| 文档 | 用途 |
|------|------|
| [CURRENT_STATE.md](CURRENT_STATE.md) | **当前状态总表**：能跑通什么、哪些 mock、过渡层 vs 长期保留、下一步替换/补齐（2 分钟速览） |
| [restructuring_plan.md](restructuring_plan.md) | **总纲**：重构目标、目标架构图、目录结构、现有模块处理、5 阶段实施、经验闭环与风险 |
| [nautilus_migration.md](nautilus_migration.md) | **NautilusTrader 迁移**：回测链现状、Paper/Live 待迁移、与 P2 方案 A 一致的任务顺序 |
| [architecture.md](architecture.md) | **架构**：分层原则、当前/目标模块、数据流、Tech Stack、与 StrategySpec/Experience/Live 的衔接 |
| [mvp_plan.md](mvp_plan.md) | **节奏**：8 周 MVP 任务与交付、Post-MVP 与重构 Phase 1–5 的对应关系 |

---

## 规范（接口与数据）

| 文档 | 用途 |
|------|------|
| [decision_contract.md](decision_contract.md) | DecisionContract 用途、核心/扩展字段、Agent 职责、规则映射、回测与评估 |
| [strategy_spec.md](strategy_spec.md) | StrategySpec 定义：可复现策略规则，由 Strategy Bridge 产出并编译进 NautilusTrader |
| [experience_schema.md](experience_schema.md) | Experience Store 表结构：strategy_run、backtest_result、trade_experience、experience_summary |

---

## 产品与上线

| 文档 | 用途 |
|------|------|
| [PRD.md](PRD.md) | 产品定位、目标用户、核心能力、MVP 范围、成功指标、未来扩展（与重构对齐） |
| [live_readiness_checklist.md](live_readiness_checklist.md) | **实盘前工作清单**：7 项必过检查（回测稳定性、OOS、交易次数、回撤、Paper、风控、券商连通性）及补齐任务 L1–L7 |
| [mock_vs_real.md](mock_vs_real.md) | 各模块 Mock vs 真实实现对照，及替换优先级（Research/数据源/IBKR/风控） |
| [openclaw_integration.md](openclaw_integration.md) | **交互形态**：通过 OpenClaw Agent 交互；CLI 与 OpenClaw Skill 打通。触发方式与报告格式（run_for_openclaw、JSON 报告） |
| [scheduling.md](scheduling.md) | 研究任务自动运行（cron、run_scheduled、REPORT_DIR 与环境变量） |
| [deferred_authorization.md](deferred_authorization.md) | **实盘与生产对接清单**：IB Gateway、LLM API 已支持；IBKR/OpenClaw/生产密钥配置与步骤（与实盘前工作配合） |

---

## 文档关系（无冲突约定）

- **DecisionContract**：单次研究输出；**StrategySpec**：由 Contract + 回测验证后得到的可复现策略定义，见 [strategy_spec.md](strategy_spec.md)。
- **Strategy Bridge**：Contract → 信号/策略参数；产出 StrategySpec 时由 **StrategyCompiler** 编译为 NautilusTrader 策略。
- **Experience Store**：表结构以 [experience_schema.md](experience_schema.md) 为准；实现与闭环逻辑见 [restructuring_plan.md](restructuring_plan.md)。
- **实盘**：MVP 完成后、Phase 5 实施前需通过 [live_readiness_checklist.md](live_readiness_checklist.md)（实盘前工作清单）全部检查项。
