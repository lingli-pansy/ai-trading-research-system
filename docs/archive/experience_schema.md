# Experience Store Schema

Experience Store 持久化所有策略运行、回测结果与交易经验，供经验闭环与下一轮研究注入使用。架构与闭环逻辑见 [restructuring_plan.md](restructuring_plan.md)，实现目录见 [architecture.md](architecture.md)。

---

## 表概览

| 表名 | 用途 |
|------|------|
| strategy_run | 每次策略运行元数据（标的、时间范围、参数、regime） |
| backtest_result | 回测绩效（Sharpe、回撤、胜率、PnL、交易次数） |
| trade_experience | 单笔交易的经验（信号快照、结果、失败原因、改进建议） |
| experience_summary | 按 regime 聚合的表现与主要失败模式 |

---

## 表结构

### strategy_run

| 字段 | 说明 |
|------|------|
| strategy_id | 策略标识 |
| strategy_version | 策略版本 |
| symbol | 标的 |
| start_date | 开始日期 |
| end_date | 结束日期 |
| regime_tag | 市场 regime 标签（可选） |
| parameters | 策略参数（JSON 或序列化） |

### backtest_result

| 字段 | 说明 |
|------|------|
| strategy_id | 关联 strategy_run |
| sharpe | Sharpe 比率 |
| max_drawdown | 最大回撤 |
| win_rate | 胜率 |
| pnl | 累计盈亏 |
| trade_count | 交易次数 |

### trade_experience

| 字段 | 说明 |
|------|------|
| trade_id | 交易 ID |
| signal_snapshot | 当时的信号/Contract 快照 |
| outcome | 结果（盈亏、是否止损等） |
| failure_reason | 若失败，原因 |
| improvement_suggestion | 改进建议（可由 Feedback 生成） |

### experience_summary

| 字段 | 说明 |
|------|------|
| regime_tag | 市场 regime |
| aggregated_performance | 聚合表现 |
| dominant_failure_patterns | 主要失败模式摘要 |

---

## 相关文档

- [restructuring_plan.md](restructuring_plan.md) — 经验闭环与 Phase 4
- [architecture.md](architecture.md) — Experience Layer 与数据流
