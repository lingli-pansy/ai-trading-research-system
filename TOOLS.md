# Trading Agent — 同步桥接入口（唯一推荐）

OpenClaw workspace 对本项目的调用**仅**通过 **Python sync bridge** 完成。Agent **不得**输出或触发 exec、process:poll、shell command。

## 唯一入口

- **Python**：`openclaw.bridge.handle_trading_intent_sync(message, config_path=None)`  
  内部直接调用 `dispatch_trading_intent`，不经 shell，不拼命令。一次调用，同步返回。

- **CLI（仅作 bridge smoke / 联调）**：  
  `openclaw-trading-intent-sync --message-json '{"message": "开始建仓"}'`  
  内部直接走 `handle_trading_intent_sync`，不 spawn 子进程。

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

- **不得**在回复中写出或触发：`exec(`、`process:poll`、`run(`、`uv run`、任何“执行终端命令”的调用。即：禁止输出类似 `exec("uv run python -m ...")` 的文本或发起此类工具调用。
- 若当前界面只能“运行命令”，则**不要运行任何命令**；改为在一条回复中说明「请在本机终端运行以下命令」并给出示例（见上方 CLI），然后结束回复。
- 禁止多轮“先 exec 再 poll”；必须一次回复结束。
