"""
Unified CLI: parse args -> command_registry.run -> renderer. No business logic, no pipeline calls.
report_dir / project_root come from command_registry.kwargs_from_cli_args only.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore[misc, assignment]

from ai_trading_research_system.application.command_registry import (
    run as command_run,
    kwargs_from_cli_args,
)
from ai_trading_research_system.presentation.renderers import render

if load_dotenv:
    load_dotenv(Path.cwd() / ".env")


def _init_logging() -> None:
    """根据环境变量 LOG_LEVEL 初始化日志，便于看到 [ib] 等 INFO 日志。"""
    level_name = (os.environ.get("LOG_LEVEL") or "").strip().upper()
    level = logging.INFO if level_name == "INFO" else (logging.DEBUG if level_name == "DEBUG" else logging.WARNING)
    if level != logging.WARNING:
        from ai_trading_research_system.utils.logging import setup_logging
        setup_logging(level=level)


def _json_serial(obj: object) -> str | float | int | None:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AI Trading Research System — unified CLI (research / backtest / paper / demo / weekly-paper / weekly_report)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def _add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--mock", action="store_true", help="Use mock research data")
        p.add_argument("--llm", action="store_true", help="Use LLM agent (requires OPENAI_API_KEY or KIMI_CODE_API_KEY)")

    p_research = subparsers.add_parser("research", help="Run research and output DecisionContract (JSON)")
    p_research.add_argument("symbol", nargs="?", default="NVDA", help="Symbol (default: NVDA)")
    _add_common(p_research)

    p_backtest = subparsers.add_parser("backtest", help="Research → Backtest → Store, print metrics")
    p_backtest.add_argument("symbol", nargs="?", default="NVDA", help="Symbol (default: NVDA)")
    p_backtest.add_argument("--start", default=None, help="Backtest start YYYY-MM-DD")
    p_backtest.add_argument("--end", default=None, help="Backtest end YYYY-MM-DD")
    _add_common(p_backtest)

    p_paper = subparsers.add_parser("paper", help="Research → Contract → Paper inject (once or runner)")
    p_paper.add_argument("--symbol", default="NVDA", help="Symbol (default: NVDA)")
    p_paper.add_argument("--once", action="store_true", help="Run one Research+inject cycle then exit")
    _add_common(p_paper)

    p_paper_cycle = subparsers.add_parser("paper-cycle", help="OpenClaw agent: single autonomous paper cycle (state in runs/)")
    p_paper_cycle.add_argument("--run_id", default="", help="Run id (default: auto-generated)")
    p_paper_cycle.add_argument("--symbols", default=None, help="Comma-separated symbols (default: NVDA)")
    p_paper_cycle.add_argument("--capital", type=float, default=10000, help="Capital (default 10000)")
    p_paper_cycle.add_argument("--benchmark", default="SPY", help="Benchmark (default SPY)")
    p_paper_cycle.add_argument("--no-execute", action="store_false", dest="execute_paper", help="Do not execute paper, only output intents (default: execute)")
    p_paper_cycle.set_defaults(execute_paper=True)
    _add_common(p_paper_cycle)

    p_demo = subparsers.add_parser("demo", help="E2E demo: research → strategy → backtest → summary (four blocks)")
    p_demo.add_argument("symbol", nargs="?", default="NVDA", help="Symbol (default: NVDA)")
    _add_common(p_demo)

    p_weekly = subparsers.add_parser("weekly-paper", help="UC-09: Weekly autonomous paper portfolio")
    p_weekly.add_argument("--capital", type=float, default=10000, help="Capital limit (default 10000)")
    p_weekly.add_argument("--benchmark", default="SPY", help="Benchmark symbol (default SPY)")
    p_weekly.add_argument("--days", type=int, default=5, help="Trading days (default 5)")
    p_weekly.add_argument("--symbols", default=None, help="Comma-separated watchlist (default: NVDA)")
    p_weekly.add_argument("--auto-confirm", action="store_true", default=True, dest="auto_confirm", help="Auto confirm trades (default True)")
    p_weekly.add_argument("--no-auto-confirm", action="store_false", dest="auto_confirm", help="Disable auto confirm")
    _add_common(p_weekly)

    p_weekly_report = subparsers.add_parser("weekly_report", help="Read latest weekly report or show summary (no execution)")
    _add_common(p_weekly_report)

    p_status = subparsers.add_parser("status", help="System status summary (experiment cycle, health, policy, triggers)")

    p_agent_run_once = subparsers.add_parser("agent-run-once", help="Agent runtime: one autonomous paper cycle, then exit")
    p_agent_run_once.add_argument("--symbols", default=None, help="Comma-separated symbols (default: NVDA)")
    p_agent_run_once.add_argument("--capital", type=float, default=10000, help="Capital (default 10000)")
    p_agent_run_once.add_argument("--benchmark", default="SPY", help="Benchmark (default SPY)")
    _add_common(p_agent_run_once)

    p_agent_loop = subparsers.add_parser("agent-loop", help="Agent runtime: run autonomous loop (error guard + health stop)")
    p_agent_loop.add_argument("--interval", type=float, default=300, help="Seconds between runs (default 300)")
    p_agent_loop.add_argument("--max-consecutive-failures", type=int, default=5, help="Stop loop after N consecutive failures (default 5)")
    p_agent_loop.add_argument("--symbols", default=None, help="Comma-separated symbols (default: NVDA)")
    p_agent_loop.add_argument("--capital", type=float, default=10000, help="Capital (default 10000)")
    p_agent_loop.add_argument("--benchmark", default="SPY", help="Benchmark (default SPY)")
    _add_common(p_agent_loop)

    p_openclaw_once = subparsers.add_parser("openclaw-agent-once", help="OpenClaw: one run via config (config -> adapter -> agent)")
    p_openclaw_once.add_argument("--config", required=True, help="Path to OpenClaw agent config (yaml/json)")
    p_openclaw_once.add_argument("--context", action="store_true", help="Include health/experience summary in output")

    p_openclaw_loop = subparsers.add_parser("openclaw-agent-loop", help="OpenClaw: loop via config (config -> adapter -> agent)")
    p_openclaw_loop.add_argument("--config", required=True, help="Path to OpenClaw agent config (yaml/json)")
    p_openclaw_loop.add_argument("--context", action="store_true", help="Include health/experience summary each run")

    p_openclaw_smoke = subparsers.add_parser("openclaw-approver-smoke", help="OpenClaw: single-round approver integration (proposal -> prompt -> mock output -> parsed decision)")
    p_openclaw_smoke.add_argument("--config", required=True, help="Path to OpenClaw agent config (yaml/json)")
    p_openclaw_smoke.add_argument("--raw", default=None, help="Mock raw agent output (default: approve)")

    p_trading_intent = subparsers.add_parser("openclaw-trading-intent", help="OpenClaw: sync intent dispatcher, no exec/poll. Message via --message-json or stdin.")
    p_trading_intent.add_argument("--message-json", default=None, help='JSON with "message" key, e.g. \'{"message": "账户建仓"}\'')
    p_trading_intent.add_argument("--config", default=None, help="Path to OpenClaw agent config (optional)")
    p_trading_intent.add_argument("--timeout", type=float, default=30, help="Handler timeout seconds (default 30)")

    p_proposal_run = subparsers.add_parser("proposal-run", help="Generate proposal only (no approval, no execution)")
    p_proposal_run.add_argument("--symbols", default="NVDA", help="Comma-separated symbols (default: NVDA)")
    p_proposal_run.add_argument("--capital", type=float, default=10000, help="Capital (default 10000)")
    p_proposal_run.add_argument("--benchmark", default="SPY", help="Benchmark (default SPY)")
    p_proposal_run.add_argument("--no-mock", action="store_true", help="Use real paper data (IBKR snapshot, yfinance research); fail if unavailable")
    _add_common(p_proposal_run)

    args = parser.parse_args()

    if args.command == "agent-run-once":
        import time
        from ai_trading_research_system.agent.runtime import AutonomousTradingAgent, format_run_observability
        symbols = [s.strip() for s in (args.symbols or "NVDA").split(",") if s.strip()]
        agent = AutonomousTradingAgent(
            symbols=symbols,
            capital=getattr(args, "capital", 10000),
            benchmark=getattr(args, "benchmark", "SPY"),
            use_mock=not getattr(args, "llm", False),
            use_llm=getattr(args, "llm", False),
            execute_paper=True,
        )
        summary = agent.run_once()
        print(format_run_observability(summary))
        return 0 if summary.get("ok", True) else 1

    if args.command == "agent-loop":
        from ai_trading_research_system.agent.runtime import AutonomousTradingAgent, format_run_observability
        symbols = [s.strip() for s in (args.symbols or "NVDA").split(",") if s.strip()]
        agent = AutonomousTradingAgent(
            symbols=symbols,
            capital=getattr(args, "capital", 10000),
            benchmark=getattr(args, "benchmark", "SPY"),
            use_mock=not getattr(args, "llm", False),
            use_llm=getattr(args, "llm", False),
            execute_paper=True,
        )
        interval = getattr(args, "interval", 300)
        max_failures = getattr(args, "max_consecutive_failures", 5)

        def on_run_done(summ, err):
            if err:
                print(f"RUN_ERROR: {err}")
            elif summ:
                print(format_run_observability(summ))
            print("---")

        agent.run_loop(
            interval_seconds=interval,
            max_consecutive_failures=max_failures,
            on_run_done=on_run_done,
        )
        return 0

    if args.command == "proposal-run":
        import time
        from ai_trading_research_system.application.commands.run_autonomous_paper_cycle import run_autonomous_paper_cycle
        from ai_trading_research_system.state.run_store import get_run_store
        symbols = [s.strip() for s in (args.symbols or "NVDA").split(",") if s.strip()]
        run_id = f"run_{int(time.time())}"
        use_mock = not getattr(args, "no_mock", False)
        out = run_autonomous_paper_cycle(
            run_id=run_id,
            symbol_universe=symbols,
            use_mock=use_mock,
            use_llm=getattr(args, "llm", False),
            capital=getattr(args, "capital", 10000),
            benchmark=getattr(args, "benchmark", "SPY"),
            execute_paper=True,
            proposal_only=True,
        )
        store = get_run_store()
        proposal_path = store.path_for_artifact(run_id, "approval_request")
        proposal = store.read_proposal(run_id) or {}
        summary_lines = proposal.get("proposal_summary") or []
        print("PROPOSAL")
        for line in summary_lines:
            print(" ", line)
        print("PROPOSAL_PATH", proposal_path)
        return 0 if out.ok else 1

    if args.command == "openclaw-agent-once":
        from ai_trading_research_system.openclaw.config import OpenClawAgentConfig
        from ai_trading_research_system.openclaw.agent_adapter import (
            run_openclaw_agent_once,
            format_openclaw_run_output,
            build_openclaw_context_summary,
        )
        config = OpenClawAgentConfig.load(Path(args.config))
        summary = run_openclaw_agent_once(config)
        if getattr(args, "context", False):
            summary["context_summary"] = build_openclaw_context_summary(runs_root=config.runs_root)
        print(format_openclaw_run_output(summary, include_context=getattr(args, "context", False)))
        return 0 if summary.get("ok", True) else 1

    if args.command == "openclaw-approver-smoke":
        from ai_trading_research_system.openclaw.config import OpenClawAgentConfig
        from ai_trading_research_system.openclaw.agent_adapter import (
            run_openclaw_approver_smoke,
            format_approver_smoke_summary,
        )
        config = OpenClawAgentConfig.load(Path(args.config))
        result = run_openclaw_approver_smoke(config, raw_agent_output=getattr(args, "raw", None))
        print(format_approver_smoke_summary(result))
        return 0 if result.get("ok", True) else 1

    if args.command == "openclaw-trading-intent":
        from ai_trading_research_system.openclaw.agent_adapter import handle_trading_intent
        from ai_trading_research_system.openclaw.config import OpenClawAgentConfig
        import sys
        msg = ""
        message_json = getattr(args, "message_json", None)
        if message_json:
            try:
                payload = json.loads(message_json)
                msg = (payload.get("message") or "").strip() if isinstance(payload, dict) else ""
            except (TypeError, ValueError):
                pass
        if not msg and not sys.stdin.isatty():
            try:
                raw = sys.stdin.read()
                payload = json.loads(raw) if raw.strip() else {}
                msg = (payload.get("message") or "").strip() if isinstance(payload, dict) else ""
            except (TypeError, ValueError):
                pass
        if not msg:
            out = {"status": "error", "summary": "missing message", "details": {"hint": "use --message-json \'{\"message\": \"...\"}\' or stdin"}}
        else:
            config = OpenClawAgentConfig.load(Path(args.config)) if getattr(args, "config", None) else None
            timeout = getattr(args, "timeout", 30) or 30
            out = handle_trading_intent(msg, config=config, timeout_seconds=timeout)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("status") != "error" else 1

    if args.command == "openclaw-agent-loop":
        from ai_trading_research_system.openclaw.config import OpenClawAgentConfig
        from ai_trading_research_system.openclaw.agent_adapter import (
            create_openclaw_agent,
            format_openclaw_run_output,
            build_openclaw_context_summary,
        )
        from ai_trading_research_system.state.run_store import get_run_store
        config = OpenClawAgentConfig.load(Path(args.config))
        agent = create_openclaw_agent(config)
        store = get_run_store(root=config.runs_root)
        include_ctx = getattr(args, "context", False)

        def on_run_done(summ, err):
            if err:
                print(f"RUN_ERROR: {err}")
            elif summ:
                run_path = str(store.run_dir(summ["run_id"])) if summ.get("run_id") else ""
                out = {
                    "agent_name": config.name,
                    "run_id": summ.get("run_id"),
                    "symbols": config.symbols,
                    "ok": summ.get("ok"),
                    "decision_summary": summ.get("decision_summary"),
                    "risk_flags": summ.get("risk_flags"),
                    "orders_executed": summ.get("executed_orders_count", 0),
                    "rebalance_summary": summ.get("rebalance_summary"),
                    "portfolio_before": {"value": summ.get("portfolio_before_value")},
                    "portfolio_after": {"value": summ.get("portfolio_after_value")},
                    "run_path": run_path,
                }
                if include_ctx:
                    out["context_summary"] = build_openclaw_context_summary(runs_root=config.runs_root)
                print(format_openclaw_run_output(out, include_context=include_ctx))
            print("---")

        agent.run_loop(
            interval_seconds=config.interval_seconds,
            max_consecutive_failures=config.stop_after_consecutive_failures,
            on_run_done=on_run_done,
        )
        return 0

    if args.command == "status":
        from ai_trading_research_system.services.status_service import get_system_status
        status = get_system_status()
        output = render("status", status.to_dict(), args)
        if isinstance(output, dict):
            print(json.dumps(output, indent=2, default=_json_serial))
        else:
            for line in output:
                print(line)
        return 0

    _init_logging()
    kwargs = kwargs_from_cli_args(args.command, args)
    result = command_run(args.command, **kwargs)

    output = render(args.command, result, args)
    if isinstance(output, dict):
        print(json.dumps(output, indent=2, default=_json_serial))
    else:
        for line in output:
            print(line)

    if getattr(result, "paused", False):
        return 1
    if getattr(result, "ok", True) is False:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
