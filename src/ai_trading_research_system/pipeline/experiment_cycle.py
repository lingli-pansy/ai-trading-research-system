"""
Experiment Lifecycle Automation: ExperimentCycle、run_experiment_cycle、下一周期初始化。
不修改 trading logic / policy / trigger / health / evolution 算法，仅编排实验生命周期。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ai_trading_research_system.autonomous.schemas import WeeklyTradingMandate
from ai_trading_research_system.autonomous.portfolio_policy import PortfolioDecisionPolicy
from ai_trading_research_system.pipeline.weekly_paper_pipe import run_weekly_autonomous_paper, WeeklyPaperResult


@dataclass
class ExperimentCycle:
    """单次实验周期：experiment_id、mandate、起止时间、状态、最后 rebalance/health/report 时间。"""
    experiment_id: str
    mandate: WeeklyTradingMandate
    start_time: str = ""
    end_time: str = ""
    status: str = "running"  # running | completed | failed
    last_rebalance: str = ""
    last_health_check: str = ""
    last_report_generated: str = ""
    cycle_number: int = 0
    policy_version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "mandate_id": self.mandate.mandate_id,
            "mandate": self.mandate.to_dict(),
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status,
            "last_rebalance": self.last_rebalance,
            "last_health_check": self.last_health_check,
            "last_report_generated": self.last_report_generated,
            "cycle_number": self.cycle_number,
            "policy_version": self.policy_version,
        }


def run_experiment_cycle(
    experiment_id: str,
    *,
    mandate: WeeklyTradingMandate | None = None,
    cycle_number: int = 1,
    policy_version: str = "",
    capital: float = 10_000.0,
    benchmark: str = "SPY",
    duration_days: int = 5,
    use_mock: bool = False,
    report_dir: Any = None,
    symbols: list[str] | None = None,
) -> tuple[ExperimentCycle, WeeklyPaperResult]:
    """
    运行一周实验周期：启动 weekly experiment → daily rebalance / intraday trigger / end-of-week report / evolution proposal。
    返回 (ExperimentCycle 含最终状态, WeeklyPaperResult)。
    """
    from ai_trading_research_system.experience.store import write_experiment_cycle, update_experiment_cycle
    from ai_trading_research_system.autonomous.mandate import mandate_from_cli

    if mandate is None:
        mandate = mandate_from_cli(
            capital=capital,
            benchmark=benchmark,
            duration_days=duration_days,
            watchlist=symbols,
        )
    now = datetime.now(timezone.utc).isoformat()
    cycle = ExperimentCycle(
        experiment_id=experiment_id,
        mandate=mandate,
        start_time=now,
        end_time="",
        status="running",
        last_rebalance=now,
        last_health_check=now,
        last_report_generated="",
        cycle_number=cycle_number,
        policy_version=policy_version or f"cycle_{cycle_number}",
    )
    write_experiment_cycle(
        experiment_id=experiment_id,
        mandate_id=mandate.mandate_id,
        start_time=cycle.start_time,
        end_time=cycle.end_time,
        status=cycle.status,
        last_rebalance=cycle.last_rebalance,
        last_health_check=cycle.last_health_check,
        last_report_generated=cycle.last_report_generated,
        cycle_number=cycle_number,
        policy_version=cycle.policy_version,
    )
    result = run_weekly_autonomous_paper(
        mandate=mandate,
        capital=capital,
        benchmark=benchmark,
        duration_days=duration_days,
        use_mock=use_mock,
        report_dir=report_dir,
        symbols=symbols or mandate.watchlist,
        experiment_id=experiment_id,
        cycle_number=cycle_number,
        policy_version=cycle.policy_version,
    )
    end_now = datetime.now(timezone.utc).isoformat()
    cycle.end_time = end_now
    cycle.status = "completed" if result.ok else "failed"
    cycle.last_report_generated = end_now
    applied_policies = mandate.policy.to_dict() if getattr(mandate, "policy", None) else {}
    evolution_decision = getattr(result, "evolution_decision", None) or {}
    final_performance = result.summary or {}
    update_experiment_cycle(
        experiment_id=experiment_id,
        cycle_number=cycle_number,
        end_time=cycle.end_time,
        status=cycle.status,
        last_report_generated=cycle.last_report_generated,
        applied_policies=applied_policies,
        evolution_decision=evolution_decision,
        final_performance=final_performance,
    )
    return cycle, result


def build_next_mandate_from_evolution(
    previous_mandate: WeeklyTradingMandate,
    evolution_decision: dict[str, Any],
) -> WeeklyTradingMandate:
    """
    根据上一周期的 evolution decision 构建下一周期 mandate（应用 approved_policy）。
    approved_evolution → new mandate/policy → next experiment cycle.
    """
    from ai_trading_research_system.autonomous.mandate import mandate_from_cli
    approved = evolution_decision.get("approved_policy")
    if not approved or not isinstance(approved, dict):
        return mandate_from_cli(
            capital=previous_mandate.capital_limit,
            benchmark=previous_mandate.benchmark,
            duration_days=previous_mandate.duration_trading_days,
            max_positions=previous_mandate.max_positions,
            cash_reserve_pct=previous_mandate.cash_reserve_pct,
            watchlist=previous_mandate.watchlist,
            policy=previous_mandate.policy,
        )
    policy = PortfolioDecisionPolicy(
        minimum_score_gap_for_replacement=float(approved.get("minimum_score_gap_for_replacement", 0.3)),
        max_replacements_per_rebalance=int(approved.get("max_replacements_per_rebalance", 2)),
        turnover_budget=float(approved.get("turnover_budget", 0.5)),
        retain_threshold=float(approved.get("retain_threshold", 0.0)),
        no_trade_if_improvement_small=bool(approved.get("no_trade_if_improvement_small", False)),
    )
    return mandate_from_cli(
        capital=previous_mandate.capital_limit,
        benchmark=previous_mandate.benchmark,
        duration_days=previous_mandate.duration_trading_days,
        max_positions=previous_mandate.max_positions,
        cash_reserve_pct=previous_mandate.cash_reserve_pct,
        watchlist=previous_mandate.watchlist,
        policy=policy,
    )
