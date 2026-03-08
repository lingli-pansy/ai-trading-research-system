"""
单周期自治 Paper 编排：分阶段、有状态闭环、可 replay、可解释调仓。
主入口 run_autonomous_paper_cycle 编排：load_state → build_research_bundle → evaluate_trigger_and_allocate
→ build_rebalance_plan → execute_paper_orders → finalize_run。
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
from ai_trading_research_system.state.schemas import (
    RebalancePlan,
    RebalancePlanItem,
    PortfolioSnapshot,
    PaperExecutionResult,
    action_type_from_weights,
)
from ai_trading_research_system.services.benchmark_service import get_benchmark_returns_and_volatility


@dataclass
class CycleInput:
    """OpenClaw agent 单周期输入契约。"""
    run_id: str
    symbol_universe: list[str]
    mode: str = "paper"
    use_mock: bool = False
    use_llm: bool = False
    time_window: str | None = None
    portfolio_snapshot_override: dict[str, Any] | None = None
    risk_budget: float | None = None
    capital: float = 10_000.0
    benchmark: str = "SPY"
    execute_paper: bool = True


@dataclass
class CycleOutput:
    """OpenClaw agent 单周期输出契约。"""
    ok: bool
    run_id: str
    candidate_decision: list[dict[str, Any]]
    final_decision: dict[str, Any]
    order_intents: list[dict[str, Any]]
    rebalance_plan: dict[str, Any] = field(default_factory=dict)
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


def _current_weight(position: dict, equity: float) -> float:
    if equity <= 0:
        return 0.0
    mv = position.get("market_value") or position.get("market_value_estimate") or 0
    if mv:
        return float(mv) / equity
    qty = position.get("quantity", 0)
    return float(qty) * 0.01 / equity if qty else 0.0


# ---------- 阶段 1: load_state ----------
def load_state(
    run_id: str,
    input_: CycleInput,
    store: RunStore,
) -> tuple[AccountSnapshot, dict[str, Any], list[str]]:
    """
    输出: portfolio_before (AccountSnapshot), run_metadata (dict), symbols (list).
    写入: meta, snapshots/portfolio_before.json
    """
    symbols = input_.symbol_universe or ["NVDA"]
    store.create_run(run_id, mode=input_.mode, symbols=symbols, config={
        "use_mock": input_.use_mock,
        "use_llm": input_.use_llm,
        "execute_paper": input_.execute_paper,
        "capital": input_.capital,
        "benchmark": input_.benchmark,
    })
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
    store.write_snapshot(run_id, "portfolio_before", _snapshot_to_dict(snap))
    run_metadata = store.read_meta(run_id) or {}
    return snap, run_metadata, symbols


# ---------- 阶段 2: build_research_bundle ----------
def build_research_bundle(
    run_id: str,
    symbols: list[str],
    use_mock: bool,
    use_llm: bool,
    store: RunStore,
) -> tuple[list[tuple[str, ResearchContext, DecisionContract]], list[dict[str, Any]], list[OpportunityScore]]:
    """
    输出: contracts_for_cycle, research_snapshot (by_symbol), opportunity_ranking.
    写入: snapshots/research.json, artifacts/candidate_decision.json
    """
    orchestrator = ResearchOrchestrator(use_mock=use_mock, use_llm=use_llm)
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
    ranker = OpportunityRanking()
    ranked: list[OpportunityScore] = ranker.rank([(s, c) for s, _, c in contracts_for_cycle])
    opportunity_ranking = [{"symbol": o.symbol, "score": o.score, "confidence": o.confidence, "risk": o.risk} for o in ranked]
    store.write_snapshot(run_id, "research", {"by_symbol": research_snapshot, "opportunity_ranking": opportunity_ranking})
    store.write_artifact(run_id, "candidate_decision", {"contracts": [{"symbol": c.symbol, "action": c.suggested_action, "confidence": c.confidence} for _, _, c in contracts_for_cycle]})
    return contracts_for_cycle, research_snapshot, ranked


# ---------- 阶段 3: evaluate_trigger_and_allocate ----------
def evaluate_trigger_and_allocate(
    run_id: str,
    snap: AccountSnapshot,
    mandate: WeeklyTradingMandate,
    contracts_for_cycle: list[tuple[str, ResearchContext, DecisionContract]],
    ranked: list[OpportunityScore],
    capital: float,
    benchmark: str,
    store: RunStore,
) -> tuple[Any, Any, AllocationResult | None]:
    """
    输出: trigger, trigger_trace, allocator_result (或 None 表示 no_trigger/no_trade).
    写入: audit (trigger)
    """
    contract_by_symbol = {s: (ctx, c) for s, ctx, c in contracts_for_cycle}
    opportunity_ranking_list = [{"symbol": o.symbol, "score": o.score, "confidence": o.confidence, "risk": o.risk} for o in ranked]
    spy_returns, bench_ret, vol_d, max_dd = get_benchmark_returns_and_volatility(symbol=benchmark, lookback_days=5)
    benchmark_data = {
        "benchmark_return": bench_ret,
        "volatility": vol_d,
        "max_drawdown": max_dd,
        "portfolio_returns": [],
        "spy_returns": spy_returns[-5:] if spy_returns else [],
    }
    health = evaluate_portfolio_health(snap, benchmark_data, snap.positions or [], initial_equity=capital)
    current_positions = {p.get("symbol"): p for p in (snap.positions or []) if p.get("symbol")}
    trigger, trigger_trace = evaluate_intraday_triggers(
        snap,
        opportunity_ranking_list,
        current_positions,
        mandate.policy,
        initial_equity=capital,
        portfolio_health=health,
    )
    store.append_audit(run_id, {"trigger": trigger.trigger_type if trigger else None, "trigger_trace": trigger_trace.to_dict() if hasattr(trigger_trace, "to_dict") else str(trigger_trace)})
    if trigger is None:
        return trigger, trigger_trace, None
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
    wait_any = not any(s.get("size_fraction", 0) > 0 or (s.get("rationale") or "").startswith("probe") for s in signals)
    allocator = PortfolioAllocator(max_position_pct=0.25)
    alloc_result = allocator.allocate(
        snap,
        mandate,
        signals,
        wait_confirmation=wait_any,
        portfolio_health=health,
        trigger_context=trigger_trace.to_dict() if hasattr(trigger_trace, "to_dict") else {},
    )
    return trigger, trigger_trace, alloc_result


# ---------- 阶段 4: build_rebalance_plan ----------
def build_rebalance_plan(
    snap: AccountSnapshot,
    alloc_result: AllocationResult,
    signals: list[dict[str, Any]],
) -> tuple[RebalancePlan, list[dict[str, Any]]]:
    """
    由 target_positions + portfolio_before 推导 RebalancePlan；
    order_intents 由 rebalance_plan 生成。
    """
    equity = snap.equity if snap.equity > 0 else snap.cash
    current_weights: dict[str, float] = {}
    for p in (snap.positions or []):
        sym = p.get("symbol")
        if sym:
            current_weights[sym] = _current_weight(p, equity)
    items: list[RebalancePlanItem] = []
    order_intents: list[dict[str, Any]] = []
    for target in alloc_result.target_positions:
        sym = target.get("symbol", "")
        if not sym:
            continue
        target_weight = float(target.get("weight_pct", 0) or 0)
        current = current_weights.get(sym, 0.0)
        delta = target_weight - current
        action = action_type_from_weights(current, target_weight)
        reason = target.get("rationale", "") or next((s.get("rationale", "") for s in signals if s.get("symbol") == sym), "")
        confidence = "medium"
        items.append(RebalancePlanItem(symbol=sym, current_position=current, target_position=target_weight, delta=delta, action_type=action, reason=reason, confidence=confidence))
        order_intents.append({
            "symbol": sym,
            "side": "buy" if delta > 0 else "sell",
            "size_fraction": target_weight,
            "delta": delta,
            "action_type": action,
            "rationale": reason,
        })
    plan = RebalancePlan(items=items)
    return plan, order_intents


# ---------- 阶段 5: execute_paper_orders ----------
def execute_paper_orders(
    run_id: str,
    alloc_result: AllocationResult,
    contract_by_symbol: dict[str, tuple[ResearchContext, DecisionContract]],
    use_mock: bool,
    execute_paper: bool,
) -> list[dict[str, Any]]:
    """输出: paper_execution_results (list of dict). 写入: execution/paper_result.json 由 finalize_run 前一步完成。"""
    results: list[dict[str, Any]] = []
    if not execute_paper or not alloc_result.target_positions:
        return results
    translator = ContractTranslator()
    for target in alloc_result.target_positions:
        sym = target.get("symbol", "")
        if not sym or sym not in contract_by_symbol:
            continue
        _, contract = contract_by_symbol[sym]
        signal = translator.translate(contract)
        runner = NautilusPaperRunner(sym, lookback_days=5)
        runner.inject(signal)
        runner.start()
        result = runner.run_once(122.5, use_mock=use_mock)
        runner.stop()
        results.append(PaperExecutionResult(
            symbol=sym,
            pnl=result.pnl,
            trade_count=result.trade_count,
            order_done=result.order_done,
            message=getattr(result, "message", ""),
        ).to_dict())
    return results


# ---------- 阶段 6: finalize_run (portfolio_after, audit, meta) ----------
def finalize_run(
    run_id: str,
    store: RunStore,
    portfolio_before: dict[str, Any],
    rebalance_plan: RebalancePlan,
    paper_results: list[dict[str, Any]],
    paths: dict[str, str],
) -> None:
    """写入 portfolio_after（由 rebalance_plan + before 推导）, execution, audit, meta.ended_at。"""
    equity_before = portfolio_before.get("equity") or portfolio_before.get("cash") or 0
    positions_before = portfolio_before.get("positions") or []
    # 推导 after：按 plan 更新权重得到新 positions 简化表示
    new_positions: list[dict[str, Any]] = []
    for item in rebalance_plan.items:
        if item.target_position <= 0:
            continue
        mv_estimate = equity_before * item.target_position if equity_before else 0
        new_positions.append({
            "symbol": item.symbol,
            "weight_pct": item.target_position,
            "market_value_estimate": mv_estimate,
            "action_type": item.action_type,
        })
    # 若未执行订单，portfolio_after = portfolio_before
    if not paper_results:
        after_data = dict(portfolio_before)
        after_data["run_id"] = run_id
        after_data["_kind"] = "after"
    else:
        after_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "positions": new_positions,
            "cash_estimate": equity_before * (1 - sum(p.get("weight_pct", 0) for p in new_positions)),
            "equity_estimate": equity_before,
            "run_id": run_id,
            "source": "derived",
        }
    store.write_snapshot(run_id, "portfolio_after", after_data)
    if paper_results:
        store.write_execution(run_id, {"results": paper_results})
    store.write_meta(run_id, (store.read_meta(run_id) or {}) | {"ended_at": datetime.now(timezone.utc).isoformat()})


def run_autonomous_paper_cycle(
    input_: CycleInput,
    *,
    run_store: RunStore | None = None,
) -> CycleOutput:
    """
    执行一轮 autonomous paper cycle（分阶段）。
    load_state → build_research_bundle → evaluate_trigger_and_allocate → build_rebalance_plan
    → execute_paper_orders → finalize_run.
    """
    store = run_store or get_run_store()
    run_id = input_.run_id
    paths: dict[str, str] = {"run_dir": str(store.run_dir(run_id))}

    def audit(msg: str, detail: dict[str, Any] | None = None) -> None:
        store.append_audit(run_id, {"message": msg, **(detail or {})})

    try:
        # 1) load_state
        snap, run_metadata, symbols = load_state(run_id, input_, store)
        paths["portfolio_before"] = store.path_for_snapshot(run_id, "portfolio_before")
        audit("cycle_start", {"symbols": symbols})

        mandate = mandate_from_cli(
            capital=input_.capital,
            benchmark=input_.benchmark,
            duration_days=1,
            auto_confirm=True,
            watchlist=symbols,
        )

        # 2) build_research_bundle
        contracts_for_cycle, research_snapshot, ranked = build_research_bundle(
            run_id, symbols, input_.use_mock, input_.use_llm, store,
        )
        paths["research_snapshot"] = store.path_for_snapshot(run_id, "research")
        paths["candidate_decision"] = store.path_for_artifact(run_id, "candidate_decision")
        audit("research_done", {"symbols": symbols})

        if not contracts_for_cycle:
            store.write_artifact(run_id, "final_decision", {"no_trade_reason": "no_contracts", "order_intents": []})
            store.write_artifact(run_id, "rebalance_plan", RebalancePlan(no_trade_reason="no_contracts").to_dict())
            finalize_run(run_id, store, _snapshot_to_dict(snap), RebalancePlan(no_trade_reason="no_contracts"), [], paths)
            return CycleOutput(
                ok=True,
                run_id=run_id,
                candidate_decision=[],
                final_decision={"no_trade_reason": "no_contracts"},
                order_intents=[],
                rebalance_plan={"no_trade_reason": "no_contracts"},
                trace=store.read_audit(run_id),
                write_paths=paths,
            )

        # 3) evaluate_trigger_and_allocate
        trigger, trigger_trace, alloc_result = evaluate_trigger_and_allocate(
            run_id, snap, mandate, contracts_for_cycle, ranked,
            input_.capital, input_.benchmark, store,
        )
        if trigger is None:
            store.write_artifact(run_id, "final_decision", {"no_trade_reason": "no_trigger", "order_intents": []})
            store.write_artifact(run_id, "rebalance_plan", RebalancePlan(no_trade_reason="no_trigger").to_dict())
            store.append_audit(run_id, {"no_trade_reason": "no_trigger"})
            finalize_run(run_id, store, _snapshot_to_dict(snap), RebalancePlan(no_trade_reason="no_trigger"), [], paths)
            cand = [{"symbol": c.symbol, "action": c.suggested_action, "confidence": c.confidence} for _, _, c in contracts_for_cycle]
            return CycleOutput(
                ok=True,
                run_id=run_id,
                candidate_decision=cand,
                final_decision={"no_trade_reason": "no_trigger"},
                order_intents=[],
                rebalance_plan={"no_trade_reason": "no_trigger"},
                no_trade_reason="no_trigger",
                trace=store.read_audit(run_id),
                write_paths=paths,
            )

        if alloc_result is None or alloc_result.no_trade:
            no_trade_reason = (alloc_result.no_trade_reason if alloc_result else "") or "no_trade"
            store.write_artifact(run_id, "final_decision", {
                "no_trade_reason": no_trade_reason,
                "order_intents": [],
                "target_positions": getattr(alloc_result, "target_positions", []) or [],
            })
            store.write_artifact(run_id, "rebalance_plan", RebalancePlan(no_trade_reason=no_trade_reason).to_dict())
            store.append_audit(run_id, {"no_trade": True, "no_trade_reason": no_trade_reason})
            finalize_run(run_id, store, _snapshot_to_dict(snap), RebalancePlan(no_trade_reason=no_trade_reason), [], paths)
            return CycleOutput(
                ok=True,
                run_id=run_id,
                candidate_decision=[{"symbol": c.symbol, "action": c.suggested_action} for _, _, c in contracts_for_cycle],
                final_decision={"no_trade_reason": no_trade_reason, "order_intents": []},
                order_intents=[],
                rebalance_plan={"no_trade_reason": no_trade_reason},
                no_trade_reason=no_trade_reason,
                trace=store.read_audit(run_id),
                write_paths=paths,
            )

        # 4) build_rebalance_plan（signals 与 allocator 输入一致，用于 rationale）
        translator = ContractTranslator()
        probe_threshold = getattr(mandate.policy, "opportunity_score_probe_threshold", 0.4) or 0.4
        probe_size = 0.03
        signals_for_plan: list[dict[str, Any]] = []
        contract_by_symbol = {s: (ctx, c) for s, ctx, c in contracts_for_cycle}
        for o in ranked:
            _, contract = contract_by_symbol[o.symbol]
            signal = translator.translate(contract)
            if contract.suggested_action in ("wait_confirmation", "watch") and contract.confidence in ("medium", "high") and o.score >= probe_threshold:
                size_fraction = probe_size
                rationale = f"probe (score={o.score:.2f})"
            else:
                size_fraction = signal.allowed_position_size
                rationale = signal.rationale
            signals_for_plan.append({"symbol": o.symbol, "size_fraction": size_fraction, "rationale": rationale, "score": o.score})
        rebalance_plan, order_intents = build_rebalance_plan(snap, alloc_result, signals_for_plan)
        store.write_artifact(run_id, "final_decision", {
            "no_trade_reason": "",
            "order_intents": order_intents,
            "target_positions": alloc_result.target_positions,
            "replacement_decisions": alloc_result.replacement_decisions,
        })
        store.write_rebalance_plan(run_id, rebalance_plan.to_dict())
        store.write_artifact(run_id, "order_intents", order_intents)
        paths["final_decision"] = store.path_for_artifact(run_id, "final_decision")
        paths["order_intents"] = store.path_for_artifact(run_id, "order_intents")
        paths["rebalance_plan"] = store.path_for_artifact(run_id, "rebalance_plan")
        audit("final_decision", {"order_intents_count": len(order_intents)})

        # 5) execute_paper_orders
        paper_results = execute_paper_orders(
            run_id,
            alloc_result,
            contract_by_symbol,
            input_.use_mock,
            input_.execute_paper,
        )
        if paper_results:
            paths["paper_execution"] = store.path_for_execution(run_id)
            audit("paper_execution_done", {"results_count": len(paper_results)})

        # 6) finalize_run
        finalize_run(run_id, store, _snapshot_to_dict(snap), rebalance_plan, paper_results, paths)
        paths["portfolio_after"] = store.path_for_snapshot(run_id, "portfolio_after")

        return CycleOutput(
            ok=True,
            run_id=run_id,
            candidate_decision=[{"symbol": c.symbol, "action": c.suggested_action, "confidence": c.confidence} for _, _, c in contracts_for_cycle],
            final_decision={"order_intents": order_intents, "target_positions": alloc_result.target_positions, "rebalance_plan": rebalance_plan.to_dict()},
            order_intents=order_intents,
            rebalance_plan=rebalance_plan.to_dict(),
            paper_execution_results=paper_results,
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
