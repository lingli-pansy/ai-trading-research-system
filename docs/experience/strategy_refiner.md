# Strategy Refiner（目标架构）

经验驱动策略优化：ExperienceStore → **Strategy Refiner** → 改进后的 StrategySpec → 下一轮回测/研究。

---

## 职责

- 消费 backtest_result、trade_experience、experience_summary
- 产出策略改进建议或新版 StrategySpec
- 与 Agent Loop 闭环衔接，见 [../architecture/agent_loop.md](../architecture/agent_loop.md)

---

## 当前实现（占位）

- `experience/refiner.refiner_suggest(strategy_run_id)`：根据该 run 的 backtest 指标做规则建议（无成交、Sharpe<0、回撤大等），返回一句改进建议；完整 Refiner Agent 为后续阶段。
