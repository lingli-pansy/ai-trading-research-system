# OpenClaw — 本仓库 Agent 说明

**用户说一句话 → agent 调统一入口 → 返回业务结果。**

- 支持 4 个动作：**开始建仓**、**查看投资组合**、**查看最新建议**、**确认执行**。
- 唯一入口：`openclaw.bridge.handle_trading_intent_sync(message, config_path=None)`。平台调用此函数，得到 `{ status, summary, details }`，agent 据此在一个回复内用自然语言回复用户。
- 边界与禁止：见 **docs/mvp-boundary.md**。禁止 agent 使用 exec/poll/shell、自己扫 runs/、自己实现交易逻辑。

**OpenClaw 路径约定**：将本仓库根目录设为 agent workspace（`~/.openclaw/openclaw.json` 中 `agents.defaults.workspace`；可运行 `uv run python scripts/set_openclaw_workspace.py` 写入）。加载本仓 `AGENTS.md` 与 `skills/`。

**开发/调试命令**（非用户主入口）：`openclaw-agent-once`、`openclaw-approver-smoke`、`openclaw-agent-loop`、`proposal-run`。用户主入口对应 CLI 仅 `openclaw-trading-intent-sync`（供本机 smoke）；正式预期为平台直接调 `handle_trading_intent_sync`。

**接入与部署**：`docs/openclaw-project-setup.md`。
