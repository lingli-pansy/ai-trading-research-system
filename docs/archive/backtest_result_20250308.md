# 回测执行结果记录

**执行日期**：2025-03-08

## 命令

```bash
# 默认区间（mock）
python -m ai_trading_research_system.cli backtest NVDA --mock

# 指定区间（mock）
python -m ai_trading_research_system.cli backtest NVDA --start 2024-01-01 --end 2024-06-01 --mock
```

## 结果摘要

| 项目 | 运行 1（默认） | 运行 2（2024-01-01 ~ 2024-06-01） |
|------|----------------|-----------------------------------|
| symbol | NVDA | NVDA |
| contract action | probe_small | probe_small |
| confidence | medium | medium |
| sharpe | 0.0000 | 0.0000 |
| max_drawdown | 0.0000 | 0.0000 |
| win_rate | 0.0000 | 0.0000 |
| pnl | 0.00 | 0.00 |
| trades | 0 | 0 |
| strategy_run_id | 302 | 303 |

## 说明

- 使用 **--mock**：研究数据与行情为 mock，回测引擎为 NautilusTrader，结果写入 Experience Store。
- 当前 mock 路径下信号为 probe_small、未产生成交（trades=0），属预期；真实数据与日期区间可得到非零交易与 pnl。
- 使用真实数据与 LLM：`python -m ai_trading_research_system.cli backtest NVDA --start 2024-01-01 --end 2024-06-01 --llm`（需配置 OPENAI/KIMI 等）。

## 相关文档

- [operations.md](operations.md) — 命令与运行说明
- [execution_pipeline.md](execution_pipeline.md) — 回测管道
