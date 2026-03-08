#!/usr/bin/env python3
"""UC-09 回归验证（mock 路径）：用于 CI / 本地快速回归，不依赖 IBKR 或真实行情。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for p in (str(SRC), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)


def main() -> int:
    failed = []
    try:
        from ai_trading_research_system.autonomous import mandate_from_cli
        m = mandate_from_cli(capital=10000, benchmark="SPY", duration_days=5)
        assert m.mandate_id and m.capital_limit == 10000 and m.benchmark == "SPY"
    except Exception as e:
        failed.append(f"1.mandate: {e}")
        return _report(failed)

    try:
        from ai_trading_research_system.autonomous import get_account_snapshot
        s = get_account_snapshot(paper=True, mock=True, initial_cash=10000)
        assert s.cash == 10000 and s.equity == 10000 and s.source == "mock"
    except Exception as e:
        failed.append(f"2.snapshot: {e}")
        return _report(failed)

    try:
        from ai_trading_research_system.autonomous import PortfolioAllocator, get_account_snapshot, mandate_from_cli
        snap = get_account_snapshot(paper=True, mock=True, initial_cash=10000)
        mand = mandate_from_cli(capital=10000)
        r = PortfolioAllocator().allocate(snap, mand, [{"symbol": "NVDA", "size_fraction": 0.25, "rationale": "test"}])
        assert r.cash_reserve >= 0
    except Exception as e:
        failed.append(f"3.allocation: {e}")
        return _report(failed)

    try:
        from ai_trading_research_system.research.orchestrator import ResearchOrchestrator
        from ai_trading_research_system.strategy.translator import ContractTranslator
        from ai_trading_research_system.execution.nautilus_paper_runner import NautilusPaperRunner
        orch = ResearchOrchestrator(use_mock=True, use_llm=False)
        contract = orch.run("NVDA")
        signal = ContractTranslator().translate(contract)
        runner = NautilusPaperRunner("NVDA", lookback_days=5)
        runner.inject(signal)
        runner.start()
        res = runner.run_once(122.5, use_mock=True)
        runner.stop()
        assert hasattr(res, "trade_count") and hasattr(res, "pnl")
    except Exception as e:
        failed.append(f"4.paper_run: {e}")
        return _report(failed)

    try:
        from ai_trading_research_system.autonomous import BenchmarkComparator
        r = BenchmarkComparator().compare(portfolio_return=0.01, benchmark_return=0.005, trade_count=3, period="week")
        assert r.excess_return == 0.005
    except Exception as e:
        failed.append(f"5.benchmark: {e}")
        return _report(failed)

    try:
        from ai_trading_research_system.autonomous import WeeklyReportGenerator, mandate_from_cli, BenchmarkComparator
        mand = mandate_from_cli(capital=10000)
        br = BenchmarkComparator().compare(0.01, 0.005, period="week")
        report = WeeklyReportGenerator().generate(mand, br)
        assert report.mandate_id == mand.mandate_id
    except Exception as e:
        failed.append(f"6.report: {e}")
        return _report(failed)

    try:
        from ai_trading_research_system.experience.writer import write_run_result, RunResultPayload
        from ai_trading_research_system.experience.store import get_connection, _get_db_path
        run_id = write_run_result(RunResultPayload(
            symbol="NVDA", start_date="2024-01-01", end_date="2024-01-05",
            sharpe=0.0, max_drawdown=0.0, win_rate=0.0, pnl=0.0, trade_count=0,
            extra={"uc09_verify_mock": True},
        ))
        assert run_id > 0
        conn = get_connection(_get_db_path())
        cur = conn.cursor()
        cur.execute("SELECT id FROM strategy_run WHERE id = ?", (run_id,))
        assert cur.fetchone() is not None
        conn.close()
    except Exception as e:
        failed.append(f"7.store: {e}")
        return _report(failed)

    try:
        from ai_trading_research_system.pipeline.weekly_paper_pipe import run_weekly_autonomous_paper
        result = run_weekly_autonomous_paper(
            capital=10000, benchmark="SPY", duration_days=2, auto_confirm=True,
            use_mock=True, use_llm=False, report_dir=ROOT / "reports",
        )
        assert result.ok and result.used_nautilus and result.mandate_id and Path(result.report_path).exists()
        assert result.summary.get("snapshot_source") == "mock"
        assert result.summary.get("market_data_source") == "mock"
    except Exception as e:
        failed.append(f"8.full_uc09_mock: {e}")
        return _report(failed)

    return _report([])


def _report(failed: list) -> int:
    if failed:
        print("UC-09 MOCK VERIFY FAIL")
        for f in failed:
            print(f"  - {f}")
        return 1
    print("UC-09 MOCK VERIFY PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
