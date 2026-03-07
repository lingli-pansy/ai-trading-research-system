# System Architecture

AI Trading Research System

> 目标架构（NautilusTrader + 经验闭环）详见 [restructuring_plan.md](restructuring_plan.md)。本文描述分层原则与当前/目标模块划分。

------------------------------------------------------------------------

## 1. System Design Principles

1. **Research and execution separation**  
   LLM 处理不确定信息；执行层保持确定性（规则 + NautilusTrader）。

2. **Structured interfaces**  
   所有研究输出统一为 Decision Contract，执行层只消费结构化信号。

3. **Automated but controllable**  
   支持自动化运行，同时保留人工干预与风控开关。

4. **Modular architecture**  
   各模块职责清晰；回测与实盘共用同一套策略代码（NautilusTrader backtest-live parity）。

------------------------------------------------------------------------

## 2. System Layers

### Control Layer

负责调度、自动化与交互。

- **组件**：OpenClaw、Task Trigger、Notification
- **职责**：调度研究任务、接受用户命令、发送研究报告、监控系统状态

------------------------------------------------------------------------

### Research Layer

负责市场分析与 Decision Contract 生成。

- **组件**：Research Orchestrator、TradingAgents（Fork）、LLM、Experience Injector
- **职责**：拉取数据、运行多 Agent 分析、注入历史经验上下文、生成 Decision Contract、产出研究报告  
- **说明**：重构后由 Fork 的 TradingAgents 提供 Analyst / Researcher / Trader / Risk 等 Agent，详见 [restructuring_plan.md](restructuring_plan.md)。

------------------------------------------------------------------------

### Strategy Bridge（目标架构新增）

负责将 Decision Contract 转为可执行信号与可复现策略定义。

- **组件**：Contract-to-Signal Translator、Strategy Factory、**StrategySpec Generator**、**StrategyCompiler**
- **职责**：校验 Contract；映射 suggested_action/confidence/risk_flags 为仓位与风控参数；生成 NautilusTrader 策略所需配置；产出 **StrategySpec**（可复现策略规则）并由 StrategyCompiler 编译为 Nautilus 策略。StrategySpec 规范见 [strategy_spec.md](strategy_spec.md)。

------------------------------------------------------------------------

### Execution Layer

负责回测与实盘执行，统一由 NautilusTrader 承载。

- **组件**：NautilusTrader BacktestNode、LiveNode（如 IBKR Adapter）、AISignalStrategy
- **职责**：历史回测、纸面交易、实盘交易；仓位与风控由 Nautilus 内置 Portfolio / Risk 模块负责  
- **说明**：当前 MVP 为自研 PortfolioEngine + PaperTradingEngine；重构后由 NautilusTrader 替代，见 [restructuring_plan.md](restructuring_plan.md)。

------------------------------------------------------------------------

### Experience Layer（目标架构新增）

负责累积交易与回测经验，并反馈到研究层。

