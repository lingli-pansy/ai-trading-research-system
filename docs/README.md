# AI Trading Research System — 文档入口

本文档为 **docs** 统一入口；新人建议按下列顺序阅读。

---

## Project Overview

- **目标**：AI 驱动的自主交易研究系统（研究 → 策略 → 回测/Paper/Live → 经验 → 策略进化）。
- **当前**：Research、Backtest、Paper、OpenClaw 已跑通；架构与当前状态分离：**architecture/** 仅目标架构，**operations/** 仅当前实现。
- 仓库根 [README 快速开始](../README.md#快速开始) 与 [operations/current_state.md](operations/current_state.md) 为最快上手路径。

---

## Architecture（目标架构）

| 文档 | 说明 |
|------|------|
| [architecture/system_architecture_overview.md](architecture/system_architecture_overview.md) | 系统架构总览、核心术语、Mermaid 图 |
| [architecture/agent_loop.md](architecture/agent_loop.md) | Agent Loop 与五层交互 |

---

## Core Concepts

| 文档 | 说明 |
|------|------|
| [core_concepts/decision_contract.md](core_concepts/decision_contract.md) | DecisionContract 规范 |
| [core_concepts/strategy_spec.md](core_concepts/strategy_spec.md) | StrategySpec 规范 |
| [core_concepts/result_schema.md](core_concepts/result_schema.md) | ResultSchema（统一结果模型） |

---

## Execution

| 文档 | 说明 |
|------|------|
| [execution/nautilus_migration.md](execution/nautilus_migration.md) | NautilusTrader 迁移与现状 |
| [execution/paper_trading.md](execution/paper_trading.md) | Paper Trading 入口与流程 |

---

## Experience Learning

| 文档 | 说明 |
|------|------|
| [experience/experience_store.md](experience/experience_store.md) | ExperienceStore 表与写入口 |
| [experience/strategy_refiner.md](experience/strategy_refiner.md) | Strategy Refiner（目标架构与占位） |

---

## Integrations

| 文档 | 说明 |
|------|------|
| [integration/openclaw_integration.md](integration/openclaw_integration.md) | OpenClaw 集成与报告格式 |
| [integration/cli_usage.md](integration/cli_usage.md) | CLI 子命令与开发前准备 |

---

## Operations（当前实现与运维）

| 文档 | 说明 |
|------|------|
| [operations/current_state.md](operations/current_state.md) | **当前状态总表**（能跑通什么、mock、过渡层、下一步） |
| [operations/mock_vs_real.md](operations/mock_vs_real.md) | Mock 与真实实现对照 |
| [operations/verify_scripts.md](operations/verify_scripts.md) | 验证脚本列表 |

---

## 统一术语

文档中统一使用：**DecisionContract**、**StrategySpec**、**ResultSchema**、**ExperienceStore**、**PortfolioController**、**TradingMandate**、**AccountSnapshot**。避免同义多词。

---

## Archive（历史参考）

历史与迁移、长文档、产品/路线类文档在 [archive/](archive/) 内，不删除，仅作参考。包含：restructuring_plan、architecture（旧）、decision_contract/strategy_spec/result_schema/experience_schema/next_phase（完整版）、nautilus_migration/openclaw_integration/CURRENT_STATE/mock_vs_real（完整版）、mvp_plan、PRD、AGENT_WORK_GUIDE、live_readiness_checklist、dev_prerequisites、deferred_authorization、scheduling、PRIVACY_AND_GIT、User_Journey、README 等。
