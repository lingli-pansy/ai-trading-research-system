# AI Trading Research System — MVP & 后续路线

本文描述 **MVP 的 8 周建设计划**（当前基线），以及 **MVP 完成后的演进路线**（与 [restructuring_plan.md](restructuring_plan.md) 对齐）。

------------------------------------------------------------------------

## MVP 目标

构建 **research → signal → paper trading** 的稳定管道，使用 TradingAgents 风格多 Agent + OpenClaw。当前实现为 mock Agent 与自研 Paper 引擎；后续由 NautilusTrader 与 Forked TradingAgents 替代，见 [restructuring_plan.md](restructuring_plan.md)。

------------------------------------------------------------------------

# Week 1 — Project Foundation

**目标**：仓库、环境与核心结构就绪。

**任务**：创建仓库、Python 环境、依赖管理、目录结构、配置加载、日志框架。

**交付**：可运行项目、目录就绪、日志与配置可用。

------------------------------------------------------------------------

# Week 2 — Data Layer

**目标**：数据接入管道。

**任务**：行情加载、新闻接入、基本面加载、存储层（PostgreSQL 或 Parquet）、统一数据接口。

**交付**：`data_loader` 模块、历史行情可用、新闻与基本面管道可用。

------------------------------------------------------------------------

# Week 3 — Research Pipeline

**目标**：研究编排层。

**任务**：实现 Research Orchestrator、Agent 框架封装、LLM 接口（可选）、Agent 执行流程定义。

**交付**：研究管道端到端可运行、Agent 可顺序执行。

------------------------------------------------------------------------

# Week 4 — TradingAgents Integration

**目标**：多 Agent 分析集成。

**任务**：实现 News / Fundamental / Technical Context / Bull / Bear / Uncertainty Agent。

**交付**：多 Agent 分析管道、Agent 输出结构化。

*说明：后续由 Fork 的 TradingAgents 替代自研 Agent，见 [restructuring_plan.md](restructuring_plan.md)。*

------------------------------------------------------------------------

# Week 5 — Decision Contract

**目标**：核心系统接口。

**任务**：实现 DecisionContract schema、Synthesis Agent、Contract 校验、持久化（可选）。

**交付**：DecisionContract 可生成、研究结果可存储、校验可用。

------------------------------------------------------------------------

# Week 6 — Rule Engine

**目标**：研究输出转信号。

**任务**：信号过滤规则、动作映射、置信度阈值、信号日志。

**交付**：从 Contract 生成信号、动作等级可用（watch / wait_confirmation / probe_small / allow_entry / forbid_trade）。

*说明：目标架构中规则并入 Strategy Bridge（Contract-to-Signal Translator），由 NautilusTrader 策略执行。*

------------------------------------------------------------------------

# Week 7 — Portfolio & Paper Trading

**目标**：执行模拟。

**任务**：Portfolio Engine、仓位规则、Risk Engine、Paper Trading Engine。

**交付**：信号可转为模拟交易、组合状态可追踪、风险限制可执行。

*说明：目标架构由 NautilusTrader 统一回测与纸面/实盘，见 [restructuring_plan.md](restructuring_plan.md)。*

------------------------------------------------------------------------

# Week 8 — Automation with OpenClaw

**目标**：自动运行与交互。

**任务**：接入 OpenClaw 控制层、任务调度、命令接口、通知。

**交付**：系统可自动运行、用户可通过命令控制。

------------------------------------------------------------------------

# MVP 完成标准

MVP 视为完成需满足：

1. 研究任务可自动运行  
2. 多 Agent 分析产出 DecisionContract  
3. Rule Engine 产出信号  
4. Paper trading 管道可用  
5. OpenClaw 可触发任务并返回报告  

------------------------------------------------------------------------

# Post-MVP 路线（与重构方案一致）

MVP 完成后，按 **[restructuring_plan.md](restructuring_plan.md)** 分阶段实施，不再使用「vectorbt 后接 nautilus」的旧路线：

| 阶段 | 内容 | 参考 |
|------|------|------|
| Phase 1 | 基础重构与依赖（NautilusTrader、TradingAgents submodule、目录调整） | [restructuring_plan.md#5](restructuring_plan.md#5-分阶段实施) |
| Phase 2 | TradingAgents Fork 集成与真实数据源 | 同上 |
| Phase 3 | NautilusTrader 回测集成 | 同上 |
| Phase 4 | 经验累积与迭代闭环（Experience Store、Feedback、Injector） | 同上 |
| Phase 5 | 实盘就绪（IBKR Paper/Live、风控与人工干预） | 同上 |

其他扩展：多市场、组合优化、Web 看板、移动通知等，在重构方案落地后按需规划。

------------------------------------------------------------------------

## 相关文档

- [README.md](README.md) — 文档索引
- [restructuring_plan.md](restructuring_plan.md) — 重构总纲与 Phase 1–5
- [architecture.md](architecture.md) — 架构
- [decision_contract.md](decision_contract.md) / [strategy_spec.md](strategy_spec.md) / [experience_schema.md](experience_schema.md) / [live_readiness_checklist.md](live_readiness_checklist.md) — 规范与检查项
