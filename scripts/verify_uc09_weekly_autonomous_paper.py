#!/usr/bin/env python3
"""UC-09 验证：mandate、account snapshot、allocation、paper 主线、benchmark、report、Experience Store."""
from __future__ import annotations

import sys
from pathlib import Path

# 确保可从项目根或 src 加载包（未 install 时：把 src 加入 path）
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for p in (str(SRC), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)


def main() -> int:
    failed = []
    # 1. 构造 mandate
    try:
        from ai_trading_research_system.autonomous import mandate_from_cli
        m = mandate_from_cli(capital=10000, benchmark="SPY", duration_days=5)
        assert m.mandate_id and m.capital_limit == 10000 and m.benchmark == "SPY"
    except Exception as e:
        failed.append(f"1.mandate: {e}")
        return _report(failed)

    # 2. 读取 account snapshot
    try:
        from ai_trading_research_system.autonomous import get_account_snapshot
        s = get_account_snapshot(paper=True, mock=True, initial_cash=10000)
        assert s.cash == 10000 and s.equity == 10000
    except Exception as e:
        failed.append(f"2.snapshot: {e}")
        return _report(failed)

    # 3. 生成 allocation
    try:
        from ai_trading_research_system.autonomous import PortfolioAllocator, get_account_snapshot, mandate_from_cli
        snap = get_account_snapshot(paper=True, mock=True, initial_cash=10000)
        mand = mandate_from_cli(capital=10000)
        alloc = PortfolioAllocator()
        r = alloc.allocate(snap, mand, [{"symbol": "NVDA", "size_fraction": 0.25, "rationale": "test"}])
        assert r.cash_reserve >= 0
    except Exception as e:
        failed.append(f"3.allocation: {e}")
        return _report(failed)

    # 4. 跑通 paper 执行主线（单轮）
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

    # 5. Benchmark comparison
    try:
        from ai_trading_research_system.autonomous import BenchmarkComparator
        comp = BenchmarkComparator()
        r = comp.compare(portfolio_return=0.01, benchmark_return=0.005, trade_count=3, period="week")
        assert r.excess_return == 0.005
    except Exception as e:
        failed.append(f"5.benchmark: {e}")
        return _report(failed)

    # 6. Weekly report
    try:
        from ai_trading_research_system.autonomous import WeeklyReportGenerator, mandate_from_cli, BenchmarkComparator
        mand = mandate_from_cli(capital=10000)
        comp = BenchmarkComparator()
        br = comp.compare(0.01, 0.005, period="week")
        gen = WeeklyReportGenerator()
        report = gen.generate(mand, br)
        assert report.mandate_id == mand.mandate_id
    except Exception as e:
        failed.append(f"6.report: {e}")
        return _report(failed)

    # 7. Experience Store 写入
    try:
        from ai_trading_research_system.experience.writer import write_run_result
        from ai_trading_research_system.experience.store import get_connection, _get_db_path
        from ai_trading_research_system.experience.writer import RunResultPayload
        payload = RunResultPayload(
            symbol="NVDA",
            start_date="2024-01-01",
            end_date="2024-01-05",
            sharpe=0.0,
            max_drawdown=0.0,
            win_rate=0.0,
            pnl=0.0,
            trade_count=0,
            extra={"uc09_verify": True},
        )
        run_id = write_run_result(payload)
        assert run_id > 0
        conn = get_connection(_get_db_path())
        cur = conn.cursor()
        cur.execute("SELECT id FROM strategy_run WHERE id = ?", (run_id,))
        row = cur.fetchone()
        conn.close()
        assert row is not None
    except Exception as e:
        failed.append(f"7.store: {e}")
        return _report(failed)

    # 8. 完整 UC-09 命令
    try:
        from ai_trading_research_system.pipeline.weekly_paper_pipe import run_weekly_autonomous_paper
        result = run_weekly_autonomous_paper(
            capital=10000,
            benchmark="SPY",
            duration_days=2,
            auto_confirm=True,
            use_mock=True,
            use_llm=False,
            report_dir=ROOT / "reports",
        )
        assert result.ok is True
        assert result.used_nautilus is True
        assert result.mandate_id
        assert Path(result.report_path).exists()
    except Exception as e:
        failed.append(f"8.full_uc09: {e}")
        return _report(failed)

    return _report([])


def _report(failed: list) -> int:
    if failed:
        print("UC-09 VERIFY FAIL")
        for f in failed:
            print(f"  - {f}")
        return 1
    print("UC-09 VERIFY PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
