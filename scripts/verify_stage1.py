#!/usr/bin/env python3
"""
阶段 1 验收脚本：验证依赖与目录可 import。
运行：.venv/bin/python scripts/verify_stage1.py
（首次运行 nautilus_trader 的 import 可能需 30–60 秒）
若需运行完整最小回测示例，见 NautilusTrader 官方 Quickstart：
https://nautilustrader.io/docs/latest/getting_started/quickstart/
"""
from __future__ import annotations

def main() -> None:
    # 1. 依赖
    import nautilus_trader  # noqa: F401
    from nautilus_trader.backtest.node import BacktestNode  # noqa: F401
    import yfinance  # noqa: F401

    # 2. 本仓新增包
    from ai_trading_research_system import strategy, backtest, experience, pipeline  # noqa: F401

    print("Stage 1 import check OK")
    print("  nautilus_trader, yfinance, strategy, backtest, experience, pipeline: all importable.")


if __name__ == "__main__":
    main()
