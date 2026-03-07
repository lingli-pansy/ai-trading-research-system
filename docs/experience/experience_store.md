# Experience Store

**ExperienceStore** 持久化策略运行、回测结果与交易经验，供经验闭环与下一轮研究注入。

---

## 表概览

| 表名 | 用途 |
|------|------|
| strategy_run | 每次策略运行元数据（标的、时间范围、参数、regime） |
| backtest_result | 回测绩效（Sharpe、回撤、胜率、PnL、交易次数） |
| trade_experience | 单笔交易经验（信号快照、结果、失败原因、改进建议） |
| experience_summary | 按 regime 聚合的表现与主要失败模式 |

---

## 写入口

- **模块**：`src/ai_trading_research_system/experience/writer.py`
- **接口**：`write_run_result(payload: RunResultPayload, *, db_path=None) -> int`
- **RunResultPayload**：symbol, start_date, end_date, sharpe, max_drawdown, win_rate, pnl, trade_count；可选 extra（如 strategy_spec_snapshot）、regime_tag。
- 每次 run 自动写入 strategy_run、backtest_result、一条 trade_experience，并触发按 regime 聚合写 experience_summary。

---

## 参考

- 表结构细节：[../archive/experience_schema.md](../archive/experience_schema.md)
- 下一阶段接口（TradingAgents 预留）：[../archive/next_phase_interface.md](../archive/next_phase_interface.md)
