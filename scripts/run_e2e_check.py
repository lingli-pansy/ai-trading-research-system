#!/usr/bin/env python3
"""
阶段 6 端到端联调：同一 symbol 跑 Research → Backtest → Pipeline 写 Store，并校验 Experience 有数据。
用法：python scripts/run_e2e_check.py [SYMBOL] [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--mock]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 项目根；Store 默认写 cwd 下 .experience/experience.db
ROOT = Path(__file__).resolve().parents[1]


def check_experience_has_data(symbol: str, db_path: Path) -> bool:
    """检查 Experience Store 中是否有该 symbol 的 strategy_run 与 backtest_result。"""
    if not db_path.exists():
        return False
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM strategy_run WHERE symbol = ?", (symbol,))
        runs = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM backtest_result b JOIN strategy_run s ON b.strategy_run_id = s.id WHERE s.symbol = ?", (symbol,))
        results = cur.fetchone()[0]
        return runs >= 1 and results >= 1
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="E2E: Research -> Backtest -> Store, then verify Experience")
    ap.add_argument("symbol", nargs="?", default="NVDA", help="Symbol (default: NVDA)")
    ap.add_argument("--start", default=None, help="Start date YYYY-MM-DD")
    ap.add_argument("--end", default=None, help="End date YYYY-MM-DD")
    ap.add_argument("--mock", action="store_true", help="Use mock research data")
    ap.add_argument("--llm", action="store_true", help="Use LLM agent (requires OPENAI_API_KEY)")
    args = ap.parse_args()

    from ai_trading_research_system.pipeline.backtest_pipe import run as run_pipe

    print(f"E2E: running pipeline for {args.symbol}...")
    result = run_pipe(
        symbol=args.symbol,
        start_date=args.start,
        end_date=args.end,
        use_mock=args.mock,
        use_llm=args.llm,
    )
    print(f"  contract: {result.contract.suggested_action}, metrics: sharpe={result.metrics.sharpe:.4f} trades={result.metrics.trade_count}")
    print(f"  strategy_run_id: {result.strategy_run_id}")

    import os
    db_path = Path(os.environ.get("EXPERIENCE_DB_PATH", str(ROOT / ".experience" / "experience.db")))
    if not db_path.exists():
        alt = Path(".experience/experience.db")
        if alt.exists():
            db_path = alt
    if not check_experience_has_data(args.symbol, db_path):
        print("FAIL: Experience Store has no data for this symbol.")
        return 1
    print("OK: Experience Store has strategy_run and backtest_result for", args.symbol)
    return 0


if __name__ == "__main__":
    sys.exit(main())
