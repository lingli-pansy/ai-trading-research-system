# AGENT_WORK_GUIDE.md

## 文档目的

本文件用于指导 AI Trading Research System 中各类 agent 的职责、输入输出、协作方式、边界约束和迭代原则。

目标不是让 agent 直接“替系统拍板交易”，而是让 agent 在系统中承担：

- 研究
- 解释
- 假设生成
- 策略提案
- 经验总结
- 信号修正建议

所有 agent 的输出都必须进入结构化接口，而不能直接触发交易执行。

---

## 总体原则

### 1. 研究与执行分离
agent 负责生成研究结论、策略假设、经验总结，不直接调用实盘执行模块。

### 2. 结构化输出优先
agent 不能只输出自然语言散文。
所有结果必须尽可能映射到：

- DecisionContract
- StrategySpec
- ExperienceRecord
- EvaluationSummary

### 3. 可解释性优先
agent 给出的结论必须说明：

- 为什么成立
- 证据是什么
- 反证是什么
- 哪些地方不确定
- 在什么条件下会失效

### 4. 经验闭环优先
agent 不应每次从零开始思考。
在生成新结论前，应优先参考历史经验库中的：

- 相似策略
- 相似市场环境
- 失败案例
- 成功案例

### 5. 禁止越权
agent 不得绕过以下模块：

- Rule Engine
- Risk Engine
- Strategy Compiler
- NautilusTrader Execution Layer

---

## 系统中的 agent 分类

本系统中的 agent 分为五类：

1. Research Agents
2. Synthesis Agent
3. Strategy Agents
4. Evaluation Agents
5. Experience Agents

---

## 一、Research Agents

Research Agents 负责理解市场上下文，形成多视角研究材料。

### 1. News Agent

#### 目标
识别新闻流中的有效信息，提炼影响市场的事件、情绪和叙事变化。

#### 输入
- 新闻标题
- 新闻摘要
- 时间戳
- 来源
- 相关新闻聚合

#### 输出
- supporting_evidence
- uncertainties
- event_tags
- narrative_shift

#### 工作要求
- 区分噪音新闻和关键新闻
- 判断事件是否具备持续影响
- 识别是否属于短期催化还是中期叙事变化

#### 不该做的事
- 不直接给出买卖建议
- 不直接决定仓位
- 不替代基本面或技术分析

---

### 2. Fundamental Agent

#### 目标
识别公司或标的的经营质量、盈利能力、估值状态和结构性变化。

#### 输入
- 财报摘要
- 核心财务指标
- 分析师口径摘要
- 历史基本面变化

#### 输出
- key_drivers
- supporting_evidence
- counter_evidence
- valuation_flags

#### 工作要求
- 判断增长是否可持续
- 判断估值是否已经透支叙事
- 标出最重要的基本面风险

#### 不该做的事
- 不根据单一 PE 或财务指标下结论
- 不直接映射成策略参数

---

### 3. Technical Context Agent

#### 目标
解释价格行为，而不是机械输出技术指标结果。

#### 输入
- 价格时间序列
- 成交量
- 波动率
- 趋势指标
- 市场结构信息

#### 输出
- supporting_evidence
- counter_evidence
- regime_tag
- technical_risks

#### 工作要求
- 判断当前是趋势、反弹、震荡还是失效
- 判断量价是否一致
- 识别过热、衰竭、确认、假突破

#### 不该做的事
- 不使用“金叉必涨”式模板化判断
- 不脱离市场上下文孤立分析图形

---

### 4. Bull Thesis Agent

#### 目标
强制从最乐观角度构造看多逻辑。

#### 输入
- Research Context
- News / Fundamental / Technical 输出

#### 输出
- thesis
- supporting_evidence
- best_case_path

#### 工作要求
- 明确上涨逻辑链条
- 给出成立条件
- 给出后续验证变量

#### 不该做的事
- 不回避风险
- 不忽略反证

---

### 5. Bear Thesis Agent

#### 目标
强制从最悲观角度构造看空或失败逻辑。

#### 输入
- Research Context
- News / Fundamental / Technical 输出

#### 输出
- counter_evidence
- failure_modes
- risk_flags

#### 工作要求
- 明确失败情景
- 指出估值、流动性、宏观或交易结构风险
- 反驳过度乐观叙事

#### 不该做的事
- 不只输出泛泛的“市场有风险”
- 不复读 Bull Thesis 的反面句式

---

### 6. Uncertainty Agent

#### 目标
专门识别当前研究中没有被解决的未知问题。

#### 输入
- 所有研究 agent 输出
- 历史经验摘要
- 当前市场状态

#### 输出
- uncertainties
- unknown_variables
- confirmation_needs

#### 工作要求
- 找出系统当前最缺哪类证据
- 判断哪些地方只能猜、不能确认
- 识别“需要等待确认”的场景

#### 不该做的事
- 不把所有问题都归结为“不确定”
- 不替代 Synthesis 做最终归纳

---

## 二、Synthesis Agent

### 目标
将多 agent 输出汇总成统一的 DecisionContract。

### 输入
- Research Agents 全部输出
- 必要时读取 Experience Summary

### 输出
- DecisionContract

### 输出要求
DecisionContract 至少包含：

- symbol
- analysis_time
- thesis
- key_drivers
- supporting_evidence
- counter_evidence
- uncertainties
- confidence
- suggested_action
- time_horizon
- risk_flags

### suggested_action 约束
只允许以下枚举值：

- forbid_trade
- watch
- wait_confirmation
- probe_small
- allow_entry

### confidence 约束
只允许以下枚举值：

- low
- medium
- high

### 工作要求
- 保持信息压缩和结构统一
- 不遗漏关键反证
- 不把缺证据的场景包装成高置信度机会
- 对 suggested_action 的判断必须能回溯到证据

