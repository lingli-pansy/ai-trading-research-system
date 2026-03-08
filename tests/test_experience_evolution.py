"""
Experience-Driven Evolution: 经验分析、StrategyRefiner 读洞察、Policy 微调钩子、周报 experience_insights。
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from ai_trading_research_system.experience.analyzer import (
    ExperienceInsights,
    analyze_experience_history,
    analyze_experience_from_store,
)
from ai_trading_research_system.experience.refiner import refiner_suggest_from_insights
from ai_trading_research_system.experience.policy_evolution import adjust_policy_from_insights
from ai_trading_research_system.experience.store import (
    get_connection,
    write_weekly_portfolio_experience,
    write_health_trigger_event,
    write_experience_insight_snapshot,
    write_evolution_proposal_snapshot,
    write_evolution_decision_snapshot,
    read_weekly_portfolio_experience_history,
)
from ai_trading_research_system.experience.evolution_boundary import (
    EvolutionProposal,
    EvolutionDecision,
    build_evolution_proposal_from_insights,
    decide_evolution,
)
from ai_trading_research_system.autonomous.portfolio_policy import default_policy
from ai_trading_research_system.autonomous.portfolio_policy import PortfolioDecisionPolicy
from ai_trading_research_system.autonomous.weekly_report import WeeklyReportGenerator
from ai_trading_research_system.autonomous.benchmark import BenchmarkResult
from ai_trading_research_system.autonomous.schemas import WeeklyTradingMandate


def test_experience_analysis():
    """analyze_experience_history 输入 weekly_experiences + health_events，输出 ExperienceInsights。"""
    weekly = [
        {
            "period": "day_0_to_5",
            "policy_snapshot": {
                "replacements_executed": 2,
                "rejected_due_to_threshold": 3,
                "replacements_skipped": 1,
                "excess_return": 0.02,
                "minimum_score_gap_for_replacement": 0.3,
                "max_replacements_per_rebalance": 2,
                "turnover_budget": 0.5,
            },
            "health_adjustment_summary": [
                {"trigger_type": "concentration_risk_trigger", "period": "day_1"},
            ],
        },
        {
            "period": "day_0_to_5_b",
            "policy_snapshot": {
                "replacements_executed": 4,
                "rejected_due_to_threshold": 2,
                "replacements_skipped": 0,
                "excess_return": -0.01,
                "minimum_score_gap_for_replacement": 0.25,
                "max_replacements_per_rebalance": 3,
                "turnover_budget": 0.5,
            },
            "health_adjustment_summary": [
                {"trigger_type": "concentration_risk_trigger", "period": "day_2"},
            ],
        },
    ]
    health_events = [
        {"trigger_type": "concentration_risk_trigger", "period": "day_0_to_5"},
        {"trigger_type": "beta_spike_trigger", "period": "day_0_to_5_b"},
    ]
    insights = analyze_experience_history(
        weekly_experiences=weekly,
        health_adjustment_events=health_events,
        replacement_failure_threshold=1,
    )
    assert isinstance(insights, ExperienceInsights)
    assert hasattr(insights, "frequent_replacement_failures")
    assert hasattr(insights, "triggers_excessive_turnover")
    assert hasattr(insights, "policies_associated_higher_excess_return")
    assert hasattr(insights, "risk_events_correlation")
    assert hasattr(insights, "strategy_adjustment_suggested")
    assert isinstance(insights.to_dict(), dict)
    assert "frequent_replacement_failures" in insights.to_dict()
    assert len(insights.frequent_replacement_failures) >= 0
    assert len(insights.risk_events_correlation) >= 0


def test_strategy_refiner_reads_insights():
    """StrategyRefiner 可读取 ExperienceInsights，产出 entry_filters / risk_controls / signal_thresholds 建议。"""
    insights = ExperienceInsights(
        frequent_replacement_failures=[{"reason": "score_gap_below_threshold", "count": 5}],
        triggers_excessive_turnover=[{"trigger_type": "opportunity_spike_trigger", "avg_replacements": 3, "high_turnover_weeks": 2}],
        risk_events_correlation=[{"trigger_type": "concentration_risk_trigger", "weeks_count": 2, "avg_excess_return": -0.02}],
        strategy_adjustment_suggested=True,
    )
    out = refiner_suggest_from_insights(insights)
    assert "entry_filters_adjustment" in out
    assert "risk_controls_adjustment" in out
    assert "signal_thresholds_adjustment" in out
    assert "strategy_adjustment_suggested" in out
    assert isinstance(out["entry_filters_adjustment"], list)
    assert isinstance(out["risk_controls_adjustment"], list)
    assert isinstance(out["signal_thresholds_adjustment"], list)
    assert out["strategy_adjustment_suggested"] is True
    assert any("score_gap" in s or "minimum" in s or "阈值" in s for s in out["signal_thresholds_adjustment"])
    assert len(out["risk_controls_adjustment"]) >= 1


def test_policy_adjustment_hook():
    """adjust_policy_from_insights 在保持 policy 结构不变前提下微调 min_gap / max_replacements / turnover。"""
    policy = PortfolioDecisionPolicy(
        minimum_score_gap_for_replacement=0.3,
        max_replacements_per_rebalance=2,
        turnover_budget=0.5,
        retain_threshold=0.0,
        no_trade_if_improvement_small=False,
    )
    insights_no_suggest = ExperienceInsights(strategy_adjustment_suggested=False)
    out_unchanged = adjust_policy_from_insights(policy, insights_no_suggest)
    assert out_unchanged.minimum_score_gap_for_replacement == 0.3
    assert out_unchanged.max_replacements_per_rebalance == 2
    assert out_unchanged.retain_threshold == 0.0
    assert out_unchanged.no_trade_if_improvement_small is False

    insights_suggest = ExperienceInsights(
        frequent_replacement_failures=[{"reason": "score_gap_below_threshold", "count": 3}],
        strategy_adjustment_suggested=True,
    )
    out_adjusted = adjust_policy_from_insights(policy, insights_suggest)
    assert hasattr(out_adjusted, "minimum_score_gap_for_replacement")
    assert hasattr(out_adjusted, "max_replacements_per_rebalance")
    assert hasattr(out_adjusted, "turnover_budget")
    assert hasattr(out_adjusted, "retain_threshold")
    assert out_adjusted.retain_threshold == policy.retain_threshold
    assert out_adjusted.no_trade_if_improvement_small == policy.no_trade_if_improvement_small


def test_experience_insights_written_to_report():
    """周报包含 experience_insights：本周表现与历史对比、是否触发策略调整建议。"""
    mandate = WeeklyTradingMandate(mandate_id="m1", watchlist=["NVDA"])
    bench = BenchmarkResult(
        portfolio_return=0.01,
        benchmark_return=0.0,
        excess_return=0.01,
        max_drawdown=0.02,
        trade_count=3,
        period="day_0_to_5",
        benchmark_source="mock",
    )
    experience_insights = {
        "summary": "本周表现与历史经验对比：未触发策略调整建议。",
        "strategy_adjustment_suggested": False,
        "insights": {
            "frequent_replacement_failures": [],
            "triggers_excessive_turnover": [],
            "policies_associated_higher_excess_return": [],
            "risk_events_correlation": [],
            "strategy_adjustment_suggested": False,
        },
    }
    gen = WeeklyReportGenerator()
    report = gen.generate(
        mandate,
        bench,
        key_trades=[],
        turnover_pct=10.0,
        experience_insights=experience_insights,
    )
    assert getattr(report, "experience_insights", None) == experience_insights
    d = gen.to_dict(report)
    assert "experience_insights" in d
    assert d["experience_insights"]["summary"]
    assert "strategy_adjustment_suggested" in d["experience_insights"]
    assert "insights" in d["experience_insights"]


def test_experience_insight_snapshot_persisted():
    """write_experience_insight_snapshot 写入 experience_insight_snapshot 表。"""
    with tempfile.TemporaryDirectory() as td:
        import os
        db_path = Path(td) / "exp.db"
        os.environ["EXPERIENCE_DB_PATH"] = str(db_path)
        try:
            insights = {
                "frequent_replacement_failures": [{"reason": "score_gap", "count": 2}],
                "strategy_adjustment_suggested": True,
            }
            rid = write_experience_insight_snapshot(
                mandate_id="m1",
                period="day_0_to_5",
                insights=insights,
                db_path=db_path,
            )
            assert rid > 0
            conn = get_connection(db_path)
            cur = conn.execute(
                "SELECT insights_json FROM experience_insight_snapshot WHERE id = ?",
                (rid,),
            )
            row = cur.fetchone()
            conn.close()
            assert row is not None
            data = json.loads(row[0])
            assert data["strategy_adjustment_suggested"] is True
            assert len(data["frequent_replacement_failures"]) == 1
        finally:
            os.environ.pop("EXPERIENCE_DB_PATH", None)


def test_analyze_experience_from_store():
    """analyze_experience_from_store 从 store 读历史并返回 ExperienceInsights。"""
    with tempfile.TemporaryDirectory() as td:
        import os
        db_path = Path(td) / "exp.db"
        os.environ["EXPERIENCE_DB_PATH"] = str(db_path)
        try:
            write_weekly_portfolio_experience(
                mandate_id="m1",
                period="day_0_to_5",
                policy_snapshot={"excess_return": 0.02, "replacements_executed": 1},
                db_path=db_path,
            )
            insights = analyze_experience_from_store(
                mandate_id="m1",
                limit_weeks=10,
                db_path=db_path,
            )
            assert isinstance(insights, ExperienceInsights)
            hist = read_weekly_portfolio_experience_history(limit=5, mandate_id="m1", db_path=db_path)
            assert len(hist) >= 1
        finally:
            os.environ.pop("EXPERIENCE_DB_PATH", None)


def test_evolution_proposal_created_from_insights():
    """从 ExperienceInsights 可构建 EvolutionProposal，含 proposed_policy_adjustments、proposed_strategy_adjustments、source_insights、confidence、rationale、auto_applicable。"""
    insights = ExperienceInsights(
        frequent_replacement_failures=[{"reason": "score_gap_below_threshold", "count": 3}],
        strategy_adjustment_suggested=True,
    )
    policy = default_policy()
    proposal = build_evolution_proposal_from_insights(insights, policy, auto_applicable=True)
    assert isinstance(proposal, EvolutionProposal)
    assert "minimum_score_gap_for_replacement" in proposal.proposed_policy_adjustments
    assert "max_replacements_per_rebalance" in proposal.proposed_policy_adjustments
    assert "entry_filters_adjustment" in proposal.proposed_strategy_adjustments
    assert proposal.source_insights
    assert proposal.confidence >= 0
    assert proposal.rationale
    assert proposal.auto_applicable is True
    d = proposal.to_dict()
    assert "proposed_policy_adjustments" in d
    assert "proposed_strategy_adjustments" in d
    assert "source_insights" in d
    assert "auto_applicable" in d


def test_policy_adjustment_requires_approval_boundary():
    """Policy 调整须经 ApprovalBoundary：未 auto_applicable 或置信度不足时保持当前 policy，不直接应用。"""
    insights = ExperienceInsights(strategy_adjustment_suggested=True)
    policy = PortfolioDecisionPolicy(
        minimum_score_gap_for_replacement=0.4,
        max_replacements_per_rebalance=1,
        turnover_budget=0.4,
    )
    proposal = build_evolution_proposal_from_insights(insights, policy, auto_applicable=False)
    decision = decide_evolution(proposal, policy)
    assert isinstance(decision, EvolutionDecision)
    assert decision.approved_policy is not None
    assert decision.approved_policy.minimum_score_gap_for_replacement == 0.4
    assert decision.auto_applied is False
    assert any(r.get("type") == "policy" for r in decision.rejected_adjustments)

    proposal_auto = build_evolution_proposal_from_insights(insights, policy, auto_applicable=True, confidence_if_suggested=0.8)
    decision_auto = decide_evolution(proposal_auto, policy, auto_approve_confidence_threshold=0.5)
    assert decision_auto.auto_applied is True
    assert decision_auto.approved_policy is not None


def test_strategy_adjustment_requires_approval_boundary():
    """Strategy 调整须经 ApprovalBoundary：不自动批准，approved_strategy_adjustments 为空，拟议项在 rejected 中。"""
    insights = ExperienceInsights(
        triggers_excessive_turnover=[{"trigger_type": "opportunity_spike", "high_turnover_weeks": 2}],
        strategy_adjustment_suggested=True,
    )
    policy = default_policy()
    proposal = build_evolution_proposal_from_insights(insights, policy, auto_applicable=True)
    decision = decide_evolution(proposal, policy)
    assert decision.approved_strategy_adjustments == {} or not decision.approved_strategy_adjustments
    strategy_rejected = [r for r in decision.rejected_adjustments if r.get("type") == "strategy"]
    assert len(strategy_rejected) >= 1
    assert "adjustments" in strategy_rejected[0] or "reason" in strategy_rejected[0]


def test_weekly_report_records_proposed_vs_approved_evolution():
    """周报区分 proposed_evolution、approved_evolution、rejected_evolution。"""
    mandate = WeeklyTradingMandate(mandate_id="m1", watchlist=["NVDA"])
    bench = BenchmarkResult(
        portfolio_return=0.0,
        benchmark_return=0.0,
        excess_return=0.0,
        max_drawdown=0.0,
        trade_count=0,
        period="day_0_to_5",
        benchmark_source="mock",
    )
    proposed_evolution = {"proposed_policy_adjustments": {"minimum_score_gap_for_replacement": 0.25}, "auto_applicable": False}
    approved_evolution = {"approved_policy": {"minimum_score_gap_for_replacement": 0.3}, "auto_applied": False}
    rejected_evolution = [{"type": "policy", "reason": "未启用自动应用"}]
    gen = WeeklyReportGenerator()
    report = gen.generate(
        mandate,
        bench,
        key_trades=[],
        turnover_pct=0.0,
        proposed_evolution=proposed_evolution,
        approved_evolution=approved_evolution,
        rejected_evolution=rejected_evolution,
    )
    assert getattr(report, "proposed_evolution", None) == proposed_evolution
    assert getattr(report, "approved_evolution", None) == approved_evolution
    assert getattr(report, "rejected_evolution", None) == rejected_evolution
    d = gen.to_dict(report)
    assert "proposed_evolution" in d
    assert "approved_evolution" in d
    assert "rejected_evolution" in d
    assert d["rejected_evolution"][0]["type"] == "policy"
