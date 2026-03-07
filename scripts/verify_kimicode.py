#!/usr/bin/env python3
"""用 .env 中的 KIMI_CODE_API_KEY 真实请求 KimiCode 接口，验证是否可用。不打印 key。"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

def main() -> None:
    key = (os.environ.get("KIMI_CODE_API_KEY") or os.environ.get("KIMI_API_KEY") or "").strip()
    if not key:
        print("FAIL: KIMI_CODE_API_KEY / KIMI_API_KEY 未设置")
        return
    base_url = (os.environ.get("KIMI_BASE_URL") or "https://api.kimi.com/coding/v1").strip()
    model = (os.environ.get("KIMI_MODEL") or "k2p5").strip()
    ua = (os.environ.get("KIMI_USER_AGENT") or "KimiCLI/1.3").strip()
    from openai import OpenAI
    client = OpenAI(api_key=key, base_url=base_url, default_headers={"User-Agent": ua})
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            temperature=0,
            max_tokens=20,
        )
        text = (resp.choices[0].message.content or "").strip()
        print("OK:", text[:80] if text else "(empty)")
    except Exception as e:
        print("FAIL:", type(e).__name__, str(e))

if __name__ == "__main__":
    main()
