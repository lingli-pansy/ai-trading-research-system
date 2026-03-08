# Trading Agent 工具说明

OpenClaw Agent 通过本仓库 workspace 与用户对话时，可调用以下工具完成四类用户指令。

## 用户指令与工具

| 用户说法示例 | 意图 | 工具调用 |
|-------------|------|----------|
| 开始建仓、建仓、start position | 开始建仓 | 见下 |
| 当前投资情况、组合、portfolio | 查看组合 | 见下 |
| 调仓建议、最近有没有调仓、rebalance | 查看调仓建议 | 见下 |
| 确认执行、确认、执行、approve | 确认并执行 | 见下 |

## 统一调用方式

在**本仓库根目录**执行，将用户原始消息传入 `--message`：

```bash
uv run python -m ai_trading_research_system.presentation.cli openclaw-trading-intent --message "<用户发送的原文>"
```

可选：`--config configs/openclaw_agent.paper.yaml` 指定配置；`--json` 输出紧凑 JSON。

返回为 JSON，包含 `intent`、`ok` 及与意图相关的字段（如 `proposal_summary`、`portfolio`、`run_id`、`paper_results` 等）。Agent 应根据返回内容向用户解释或请求确认。

## 说明

- Agent 只负责：解释 proposal、请求用户确认、在用户确认后触发执行。
- 不发明交易逻辑；不直接修改 runtime / proposal schema / execution pipeline。
