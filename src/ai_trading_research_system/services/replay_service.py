"""
Experiment Replay: 使用历史 market data 与指定 policy/strategy 重新运行 allocation/decision，
不修改原始实验；用于 scenario replay 与结果对比。深化 Replay Analysis：decision diff、replay comparison 写入 store。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_trading_research_system.experience.store import (
    read_latest_experiment_cycle,
    read_latest_decision_traces_snapshot,
    write_replay_comparison,
)
from ai_trading_research_system.autonomous.mandate import mandate_from_cli
from ai_trading_research_system.autonomous.portfolio_policy import (
    PortfolioDecisionPolicy,
    default_policy,
)
from ai_trading_research_system.pipeline.weekly_paper_pipe import (
    run_weekly_autonomous_paper,
    WeeklyPaperResult,
)


@dataclass
class ExperimentReplay:
    """单次实验重放：源实验、策略/政策版本、重放区间、重放结果。"""
    source_experiment_id: str
    policy_version: str
    strategy_version: str
    replay_start: str
    replay_end: str
    replay_result: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_experiment_id": self.source_experiment_id,
            "policy_version": self.policy_version,
            "strategy_version": self.strategy_version,
            "replay_start": self.replay_start,
            "replay_end": self.replay_end,
            "replay_result": self.replay_result,
        }


@dataclass
class ResultComparison:
    """原始 vs 重放结果对比：return / drawdown / turnover 的差值。"""
    return_delta: float
    drawdown_delta: float
    turnover_delta: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "return_delta": self.return_delta,
            "drawdown_delta": self.drawdown_delta,
            "turnover_delta": self.turnover_delta,
        }


def run_experiment_replay(
    source_experiment_id: str,
    *,
    replay_start: str = "",
    replay_end: str = "",
    policy_version: str = "",
    strategy_version: str = "",
    duration_days: int = 5,
    capital: float = 10_000.0,
    benchmark: str = "SPY",
    symbols: list[str] | None = None,
    use_mock: bool = True,
    report_dir: Path | None = None,
    db_path: Path | None = None,
) -> ExperimentReplay:
    """
    使用历史 market data（当前为 use_mock）与指定 policy/strategy 重新运行一周 allocation/decision。
    使用 experiment_id = "replay_<source_experiment_id>"，不写入/更新源实验的 experiment_cycles。
    返回 ExperimentReplay（含 replay_result = WeeklyPaperResult.summary）。
    """
    replay_id = f"replay_{source_experiment_id}"
    cycle = read_latest_experiment_cycle(experiment_id=source_experiment_id, db_path=db_path)
    policy = default_policy()
    if cycle:
        applied = (cycle.get("applied_policies") or {}) if isinstance(cycle.get("applied_policies"), dict) else {}
        if applied:
            policy = PortfolioDecisionPolicy(
                minimum_score_gap_for_replacement=float(applied.get("minimum_score_gap_for_replacement", 0.3)),
                max_replacements_per_rebalance=int(applied.get("max_replacements_per_rebalance", 2)),
                turnover_budget=float(applied.get("turnover_budget", 0.5)),
                retain_threshold=float(applied.get("retain_threshold", 0.0)),
                no_trade_if_improvement_small=bool(applied.get("no_trade_if_improvement_small", False)),
            )
    mandate = mandate_from_cli(
        capital=capital,
        benchmark=benchmark,
        duration_days=duration_days,
        watchlist=symbols or ["NVDA"],
        policy=policy,
    )
    now_start = datetime.now(timezone.utc).isoformat()
    result: WeeklyPaperResult = run_weekly_autonomous_paper(
        mandate=mandate,
        capital=capital,
        benchmark=benchmark,
        duration_days=duration_days,
        use_mock=use_mock,
        report_dir=report_dir,
        symbols=mandate.watchlist,
        experiment_id=replay_id,
        cycle_number=0,
        policy_version=policy_version or "replay",
    )
    now_end = datetime.now(timezone.utc).isoformat()
    replay_start_actual = replay_start or now_start
    replay_end_actual = replay_end or now_end
    replay_result = result.summary if result.summary else {}
    decision_diff_summary: dict[str, Any] = {}
    original_snapshot = read_latest_decision_traces_snapshot(experiment_id=source_experiment_id, db_path=db_path)
    replay_dts = replay_result.get("decision_traces_summary") or {}
    replay_traces = replay_dts.get("traces") or []
    replay_trigger_traces = replay_dts.get("trigger_traces") or []
    if original_snapshot and (replay_traces or replay_trigger_traces):
        orig_traces = original_snapshot.get("traces") or []
        orig_trigger_traces = original_snapshot.get("trigger_traces") or []
        decision_diff_summary = compare_decision_traces(
            orig_traces, orig_trigger_traces, replay_traces, replay_trigger_traces
        )
    replay_result["decision_diff_summary"] = decision_diff_summary
    original_summary = (cycle.get("final_performance") or {}) if cycle else {}
    result_comparison = compare_experiment_results(original_summary, replay_result).to_dict()
    write_replay_comparison(
        source_experiment_id=source_experiment_id,
        replay_experiment_id=replay_id,
        result_comparison=result_comparison,
        decision_diff=decision_diff_summary,
        db_path=db_path,
    )
    return ExperimentReplay(
        source_experiment_id=source_experiment_id,
        policy_version=policy_version or "replay",
        strategy_version=strategy_version or "replay",
        replay_start=replay_start_actual,
        replay_end=replay_end_actual,
        replay_result=replay_result,
    )


def compare_decision_traces(
    original_traces: list[dict[str, Any]],
    original_trigger_traces: list[dict[str, Any]],
    replay_traces: list[dict[str, Any]],
    replay_trigger_traces: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    比较原始与重放的 decision/trigger traces，输出 position_differences、trigger_differences、policy_constraint_differences。
    """
    def _replace_symbols(traces: list[dict]) -> set[str]:
        return {t.get("symbol", "") for t in traces if t.get("final_action") == "replace" and t.get("symbol")}

    def _rejected_symbols(traces: list[dict]) -> set[str]:
        return {t.get("symbol", "") for t in traces if t.get("final_action") == "rejected" and t.get("symbol")}

    orig_replace = _replace_symbols(original_traces)
    replay_replace = _replace_symbols(replay_traces)
    orig_rejected = _rejected_symbols(original_traces)
    replay_rejected = _rejected_symbols(replay_traces)

    position_differences = {
        "only_in_original_replace": list(orig_replace - replay_replace),
        "only_in_replay_replace": list(replay_replace - orig_replace),
        "common_replace": list(orig_replace & replay_replace),
        "only_in_original_rejected": list(orig_rejected - replay_rejected),
        "only_in_replay_rejected": list(replay_rejected - orig_rejected),
    }

    orig_fired = [t for t in original_trigger_traces if t.get("trigger_fired")]
    replay_fired = [t for t in replay_trigger_traces if t.get("trigger_fired")]
    type_mismatches: list[dict[str, Any]] = []
    for i, (o, r) in enumerate(zip(original_trigger_traces, replay_trigger_traces)):
        if o.get("trigger_type") != r.get("trigger_type") or o.get("trigger_reason") != r.get("trigger_reason"):
            type_mismatches.append({"index": i, "original_type": o.get("trigger_type"), "replay_type": r.get("trigger_type"), "original_reason": o.get("trigger_reason"), "replay_reason": r.get("trigger_reason")})
    if len(original_trigger_traces) != len(replay_trigger_traces):
        type_mismatches.append({"length_mismatch": True, "original_count": len(original_trigger_traces), "replay_count": len(replay_trigger_traces)})

    trigger_differences = {
        "original_fired_count": len(orig_fired),
        "replay_fired_count": len(replay_fired),
        "type_mismatches": type_mismatches,
    }

    def _first_policy(traces: list[dict]) -> dict[str, Any]:
        for t in traces:
            pc = t.get("policy_constraints") or {}
            if pc:
                return pc
        return {}

    orig_policy = _first_policy(original_traces)
    replay_policy = _first_policy(replay_traces)
    all_keys = set(orig_policy) | set(replay_policy)
    deltas: dict[str, Any] = {}
    for k in all_keys:
        ov = orig_policy.get(k)
        rv = replay_policy.get(k)
        if ov != rv:
            deltas[k] = {"original": ov, "replay": rv}
    policy_constraint_differences = {
        "original": orig_policy,
        "replay": replay_policy,
        "deltas": deltas,
    }

    return {
        "position_differences": position_differences,
        "trigger_differences": trigger_differences,
        "policy_constraint_differences": policy_constraint_differences,
    }


def compare_experiment_results(
    original_summary: dict[str, Any],
    replay_summary: dict[str, Any],
) -> ResultComparison:
    """
    比较原始实验与重放实验的结果，输出 return delta、drawdown delta、turnover delta。
    若 summary 中缺少对应 key，按 0.0 处理。
    """
    def _ret(s: dict[str, Any]) -> float:
        return float(s.get("portfolio_return") or s.get("excess_return") or 0.0)

    def _dd(s: dict[str, Any]) -> float:
        return float(s.get("max_drawdown", 0.0))

    def _to(s: dict[str, Any]) -> float:
        return float(s.get("turnover_pct", 0.0))

    return ResultComparison(
        return_delta=_ret(replay_summary) - _ret(original_summary),
        drawdown_delta=_dd(replay_summary) - _dd(original_summary),
        turnover_delta=_to(replay_summary) - _to(original_summary),
    )
