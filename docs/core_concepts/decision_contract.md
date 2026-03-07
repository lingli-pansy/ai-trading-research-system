# DecisionContract 规范

**DecisionContract** 是研究层与执行层之间的核心接口：LLM 多智能体产出研究结论，执行层只消费结构化契约。

---

## 用途

- 将研究结论结构化、可解释
- 供规则/Strategy Bridge 过滤与风控
- 支持回测复现与经验注入（目标架构）

---

## Schema（核心字段）

| 字段 | 说明 |
|------|------|
| symbol | 交易标的 |
| analysis_time | 分析时间 |
| thesis | 结论摘要 |
| key_drivers | 关键驱动 |
| supporting_evidence / counter_evidence / uncertainties | 证据与不确定性 |
| confidence | low / medium / high |
| suggested_action | forbid_trade / watch / wait_confirmation / probe_small / allow_entry |
| time_horizon | intraday / swing / position |
| risk_flags | 风险标签列表 |

扩展字段（目标架构）：strategy_params、backtest_reference、experience_basis。与 **StrategySpec** 的关系见 [strategy_spec.md](strategy_spec.md)。

---

## 参考

- 完整字段定义与 Agent 职责：[../archive/decision_contract.md](../archive/decision_contract.md)
