# 当前仓库状态总表

面向新协作者与外部用户：**现在能跑通什么、哪些是 mock、哪些是过渡实现、下一步会换什么**。细节见 [mock_vs_real.md](mock_vs_real.md)、[live_readiness_checklist.md](live_readiness_checklist.md)、[mvp_plan.md](mvp_plan.md)、[restructuring_plan.md](restructuring_plan.md)。

---

## 1. 现在能跑通什么

- **最短一条命令**：`python cli.py demo NVDA`（或 `--mock` 免网络），可看到研究结论、策略生成、回测结果、交易总结四块。见 [README 快速开始](../README.md)、[dev_prerequisites.md](dev_prerequisites.md)。
- **Research**：`python cli.py research [SYMBOL] [--mock] [--llm]`，输出 DecisionContract JSON。
- **Backtest**：`python cli.py backtest [SYMBOL] [--start] [--end] [--mock] [--llm]`，Research → 回测 → Experience Store，打印指标。
- **Paper**：`python cli.py paper [--symbol SYMBOL] [--once] [--mock] [--llm]`，Research → Contract → 默认由 NautilusTrader 短窗口回测执行（与 backtest 同一套策略）；或配置 IBKR_* 后走 TWS。
- **OpenClaw 调用**：`python cli.py research NVDA --mock` 或 `python scripts/run_for_openclaw.py research NVDA --mock`，stdout 单条 JSON 报告；Skill 可调用 cli 或 control 层 API，见 [openclaw_integration.md](openclaw_integration.md)。
- **E2E 检查**：`python scripts/run_e2e_check.py NVDA --mock`，校验 Pipeline 与 Experience Store 有数据。
- **调度**：`python scripts/run_scheduled.py [--once]`，报告落盘至 REPORT_DIR。

---

## 2. 现在还是 mock 的

- **数据**：`use_mock=True` 时使用 MockDataProvider（价格、基本面、新闻全量 mock）；未配 API Key 时 LLM 为占位。
- **Research Agent**：BullThesisAgent、BearThesisAgent 等为写死内容；可与 `use_llm=True` 的 LLMResearchAgent 二选一。NewsAgent、TechnicalContextAgent、SynthesisAgent 为实逻辑，产出随输入变化。
- **IB Gateway、LLM API 已支持**：配置见 [dev_prerequisites.md](dev_prerequisites.md)；实盘/生产对接步骤见 [deferred_authorization.md](deferred_authorization.md)。

详见 [mock_vs_real.md](mock_vs_real.md)。

---

## 3. 哪些是过渡实现 / 过渡层 vs 长期保留

**过渡层（目标由 NautilusTrader + 重构 Phase 替代）**

- 本仓 **RuleEngine**、**PortfolioEngine**、**PaperTradingEngine**（`use_nautilus=False` 时仍可用；默认 Paper 已走 Nautilus 短窗口回测）。
- 当前 **backtest runner**（`backtest/runner.py`）已由 Nautilus 驱动；Paper 默认由 `run_paper_simulation` + `NautilusPaperRunner` 执行。
- 上述本仓执行模块在 [restructuring_plan.md](restructuring_plan.md) 的 Phase 1–5 中将继续收口；Live 待实盘清单通过后接 NautilusTrader LiveNode。

**长期保留（不因重构替换）**

- **ResearchOrchestrator**、**DecisionContract** 与 Contract 规范、**ContractTranslator**（规则/信号映射）。
- **Experience Store** 接口与表结构（[experience_schema.md](experience_schema.md)）、StrategySpec/Experience 规范文档。
- **CLI**（`cli.py`）、**control 层**（command_router、skill_interface）、**openclaw_integration** 约定与报告格式。
- 数据层抽象（providers）、research/agents 的接口形态（具体 Agent 实现可能由 TradingAgents Fork 替代，但 Research 层职责与输出格式保留）。

新增本仓执行层逻辑时，需区分：属于过渡层（将来由 Nautilus/重构替代）还是长期资产（接口与约定保留）。过渡 vs 长期以本文档为准；与 [restructuring_plan.md](restructuring_plan.md) Phase 替换顺序一致。

---

## 4. 下一步会替换 / 补齐的

- **实盘前 7 项**：多时间窗口回测、OOS、最小交易次数、回撤上限、纸面阶段、风控验证、券商连通性；交付物与 L1–L7 见 [live_readiness_checklist.md](live_readiness_checklist.md)。
- **Post-MVP 路线**：StrategySpec compiler、NautilusTrader adapter、Experience store 增强、TradingAgents Fork 集成、实盘就绪（IBKR Paper/Live）；阶段划分见 [mvp_plan.md](mvp_plan.md#post-mvp-路线与重构方案一致)、[restructuring_plan.md](restructuring_plan.md#5-分阶段实施)。
- **实盘/生产对接**：IBKR、OpenClaw 服务端、生产密钥、风控步骤见 [deferred_authorization.md](deferred_authorization.md)。

---

## 5. 下一步优先级（执行顺序）

- **P1（当前阶段）**：收敛首屏试用路径为一条主线（见 [README 快速开始](../README.md#快速开始)）。
- **P2**：先硬替换一个过渡层，不并行改 Research / Execution / Experience。二选一推进：
  - **方案 A**：Strategy → Backtest 链朝 NautilusTrader 适配推进；
  - **方案 B**：Research Orchestrator 朝 TradingAgents(Fork) 迁移一部分。
  优先完成 P1 后再定 P2 选 A 或 B。
- **P3**：把 OpenClaw 从「可调用脚本」升级为「标准接口层」：明确入参/出参与错误契约，由 OpenClaw/Agent 调用该层而非直接调脚本；详见 [openclaw_integration.md](openclaw_integration.md#目标标准接口层)。P3 在 P2 有进展后落地。
