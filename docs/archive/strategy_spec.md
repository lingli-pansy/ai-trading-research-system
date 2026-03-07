# StrategySpec v1

StrategySpec 定义**可复现的策略规则**，由 Strategy Bridge 根据 DecisionContract 与回测验证结果产出，经 StrategyCompiler 编译为 NautilusTrader 策略。与单次分析输出 **DecisionContract** 的区别见下方「与 DecisionContract 的关系」。

---

## Schema

```text
StrategySpec
    strategy_id: string
    symbol: string
    thesis: string
    entry_logic: list[string]
    exit_logic: list[string]
    filters: list[string]
    risk_controls:
        stop_loss_pct: float
        take_profit_pct: float
        max_position_pct: float
    time_horizon: intraday | swing | position
    regime_tag: optional string
```

---

## 用途

- 可复现回测（同一 StrategySpec 多次回测结果一致）
- 参数调优与版本管理
- 策略想法的版本化与审计

---

## 与 DecisionContract 的关系

- **DecisionContract**：单次研究输出，包含 thesis、evidence、suggested_action、confidence 等，见 [decision_contract.md](decision_contract.md)。
- **StrategySpec**：由 Contract + 回测/经验验证后沉淀的「可执行策略规则」；Contract 的 strategy_params、backtest_reference 等可参与生成 StrategySpec。Bridge 负责 Contract → 信号/StrategySpec，StrategyCompiler 负责 StrategySpec → NautilusTrader Strategy。

---

## 相关文档

- [decision_contract.md](decision_contract.md) — DecisionContract 规范
- [architecture.md](architecture.md) — Strategy Bridge 与 StrategyCompiler
- [restructuring_plan.md](restructuring_plan.md) — 目标架构与目录结构
