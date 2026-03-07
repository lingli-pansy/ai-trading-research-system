#!/usr/bin/env python3
"""
验证 Experience Store：打印最新 strategy_run、backtest_result 及 strategy_spec_snapshot。
用于偏移开发计划验收。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ai_trading_research_system.experience.store import get_connection, _get_db_path


def main() -> int:
    db_path = _get_db_path()
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        return 1
    conn = get_connection(db_path)
    cur = conn.cursor()
    # 最新 strategy_run
    cur.execute(
        "SELECT id, strategy_id, symbol, start_date, end_date, regime_tag, parameters, created_at FROM strategy_run ORDER BY id DESC LIMIT 1"
    )
    row = cur.fetchone()
    if not row:
        print("No strategy_run rows.")
        conn.close()
        return 0
    run_id, strategy_id, symbol, start_date, end_date, regime_tag, parameters, created_at = row
    print("=== Latest strategy_run ===")
    print(f"id={run_id} strategy_id={strategy_id} symbol={symbol} start_date={start_date} end_date={end_date} created_at={created_at}")
    if parameters:
        try:
            params = json.loads(parameters)
            if "strategy_spec_snapshot" in params:
                print("\n--- strategy_spec_snapshot ---")
                print(json.dumps(params["strategy_spec_snapshot"], indent=2, ensure_ascii=False))
            else:
                print("\nparameters (no strategy_spec_snapshot):", params)
        except Exception as e:
            print("\nparameters (raw):", parameters[:200], "...", e)
    cur.execute("SELECT id, strategy_run_id, sharpe, max_drawdown, win_rate, pnl, trade_count FROM backtest_result WHERE strategy_run_id = ?", (run_id,))
    bt = cur.fetchone()
    if bt:
        print("\n=== backtest_result (same run) ===")
        print(f"id={bt[0]} strategy_run_id={bt[1]} sharpe={bt[2]:.4f} max_drawdown={bt[3]:.4f} win_rate={bt[4]:.4f} pnl={bt[5]:.2f} trade_count={bt[6]}")
    # trade_experience / experience_summary
    cur.execute("SELECT COUNT(*) FROM trade_experience")
    te_count = cur.fetchone()[0]
    print("\n=== trade_experience ===", "count =", te_count)
    cur.execute("SELECT regime_tag, aggregated_performance FROM experience_summary")
    for r in cur.fetchall():
        perf = (r[1] or "")[:80] + "..." if r[1] and len(r[1]) > 80 else (r[1] or "")
        print("experience_summary:", r[0], "->", perf)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print("\n=== Tables ===", tables)
    conn.close()
    from ai_trading_research_system.experience.refiner import refiner_suggest
    print("\n=== Refiner 建议 (run_id={}) ===".format(run_id), refiner_suggest(run_id))
    return 0


if __name__ == "__main__":
    sys.exit(main())
