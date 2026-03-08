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
        CREATE TABLE IF NOT EXISTS trade_experience (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id TEXT NOT NULL,
            signal_snapshot TEXT,
            outcome TEXT,
            failure_reason TEXT,
            improvement_suggestion TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS experience_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            regime_tag TEXT NOT NULL,
            aggregated_performance TEXT,
            dominant_failure_patterns TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS weekly_portfolio_experience (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mandate_id TEXT NOT NULL,
            period TEXT NOT NULL,
            top_opportunity_scores TEXT,
            replaced_positions TEXT,
            retained_positions TEXT,
            policy_snapshot TEXT,
            health_adjustment_summary TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS intraday_trigger_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mandate_id TEXT NOT NULL,
            period TEXT NOT NULL,
            trigger_type TEXT NOT NULL,
            trigger_reason TEXT,
            severity TEXT,
            positions_changed TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS portfolio_health_snapshot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mandate_id TEXT NOT NULL,
            period TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS health_trigger_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mandate_id TEXT NOT NULL,
            period TEXT NOT NULL,
            trigger_type TEXT NOT NULL,
            trigger_reason TEXT,
            severity TEXT,
            health_snapshot_excerpt TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    # Migration: add policy_snapshot if missing (existing DBs)
    try:
        conn.execute("ALTER TABLE weekly_portfolio_experience ADD COLUMN policy_snapshot TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE weekly_portfolio_experience ADD COLUMN health_adjustment_summary TEXT")
    except sqlite3.OperationalError:
        pass


def write_intraday_trigger_event(
    mandate_id: str,
    period: str,
    trigger_type: str,
    trigger_reason: str,
    severity: str,
    *,
    positions_changed: list[str] | None = None,
    db_path: Path | None = None,
) -> int:
    """Write one intraday_trigger_events row. Returns row id."""
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO intraday_trigger_events (mandate_id, period, trigger_type, trigger_reason, severity, positions_changed)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                mandate_id,
                period,
                trigger_type,
                trigger_reason,
                severity,
                json.dumps(positions_changed or [], ensure_ascii=False),
            ),
        )
        conn.commit()
        return cur.lastrowid or 0
    finally:
        conn.close()


def write_health_trigger_event(
    mandate_id: str,
    period: str,
    trigger_type: str,
    trigger_reason: str,
    severity: str,
    *,
    health_snapshot_excerpt: dict[str, Any] | None = None,
    db_path: Path | None = None,
) -> int:
    """Write one health_trigger_events row (concentration_risk / beta_spike / excess_drawdown). Returns row id."""
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO health_trigger_events (mandate_id, period, trigger_type, trigger_reason, severity, health_snapshot_excerpt)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                mandate_id,
                period,
                trigger_type,
                trigger_reason,
                severity,
                json.dumps(health_snapshot_excerpt or {}, ensure_ascii=False),
            ),
        )
        conn.commit()
        return cur.lastrowid or 0
    finally:
        conn.close()


def write_portfolio_health_snapshot(
    mandate_id: str,
    period: str,
    snapshot: dict[str, Any],
    *,
    db_path: Path | None = None,
) -> int:
    """Write one portfolio_health_snapshot row. snapshot = PortfolioHealthSnapshot.to_dict(). Returns row id."""
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO portfolio_health_snapshot (mandate_id, period, snapshot_json)
            VALUES (?, ?, ?)
            """,
            (mandate_id, period, json.dumps(snapshot, ensure_ascii=False)),
        )
        conn.commit()
        return cur.lastrowid or 0
    finally:
        conn.close()


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


def write_trade_experience(
    trade_id: str,
    *,
    signal_snapshot: str | None = None,
    outcome: str | None = None,
    failure_reason: str | None = None,
    improvement_suggestion: str | None = None,
    db_path: Path | None = None,
) -> int:
    """
    Write one trade_experience row. Returns row id.
    Schema aligned with docs/experience_schema.md.
    """
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO trade_experience (trade_id, signal_snapshot, outcome, failure_reason, improvement_suggestion)
            VALUES (?, ?, ?, ?, ?)
            """,
            (trade_id, signal_snapshot, outcome, failure_reason, improvement_suggestion),
        )
        conn.commit()
        return cur.lastrowid or 0
    finally:
        conn.close()


