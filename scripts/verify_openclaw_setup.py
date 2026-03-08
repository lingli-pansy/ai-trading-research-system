#!/usr/bin/env python3
"""
最小验证：确认本仓库已具备被 OpenClaw 接入的配置准备。
不调用真实 OpenClaw，只检查必要文件存在，并提示 smoke 命令可作为项目内验证入口。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    checks = [
        ("AGENTS.md", ROOT / "AGENTS.md"),
        ("skills/trading-approver/SKILL.md", ROOT / "skills" / "trading-approver" / "SKILL.md"),
        ("docs/openclaw-project-setup.md", ROOT / "docs" / "openclaw-project-setup.md"),
    ]
    ok = True
    for name, path in checks:
        if path.exists():
            print(f"OK   {name}")
        else:
            print(f"MISS {name}")
            ok = False
    if ok:
        print("")
        print("Project is ready for OpenClaw onboarding (minimal config).")
        print("Smoke: python -m ai_trading_research_system.presentation.cli openclaw-approver-smoke --config configs/openclaw_agent.paper.yaml")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
