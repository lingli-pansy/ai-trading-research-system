"""
OpenClaw approver 联调用 prompt 模板。
仅输出 approve / reject / defer，不输出解释段落。
另：Agent 对话入口的 system instruction（四类用户指令）。
"""
from __future__ import annotations

APPROVER_SYSTEM = """You are a trading proposal approver. Output exactly one word: approve, reject, or defer.
Do not output any explanation or extra text."""

APPROVER_OUTPUT_EXAMPLE = "approve"

# Agent 对话入口：同步完成式；禁止 exec/poll/shell，一个响应内完成
AGENT_UI_SYSTEM = """你是交易审批助手（Trading Approver）。当用户说：开始建仓/账户建仓、当前投资情况/组合、调仓建议、确认执行 时：

**硬性禁止**：不得在回复中写出或触发 exec(、process:poll、run(、uv run、或任何“执行终端命令”的调用。即：不要输出 exec("uv run python -m ...")，不要使用“运行命令”类工具。

**正确做法**：
- 若可调用 Python 桥接（handle_trading_intent_sync）：调用后根据返回的 status/details 在一个回复内生成自然语言并结束。
- 若不可调用桥接（例如只有“运行命令”工具）：不要执行任何命令。仅用一条回复写：「请在本机终端执行以下命令查看结果：」然后给出示例命令 openclaw-trading-intent-sync --message-json '{"message":"当前投资情况"}'（按用户原意替换 message），最后写「本次请求已完成。」结束。

一个响应内必须结束，不得出现 exec/poll/命令执行。"""


def build_approver_user_message(prompt_input: dict) -> str:
    """
    根据 build_approver_prompt_input 的返回构造 user message 正文（纯文本，便于联调）。
    """
    lines = []
    ps = prompt_input.get("portfolio_summary") or {}
    lines.append("PORTFOLIO_SUMMARY")
    lines.append(f"equity={ps.get('equity', '')} cash={ps.get('cash', '')} positions={ps.get('positions', {})}")
    lines.append("")
    lines.append("RISK_FLAGS")
    for f in prompt_input.get("risk_flags") or []:
        lines.append(f"  - {f}")
    if not prompt_input.get("risk_flags"):
        lines.append("  (none)")
    lines.append("")
    lines.append("PROPOSAL_SUMMARY")
    for s in prompt_input.get("proposal_summary") or []:
        lines.append(f"  {s}")
    if not prompt_input.get("proposal_summary"):
        lines.append("  (none)")
    lines.append("")
    lines.append("APPROVAL_FOCUS")
    for a in prompt_input.get("approval_focus") or []:
        lines.append(f"  {a.get('symbol', '')} {a.get('one_line_reason', '')}")
    if not prompt_input.get("approval_focus"):
        lines.append("  (none)")
    lines.append("")
    lines.append("RECOMMENDATION")
    lines.append(f"  {prompt_input.get('recommendation', 'defer')}")
    for r in prompt_input.get("recommendation_reasons") or []:
        lines.append(f"  - {r}")
    return "\n".join(lines)
