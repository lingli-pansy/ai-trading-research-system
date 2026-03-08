"""
单周期自治 Paper 编排：OpenClaw agent 主路径。
一轮 cycle = 读组合快照 → 研究/打分 → 候选决策 → 规则/风控/allocator → 最终动作 → paper 订单意图/执行 → 落盘与审计。
所有状态与决策写入 state.RunStore，不依赖纯接口即状态。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_trading_research_system.autonomous import (
    get_account_snapshot,
    mandate_from_cli,
    PortfolioAllocator,
    AllocationResult,
)
from ai_trading_research_system.autonomous.schemas import AccountSnapshot, WeeklyTradingMandate
from ai_trading_research_system.autonomous.opportunity_ranking import OpportunityRanking, OpportunityScore
from ai_trading_research_system.autonomous.trigger_evaluator import evaluate_intraday_triggers
from ai_trading_research_system.autonomous.portfolio_health import evaluate_portfolio_health
from ai_trading_research_system.research.orchestrator import ResearchOrchestrator
from ai_trading_research_system.research.schemas import DecisionContract, ResearchContext
from ai_trading_research_system.strategy.translator import ContractTranslator
from ai_trading_research_system.execution.nautilus_paper_runner import NautilusPaperRunner
from ai_trading_research_system.state.run_store import RunStore, get_run_store
from ai_trading_research_system.services.regime_context import get_regime_context
from ai_trading_research_system.services.benchmark_service import get_benchmark_returns_and_volatility


@dataclass
class CycleInput:
    """OpenClaw agent 单周期输入契约。"""
    run_id: str
    symbol_universe: list[str]
    mode: str = "paper"
    use_mock: bool = False
    use_llm: bool = False
    time_window: str | None = None  # 可选，如 "2025-01-01"
    portfolio_snapshot_override: dict[str, Any] | None = None  # 若提供则优先用，否则拉取
    risk_budget: float | None = None
    capital: float = 10_000.0
    benchmark: str = "SPY"
    execute_paper: bool = True  # 是否执行 paper 成交（否则只出意图）


@dataclass
class CycleOutput:
    """OpenClaw agent 单周期输出契约。"""
    ok: bool
    run_id: str
    candidate_decision: list[dict[str, Any]]
    final_decision: dict[str, Any]
    order_intents: list[dict[str, Any]]
    paper_execution_results: list[dict[str, Any]] = field(default_factory=list)
    no_trade_reason: str = ""
    rejected_reason: str = ""
    skipped_reason: str = ""
    trace: list[dict[str, Any]] = field(default_factory=list)
    write_paths: dict[str, str] = field(default_factory=dict)
    error: str = ""


def _snapshot_to_dict(snap: AccountSnapshot) -> dict[str, Any]:
    return {
        "cash": snap.cash,
        "equity": snap.equity,
        "positions": list(snap.positions or []),
        "source": snap.source,
        "timestamp": snap.timestamp,
        "risk_budget": snap.risk_budget,
    }


def run_autonomous_paper_cycle(
    input_: CycleInput,
    *,
    run_store: RunStore | None = None,
) -> CycleOutput:
    """
    执行一轮 autonomous paper cycle：读组合 → 研究 → 排名 → 规则/风控 → 最终决策 → 订单意图（可选执行）→ 落盘。
    单一主路径入口，供 OpenClaw adapter 调用。
    """
    store = run_store or get_run_store()
    run_id = input_.run_id
    symbols = input_.symbol_universe or ["NVDA"]
    paths: dict[str, str] = {}

    def audit(msg: str, detail: dict[str, Any] | None = None) -> None:
        store.append_audit(run_id, {"message": msg, **(detail or {})})

    try:
        store.create_run(run_id, mode=input_.mode, symbols=symbols, config={
            "use_mock": input_.use_mock,
            "use_llm": input_.use_llm,
            "execute_paper": input_.execute_paper,
            "capital": input_.capital,
            "benchmark": input_.benchmark,
        })
        paths["run_dir"] = str(store.run_dir(run_id))
        audit("cycle_start", {"symbols": symbols})

        # 1) 组合快照：优先 override，否则拉取
        if input_.portfolio_snapshot_override:
            snap = AccountSnapshot(
                cash=float(input_.portfolio_snapshot_override.get("cash", input_.capital)),
                equity=float(input_.portfolio_snapshot_override.get("equity", input_.capital)),
                positions=input_.portfolio_snapshot_override.get("positions", []),
                open_orders=input_.portfolio_snapshot_override.get("open_orders", []),
                risk_budget=float(input_.portfolio_snapshot_override.get("risk_budget", 0)),
                timestamp=datetime.now(timezone.utc).isoformat(),
                source="override",
            )
        else:
            import os
            reject_mock = not input_.use_mock or (os.environ.get("AI_TRADING_REJECT_MOCK", "").strip() == "1")
            snap = get_account_snapshot(
                paper=True,
                mock=input_.use_mock,
                initial_cash=input_.capital,
                allow_fallback=not reject_mock,
            )
        store.write_portfolio_snapshot(run_id, "before", _snapshot_to_dict(snap))
        paths["portfolio_before"] = str(store._snapshots_dir(run_id) / "portfolio_before.json")
        audit("portfolio_snapshot_loaded", {"source": snap.source, "equity": snap.equity})

        mandate = mandate_from_cli(
            capital=input_.capital,
            benchmark=input_.benchmark,
            duration_days=1,
            auto_confirm=True,
            watchlist=symbols,
        )

        # 2) 研究
        orchestrator = ResearchOrchestrator(use_mock=input_.use_mock, use_llm=input_.use_llm)
        contracts_for_cycle: list[tuple[str, ResearchContext, DecisionContract]] = []
        research_snapshot: list[dict[str, Any]] = []
        for sym in symbols:
            ctx, contract = orchestrator.run_with_context(sym)
            contracts_for_cycle.append((sym, ctx, contract))
            research_snapshot.append({
                "symbol": sym,
                "thesis": (contract.thesis or "")[:500],
                "suggested_action": contract.suggested_action,
                "confidence": contract.confidence,
                "key_drivers": (contract.key_drivers or [])[:5],
            })
        store.write_research_snapshot(run_id, {"by_symbol": research_snapshot})
        paths["research_snapshot"] = str(store._snapshots_dir(run_id) / "research.json")
        store.write_candidate_decision(run_id, {"contracts": [{"symbol": c.symbol, "action": c.suggested_action, "confidence": c.confidence} for _, _, c in contracts_for_cycle]})
        paths["candidate_decision"] = str(store._artifacts_dir(run_id) / "candidate_decision.json")
        audit("research_done", {"symbols": symbols})

        if not contracts_for_cycle:
            store.write_final_decision(run_id, {"no_trade_reason": "no_contracts", "order_intents": []})
            meta = store.read_meta(run_id) or {}
            meta["ended_at"] = datetime.now(timezone.utc).isoformat()
            store.write_meta(run_id, meta)
            return CycleOutput(
                ok=True,
                run_id=run_id,
                candidate_decision=[],
                final_decision={"no_trade_reason": "no_contracts"},
                order_intents=[],
                no_trade_reason="no_contracts",
                trace=store.read_audit(run_id),
                write_paths=paths,
            )

        # 3) 排名与 trigger
        ranker = OpportunityRanking()
        ranked: list[OpportunityScore] = ranker.rank([(s, c) for s, _, c in contracts_for_cycle])
        contract_by_symbol = {s: (ctx, c) for s, ctx, c in contracts_for_cycle}
        opportunity_ranking_list = [{"symbol": o.symbol, "score": o.score, "confidence": o.confidence, "risk": o.risk} for o in ranked]

        spy_returns, bench_ret, vol_d, max_dd = get_benchmark_returns_and_volatility(symbol=input_.benchmark, lookback_days=5)
        benchmark_data = {
            "benchmark_return": bench_ret,
            "volatility": vol_d,
            "max_drawdown": max_dd,
            "portfolio_returns": [],
            "spy_returns": spy_returns[-5:] if spy_returns else [],
        }
        health = evaluate_portfolio_health(snap, benchmark_data, snap.positions or [], initial_equity=input_.capital)
        current_positions = {p.get("symbol"): p for p in (snap.positions or []) if p.get("symbol")}
        trigger, trigger_trace = evaluate_intraday_triggers(
            snap,
            opportunity_ranking_list,
            current_positions,
            mandate.policy,
            initial_equity=input_.capital,
            portfolio_health=health,
        )
        store.append_audit(run_id, {"trigger": trigger.trigger_type if trigger else None, "trigger_trace": trigger_trace.to_dict() if hasattr(trigger_trace, "to_dict") else str(trigger_trace)})
        if trigger is None:
            store.write_final_decision(run_id, {"no_trade_reason": "no_trigger", "order_intents": []})
            store.append_audit(run_id, {"no_trade_reason": "no_trigger"})
            meta = store.read_meta(run_id) or {}
            meta["ended_at"] = datetime.now(timezone.utc).isoformat()
            store.write_meta(run_id, meta)
            cand = [{"symbol": c.symbol, "action": c.suggested_action, "confidence": c.confidence} for _, _, c in contracts_for_cycle]
            return CycleOutput(
                ok=True,
                run_id=run_id,
                candidate_decision=cand,
                final_decision={"no_trade_reason": "no_trigger"},
                order_intents=[],
                no_trade_reason="no_trigger",
                trace=store.read_audit(run_id),
                write_paths=paths,
            )

        # 4) 构建 signals，allocator
        translator = ContractTranslator()
        probe_threshold = getattr(mandate.policy, "opportunity_score_probe_threshold", 0.4) or 0.4
        probe_size = 0.03
        signals = []
        for o in ranked:
            _, contract = contract_by_symbol[o.symbol]
            signal = translator.translate(contract)
            if contract.suggested_action in ("wait_confirmation", "watch") and contract.confidence in ("medium", "high") and o.score >= probe_threshold:
                size_fraction = probe_size
                rationale = f"probe (score={o.score:.2f})"
            else:
                size_fraction = signal.allowed_position_size
                rationale = signal.rationale
            signals.append({
                "symbol": o.symbol,
                "size_fraction": size_fraction,
                "rationale": rationale,
                "score": o.score,
                "research_thesis": getattr(contract, "thesis", "") or "",
                "research_key_drivers": list(getattr(contract, "key_drivers", []) or [])[:10],
                "research_risk_factors": list(getattr(contract, "risk_flags", []) or []),
            })
        wait_any = not any(s.get("size_fraction", 0) > 0 or s.get("rationale", "").startswith("probe") for s in signals)
        allocator = PortfolioAllocator(max_position_pct=0.25)
        alloc_result: AllocationResult = allocator.allocate(
            snap,
            mandate,
            signals,
            wait_confirmation=wait_any,
            portfolio_health=health,
            trigger_context=trigger_trace.to_dict() if hasattr(trigger_trace, "to_dict") else {},
        )

        no_trade_reason = alloc_result.no_trade_reason or "no_trade"
        rejected_reason = ""
        skipped_reason = ""
        if alloc_result.no_trade:
            store.write_final_decision(run_id, {
                "no_trade_reason": no_trade_reason,
                "rejected_reason": rejected_reason,
                "skipped_reason": skipped_reason,
                "order_intents": [],
                "target_positions": [],
            })
            store.append_audit(run_id, {"no_trade": True, "no_trade_reason": no_trade_reason})
            meta = store.read_meta(run_id) or {}
            meta["ended_at"] = datetime.now(timezone.utc).isoformat()
            store.write_meta(run_id, meta)
            return CycleOutput(
                ok=True,
                run_id=run_id,
                candidate_decision=[{"symbol": c.symbol, "action": c.suggested_action} for _, _, c in contracts_for_cycle],
                final_decision={"no_trade_reason": no_trade_reason, "order_intents": []},
                order_intents=[],
                no_trade_reason=no_trade_reason,
                rejected_reason=rejected_reason,
                skipped_reason=skipped_reason,
                trace=store.read_audit(run_id),
                write_paths=paths,
            )

        # 5) 订单意图
        order_intents: list[dict[str, Any]] = []
        for target in alloc_result.target_positions:
            sym = target.get("symbol", "")
            if not sym:
                continue
            order_intents.append({
                "symbol": sym,
                "side": "buy",
                "size_fraction": next((s.get("size_fraction") for s in signals if s.get("symbol") == sym), 0),
                "rationale": next((s.get("rationale") for s in signals if s.get("symbol") == sym), ""),
            })
        store.write_final_decision(run_id, {
            "no_trade_reason": "",
            "order_intents": order_intents,
            "target_positions": alloc_result.target_positions,
            "replacement_decisions": alloc_result.replacement_decisions,
        })
        store.write_order_intents(run_id, order_intents)
        paths["final_decision"] = str(store._artifacts_dir(run_id) / "final_decision.json")
        paths["order_intents"] = str(store._artifacts_dir(run_id) / "order_intents.json")
        audit("final_decision", {"order_intents_count": len(order_intents)})

        # 6) 可选：执行 paper
        paper_results: list[dict[str, Any]] = []
        if input_.execute_paper and order_intents:
            for target in alloc_result.target_positions:
                sym = target.get("symbol", "")
                if not sym or sym not in contract_by_symbol:
                    continue
                _, contract = contract_by_symbol[sym]
                signal = translator.translate(contract)
                runner = NautilusPaperRunner(sym, lookback_days=5)
                runner.inject(signal)
                runner.start()
                result = runner.run_once(122.5, use_mock=input_.use_mock)
                runner.stop()
                paper_results.append({
                    "symbol": sym,
                    "pnl": result.pnl,
                    "trade_count": result.trade_count,
                    "order_done": result.order_done,
                    "message": getattr(result, "message", ""),
                })
            store.write_paper_execution(run_id, {"results": paper_results})
            paths["paper_execution"] = str(store._execution_dir(run_id) / "paper_result.json")
            audit("paper_execution_done", {"results_count": len(paper_results)})

        meta = store.read_meta(run_id) or {}
        meta["ended_at"] = datetime.now(timezone.utc).isoformat()
        store.write_meta(run_id, meta)
        return CycleOutput(
            ok=True,
            run_id=run_id,
            candidate_decision=[{"symbol": c.symbol, "action": c.suggested_action, "confidence": c.confidence} for _, _, c in contracts_for_cycle],
            final_decision={"order_intents": order_intents, "target_positions": alloc_result.target_positions},
            order_intents=order_intents,
            paper_execution_results=paper_results,
            no_trade_reason="",
            rejected_reason=rejected_reason,
            skipped_reason=skipped_reason,
            trace=store.read_audit(run_id),
            write_paths=paths,
        )
    except Exception as e:
        store.append_audit(run_id, {"error": str(e), "phase": "cycle"})
        meta = store.read_meta(run_id)
        if meta:
            meta["ended_at"] = datetime.now(timezone.utc).isoformat()
            meta["error"] = str(e)
            store.write_meta(run_id, meta)
        return CycleOutput(
            ok=False,
            run_id=run_id,
            candidate_decision=[],
            final_decision={},
            order_intents=[],
            error=str(e),
            trace=store.read_audit(run_id),
            write_paths=paths,
        )
