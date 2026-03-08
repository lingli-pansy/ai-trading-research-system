#!/usr/bin/env python3
"""UC-09: Weekly autonomous paper. Entry for OpenClaw / CLI. Stdout=JSON only."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="UC-09 Weekly autonomous paper")
    parser.add_argument("--capital", type=float, default=10000)
    parser.add_argument("--benchmark", default="SPY")
    parser.add_argument("--days", type=int, default=5)
    parser.add_argument("--mock", action="store_true", dest="mock", default=False, help="Use mock data/snapshot")
    parser.add_argument("--no-mock", action="store_false", dest="mock", help="Use real path (default)")
    parser.add_argument("--llm", action="store_true")
    args = parser.parse_args()
    (ROOT / "reports").mkdir(parents=True, exist_ok=True)
    from ai_trading_research_system.pipeline.weekly_paper_pipe import run_weekly_autonomous_paper
    result = run_weekly_autonomous_paper(
        capital=args.capital,
        benchmark=args.benchmark,
        duration_days=args.days,
        auto_confirm=True,
        use_mock=args.mock,
        use_llm=args.llm,
        report_dir=ROOT / "reports",
    )
    out = {
        "ok": result.ok,
        "mandate_id": result.mandate_id,
        "status": result.status,
        "capital_limit": result.capital_limit,
        "benchmark": result.benchmark,
        "engine_type": result.engine_type,
        "used_nautilus": result.used_nautilus,
        "report_path": result.report_path,
        "summary": result.summary,
    }
    print(json.dumps(out, indent=2))
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
