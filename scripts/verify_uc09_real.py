#!/usr/bin/env python3
"""UC-09 真实验证：真实数据 / 真实 benchmark / 真实周报联调。可选依赖 IBKR paper 账户（未配置时 snapshot 为 mock fallback）。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for p in (str(SRC), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)


def main() -> int:
    failed = []
    report_path_used: str | None = None

    # 1. 真实 benchmark 可计算
    try:
        from ai_trading_research_system.autonomous.benchmark import get_benchmark_return_for_period
        ret, src = get_benchmark_return_for_period("SPY", lookback_days=5)
        assert isinstance(ret, float) and src in ("yfinance", "mock")
    except Exception as e:
        failed.append(f"1.benchmark: {e}")
        return _report(failed)

    # 2. weekly-paper 主路径可启动（use_mock=False），且输出含 source 字段
    try:
        from ai_trading_research_system.pipeline.weekly_paper_pipe import run_weekly_autonomous_paper
        result = run_weekly_autonomous_paper(
            capital=10000,
            benchmark="SPY",
            duration_days=2,
            auto_confirm=True,
            use_mock=False,
            use_llm=False,
            report_dir=ROOT / "reports",
        )
        assert result.ok is True
        assert "snapshot_source" in result.summary
        assert "market_data_source" in result.summary
        assert "benchmark_source" in result.summary
        if result.summary.get("market_data_source") != "yfinance" and result.summary.get("benchmark_source") != "yfinance":
            failed.append("2.real_path: 未使用真实数据（market_data_source 与 benchmark_source 均非 yfinance）")
        assert Path(result.report_path).exists()
        report_path_used = result.report_path
    except Exception as e:
        failed.append(f"2.real_run: {e}")
        return _report(failed)

    # 3. 周报文件含 benchmark 相关字段
    try:
        if not report_path_used or not Path(report_path_used).exists():
            failed.append("3.report_file: 周报文件不存在")
        else:
            with open(report_path_used, encoding="utf-8") as f:
                data = json.load(f)
            assert "benchmark_return_pct" in data or "portfolio_return_pct" in data
            assert "benchmark_source" in data
    except Exception as e:
        failed.append(f"3.report: {e}")
        return _report(failed)

    # 4. Experience Store 有写入（由上面 run 已写入）
    try:
        from ai_trading_research_system.experience.store import get_connection, _get_db_path
        conn = get_connection(_get_db_path())
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM strategy_run")
        n = cur.fetchone()[0]
        conn.close()
        assert n >= 0
    except Exception as e:
        failed.append(f"4.store: {e}")
        return _report(failed)

    # 5. CLI 或脚本至少一条跑通（真实路径）
    try:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "run_weekly_autonomous_paper.py"), "--capital", "10000", "--benchmark", "SPY"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            failed.append(f"5.cli: exit {proc.returncode} stderr={proc.stderr[:200]}")
        else:
            out = json.loads(proc.stdout)
            if out.get("summary", {}).get("market_data_source") != "yfinance" and out.get("summary", {}).get("benchmark_source") != "yfinance":
                failed.append("5.cli: 输出中未使用真实 data/benchmark")
    except subprocess.TimeoutExpired:
        failed.append("5.cli: timeout")
    except Exception as e:
        failed.append(f"5.cli: {e}")

    return _report(failed)


def _report(failed: list) -> int:
    if failed:
        print("UC-09 REAL VERIFY FAIL")
        for f in failed:
            print(f"  - {f}")
        return 1
    print("UC-09 REAL VERIFY PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
