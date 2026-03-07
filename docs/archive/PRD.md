# AI Trading Research System — PRD v1

## 1. 产品定位

AI Trading Research System 是面向个人交易者的研究与决策增强系统。系统利用 LLM 多智能体对市场中的模糊、不完整和冲突信息做结构化分析，输出可解释的研究结论和交易建议。

系统目标不是直接替代交易员，而是：**提升研究效率 + 结构化不确定性 + 自动化研究流程。**

系统由三部分组成：

- **Research Layer（LLM）**：TradingAgents 风格多智能体分析（目标为 Fork 集成）
- **Control Layer（OpenClaw）**：自动运行、调度、交互
- **Execution Layer（确定性引擎）**：规则、风控与执行；目标为 **NautilusTrader** 统一回测与实盘

后续演进（经验闭环、多市场）见 [restructuring_plan.md](restructuring_plan.md)。

------------------------------------------------------------------------

## 2. 目标用户

核心用户：个人交易者 / 独立投资者 / 量化研究者

用户特征：有自身交易框架、不单纯依赖技术指标、需要整合新闻/基本面/情绪/价格、希望自动化研究流程、将 AI 作为研究辅助。

------------------------------------------------------------------------

## 3. 核心问题

- **信息碎片化**：新闻、公告、财报与行情分散，整合成本高。
- **模糊信息难结构化**：如突发事件、行业与叙事变化。
- **研究流程重复**：每日查新闻、公告、技术图并写判断。
- **研究与交易脱节**：决策缺少统一框架，复盘困难。

------------------------------------------------------------------------

## 4. 产品目标

让 AI 处理不确定信息，让系统保持纪律执行。

目标：① 自动化研究流程 ② 结构化交易判断 ③ 提升研究质量 ④ 支持自动运行 ⑤（演进）基于回测与实盘结果累积经验、迭代决策信号。

------------------------------------------------------------------------

## 5. 核心能力

### 自动研究任务

系统自动触发分析：每日盘前分析、标的事件分析、组合风险检查。触发方式：定时、用户命令、市场事件。

### 多智能体研究分析

Agent：News、Fundamental、Technical Context、Bull Thesis、Bear Thesis、Uncertainty、Synthesis；目标架构由 Fork 的 TradingAgents 提供，并注入历史经验上下文，见 [restructuring_plan.md](restructuring_plan.md)。

### 决策契约（Decision Contract）

研究输出标准化结构：symbol、thesis、supporting_evidence、counter_evidence、uncertainties、confidence、suggested_action、time_horizon、risk_flags；演进中增加 strategy_params、backtest_reference、experience_basis 等，见 [decision_contract.md](decision_contract.md)。

### 自动报告生成

生成：研究报告、每日市场总结、持仓分析、风险提示。

### 规则决策层

规则负责：信号过滤、风控、仓位约束。输出：watch、wait、small probe、allow entry、forbid trade。目标架构中规则并入 Strategy Bridge（Contract-to-Signal Translator），由 NautilusTrader 策略执行。

### 自动运行与交互

通过 OpenClaw：定时任务、聊天交互、任务控制、通知推送。

### 回测与经验闭环（目标架构）

- 使用 **NautilusTrader** 进行历史回测，与实盘同一套策略代码。
- 回测/实盘结果写入 **Experience Store**，下一轮研究注入历史经验，持续迭代信号质量。详见 [restructuring_plan.md](restructuring_plan.md)。

------------------------------------------------------------------------

## 6. 非目标

MVP 阶段不包括：高频交易、盘口级实时交易、LLM 直接下单、完全无人值守实盘。系统重点为研究增强。实盘将采用渐进式上线与风控（Circuit Breaker、仓位/回撤限制等），见 [restructuring_plan.md](restructuring_plan.md)。

------------------------------------------------------------------------

## 7. MVP 范围

支持：单标的研究、分钟/小时级任务、结构化分析输出、研究报告生成、CLI 或聊天交互。

当前不包含：复杂组合管理、多交易所实盘、复杂 Web UI。后续通过重构方案分阶段引入 NautilusTrader、经验闭环与实盘，见 [restructuring_plan.md](restructuring_plan.md)。

------------------------------------------------------------------------

## 8. 成功指标

1. 系统能稳定自动运行  
2. 每个研究任务生成结构化分析  
3. 研究输出可解释  
4. 用户可通过交互控制系统  
5. 研究流程明显自动化  
6. （演进）回测可复现、经验闭环可观测到信号/表现迭代

------------------------------------------------------------------------

## 9. 未来扩展（与重构方案对齐）

按 [restructuring_plan.md](restructuring_plan.md) 分阶段实施：

- **Phase 1–2**：NautilusTrader 依赖与目录重构；TradingAgents Fork 集成与真实数据
- **Phase 3**：NautilusTrader 回测集成
- **Phase 4**：经验累积与迭代闭环（Experience Store、Feedback、Injector）
- **Phase 5**：实盘就绪（IBKR Paper/Live、风控与人工干预）

其他扩展：多市场（A 股、加密货币）、组合管理、移动端通知、研究数据库等。

规范与检查项（DecisionContract、StrategySpec、Experience Store、实盘检查）见 [docs/README.md](README.md)。
