# Mock 与真实实现对照

阶段 1–6 与 MVP 执行计划完成后，链路已跑通；Research 可选用真实数据与 LLM，本仓 Paper 与 OpenClaw 报告可用。IB Gateway、LLM API 已支持，配置见 [dev_prerequisites.md](dev_prerequisites.md)。本文档列出各模块当前状态与替换优先级。

---

## 一、按模块：实 vs Mock

| 模块 / 组件 | 当前状态 | 说明 |
|-------------|----------|------|
| **环境与依赖** | 实 | Python、venv、nautilus_trader、yfinance、openai、check_dev_prerequisites |
| **data/providers.py** |  |  |
| └ get_price(symbol) | 实（YFinanceProvider） | yfinance 拉取；失败时 fallback 到 mock 价并打 stderr |
| └ get_fundamentals(symbol) | 实 | YFinanceProvider 用 yfinance ticker.info；失败时 fallback mock |
| └ get_news(symbol) | 实 | YFinanceProvider 用 yfinance ticker.news；失败或空时 fallback mock |
| └ MockDataProvider | Mock | use_mock=True 时全量 mock（价格+基本面+新闻） |
| **research/agents/** |  |  |
| └ LLMResearchAgent | 实（可选） | use_llm=True 时调用 OpenAI，产出 evidence/thesis；无 key 时返回占位 | 
| └ NewsAgent / TechnicalContextAgent | 实逻辑 | 产出随 ResearchContext 变化（新闻条数、价格涨跌等），Synthesis 可得到不同 action |
| └ BullThesisAgent / BearThesisAgent / … | Mock | 写死内容；可与 LLM 二选一（use_llm 切换） |
| └ SynthesisAgent | 实逻辑 | 规则为真，输入可为真实聚合结果 |
| **research/orchestrator** | 实 | 支持 use_mock、use_llm；数据源与 Agent 组合可配置 |
| **Contract → 信号** | 实 | ContractTranslator、decision/rules.py，无 mock |
| **回测 / Experience / Paper 执行路径** | 实 | 历史 yfinance、Nautilus、Store、本仓 Paper 均为实；信号来自 Contract |
| **OpenClaw / 调度** | 实 | run_for_openclaw、openclaw_adapter 报告 JSON；run_scheduled 自动运行与落盘 |
| **IBKR / LLM** | 已支持 | 配置 TWS/IB Gateway 与 IBKR_*、OPENAI_API_KEY 或 KIMI_CODE_API_KEY 即可；实盘/生产步骤见 [deferred_authorization.md](deferred_authorization.md) |

---

## 二、替换优先级与状态

| 优先级 | 替换项 | 状态 | 说明 |
|--------|--------|------|------|
| **P0** | Research Agent 产出改为真实 | 已实现 | LLMResearchAgent（--llm）、Context 相关 Agent 使 Contract 随输入变化；可选真实数据 + LLM |
| **P1** | 基本面 / 新闻数据源 | 已实现 | YFinanceProvider.get_fundamentals / get_news 已接 yfinance，失败 fallback mock |
| **P2** | Paper 执行端接 IBKR（或 Nautilus Paper） | **已支持** | 配置 TWS/IB Gateway 与 IBKR_* 后可用，见 [dev_prerequisites.md](dev_prerequisites.md)、[deferred_authorization.md](deferred_authorization.md) |
| **P3** | 风控与 Kill Switch | **已实装** | 仓位上限、单日止损已接入 PaperRunner，可通过 PAPER_MAX_POSITION_PCT、PAPER_DAILY_STOP_LOSS_PCT 配置；Kill Switch 可扩展 |

**实盘/生产**：IBKR、LLM API 已支持，配置见 [dev_prerequisites.md](dev_prerequisites.md) 与 [deferred_authorization.md](deferred_authorization.md)。风控已实装。

---

## 三、相关文档

- **当前状态总表**（能跑通什么、mock、过渡层 vs 长期保留、下一步替换）：[CURRENT_STATE.md](CURRENT_STATE.md)；过渡 vs 长期以 CURRENT_STATE 为准。
- MVP 与实盘前工作：[mvp_plan.md](mvp_plan.md)、[live_readiness_checklist.md](live_readiness_checklist.md)
- 实盘前检查项：[live_readiness_checklist.md](live_readiness_checklist.md)
- 开发前准备：[dev_prerequisites.md](dev_prerequisites.md)