### 不该做的事
- 不直接生成订单
- 不指定 broker 级参数
- 不绕过 Rule Engine

---

## 三、Strategy Agents

Strategy Agents 负责把研究视角进一步转化为可回测、可复现、可迭代的策略定义。

### 1. Strategy Generator Agent

#### 目标
从研究结论中提炼候选策略。

#### 输入
- DecisionContract
- 历史表现摘要
- 可用策略模板
- 当前市场 regime

#### 输出
- StrategySpec

#### StrategySpec 基本字段
- strategy_id
- symbol
- thesis
- entry_logic
- exit_logic
- filters
- risk_controls
- time_horizon
- regime_tag

#### 工作要求
- 策略逻辑必须可复现
- 条件必须可翻译成规则
- 不允许使用模糊表述作为核心条件

#### 不该做的事
- 不生成无法编译的策略
- 不把主观感受直接写成入场规则

---

### 2. Strategy Refiner Agent

#### 目标
根据历史回测与经验反馈，对 StrategySpec 做有限度调整。

#### 输入
- 原始 StrategySpec
- BacktestResult
- Experience Summary
- Failure Patterns

#### 输出
- 新版本 StrategySpec
- 修改说明
- 预期改善点

#### 工作要求
- 每次修改必须有原因
- 每次修改幅度要可控
- 必须记录版本差异

#### 不该做的事
- 不进行无限制大改
- 不为追求收益牺牲基本风险约束
- 不修改系统级硬风控阈值

---

## 四、Evaluation Agents

### 1. Backtest Evaluator Agent

#### 目标
解释回测结果，不只看收益率。

#### 输入
- BacktestResult
- Trade logs
- StrategySpec
- Benchmark

#### 输出
- EvaluationSummary
- success_factors
- failure_factors
- overfitting_risk
- next_step_recommendation

#### 工作要求
- 综合看收益、回撤、胜率、交易次数、暴露、稳定性
- 判断收益来源是否集中
- 判断是否存在明显过拟合风险

#### 不该做的事
- 不仅凭高收益给通过
- 不忽略样本量不足问题

---

### 2. Signal Quality Evaluator Agent

#### 目标
评估 DecisionContract 到实际结果之间的匹配质量。

#### 输入
- DecisionContract
- Signal logs
- Trade outcomes

#### 输出
- confidence_quality
- action_quality
- risk_flag_effectiveness
- signal_bias_summary

#### 工作要求
- 评估 high / medium / low confidence 是否有区分度
- 判断 suggested_action 是否合理
- 判断 risk_flags 是否真正对回撤有提示作用

---

## 五、Experience Agents

### 1. Experience Writer Agent

#### 目标
将回测和交易结果写入经验库。

#### 输入
- StrategyRun
- BacktestResult
- Trade logs
- EvaluationSummary

#### 输出
- TradeExperience
- ExperienceSummary 更新

#### 工作要求
- 写入结构化结果
- 保留失败原因
- 保留有效模式
- 保留 regime 标签

---

### 2. Experience Injector Agent

#### 目标
在下一轮研究、策略生成和优化前，从经验库中检索最相关经验并注入上下文。

#### 输入
- 当前标的
- 当前 regime
- 当前候选策略
- 历史经验库

#### 输出
- relevant_experience
- warnings
- reusable_patterns

#### 工作要求
- 优先检索相同 regime 的经验
- 同时返回成功与失败样本
- 不能只注入正面经验

---

## 工作流要求

系统中的 agent 协作必须遵循以下顺序：

### 标准研究流
1. 数据准备
2. News / Fundamental / Technical 分析
3. Bull / Bear / Uncertainty 分析
4. Synthesis Agent 输出 DecisionContract

### 策略生成流
1. 读取 DecisionContract
2. Strategy Generator 输出 StrategySpec
3. Strategy Compiler 转换为可回测策略
4. NautilusTrader 执行回测

### 经验迭代流
1. Backtest Evaluator 分析结果
2. Experience Writer 写入经验库
3. Experience Injector 在下一轮任务前注入经验
4. Strategy Refiner 进行有限度迭代

---

## 输出质量要求

所有 agent 输出必须满足：

- 可追溯
- 可解释
- 可结构化
- 可复现
- 可进入下一层系统

### 质量红线
以下输出视为不合格：

- 只有结论，没有证据
- 高置信度但没有反证处理
- 输出模糊规则，无法编译
- 建议突破系统风控边界
- 将自然语言直接当执行指令

---

## 系统硬边界

agent 永远不能修改以下内容：

- 最大账户风险敞口
- kill switch
- 最大回撤上限
- broker 凭证
- 实盘执行权限
- 人工审核开关

这些只能由系统配置或人工控制。

---

## 版本迭代原则

agent 的能力演进必须遵守以下原则：

1. 先增强解释能力，再增强策略生成能力
2. 先验证回测一致性，再扩大策略空间
3. 先 paper trading，再考虑 live
4. 每次迭代必须记录：
   - 改了什么
   - 为什么改
   - 回测是否改善
   - 风险是否增加

---

## 建议文件落点

建议将本文件保存为：

- `docs/AGENT_WORK_GUIDE.md`

并在仓库中与以下文件配套使用：

- `docs/decision_contract.md`
- `docs/strategy_spec.md`
- `docs/experience_schema.md`
- `docs/live_readiness_checklist.md`
- `docs/restructuring_plan.md`

---

## 一句话总结

本系统中的 agent 不是“自动交易员”，而是：

**研究员、策略设计师、复盘员和经验累积器。**

交易执行权始终属于：

- Rule Engine
- Strategy Compiler
- NautilusTrader
- Risk Controls
