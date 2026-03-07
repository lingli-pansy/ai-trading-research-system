# StrategySpec 规范

**StrategySpec** 定义可复现的策略规则，由 Strategy Bridge 根据 DecisionContract 与回测验证结果产出，经 StrategyCompiler 编译为 NautilusTrader 策略。

---

## Schema

- strategy_id, symbol, thesis
- entry_logic, exit_logic, filters
- risk_controls（stop_loss_pct, take_profit_pct, max_position_pct）
- time_horizon（intraday | swing | position）
- regime_tag（可选）

---

## 与 DecisionContract 的关系

- **DecisionContract**：单次研究输出，见 [decision_contract.md](decision_contract.md)。
- **StrategySpec**：Contract + 回测/经验验证后沉淀的可执行策略规则；StrategyCompiler 将 StrategySpec 编译为 NautilusTrader Strategy。

---

## 参考

- 完整 Schema 与用途：[../archive/strategy_spec.md](../archive/strategy_spec.md)
