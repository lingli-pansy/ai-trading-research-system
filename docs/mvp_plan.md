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

# MVP 完成核对（当前交付）

| # | 标准 | 状态 | 交付物 | 备注 |
|---|------|------|--------|------|
| 1 | 研究任务可自动运行 | 已达成 | `run_scheduled.py`（--once 或 SCHEDULE_INTERVAL_MINUTES）、cron 示例见 [scheduling.md](scheduling.md) | 报告落盘至 REPORT_DIR |
| 2 | 多 Agent 分析产出 DecisionContract | 已达成 | ResearchOrchestrator、真实数据（yfinance 行情/基本面/新闻）、LLMResearchAgent（可选 --llm）、Context 相关 Agent 产出随输入变化 | 无 |
| 3 | Rule Engine 产出信号 | 已达成 | ContractTranslator、decision/rules.py，与 Nautilus 信号一致 | 无 |
| 4 | Paper trading 管道可用 | 已达成 | run_paper、PaperRunner、本仓 PaperTradingEngine；IBKR Paper 暂缓（需授权） | 见下方暂缓项 |
| 5 | OpenClaw 可触发任务并返回报告 | 已达成 | run_for_openclaw.py、openclaw_adapter（research/backtest 报告 JSON），见 [openclaw_integration.md](openclaw_integration.md) | 协议为 CLI/stdout；服务端对接可暂缓 |

**暂缓项（实盘前补齐）**：IBKR Paper 真实下单、OpenClaw 服务端或生产环境接入、生产用 API Key 与密钥管理，按 [live_readiness_checklist.md](live_readiness_checklist.md) 与 [deferred_authorization.md](deferred_authorization.md) 逐项对接。本仓 Paper 与 OpenClaw CLI 报告已可用，不影响 MVP 验收。

------------------------------------------------------------------------

# 实盘前工作（Pre-Live）

MVP 5 条已达成后，进入实盘前需完成以下工作，以 [live_readiness_checklist.md](live_readiness_checklist.md) 为验收清单。

| # | 检查项 | 状态 | 补齐要点 |
|---|--------|------|----------|
| 1 | 多时间窗口回测稳定 | 未达成 | 多区间回测脚本/报告，结果可复现 |
| 2 | 样本外表现可接受 | 未达成 | OOS 评估流程与阈值 |
| 3 | 最小交易次数阈值 | 未达成 | 阈值与统计口径（如 Store 查询） |
| 4 | 最大回撤在风险容忍内 | 未达成 | 回撤上限配置与监控 |
| 5 | 纸面交易阶段完成 | 部分达成 | 本仓 Paper 已完成；IBKR Paper 接入后勾选 |
| 6 | Kill Switch 与风控已验证 | 已达成 | 仓位上限、单日止损已实装（PAPER_*），可验证 |
| 7 | 券商连通性已测试 | 未达成 | TWS 端口已配置；需连通性验证脚本或步骤 |

**要求**：实盘前工作全部通过后，方可进入实盘或 IBKR Live 验证。详见 [live_readiness_checklist.md](live_readiness_checklist.md)。

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
- [live_readiness_checklist.md](live_readiness_checklist.md) — **实盘前工作清单**（必过项与补齐任务）
- [deferred_authorization.md](deferred_authorization.md) — 授权就绪后对接清单（IBKR / OpenClaw / 密钥 / 风控）
- [decision_contract.md](decision_contract.md) / [strategy_spec.md](strategy_spec.md) / [experience_schema.md](experience_schema.md) — 规范与数据
