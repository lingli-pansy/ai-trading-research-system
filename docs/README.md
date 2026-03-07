# 文档索引

开发前建议按以下顺序阅读，便于直接进入开发阶段。

**当前执行计划**：跑通链路并在 Paper 试跑 → 见 [plan_week_to_paper.md](plan_week_to_paper.md)（执行顺序与阶段验收）。  
**开发前准备**：阶段验收前置条件（权限、数据、IBKR Paper 等）→ 见 [dev_prerequisites.md](dev_prerequisites.md)。

---

## 必读（开发入口）

| 文档 | 用途 |
|------|------|
| [restructuring_plan.md](restructuring_plan.md) | **总纲**：重构目标、目标架构图、目录结构、现有模块处理、5 阶段实施、经验闭环与风险 |
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
| [live_readiness_checklist.md](live_readiness_checklist.md) | 策略进入实盘前的检查项（回测稳定性、OOS、纸面、风控、Kill Switch、券商连通性） |

---

## 文档关系（无冲突约定）

- **DecisionContract**：单次研究输出；**StrategySpec**：由 Contract + 回测验证后得到的可复现策略定义，见 [strategy_spec.md](strategy_spec.md)。
- **Strategy Bridge**：Contract → 信号/策略参数；产出 StrategySpec 时由 **StrategyCompiler** 编译为 NautilusTrader 策略。
- **Experience Store**：表结构以 [experience_schema.md](experience_schema.md) 为准；实现与闭环逻辑见 [restructuring_plan.md](restructuring_plan.md)。
- **实盘**：Phase 5 实施前需通过 [live_readiness_checklist.md](live_readiness_checklist.md)。
