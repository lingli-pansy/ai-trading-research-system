# OpenClaw — 本仓库 Agent 说明

**【硬性】禁止使用 `<tool>exec</tool>` 或任何“执行命令”类工具。** 当用户说「开始建仓」「当前投资情况」「调仓建议」「确认执行」时，**仅用一条文字回复**说明或引导用户在本机终端执行 sync 命令，**不要**调用 exec、不要运行 uv run / shell。

**项目**：AI trading runtime，带 proposal / approval / execution 工作流。

**OpenClaw 路径约定**：将本仓库根目录设为 OpenClaw 的 **agent workspace**（在 `~/.openclaw/openclaw.json` 中配置 `agents.defaults.workspace` 指向本仓根目录；可运行 `uv run python scripts/set_openclaw_workspace.py` 自动写入）。这样 OpenClaw 会加载工作区根目录的 `AGENTS.md` 与 `skills/`。

**主线（Canonical path）**：

```
agent workspace = 本仓库根目录
  → AGENTS.md（本文件）、skills/trading-approver/
  → 本仓 CLI：openclaw-agent-once / openclaw-approver-smoke
  → autonomous_paper_cycle → proposal → approval → execution
```

**OpenClaw agent 角色**：proposal approver / operator。根据 agent_context 与 recommendation 输出 approve / reject / defer，不直接驱动 execution。

**推荐入口**：

- 单次运行：`python -m ai_trading_research_system.presentation.cli openclaw-agent-once --config configs/openclaw_agent.paper.yaml`
- 联调前自检：`python -m ai_trading_research_system.presentation.cli openclaw-approver-smoke --config configs/openclaw_agent.paper.yaml`
- **对话入口（四类用户指令）**：**仅**通过 **Python sync bridge**：`openclaw.bridge.handle_trading_intent_sync(message)`。一次调用、同步返回、一个回复内完成。**禁止**在 TUI 中输出或执行 exec、process:poll、shell command。Bridge smoke：`openclaw-trading-intent-sync --message-json '{"message":"开始建仓"}'`。详见 TOOLS.md。

**不要**：

- 绕过 runtime 直接调 execution
- 在 runtime 外发明交易逻辑
- 跳过 proposal/approval 直接下单

**优先使用的 artifacts**：

- `runs/<run_id>/artifacts/agent_context.json`
- `runs/<run_id>/artifacts/approval_recommendation.json`
- `runs/<run_id>/artifacts/approval_decision.json`
- `runs/<run_id>/artifacts/approver_prompt_input.json`
- `runs/<run_id>/artifacts/approver_user_message.txt`

**Workspace skill**：`skills/trading-approver/SKILL.md`（如何在本项目中做 proposal approval）。

**接入与部署说明**：`docs/openclaw-project-setup.md`（含 OpenClaw 安装、workspace 配置、部署步骤）。
