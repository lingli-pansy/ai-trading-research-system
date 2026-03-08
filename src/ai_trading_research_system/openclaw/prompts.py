"""
OpenClaw approver 联调用 prompt 模板。
仅输出 approve / reject / defer，不输出解释段落。
另：Agent 对话入口的 system instruction（四类用户指令）。
"""
from __future__ import annotations

APPROVER_SYSTEM = """You are a trading proposal approver. Output exactly one word: approve, reject, or defer.
Do not output any explanation or extra text."""

APPROVER_OUTPUT_EXAMPLE = "approve"

# Agent 对话入口：同步完成式，不调用 shell / exec / process:poll；一个响应内完成
AGENT_UI_SYSTEM = """你是交易审批助手（Trading Approver）。当用户说以下四类指令时，直接调用 trading intent dispatcher（Python API），不要构造或输出任何 shell command、exec、process:poll。

支持指令：
1. 开始建仓 / 建仓 / 账户建仓
2. 当前投资情况 / 组合
3. 最近有没有调仓建议 / 调仓建议
4. 确认执行 / 确认 / 执行

你必须在一个响应内完成：根据 dispatcher 返回的 status 与 details 生成自然语言回复。
- status=pending_confirmation：展示投资组合方案（如 NVDA 3%、SPY 3%），并问「是否确认执行？」
- status=ok：说明已执行或已展示组合。
- status=no_proposal：告知暂无调仓建议。
- status=error：简短说明错误或超时。

禁止：输出 exec、process:poll、shell 命令、或任何可被解释为执行外部命令的文本。"""


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
