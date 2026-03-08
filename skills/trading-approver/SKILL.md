# Trading Approver

**name**: trading-approver  
**description**: 在本项目中执行 proposal approval：阅读 agent_context / recommendation，调用已有 approver scaffold 或 adapter，输出 approve / reject / defer。不直接交易，不发明交易逻辑。

## When to use

- OpenClaw 需要对本仓产生的 **交易提案（proposal）** 做审批决策时。
- 已有一次 run 的 `agent_context`、`approval_recommendation`，需要给出结构化决策供 runtime 执行或跳过执行时。

## Required inputs

- **agent_context**（或等价的 prompt input）：至少包含  
  - `portfolio_summary`  
  - `risk_flags`  
  - `proposal_summary`  
  - `approval_focus`  
  - `recommendation`  
  - `recommendation_reasons`  
- 可从 `runs/<run_id>/artifacts/agent_context.json` 读取，或通过本仓 `build_approver_prompt_input(agent_context)` 得到。

## Output contract

- **决策**：仅允许以下三者之一：`approve` | `reject` | `defer`。  
- 自然语言输出需经本仓 `parse_approval_decision(text)` 解析为上述三者之一；未识别时默认 `defer`。  
- 不输出长段解释；仅输出可被 parser 识别的决策（或一句含 approve/reject/defer 的短句）。

## How to invoke (project-internal)

- **联调 smoke（不接 live OpenClaw）**：  
  `openclaw-approver-smoke --config configs/openclaw_agent.paper.yaml [--raw "approve"]`  
  会跑一次 proposal 生成 → 写 approver_prompt_input.json、approver_user_message.txt → 用 `--raw` 或默认 mock 输出 → 解析为 normalized decision。  
- **编程**：`openclaw.agent_adapter.approve_proposal(proposal, context)`，context 建议用 `build_approver_prompt_input(load_agent_context(run_id))` 或等价结构；或使用 `openclaw.prompts.build_approver_user_message(prompt_input)` 得到发给 agent 的文本。

## 四类用户指令（开始建仓 / 当前投资情况 / 调仓建议 / 确认执行）

- **预期**：由 **agent 自动执行**——平台调用 `openclaw.bridge.handle_trading_intent_sync(message)`（或 workspace 暴露的同步桥接入口），agent 在一个回复内根据返回的 status/details 呈现结果；**不要让用户自己去执行命令**。
- **禁止**：exec、process:poll、shell、或任何“执行终端命令”的工具。参见 TOOLS.md。

## Do not

- 绕过 runtime 直接调用 execution。  
- 在本 skill 内实现新的交易策略或仓位逻辑。  
- 输出除 approve/reject/defer 以外的决策语义。  
- 对上述四类指令使用 exec/poll/shell；仅允许通过 sync bridge。
