#!/usr/bin/env python3
"""
OpenClaw 单轮联调脚手架：运行一次 proposal/recommendation → 构造 approver prompt → 写入 artifacts → 模拟输出 → 解析。
用法: python scripts/openclaw_approver_smoke.py --config configs/openclaw_agent.paper.yaml [--raw "approve"]
或: uv run python -m scripts.openclaw_approver_smoke --config configs/openclaw_agent.paper.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 确保项目根在 path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="OpenClaw single-round approver integration: proposal -> prompt artifacts -> mock output -> parsed decision"
    )
    parser.add_argument("--config", required=True, help="Path to OpenClaw agent config (yaml/json)")
    parser.add_argument("--raw", default=None, help="Mock raw agent output (default: approve)")
    args = parser.parse_args()

    from ai_trading_research_system.openclaw.config import OpenClawAgentConfig
    from ai_trading_research_system.openclaw.agent_adapter import (
        run_openclaw_approver_smoke,
        format_approver_smoke_summary,
    )

    config = OpenClawAgentConfig.load(Path(args.config))
    result = run_openclaw_approver_smoke(config, raw_agent_output=args.raw)
    print(format_approver_smoke_summary(result))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    sys.exit(main())
