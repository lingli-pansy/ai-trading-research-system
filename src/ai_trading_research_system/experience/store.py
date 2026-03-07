"""
Experience Store: SQLite persistence for strategy_run and backtest_result.
Schema aligned with docs/experience_schema.md.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ai_trading_research_system.backtest.runner import BacktestMetrics

DEFAULT_DB_PATH = Path(".experience/experience.db")
STRATEGY_ID_DEFAULT = "AISignalStrategy"
STRATEGY_VERSION_DEFAULT = "0.1"


def _get_db_path() -> Path:
    import os
    return Path(os.environ.get("EXPERIENCE_DB_PATH", DEFAULT_DB_PATH))


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS strategy_run (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id TEXT NOT NULL,
            strategy_version TEXT NOT NULL,
            symbol TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            regime_tag TEXT,
            parameters TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS backtest_result (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_run_id INTEGER NOT NULL REFERENCES strategy_run(id),
            sharpe REAL NOT NULL,
            max_drawdown REAL NOT NULL,
            win_rate REAL NOT NULL,
            pnl REAL NOT NULL,
            trade_count INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or _get_db_path()
    _ensure_dir(path)
    conn = sqlite3.connect(str(path))
    _init_schema(conn)
    return conn


def write_backtest_result(
    symbol: str,
    start_date: str,
    end_date: str,
    metrics: BacktestMetrics,
    *,
    strategy_id: str = STRATEGY_ID_DEFAULT,
    strategy_version: str = STRATEGY_VERSION_DEFAULT,
    regime_tag: str | None = None,
    parameters: dict[str, Any] | None = None,
    db_path: Path | None = None,
) -> int:
    """
    Write one strategy_run and one backtest_result row. Returns strategy_run id.
    """
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO strategy_run (strategy_id, strategy_version, symbol, start_date, end_date, regime_tag, parameters)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                strategy_id,
                strategy_version,
                symbol,
                start_date,
                end_date,
                regime_tag,
                json.dumps(parameters) if parameters else None,
            ),
        )
        run_id = cur.lastrowid
        cur.execute(
            """
            INSERT INTO backtest_result (strategy_run_id, sharpe, max_drawdown, win_rate, pnl, trade_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, metrics.sharpe, metrics.max_drawdown, metrics.win_rate, metrics.pnl, metrics.trade_count),
        )
        conn.commit()
        return run_id
    finally:
        conn.close()
