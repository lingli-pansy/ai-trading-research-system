# Trading Agent — 同步桥接入口（唯一推荐）

**预期**：用户说 开始建仓/当前投资情况/调仓建议/确认执行 时，**由 agent 自动执行**——OpenClaw 应调用本仓 sync bridge，agent 在一个回复内呈现结果，**不让用户自己执行命令**。调用方式仅通过 **Python sync bridge**，**禁止** agent 使用 exec、process:poll、shell。

## 唯一入口（供平台/agent 自动调用）

- **Python**：`openclaw.bridge.handle_trading_intent_sync(message, config_path=None)`  
  平台应将此作为 workspace 的“调用入口”，由 agent **自动调用**以获取结果；内部直接调用 `dispatch_trading_intent`，一次调用、同步返回。不经 shell，不拼命令。

- **CLI（仅作人工联调 / bridge smoke）**：若需在本机终端手动测试，在本仓根目录执行：  
  `uv run python -m ai_trading_research_system.presentation.cli openclaw-trading-intent-sync --message-json '{"message": "开始建仓"}'`  
  正常预期是**平台调用 bridge、agent 自动执行**，而非用户跑此命令。

## 用户指令与 status

| 用户说法       | 意图         | 返回 status 示例           |
|----------------|--------------|----------------------------|
| 开始建仓、账户建仓 | 开始建仓     | pending_confirmation       |
| 当前投资情况、组合 | 查看组合     | ok                         |
| 调仓建议       | 查看调仓建议 | pending_confirmation / no_proposal |
| 确认执行、确认、执行 | 确认并执行   | ok / error                 |

## 返回格式

每次桥接返回均包含：

- `status`：ok | pending_confirmation | no_proposal | error  
- `summary`：简短说明（含「本次请求已完成。」）  
- `details`：结构化数据  
- `bridge_invoked`：true  
- `bridge_mode`：sync  
- `intent`：解析出的意图  

Agent 根据 `status` 与 `details` 在一个回复内生成自然语言，**不得**再发起 exec/poll/shell。

## 禁止（硬性）

- **不得**使用 `exec`、`process:poll`、任何“执行终端命令”的工具。应由**平台提供“调用 sync bridge”**的方式，agent 通过该方式**自动**取得结果并回复。
- 禁止多轮“先 exec 再 poll”；必须一次调用 bridge、一次回复结束。
- 若当前 OpenClaw 尚未配置“调用 sync bridge”的入口，需在平台侧添加；本仓不以“让用户执行命令”为预期流程。
