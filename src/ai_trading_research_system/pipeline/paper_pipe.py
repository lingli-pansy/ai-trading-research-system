"""
Paper pipeline: Research → Contract → Translator → 注入 PaperRunner。
"""
from __future__ import annotations

from dataclasses import dataclass

from ai_trading_research_system.research.orchestrator import ResearchOrchestrator
from ai_trading_research_system.research.schemas import DecisionContract
from ai_trading_research_system.strategy.translator import ContractTranslator, AISignal
from ai_trading_research_system.execution.paper_runner import PaperRunner, PaperRunnerResult


@dataclass
class PaperPipeResult:
    contract: DecisionContract
    signal: AISignal
    runner_result: PaperRunnerResult | None = None


def run(
    symbol: str,
    *,
    use_mock: bool = False,
    use_llm: bool = False,
) -> PaperPipeResult:
    """
    Research → Contract → Translator，返回 contract 与 signal，供注入 Runner。
    """
    orchestrator = ResearchOrchestrator(use_mock=use_mock, use_llm=use_llm)
    contract = orchestrator.run(symbol)
    signal = ContractTranslator().translate(contract)
    return PaperPipeResult(contract=contract, signal=signal)


def run_and_inject(
    symbol: str,
    runner: PaperRunner,
    price: float,
    *,
    use_mock: bool = False,
    use_llm: bool = False,
) -> PaperPipeResult:
    """
    Research → Contract → Translator → 注入 runner → start → run_once(price) → 返回结果。
    """
    res = run(symbol=symbol, use_mock=use_mock, use_llm=use_llm)
    runner.inject(res.signal)
    runner.start()
    runner_result = runner.run_once(price)
    runner.stop()
    return PaperPipeResult(contract=res.contract, signal=res.signal, runner_result=runner_result)
