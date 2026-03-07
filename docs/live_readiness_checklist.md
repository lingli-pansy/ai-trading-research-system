# Live Readiness Checklist

策略进入实盘前必须通过以下检查项。对应重构方案 Phase 5，见 [restructuring_plan.md](restructuring_plan.md#5-分阶段实施)。

---

1. **Backtest stability across multiple time windows** — 多时间窗口回测稳定
2. **Out-of-sample performance acceptable** — 样本外表现可接受
3. **Minimum trade count threshold** — 达到最小交易次数阈值
4. **Maximum drawdown within risk tolerance** — 最大回撤在风险容忍内
5. **Paper trading period completed** — 纸面交易阶段完成
6. **Kill switch and risk guards verified** — Kill Switch 与风控（Circuit Breaker、仓位/回撤限制）已验证
7. **Broker connectivity tested** — 券商连通性（如 IBKR）已测试

---

## 相关文档

- [restructuring_plan.md](restructuring_plan.md) — Phase 5 实盘就绪
- [architecture.md](architecture.md) — Execution Layer 与风控
