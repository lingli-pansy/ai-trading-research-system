# Execution Pipeline（执行流水线）

执行层统一由 NautilusTrader 承载；回测与 Paper 已按此实现，Live 待实盘清单通过后接入。

---

## 高层流（Mermaid）

```mermaid
flowchart LR
    Contract["DecisionContract"]
    Signal["AISignal / StrategySpec"]
    Engine["NautilusTrader Engine"]
    Result["Result Schema"]

    Contract --> Signal
    Signal --> Engine
    Engine --> Result
```

- **Backtest**：Research → Contract → Translator → run_backtest → ExperienceStore。
- **Paper**：同上，run_paper_simulation（短窗口）。
- **Live**：目标 NautilusTrader LiveNode + IBKR 适配器。

---

## 控制面主线

- **入口**：CLI（`presentation/cli.py`）或 OpenClaw（`scripts/run_for_openclaw.py` → `openclaw.adapter`）。
- **业务**：全部由 `application.commands` 执行；control/ 为兼容层，不再作为主入口。

## 现状概览

| 路径 | 当前实现 |
|------|----------|
| Strategy to Backtest | NautilusTrader：backtest/runner.run_backtest；backtest_pipe 串联 Research 到 ExperienceStore。 |
| Strategy to Paper | 默认 Nautilus 短窗口回测（run_paper_simulation + NautilusPaperRunner），与 backtest 同一套 AISignalStrategy。 |
| Strategy to Live | 实盘前清单见 [archive/live_readiness_checklist.md](archive/live_readiness_checklist.md)。 |

---

## Paper Trading 入口

```bash
python cli.py paper [--symbol SYMBOL] [--once] [--mock] [--llm]
```

默认 symbol=NVDA。配置 IBKR_* 后可走 TWS Paper。执行流：Research → DecisionContract → ContractTranslator → AISignal → NautilusPaperRunner；结果见 [core_concepts.md](core_concepts.md)。

---

## 参考

- 迁移与验收：[archive/nautilus_migration.md](archive/nautilus_migration.md)
- 当前状态：[operations.md](operations.md)
