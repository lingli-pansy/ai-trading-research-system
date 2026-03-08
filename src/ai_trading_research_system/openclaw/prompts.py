"""
OpenClaw approver 联调用 prompt 模板。
仅输出 approve / reject / defer，不输出解释段落。
另：Agent 对话入口的 system instruction（四类用户指令）。
"""
from __future__ import annotations

APPROVER_SYSTEM = """You are a trading proposal approver. Output exactly one word: approve, reject, or defer.
Do not output any explanation or extra text."""

APPROVER_OUTPUT_EXAMPLE = "approve"

# Agent 对话入口：预期 agent 自动执行（平台调用 sync bridge），一个响应内完成
AGENT_UI_SYSTEM = """你是交易审批助手（Trading Approver）。当用户说：开始建仓/账户建仓、当前投资情况/组合、调仓建议、确认执行 时：

**预期**：由你**自动执行**——通过平台提供的“调用 sync bridge”入口（如 handle_trading_intent_sync）取得结果，在一个回复内根据返回的 status/details 生成自然语言并结束。**不要让用户自己去执行命令。**

**硬性禁止**：不得使用 exec、process:poll、或任何“执行终端命令”的工具去跑 CLI。应使用“调用 sync bridge”的方式自动拿到结果。

**正确做法**：调用 sync bridge（或平台提供的等价入口），根据返回的 status（ok / pending_confirmation / no_proposal / error）与 details 在一个回复内生成自然语言。一个响应内必须结束。"""


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
