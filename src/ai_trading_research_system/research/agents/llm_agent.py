"""
LLMResearchAgent: uses ResearchContext to call LLM (OpenAI) and produce
supporting_evidence, counter_evidence, thesis, key_drivers, uncertainties, risk_flags.
Output shape matches SynthesisAgent aggregation; when used, Contract reflects real input.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

from ..schemas import ResearchContext


def _default_evidence() -> dict[str, Any]:
    """Return empty evidence when LLM is unavailable."""
    return {
        "supporting_evidence": [],
        "counter_evidence": [],
        "thesis": "LLM unavailable; use mock agents or set OPENAI_API_KEY / KIMI_CODE_API_KEY.",
        "key_drivers": [],
        "uncertainties": [],
        "risk_flags": [],
    }


def _llm_client_and_model() -> tuple[Any, str] | None:
    """Return (OpenAI client, model_name) for OPENAI or Kimi (KIMI_CODE_API_KEY / KIMI_API_KEY)."""
    openai_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    kimi_key = (os.environ.get("KIMI_CODE_API_KEY") or os.environ.get("KIMI_API_KEY") or "").strip()
    api_key = openai_key or kimi_key
    if not api_key:
        return None
    from openai import OpenAI
    if kimi_key and not openai_key:
        # KimiCode（Kimi 编程产品）：api.kimi.com/coding/v1，模型 k2p5；服务端按 User-Agent 白名单放行（参考 OpenClaw/CLIProxyAPI）
        base_url = (os.environ.get("KIMI_BASE_URL") or "https://api.kimi.com/coding/v1").strip()
        model = (os.environ.get("KIMI_MODEL") or "k2p5").strip()
        ua = (os.environ.get("KIMI_USER_AGENT") or "KimiCLI/1.3").strip()
        return OpenAI(api_key=api_key, base_url=base_url, default_headers={"User-Agent": ua}), model
    model = (os.environ.get("OPENAI_RESEARCH_MODEL") or "gpt-4o-mini").strip()
    return OpenAI(api_key=api_key), model


class LLMResearchAgent:
    """Agent that calls OpenAI or Kimi (OpenAI-compatible) to produce evidence from ResearchContext."""

    name = "llm_research"

    def run(self, context: ResearchContext) -> dict[str, Any]:
        client_model = _llm_client_and_model()
        if client_model is None:
            return _default_evidence()
        client, model = client_model

        prompt = f"""You are a research analyst. Given the following context for symbol {context.symbol}, produce a short trading-oriented analysis.

Context:
- Price: {context.price_summary}
- Fundamentals: {context.fundamentals_summary}
- News (summary): {chr(10).join(context.news_summaries[:5])}

Respond with a JSON object only (no markdown), with these exact keys:
- "thesis": one short sentence (trading view)
- "supporting_evidence": list of 0-3 short strings
- "counter_evidence": list of 0-3 short strings
- "key_drivers": list of 0-3 short strings (e.g. "revenue growth", "margin")
- "uncertainties": list of 0-3 short strings
- "risk_flags": list of 0-3 short strings (e.g. "valuation_risk", "liquidity_risk")
"""

        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            text = (resp.choices[0].message.content or "").strip()
            # Strip markdown code block if present
            if text.startswith("```"):
                lines = text.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                text = "\n".join(lines)
            data = json.loads(text)
            return {
                "supporting_evidence": data.get("supporting_evidence", []) or [],
                "counter_evidence": data.get("counter_evidence", []) or [],
                "thesis": data.get("thesis", "") or _default_evidence()["thesis"],
                "key_drivers": data.get("key_drivers", []) or [],
                "uncertainties": data.get("uncertainties", []) or [],
                "risk_flags": data.get("risk_flags", []) or [],
            }
        except Exception as e:
            print(f"[LLMResearchAgent] API 调用异常: {e}", file=sys.stderr)
            return _default_evidence()
