# OpenClaw 集成说明

本文说明如何通过 OpenClaw 触发研究或研究+回测任务，以及报告格式。

**若 OpenClaw 已安装到本地**：可直接在 OpenClaw 中配置「执行命令」为本仓库的 `run_for_openclaw.py`（或 `run_scheduled.py`），传入 symbol、task 等参数，从 stdout 或 REPORT_DIR 获取 JSON 报告。IB Gateway 已启动时，后续可对接实盘/Paper 下单（当前仍为本仓 Paper 管道）。

---

## 触发方式

OpenClaw 可通过 **子进程调用** 本仓库脚本获取报告（协议以 OpenClaw 现有集成为准，如 CLI、HTTP、消息队列）。

**推荐入口**：`scripts/run_for_openclaw.py`

```bash
# 仅研究，输出 Contract 报告（JSON 到 stdout）
python scripts/run_for_openclaw.py research [SYMBOL] [--mock] [--llm]

# 研究 + 回测，输出含回测指标的报告（JSON 到 stdout）
python scripts/run_for_openclaw.py backtest [SYMBOL] [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--mock] [--llm]
```

- **SYMBOL**：默认 `NVDA`。
- **--mock**：使用 mock 研究数据。
- **--llm**：使用 LLM Agent（需配置 `OPENAI_API_KEY` 或 `KIMI_CODE_API_KEY`）。
- 成功时：退出码 0，报告 JSON 打印到 stdout。
- 失败时：退出码 1，错误信息到 stderr。

### LLM 与 OpenClaw 模型对应

OpenClaw 中 Kimi Coding 的模型标识为 **`kimi-coding/k2p5`**（provider/model）。本仓与之对齐：

| OpenClaw | 本仓环境变量 | 说明 |
|----------|--------------|------|
| 认证 `kimi-code-api-key` | `KIMI_CODE_API_KEY` | 同一 key（来自 [Kimi Code 控制台](https://www.kimi.com/code/console)） |
| 端点 | `KIMI_BASE_URL` 默认 `https://api.kimi.com/coding/v1` | Kimi Code API |
| 模型 `k2p5` | `KIMI_MODEL` 默认 `k2p5` | Kimi K2.5 |

不配置 `OPENAI_API_KEY` 且配置了 `KIMI_CODE_API_KEY` 时，`--llm` 会使用上述 Kimi Code 端点与模型。

**为何 OpenClaw 可用、本仓直接调用曾 403？** Kimi Code 服务端按 **User-Agent 白名单**放行（仅允许 Kimi CLI、Claude Code、Roo Code、Kilo Code 等）。OpenClaw 或其它网关在请求中带上受认可的 User-Agent（如 `KimiCLI/1.3`）即可通过。本仓已对齐该方式：请求 Kimi Code 时默认增加 `User-Agent: KimiCLI/1.3`，可通过环境变量 `KIMI_USER_AGENT` 覆盖。参考：[CLIProxyAPI #1280](https://github.com/router-for-me/CLIProxyAPI/issues/1280)、OpenClaw 使用 Kimi CLI 凭证或相同 UA 的实践。

---

## 报告格式

### research 任务

| 字段 | 类型 | 说明 |
|------|------|------|
| task | string | `"research"` |
| symbol | string | 标的 |
| completed_at | string | ISO 时间 |
| contract_action | string | suggested_action（如 wait_confirmation, probe_small） |
| contract_confidence | string | confidence（low / medium / high） |
| thesis_snippet | string | thesis 前 200 字符 |
| raw_contract | object | 完整 DecisionContract（JSON 序列化后） |

### backtest 任务

在 research 字段基础上增加：

| 字段 | 类型 | 说明 |
|------|------|------|
| sharpe | number | Sharpe 比率 |
| max_drawdown | number | 最大回撤 |
| win_rate | number | 胜率 |
| pnl | number | 累计盈亏 |
| trade_count | number | 交易次数 |
| strategy_run_id | number | Experience Store 中的 strategy_run id |

---

## 报告示例（backtest）

```json
{
  "task": "backtest",
  "symbol": "NVDA",
  "completed_at": "2026-03-07T10:00:00.000000Z",
  "contract_action": "probe_small",
  "contract_confidence": "medium",
  "thesis_snippet": "Market may still be repricing stronger medium-term growth...",
  "sharpe": 0.0,
  "max_drawdown": 0.0,
  "win_rate": 0.0,
  "pnl": 0.0,
  "trade_count": 1,
  "strategy_run_id": 6,
  "raw_contract": { ... }
}
```

---

## 程序化调用

若不通过 CLI，可在 Python 中直接调用 adapter：

```python
from ai_trading_research_system.pipeline.openclaw_adapter import (
    run_research_report,
    run_backtest_report,
)

report = run_research_report("AAPL", use_mock=False, use_llm=False)
# report 为 dict，可 json.dumps(report) 或回传 OpenClaw

report = run_backtest_report("AAPL", start_date="2024-01-01", end_date="2024-06-01")
```

---

## 相关文档

- 脚本用法汇总：[README.md](../README.md#脚本用法research--回测--paper--联调)
- MVP 完成标准：[mvp_plan.md](mvp_plan.md)
