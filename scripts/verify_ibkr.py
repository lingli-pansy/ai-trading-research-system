#!/usr/bin/env python3
"""验证 IBKR TWS/Gateway 连通性：检测 IBKR_HOST:IBKR_PORT 是否可达（实盘前 L7）。"""
from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_PROJECT_ROOT / ".env")

def main() -> int:
    host = (os.environ.get("IBKR_HOST") or "127.0.0.1").strip()
    port_str = (os.environ.get("IBKR_PORT") or "").strip()
    if not port_str:
        print("FAIL: IBKR_PORT 未设置（.env 中配置，如 4002）")
        return 1
    try:
        port = int(port_str)
    except ValueError:
        print("FAIL: IBKR_PORT 非整数:", port_str)
        return 1
    try:
        with socket.create_connection((host, port), timeout=5) as sock:
            print(f"OK: {host}:{port} 可达（Socket）")
            return 0
    except OSError as e:
        print(f"FAIL: {host}:{port} 不可达 — {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
