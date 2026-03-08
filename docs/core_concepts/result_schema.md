# ResultSchema（统一结果模型）

CLI、OpenClaw、E2E 消费的执行结果字段对齐。backtest / paper / demo 均包含以下核心字段。

---

## 核心字段

| 字段 | 说明 |
|------|------|
| symbol | 标的 |
| action / suggested_action / confidence | 策略信号与契约 |
| trade_count | 成交笔数，0 表示未下单 |
| pnl, max_drawdown | 绩效 |
| engine_type, used_nautilus | 执行引擎 |
| status | "ok" 或 "no_trade" |
| reason | status=no_trade 时原因（如 wait_confirmation） |

---

## status 与 reason

- **status=ok**：正常执行，可有 trade_count=0。
- **status=no_trade**：未产生交易，非异常；reason=wait_confirmation 等。

---

## UC-09 周报输出（weekly-paper）

| 字段 | 说明 |
|------|------|
| ok | 是否成功 |
| mandate_id | 本次 mandate 标识 |
| status | 状态（如 completed_week） |
| capital_limit, benchmark | 资本与基准 |
| engine_type, used_nautilus | 执行引擎 |
| report_path | 周报 JSON 文件路径；**分析结果、新闻、盘面指标**均在此文件内 |
| summary | portfolio_return, benchmark_return, excess_return, trade_count, pnl, daily_research_count, analysis_in_report |

**周报文件（report_path）内容**：除收益与交易汇总外，含 **daily_research** 数组；以及 **benchmark_source**（"yfinance" | "mock"）。主路径默认真实数据，输出 JSON 含 **snapshot_source**、**market_data_source**、**benchmark_source**，fallback 到 mock 时显式标记。

---

## 参考

- 实现：`src/ai_trading_research_system/pipeline/result_schema.py`
- 报告格式：[../integration/openclaw_integration.md](../integration/openclaw_integration.md)
- 完整说明：[../archive/result_schema.md](../archive/result_schema.md)
