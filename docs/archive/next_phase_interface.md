# 下一阶段接口准备（Experience Store / TradingAgents）

本文说明当前为 Experience Store 增强与 TradingAgents 真接入预留的最小接口，**本阶段不实现完整闭环**，只把「写入口」与扩展点约定清楚。

## Experience Store 写入口

- **模块**：`src/ai_trading_research_system/experience/writer.py`
- **接口**：`write_run_result(payload: RunResultPayload, *, db_path=None) -> int`
- **RunResultPayload**：symbol, start_date, end_date, sharpe, max_drawdown, win_rate, pnl, trade_count；可选 `extra` 字典供后续扩展。
- **当前实现**：委托现有 `store.write_backtest_result`，返回 strategy_run id；**backtest_pipe 已切到 `write_run_result`**，并写入 strategy_spec_snapshot 至 strategy_run.parameters。
- **下一阶段**：可在此处扩展为多表写入、本地 JSON 落盘、或对接 PostgreSQL/完整 Store 闭环；调用方统一通过 `write_run_result` 写入，便于切换实现。
- **UC-09 周自治 paper**：`weekly_paper_pipe` 每轮执行后调用 `write_run_result` 写入 strategy_run、backtest_result、trade_experience、experience_summary；周报与 benchmark 对比可写入 `extra` 或单独 JSON 文件（如 `reports/weekly_report_<mandate_id>.json`），与下一阶段报表/分析对接。

## TradingAgents 真接入

- **Orchestrator**：本阶段**不**对 `research/orchestrator.py` 做大规模替换；保持现有 ResearchOrchestrator 与 mock/LLM Agent 组合。
- **预留方式**：在 research 层保留「可替换 Agent 来源」的扩展点（如通过配置或 adapter 注入 TradingAgents graph）；具体 adapter 接口在确定 Fork 形态后再补。
- **文档**：重构方案见 [restructuring_plan.md](restructuring_plan.md) Phase 2（TradingAgents Fork 集成）；当前仅做接口与文档预留，不做实现。

## 参考

- Experience 表结构：[experience_schema.md](experience_schema.md)
- 重构阶段：[restructuring_plan.md](restructuring_plan.md#5-分阶段实施)
- 当前状态与优先级：[CURRENT_STATE.md](CURRENT_STATE.md)
