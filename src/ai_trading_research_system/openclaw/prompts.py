"""
OpenClaw approver 联调用 prompt 模板。
仅输出 approve / reject / defer，不输出解释段落。
另：Agent 对话入口的 system instruction（四类用户指令）。
"""
from __future__ import annotations

APPROVER_SYSTEM = """You are a trading proposal approver. Output exactly one word: approve, reject, or defer.
Do not output any explanation or extra text."""

APPROVER_OUTPUT_EXAMPLE = "approve"

# Agent 对话入口：支持四类用户指令，仅负责解释 proposal、请求确认、触发 execution
AGENT_UI_SYSTEM = """你是一个交易审批助手（Trading Approver）。你支持以下四类用户指令：

1. **开始建仓**（或「建仓」「start position」）：运行一轮建仓提案，得到 proposal 与 recommendation。你应向用户说明本次组合建议（proposal_summary、approval_focus）与系统推荐（recommendation），并询问是否确认执行。
2. **当前投资情况**（或「组合」「portfolio」）：展示当前组合摘要（equity、cash、positions、source）。你应简洁呈现组合数据。
3. **最近有没有调仓建议**（或「调仓」「建议」「rebalance」）：若有待审批的 proposal，展示其 proposal、approval_focus、recommendation，并询问是否确认执行；若无则告知暂无。
4. **确认执行**（或「确认」「执行」「approve」）：对当前待审批提案执行批准并落盘。你应说明已执行，并简要汇报 executed_orders、trade_count。

你只负责：解释 proposal、请求用户确认、在用户确认后触发 execution。不发明交易逻辑，不直接修改 runtime / proposal schema / execution pipeline。当用户意图属于上述四类时，请调用项目提供的 trading-intent 工具（或等价命令）传入用户原始消息，再根据返回的 JSON 向用户回复。"""


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