- **组件**：Experience Store、Feedback Generator、Experience Injector
- **职责**：持久化交易/回测结果、生成结构化经验与教训、在下一轮 Research 前注入历史上下文  
- **说明**：表结构见 [experience_schema.md](experience_schema.md)；闭环与实施见 [restructuring_plan.md](restructuring_plan.md#5-分阶段实施)。

------------------------------------------------------------------------

## 3. Module Flow

**当前 MVP：**

```text
User / Scheduler
      ↓
OpenClaw Control Plane
      ↓
Research Orchestrator → TradingAgents（当前为 mock）
      ↓
Decision Contract
      ↓
Rule Engine
      ↓
Portfolio & Risk Engine
      ↓
Execution Engine（Paper）
```

**目标架构：**

```text
User / Scheduler
      ↓
OpenClaw Control Plane
      ↓
Research Orchestrator → TradingAgents（Fork）+ Experience Injector
      ↓
Decision Contract
      ↓
Contract-to-Signal Translator / StrategySpec Generator → StrategyCompiler → AISignalStrategy
      ↓
NautilusTrader（BacktestNode / LiveNode）
      ↓
Experience Store ← 回测/实盘结果
      ↓
Experience Injector → 下一轮 Research
```

------------------------------------------------------------------------

## 4. Core Modules

### OpenClaw Control Plane

系统入口。负责：启动与调度、用户交互、通知。不负责：交易逻辑、研究分析、下单执行。

------------------------------------------------------------------------

### Research Orchestrator

研究任务编排。负责：触发研究、调用数据源、协调 TradingAgents、注入经验上下文、输出 Decision Contract。

------------------------------------------------------------------------

### TradingAgents

多智能体研究层。当前 MVP 为本地 mock Agent；目标为 Fork [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents)，定制 Analyst / Researcher / Trader / Risk，输出与 Decision Contract 对齐。

------------------------------------------------------------------------

### Decision Contract

结构化研究结果接口。字段定义见 [decision_contract.md](decision_contract.md)。目标架构将扩展 strategy_params、backtest_reference、experience_basis 等字段。

------------------------------------------------------------------------

### Rule Engine / Contract Translator

当前：独立 RuleEngine 将 Contract 转为信号与仓位比例。  
目标：规则逻辑并入 Strategy Bridge（Contract-to-Signal Translator），由 NautilusTrader 策略执行。

------------------------------------------------------------------------

### Portfolio / Risk / Execution

当前：自研 PortfolioEngine、PaperTradingEngine。  
目标：由 NautilusTrader 内置 Portfolio、风控与执行模块承担；实盘通过 IBKR 等适配器接入。

------------------------------------------------------------------------

### Experience Store

目标架构新增。存储交易与回测结果、策略演进记录、经验总结，并为 Research 层提供可注入的上下文。表结构见 [experience_schema.md](experience_schema.md)；闭环逻辑见 [restructuring_plan.md](restructuring_plan.md)。

------------------------------------------------------------------------

## 5. Data Flow

1. OpenClaw 触发任务（如：分析标的、每日摘要、组合风险检查）
2. Research Orchestrator 拉取数据（行情、新闻、基本面等），并从 Experience Store 拉取相关历史经验
3. TradingAgents 执行多 Agent 分析，输出 Decision Contract
4. Strategy Bridge 将 Contract 转为 NautilusTrader 可消费的信号与策略参数
5. Strategy Bridge 将 Contract 转为信号或 StrategySpec；StrategyCompiler 编译为 Nautilus 策略
6. NautilusTrader 执行回测或实盘
7. 回测/实盘结果写入 Experience Store，供下一轮研究使用。实盘上线前需通过 [live_readiness_checklist.md](live_readiness_checklist.md)

------------------------------------------------------------------------

## 6. System Modes

- **Research Mode**：仅生成研究报告与 Decision Contract，不执行交易。
- **Signal Mode**：生成信号与策略参数，可进入回测，不实盘。
- **Auto Mode**：完整管道：研究 → 回测/纸面 → 经验写入；实盘需单独开关与风控。

------------------------------------------------------------------------

## 7. Tech Stack

| 类别     | 当前 MVP           | 目标（重构后）                    |
|----------|--------------------|-----------------------------------|
| 语言     | Python             | Python                            |
| LLM 编排 | -                  | LangGraph / LangChain             |
| Agent    | 自研 mock          | Forked TradingAgents              |
| 控制平面 | OpenClaw（规划）   | OpenClaw                          |
| 数据     | Mock               | yfinance / AkShare / News API 等  |
| 存储     | -                  | PostgreSQL / Parquet              |
| 回测/执行 | 自研 Paper         | **NautilusTrader**（统一回测与实盘） |

------------------------------------------------------------------------

## 8. 相关文档

- [restructuring_plan.md](restructuring_plan.md) — 重构方案（NautilusTrader + 经验闭环）
- [decision_contract.md](decision_contract.md) — Decision Contract 规范
- [strategy_spec.md](strategy_spec.md) — StrategySpec 规范（可复现策略规则）
- [experience_schema.md](experience_schema.md) — Experience Store 表结构
- [live_readiness_checklist.md](live_readiness_checklist.md) — 实盘前检查项
- [PRD.md](PRD.md) — 产品需求
- [mvp_plan.md](mvp_plan.md) — MVP 与后续路线
- [README.md](README.md) — 文档索引（开发入口）
