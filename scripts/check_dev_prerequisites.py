#!/usr/bin/env python3
"""
开发前准备自动核对：环境、权限、依赖、数据可访问性。
各阶段验收前可运行本脚本做一次性核对。用法：python scripts/check_dev_prerequisites.py [--quick]
--quick：跳过 yfinance 拉数（避免网络慢或限流）
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 项目根（脚本在 scripts/，上一级为根）
ROOT = Path(__file__).resolve().parents[1]


def ok(msg: str) -> None:
    print(f"  [OK]   {msg}")


def warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


def fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


def check_python() -> bool:
    print("\n--- Python 与 venv ---")
    v = sys.version_info
    if v.major >= 3 and v.minor >= 12:
        ok(f"Python {v.major}.{v.minor}.{v.micro} >= 3.12")
    else:
        fail(f"Python {v.major}.{v.minor}.{v.micro} 需要 >= 3.12")
        return False
    # 是否在 venv 内（可选）
    if getattr(sys, "prefix", "") != getattr(sys, "base_prefix", ""):
        ok("当前在虚拟环境中")
    else:
        warn("未检测到虚拟环境，建议 python3 -m venv .venv && source .venv/bin/activate")
    return True


def check_disk() -> bool:
    print("\n--- 磁盘与权限 ---")
    try:
        test_dir = ROOT / ".experience"
        test_dir.mkdir(parents=True, exist_ok=True)
        (test_dir / ".write_test").write_text("ok")
        (test_dir / ".write_test").unlink()
        ok(f"项目目录可写: {ROOT}")
    except Exception as e:
        fail(f"项目目录不可写: {e}")
        return False
    return True


def check_env() -> bool:
    print("\n--- 配置 .env ---")
    env_file = ROOT / ".env"
    example = ROOT / ".env.example"
    if env_file.exists():
        ok(".env 已存在")
        return True
    if example.exists():
        warn(".env 不存在，请复制 .env.example 为 .env（cp .env.example .env）")
    else:
        fail(".env.example 不存在，无法复制")
        return False
    # 无 .env 时仅警告，不阻断（config/settings 有默认值）
    return True


def check_deps() -> bool:
    print("\n--- 依赖（nautilus_trader / yfinance）---")
    try:
        import nautilus_trader  # noqa: F401
        ok("nautilus_trader 可 import")
    except Exception as e:
        fail(f"nautilus_trader 不可用: {e}")
        return False
    try:
        import yfinance  # noqa: F401
        ok("yfinance 可 import")
    except Exception as e:
        fail(f"yfinance 不可用: {e}")
        return False
    return True


def check_package() -> bool:
    print("\n--- 本包可 import ---")
    try:
        from ai_trading_research_system.research.orchestrator import ResearchOrchestrator  # noqa: F401
        from ai_trading_research_system.backtest.runner import run_backtest  # noqa: F401
        from ai_trading_research_system.experience.store import write_backtest_result  # noqa: F401
        ok("ai_trading_research_system 可 import（Research / backtest / experience）")
    except Exception as e:
        fail(f"包 import 失败: {e}（请在该项目根目录执行 pip install -e .）")
        return False
    return True


def check_yfinance_network(quick: bool) -> bool:
    print("\n--- 数据（yfinance 行情）---")
    if quick:
        warn("--quick 已跳过 yfinance 拉数")
        return True
    try:
        import yfinance as yf
        t = yf.Ticker("NVDA")
        hist = t.history(period="5d")
        if hist is not None and not hist.empty:
            ok("yfinance 可拉取 NVDA 近期行情")
        else:
            warn("yfinance 返回空数据（可能限流或网络问题）")
    except Exception as e:
        warn(f"yfinance 拉数异常: {e}（验收时请确认网络可访问 Yahoo Finance）")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="开发前准备核对")
    ap.add_argument("--quick", action="store_true", help="跳过 yfinance 拉数")
    args = ap.parse_args()

    print("开发前准备核对（见 docs/dev_prerequisites.md）")
    all_ok = True
    all_ok &= check_python()
    all_ok &= check_disk()
    all_ok &= check_env()
    all_ok &= check_deps()
    all_ok &= check_package()
    check_yfinance_network(args.quick)

    print("\n--- 汇总 ---")
    if all_ok:
        print("  环境与权限、依赖、配置通过。可进行阶段验收。")
        print("  Paper 试跑（IBKR）需单独确认 TWS/IB Gateway 与端口，见 dev_prerequisites.md。")
    else:
        print("  存在 [FAIL]，请先补齐后再验收。")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
