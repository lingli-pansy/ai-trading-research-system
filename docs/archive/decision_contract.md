# Decision Contract Specification v1

AI Trading Research System

> 执行层与经验闭环的对接方式见 [restructuring_plan.md](restructuring_plan.md)。本文定义 Contract 的用途与字段，含目标架构下的扩展字段。

------------------------------------------------------------------------

## 1. Purpose

Decision Contract 是系统研究层与执行层之间的核心接口协议。

LLM 多智能体负责生成研究结论，但不直接执行交易。执行层（当前为 RuleEngine + Paper；目标为 NautilusTrader）只接收结构化数据，而不是自然语言。

Decision Contract 的作用：

- 将模糊研究结论结构化
- 提供可解释的交易建议
- 允许规则/Strategy Bridge 进行过滤和风控
- 允许回测系统复现历史决策
- （目标架构）关联策略参数与历史回测，支撑经验注入与迭代

------------------------------------------------------------------------

## 2. Contract Schema

### 2.1 核心字段（当前已用）

    DecisionContract

    symbol: string
    analysis_time: datetime

    thesis: string
    key_drivers: list[string]

    supporting_evidence: list[string]
    counter_evidence: list[string]

    uncertainties: list[string]

    confidence: enum
        low
        medium
        high

    suggested_action: enum
        forbid_trade
        watch
        wait_confirmation
        probe_small
        allow_entry

    time_horizon: enum
        intraday
        swing
        position

    risk_flags: list[string]

### 2.2 扩展字段（目标架构，见 restructuring_plan.md）

    strategy_params: StrategyParams | null   # 策略参数建议（仓位、止损/止盈等）
    backtest_reference: string | null        # 关联的历史回测 ID
    experience_basis: list[string]           # 本结论所依据的经验条目摘要

**与 StrategySpec 的关系**：Contract 是单次研究输出；可复现的策略规则由 Strategy Bridge 产出为 **StrategySpec**，见 [strategy_spec.md](strategy_spec.md)。

------------------------------------------------------------------------

## 3. Field Definitions

### symbol

交易标的。

### analysis_time

分析时间，用于回测和历史记录。

### thesis

核心市场叙事。

示例： "市场正在重新定价AI服务器需求增长。"

### key_drivers

推动 thesis 的关键变量。

例如： - earnings growth - policy support - sector momentum

### supporting_evidence

支持当前 thesis 的证据。

例如： - 最新财报 - 新闻事件 - 技术走势

### counter_evidence

反对当前 thesis 的证据。

例如： - 宏观风险 - 估值过高 - 资金流出

### uncertainties

当前判断中最大的不确定性。

例如： - upcoming earnings - regulatory changes

### confidence

LLM 对当前 thesis 的置信度。

low：信号弱\
medium：有一定信号\
high：多维度一致

### suggested_action

系统建议的交易动作等级。

forbid_trade\
禁止交易

watch\
加入观察池

wait_confirmation\
等待额外信号

probe_small\
小仓位试错

allow_entry\
允许开仓

### time_horizon

交易时间框架。

intraday\
日内

swing\
几天到几周

position\
中期持仓

### risk_flags

标记潜在风险，例如：

-   earnings_risk
-   liquidity_risk
-   macro_risk
-   valuation_risk

------------------------------------------------------------------------

## 4. Agent Output Responsibilities

### News Agent

负责新闻摘要与事件识别。

输出：

-   supporting_evidence
-   uncertainties

------------------------------------------------------------------------

### Fundamental Agent

负责财务与基本面分析。

输出：

-   key_drivers
-   supporting_evidence
-   counter_evidence

------------------------------------------------------------------------

### Technical Context Agent

负责价格行为和市场结构。

输出：

-   supporting_evidence
-   counter_evidence

------------------------------------------------------------------------

### Bull Thesis Agent

负责构造最乐观逻辑。

输出：

-   thesis
-   supporting_evidence

------------------------------------------------------------------------

### Bear Thesis Agent

负责构造最悲观逻辑。

输出：

-   counter_evidence
-   risk_flags

------------------------------------------------------------------------

### Uncertainty Agent

专门寻找未知变量。

输出：

-   uncertainties

------------------------------------------------------------------------

### Synthesis Agent

整合所有 Agent 输出。

负责生成最终：

-   thesis
-   confidence
-   suggested_action

------------------------------------------------------------------------

## 5. Rule Engine / Strategy Bridge Mapping

执行层不读取自然语言，只消费以下字段及扩展字段（若存在）：

- suggested_action
- confidence
- risk_flags
- time_horizon
- （目标架构）strategy_params、backtest_reference

**当前 MVP**：独立 RuleEngine 将 Contract 转为信号与仓位比例，见 `decision/rules.py`。

**目标架构**：规则逻辑并入 Strategy Bridge（Contract-to-Signal Translator），由 NautilusTrader 的 AISignalStrategy 执行，见 [restructuring_plan.md](restructuring_plan.md) 与 [architecture.md](architecture.md)。

示例规则逻辑（与当前 RuleEngine 一致，可迁移到 Translator）：

    if suggested_action == "forbid_trade":
        block()

    if confidence == "low":
        ignore()

    if suggested_action == "probe_small":
        position_size = 0.25 * normal_size

    if suggested_action == "allow_entry" and confidence == "high":
        position_size = normal_size

------------------------------------------------------------------------

## 6. Backtest Replay

回测时不重新运行 LLM，而是直接使用历史 DecisionContract（或由 Contract 翻译得到的信号序列）。

优点：可复现、可统计 LLM 判断质量、可分析信号质量。

**目标架构**：回测由 NautilusTrader BacktestNode 执行；历史 Contract 或信号通过 ParquetDataCatalog 等注入，同一套 AISignalStrategy 用于回测与实盘，见 [restructuring_plan.md](restructuring_plan.md)。

------------------------------------------------------------------------

## 7. Evaluation Metrics

系统会评估：

- high confidence 信号胜率
- probe_small 成功率
- risk_flags 与回撤关系
- thesis 与实际市场走势偏差

目标架构中，回测指标写入 Experience Store，用于经验闭环与反馈生成，见 [restructuring_plan.md](restructuring_plan.md)。

------------------------------------------------------------------------

## 8. 相关文档

- [README.md](README.md) — 文档索引（开发入口）
- [restructuring_plan.md](restructuring_plan.md) — 重构方案（Contract 与 Strategy Bridge / Experience Store 的衔接）
- [architecture.md](architecture.md) — 系统分层与模块
- [strategy_spec.md](strategy_spec.md) — StrategySpec（可复现策略规则，由 Contract 参与生成）
- [PRD.md](PRD.md) — 产品需求
