# Trading Approver

**name**: trading-approver  
**description**: 本仓 proposal approval：读 agent_context / recommendation，输出 approve / reject / defer。不直接交易，不发明交易逻辑。

## When to use

- OpenClaw 对本仓产生的 **交易提案** 做审批决策时。
- 已有 agent_context、approval_recommendation，需给出结构化决策时。

## 四类用户指令（开始建仓 / 查看投资组合 / 查看最新建议 / 确认执行）

统一走 **openclaw.bridge.handle_trading_intent_sync(message)**。Agent 调用后仅用返回的 **summary** 在一个回复内呈现业务结果，不得向用户提及 bridge、platform、run_id、exec、shell 等。禁止 exec/poll/shell。见 TOOLS.md、docs/mvp-boundary.md。

## How to invoke (project-internal)

- 联调 smoke：`openclaw-approver-smoke --config configs/openclaw_agent.paper.yaml [--raw "approve"]`
- 编程：`openclaw.agent_adapter.approve_proposal(proposal, context)`，context 用 `build_approver_prompt_input(load_agent_context(run_id))` 或等价。

## Do not

- 绕过 runtime 直接调 execution；不在本 skill 内实现新交易策略；不对四类指令使用 exec/poll/shell。
