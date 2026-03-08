# AI Trading Research System — 文档入口

**docs** 统一入口；新人建议按顺序阅读。

---

## 核心文档

| 文档 | 说明 |
|------|------|
| [system_architecture.md](system_architecture.md) | 目标架构、核心术语、层级简述 |
| [core_concepts.md](core_concepts.md) | ResultSchema、DecisionContract、StrategySpec、Experience Store 写入口 |
| [execution_pipeline.md](execution_pipeline.md) | 执行流水线、Backtest/Paper/Live、NautilusTrader 现状 |
| [uc09_weekly_autonomous_paper.md](uc09_weekly_autonomous_paper.md) | UC-09 周自治 Paper 入口、OpenClaw、验证 |
| [operations.md](operations.md) | 当前状态、能跑通什么、Mock 与过渡、验证脚本、下一步 |

控制面：CLI / OpenClaw → `application.commands`；OpenClaw 契约见 `src/ai_trading_research_system/openclaw/contract.py`（persona、skills 见同目录 persona.md、skills.md）。`control/` 为兼容层，退场中。

---

## 历史与参考

历史与迁移、长文档在 [archive/](archive/) 内，不删除，仅作参考。
