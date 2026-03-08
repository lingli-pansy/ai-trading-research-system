# OpenClaw — 本仓库 Agent 说明

**预期**：当用户说「开始建仓」「当前投资情况」「调仓建议」「确认执行」时，**由 agent 自动执行**——平台应调用本仓的 sync bridge（`handle_trading_intent_sync`）取得结果，agent 在一个回复内呈现，**不要**让用户自己去执行命令。**【硬性】禁止**使用 `<tool>exec</tool>` 或任何“执行命令”类工具；应使用平台提供的“调用 sync bridge”入口实现自动执行。

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
- **对话入口（四类用户指令）**：**预期 agent 自动执行**——平台调用 `openclaw.bridge.handle_trading_intent_sync(message)`，agent 在一个回复内呈现结果；**禁止** exec/process:poll。详见 TOOLS.md。

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
