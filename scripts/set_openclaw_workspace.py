#!/usr/bin/env python3
"""
将本仓库根目录设为 OpenClaw 的 agent workspace。
在仓库根执行：uv run python scripts/set_openclaw_workspace.py
会创建或合并 ~/.openclaw/openclaw.json，写入 agent.workspace 与 skipBootstrap。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OPENCLAW_DIR = Path.home() / ".openclaw"
CONFIG_PATH = OPENCLAW_DIR / "openclaw.json"


def main() -> int:
    OPENCLAW_DIR.mkdir(parents=True, exist_ok=True)
    workspace_path = str(REPO_ROOT)

    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"读取现有配置失败: {e}", file=sys.stderr)
            return 1
    else:
        data = {}

    # 使用 OpenClaw 新格式：agents.defaults + agents.list 中显式加入本仓 agent
    if "agent" in data:
        del data["agent"]
    if "agents" not in data:
        data["agents"] = {}
    if "defaults" not in data["agents"]:
        data["agents"]["defaults"] = {}
    data["agents"]["defaults"]["workspace"] = workspace_path
    data["agents"]["defaults"]["skipBootstrap"] = True

    # 在 agents.list 中确保有一个 workspace 指向本仓的 agent，TUI 里 Ctrl+G 可切换
    if "list" not in data["agents"]:
        data["agents"]["list"] = []
    list_ = data["agents"]["list"]
    trading_id = "trading"
    has_trading = any(
        (a.get("workspace") or "").rstrip("/") == workspace_path.rstrip("/")
        or a.get("id") == trading_id
        for a in list_
    )
    if not has_trading:
        # 追加本仓专用 agent；default: true 使 Dashboard/TUI 在本仓下优先用 trading 而非 main
        list_.append({
            "id": trading_id,
            "workspace": workspace_path,
            "default": True,
            "identity": {"name": "AI Trading Approver", "emoji": "📊"},
        })
    else:
        for a in list_:
            if a.get("id") == trading_id:
                a["workspace"] = workspace_path
                a["default"] = True
                break

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"已写入 {CONFIG_PATH}")
    print(f"  agents.defaults.workspace = {workspace_path}")
    print(f"  agents.defaults.skipBootstrap = true")
    print(f"  agents.list 中已包含 id={trading_id!r}，workspace 指向本仓")
    print("")
    print("TUI 中请按 Ctrl+G 选择 agent「trading」，才会加载本仓 AGENTS.md。")
    print("或在本仓根目录执行 openclaw tui，再在 TUI 里切到 trading。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
