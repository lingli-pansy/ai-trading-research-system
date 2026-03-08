# Trading Agent 工具说明（同步完成式，无 exec/poll）

Agent 通过 **Python API** 调用 trading intent dispatcher，不构造 shell / exec / process:poll。一次调用同步返回 `{ status, summary, details }`，在一个响应内完成回复。

## 用户指令

| 用户说法 | 意图 |
|----------|------|
| 开始建仓、建仓、账户建仓 | 开始建仓 |
| 当前投资情况、组合 | 查看组合 |
| 调仓建议、最近有没有调仓 | 查看调仓建议 |
| 确认执行、确认、执行 | 确认并执行 |

## 调用方式（供 OpenClaw 或脚本）

**推荐：结构化参数，避免转义**

```bash
uv run python -m ai_trading_research_system.presentation.cli openclaw-trading-intent --message-json '{"message": "账户建仓"}'
```

**或 stdin：**

```bash
echo '{"message": "账户建仓"}' | uv run python -m ai_trading_research_system.presentation.cli openclaw-trading-intent
```

可选：`--config configs/openclaw_agent.paper.yaml`，`--timeout 30`（默认 30 秒）。

## 返回格式

```json
{
  "intent_run_id": "intent_...",
  "status": "ok | pending_confirmation | no_proposal | error",
  "summary": "简短说明",
  "details": { ... }
}
```

- Agent 根据 `status` 生成自然语言；`pending_confirmation` 时展示方案并问「是否确认执行？」；任务明确结束，无 poll。
