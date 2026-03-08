"""
OpenClaw approver 联调用 prompt 模板。
仅输出 approve / reject / defer，不输出解释段落。
"""
from __future__ import annotations

APPROVER_SYSTEM = """You are a trading proposal approver. Output exactly one word: approve, reject, or defer.
Do not output any explanation or extra text."""

APPROVER_OUTPUT_EXAMPLE = "approve"


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
        lines.append(f"  {a.get('symbol', '')} score={a.get('score')} {a.get('allocator')} {a.get('one_line_reason', '')}")
    if not prompt_input.get("approval_focus"):
        lines.append("  (none)")
    lines.append("")
    lines.append("RECOMMENDATION")
    lines.append(f"  {prompt_input.get('recommendation', 'defer')}")
    for r in prompt_input.get("recommendation_reasons") or []:
        lines.append(f"  - {r}")
    return "\n".join(lines)
