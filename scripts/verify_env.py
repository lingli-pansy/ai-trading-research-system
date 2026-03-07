#!/usr/bin/env python3
"""检查项目根 .env 是否被加载以及 LLM 相关变量是否已设置（不打印 key 内容）。"""
from __future__ import annotations

from pathlib import Path
import os

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
env_file = PROJECT_ROOT / ".env"
load_dotenv(env_file)

def main() -> None:
    print(f"Project root: {PROJECT_ROOT}")
    print(f".env path:    {env_file}")
    print(f".env exists:  {env_file.exists()}")
    kimi = os.environ.get("KIMI_CODE_API_KEY") or os.environ.get("KIMI_API_KEY")
    openai = os.environ.get("OPENAI_API_KEY")
    print(f"KIMI_CODE_API_KEY or KIMI_API_KEY: {'已设置 (len=%d)' % len((kimi or '').strip()) if (kimi and kimi.strip()) else '未设置'}")
    print(f"OPENAI_API_KEY:                     {'已设置 (len=%d)' % len((openai or '').strip()) if (openai and openai.strip()) else '未设置'}")
    if (kimi and kimi.strip()) or (openai and openai.strip()):
        print("-> 运行 run_research.py --llm 应能使用 LLM。")
    else:
        print("-> 请在 .env 中添加一行: KIMI_CODE_API_KEY=你的key（等号两侧无空格，不要用引号包住整行值）")

if __name__ == "__main__":
    main()
