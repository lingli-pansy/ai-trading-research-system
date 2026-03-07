# 统一结果模型（result_schema）

CLI、OpenClaw、E2E 消费的执行结果字段对齐说明。backtest / paper / demo 输出均包含以下核心字段，便于外部一致解析。

## 核心字段（必含）

| 字段 | 类型 | 说明 |
|------|------|------|
| symbol | str | 标的 |
| action | str | 策略信号动作，如 paper_buy、wait、no_trade |
| confidence | str | 契约置信度，如 low、medium、high |
| suggested_action | str | 契约建议动作，如 probe_small、wait_confirmation、allow_entry |
| trade_count | int | 成交笔数，0 表示未下单 |
| pnl | float | 盈亏 |
| max_drawdown | float | 最大回撤（paper 可为 0） |
| engine_type | str | 执行引擎类型，当前固定 "nautilus" |
| used_nautilus | bool | 是否走 Nautilus 路径 |
| status | str | "ok" 或 "no_trade" |
| reason | str | 当 status=no_trade 时的原因，如 "wait_confirmation"、"runner_not_started" |

## status 与 reason 约定

- **status=ok**：正常执行，可能有 trade_count=0（例如信号为 wait 但执行成功）。
- **status=no_trade**：未产生交易；**不视为异常**，为明确结果状态。
  - **reason=wait_confirmation**：Research 输出为观望（如 wait_confirmation、watch_only），Contract 译为不下单。
  - reason 其他值：runner_not_started、no_signal、no_runner_result 等，见代码与日志。

## 来源与复用

- **BacktestPipeResult** → `pipeline.result_schema.from_backtest_pipe()` → `UnifiedRunOutput`；OpenClaw 的 BacktestReport / run_demo_report 已包含 engine_type、used_nautilus、status、reason。
- **PaperPipeResult** → `from_paper_pipe()` → `UnifiedRunOutput`；PaperRunnerResult 已扩展 trade_count、pnl、status、reason、used_nautilus。
- **CLI**：backtest / demo 使用 BacktestPipeResult；paper 使用 PaperRunnerResult，二者在 OpenClaw 与 E2E 中通过上述统一字段对齐。

## 参考

- 实现：`src/ai_trading_research_system/pipeline/result_schema.py`
- OpenClaw 报告格式：[openclaw_integration.md](openclaw_integration.md)
