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

**治理与变更记录**（控制面/命令面收口结果）：[control_plane_governance_result.md](control_plane_governance_result.md)、[command_surface_governance_result.md](command_surface_governance_result.md)。

控制面：CLI / OpenClaw → `application.command_registry` → `application.commands`。命令元数据 **single source of truth** 为 `openclaw/registry.py`（canonical、aliases、schema、handler_target）；契约与 schema 见 `openclaw/contract.py`；persona、skills 见同目录 persona.md、skills.md。`control/` 已删除。

---

## 历史与参考

历史与迁移、长文档在 [archive/](archive/) 内，不删除，仅作参考。
