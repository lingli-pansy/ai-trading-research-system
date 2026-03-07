# AI Trading Research System

AI Trading Research System 是一个面向个人交易者的 **AI 研究与决策增强系统**。

系统目标不是让 LLM 直接接管交易，而是：

- 用多智能体研究系统处理不确定信息
- 输出结构化的 `DecisionContract`
- 由规则系统做信号过滤与风险控制
- 支持 OpenClaw 作为自动运行与交互入口
- 先打通 research → signal → paper trading 的完整闭环

## 项目状态

当前仓库 **MVP 已达成**（5 条完成标准见 [mvp_plan.md](docs/mvp_plan.md#mvp-完成核对当前交付)）。**实盘前工作**见 [live_readiness_checklist.md](docs/live_readiness_checklist.md)，按清单逐项补齐后可进入实盘验证；其中 IBKR / OpenClaw 服务端 / 生产密钥等对接步骤见 [deferred_authorization.md](docs/deferred_authorization.md)。后续将按 [重构方案](docs/restructuring_plan.md) 演进为：

- **NautilusTrader**：统一回测与实盘引擎，保证 backtest-live parity
- **TradingAgents（Fork）**：主动研究、多 Agent 协作，输出 DecisionContract
- **经验闭环**：回测/实盘结果写入 Experience Store，下一轮研究注入历史经验，持续迭代决策信号
- **多市场**：先美股（yfinance + IBKR），架构预留 A 股/加密货币扩展

详见：[docs/restructuring_plan.md](docs/restructuring_plan.md)

## 核心架构（当前 MVP）

```text
User / Scheduler
      ↓
OpenClaw Control Plane
      ↓
Research Orchestrator
      ↓
TradingAgents
      ↓
Decision Contract
      ↓
Rule Engine
      ↓
Portfolio & Risk Engine
      ↓
Execution Engine
```

目标架构（重构后）见 [docs/restructuring_plan.md#2-目标架构](docs/restructuring_plan.md#2-目标架构)。

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env      # 开发前准备：配置环境变量（见 docs/dev_prerequisites.md）

export OPENAI_API_KEY=your_key_here   # 可选
python scripts/run_demo.py
```

**开发前准备**：各阶段验收前可运行 `python scripts/check_dev_prerequisites.py` 核对环境与依赖；详见 [docs/dev_prerequisites.md](docs/dev_prerequisites.md)。

**阶段 1 验收**：`pip install -e .` 后运行 `.venv/bin/python scripts/verify_stage1.py`，确认 nautilus_trader、yfinance 与 strategy/backtest/experience/pipeline 可 import（首次运行 nautilus 的 import 可能需 30–60 秒）。

## 脚本用法（Research / 回测 / Paper / 联调）

前置：环境与依赖见 [docs/dev_prerequisites.md](docs/dev_prerequisites.md)；可选 `.env` 中 `OPENAI_API_KEY` 或 `KIMI_CODE_API_KEY`（Kimi，mock 路径不调用 LLM）、`DEFAULT_SYMBOL`（默认 NVDA）。IB Gateway 已启动时可后续对接 IBKR Paper；当前 Paper 为本仓引擎试跑。

| 脚本 | 用法 | 说明 |
|------|------|------|
| **run_research** | `python scripts/run_research.py [SYMBOL] [--mock] [--llm]` | Research → 输出 Contract JSON |
| **run_backtest** | `python scripts/run_backtest.py [SYMBOL] [--start] [--end] [--mock] [--llm]` | Research → Contract → 回测 → 写 Store → 打印指标（可选 MIN_TRADE_COUNT/MAX_DRAWDOWN_PCT 校验） |
| **run_backtest_windows** | `python scripts/run_backtest_windows.py [SYMBOL] [--windows 90,180] [--oos-days N] [--mock] [--llm]` | 实盘前 L1/L2：多时间窗口回测稳定性报告、OOS 单窗口 |
| **run_pipeline** | `python scripts/run_pipeline.py [SYMBOL] [--start] [--end] [--mock] [--llm]` | 单次 Research → 回测 → Store，打印 Contract 与指标 |
| **run_paper** | `python scripts/run_paper.py [--symbol SYMBOL] [--once] [--mock] [--llm]` | Research → Contract → 本仓 Paper 或 IBKR Paper（配置 IBKR_* 时）；Kill Switch：STOP_PAPER / .paper_stop |
| **verify_ibkr** | `python scripts/verify_ibkr.py` | 实盘前 L7：验证 IBKR_HOST:IBKR_PORT 可达 |
| **run_e2e_check** | `python scripts/run_e2e_check.py [SYMBOL] [--start] [--end] [--mock] [--llm]` | 阶段 6 联调：跑 Pipeline 并校验 Experience Store 有数据 |
| **run_for_openclaw** | `python scripts/run_for_openclaw.py research\|backtest [SYMBOL] [--start] [--end] [--mock] [--llm]` | OpenClaw 可调用：执行研究或研究+回测，**stdout 输出 JSON 报告** |
| **run_scheduled** | `python scripts/run_scheduled.py [--once] [--symbol SYMBOL] [--backtest] [--mock] [--llm]` | 自动运行：单次或按间隔执行研究/回测，报告写入 `REPORT_DIR`（默认 `.reports`）；见 [docs/scheduling.md](docs/scheduling.md) |

**OpenClaw 集成**：通过子进程或 CLI 调用 `run_for_openclaw.py`，传入 `task`（research / backtest）、`symbol` 及可选参数；报告为单条 JSON，含 `task`、`symbol`、`completed_at`、`contract_action`、`contract_confidence`、`thesis_snippet`，backtest 任务另含 `sharpe`、`max_drawdown`、`trade_count`、`strategy_run_id` 等。详见 [docs/openclaw_integration.md](docs/openclaw_integration.md)。

数据与存储：行情默认 yfinance；Experience Store 默认 `.experience/experience.db`（可通过 `EXPERIENCE_DB_PATH` 覆盖）。回测历史写入临时目录 `.backtest_catalog`。

## 文档（开发入口）

所有设计文档在 `docs/` 下，**开发前请从 [docs/README.md](docs/README.md) 文档索引进入**，按「必读 → 规范 → 产品与上线」顺序阅读，避免遗漏或冲突。

| 文档 | 说明 |
|------|------|
| [docs/README.md](docs/README.md) | **文档索引**（必读/规范/产品与上线分类） |
| [docs/restructuring_plan.md](docs/restructuring_plan.md) | 重构总纲、目标架构、5 阶段实施 |
| [docs/architecture.md](docs/architecture.md) | 系统分层、模块、数据流、Tech Stack |
| [docs/decision_contract.md](docs/decision_contract.md) | DecisionContract 规范 |
| [docs/strategy_spec.md](docs/strategy_spec.md) | StrategySpec 规范 |
| [docs/experience_schema.md](docs/experience_schema.md) | Experience Store 表结构 |
| [docs/mvp_plan.md](docs/mvp_plan.md) | MVP 完成标准与 Post-MVP 路线 |
| [docs/live_readiness_checklist.md](docs/live_readiness_checklist.md) | 实盘前工作清单（L1–L7） |
| [docs/deferred_authorization.md](docs/deferred_authorization.md) | 授权就绪后对接（IBKR/OpenClaw/密钥/风控） |
| [docs/PRD.md](docs/PRD.md) | 产品需求 |

## 目录结构

```text
ai-trading-research-system/
├── docs/                  # 见上方文档表；入口为 docs/README.md
├── scripts/
├── src/
│   └── ai_trading_research_system/
│       ├── config/
│       ├── data/
│       ├── research/
│       ├── decision/
│       ├── portfolio/
│       ├── execution/
│       └── utils/
└── tests/
```

重构后的目标目录结构见 [docs/restructuring_plan.md#3-目录结构](docs/restructuring_plan.md#3-目录结构)。

## 当前包含

- `DecisionContract` 数据结构
- 一个最小可运行 `ResearchOrchestrator`
- 多个示例 Agent（mock）
- `RuleEngine`
- `PortfolioEngine`
- `PaperTradingEngine`
- 一个演示脚本：`scripts/run_demo.py`

## 后续路线（按重构方案）

1. Phase 1：基础重构与依赖（NautilusTrader、TradingAgents submodule）
2. Phase 2：TradingAgents Fork 集成与真实数据源
3. Phase 3：NautilusTrader 回测集成
4. Phase 4：经验累积与迭代闭环
5. Phase 5：实盘就绪（IBKR Paper/Live）

详见 [docs/restructuring_plan.md](docs/restructuring_plan.md)。