def write_experience_summary(
    regime_tag: str,
    *,
    aggregated_performance: str | None = None,
    dominant_failure_patterns: str | None = None,
    db_path: Path | None = None,
) -> int:
    """
    Write one experience_summary row. Returns row id.
    Schema aligned with docs/experience_schema.md.
    """
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO experience_summary (regime_tag, aggregated_performance, dominant_failure_patterns)
            VALUES (?, ?, ?)
            """,
            (regime_tag, aggregated_performance, dominant_failure_patterns),
        )
        conn.commit()
        return cur.lastrowid or 0
    finally:
        conn.close()


def write_weekly_portfolio_experience(
    mandate_id: str,
    period: str,
    *,
    top_opportunity_scores: list[dict[str, Any]] | None = None,
    replaced_positions: list[dict[str, Any]] | None = None,
    retained_positions: list[dict[str, Any]] | None = None,
    policy_snapshot: dict[str, Any] | None = None,
    health_adjustment_summary: list[dict[str, Any]] | dict[str, Any] | None = None,
    db_path: Path | None = None,
) -> int:
    """Write one weekly_portfolio_experience row. policy_snapshot: score_gap_used, replacements_executed, etc. health_adjustment_summary: 当周健康触发的汇总。"""
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO weekly_portfolio_experience (mandate_id, period, top_opportunity_scores, replaced_positions, retained_positions, policy_snapshot, health_adjustment_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mandate_id,
                period,
                json.dumps(top_opportunity_scores or [], ensure_ascii=False),
                json.dumps(replaced_positions or [], ensure_ascii=False),
                json.dumps(retained_positions or [], ensure_ascii=False),
                json.dumps(policy_snapshot or {}, ensure_ascii=False),
                json.dumps(health_adjustment_summary if isinstance(health_adjustment_summary, (list, dict)) else (health_adjustment_summary or []), ensure_ascii=False),
            ),
        )
        conn.commit()
        return cur.lastrowid or 0
    finally:
        conn.close()


def aggregate_and_write_experience_summary(db_path: Path | None = None) -> None:
    """
    按 regime_tag 聚合 strategy_run + backtest_result，每个 regime 写一条 experience_summary（覆盖该 regime 旧行）。
    regime_tag 为 NULL 的 run 归为 "default"。
    """
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT COALESCE(s.regime_tag, 'default') AS regime_tag,
                   COUNT(*) AS run_count,
                   AVG(b.sharpe) AS avg_sharpe,
                   SUM(b.pnl) AS total_pnl,
                   AVG(b.win_rate) AS avg_win_rate,
                   SUM(CASE WHEN b.trade_count = 0 THEN 1 ELSE 0 END) AS no_trade_count
            FROM strategy_run s
            JOIN backtest_result b ON s.id = b.strategy_run_id
            GROUP BY COALESCE(s.regime_tag, 'default')
        """)
        rows = cur.fetchall()
        for row in rows:
            regime_tag, run_count, avg_sharpe, total_pnl, avg_win_rate, no_trade_count = row
            aggregated = json.dumps({
                "run_count": run_count,
                "avg_sharpe": round(avg_sharpe or 0, 4),
                "total_pnl": round(total_pnl or 0, 2),
                "avg_win_rate": round(avg_win_rate or 0, 4),
            }, ensure_ascii=False)
            failure_patterns = json.dumps({"no_trade_runs": no_trade_count or 0}, ensure_ascii=False) if (no_trade_count or 0) > 0 else None
            cur.execute("DELETE FROM experience_summary WHERE regime_tag = ?", (regime_tag,))
            cur.execute(
                """
                INSERT INTO experience_summary (regime_tag, aggregated_performance, dominant_failure_patterns)
                VALUES (?, ?, ?)
                """,
                (regime_tag, aggregated, failure_patterns),
            )
        conn.commit()
    finally:
        conn.close()
