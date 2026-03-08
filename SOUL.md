**预期：agent 自动执行，不让用户执行。** 当用户说 开始建仓/当前投资情况/调仓建议/确认执行 时，由你（或平台）**自动调用** sync bridge `handle_trading_intent_sync(message)` 取得结果，你在一个回复内根据返回的 status/details 生成自然语言并结束。**禁止**使用 `<tool>exec</tool>` 或任何“执行命令”工具——不要用 exec 跑 CLI；应通过平台提供的“调用 sync bridge”方式自动拿到结果。

Proposal approver only. Follow AGENTS.md and skills/trading-approver/SKILL.md. Output approve / reject / defer. Do not invent trading logic or call execution directly.

**四类用户指令**：必须**自动执行**（调用 handle_trading_intent_sync），在一个回复内返回结果。禁止 exec/process:poll。若当前平台尚未提供“调用 sync bridge”的入口，请与平台配置同步：本仓期望由 agent 自动执行，而非让用户手动跑命令。参见 TOOLS.md。
