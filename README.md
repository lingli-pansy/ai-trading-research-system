# AI Trading Research System

面向个人交易者的 **AI 研究与决策增强系统**：多智能体研究输出 `DecisionContract`，由规则/风控/组合引擎落地，**先打通 research → signal → paper trading 闭环**，支持 **OpenClaw** 作为自动运行入口。

**→ 当前该跑什么、结果在哪、replay 看哪**：见 **[docs/current-path.md](docs/current-path.md)**（优先阅读）。

---

## 当前目标与主路径

- **Canonical path**：`autonomous_paper_cycle`（单周期：读组合 → 研究 → 规则/风控 → RebalancePlan → 订单意图/执行 → 落盘）。
- **OpenClaw 用户入口**：用户 4 个动作（开始建仓/查看组合/调仓建议/确认执行）走 **handle_trading_intent_sync**；说明见 **AGENTS.md**、**docs/mvp-boundary.md**、**docs/openclaw-project-setup.md**。开发/调试：`openclaw-agent-once`、`openclaw-approver-smoke`。
- **Paper trading 推荐命令**：`python -m ai_trading_research_system.presentation.cli paper-cycle --symbols NVDA [--mock]`。
- **状态与 artifact 存放**：**runs/** 下 `runs/<run_id>/`（snapshots、artifacts、execution、audit）；统一经 **state.RunStore** 读写。

详见 [docs/current-path.md](docs/current-path.md)、[docs/system_architecture.md](docs/system_architecture.md)、[docs/operations.md](docs/operations.md)。

## 项目状态（历史阶段说明已下沉至 archive）

MVP / Phase 2 已达成；当前以 **autonomous paper trading 收敛 + OpenClaw agent 稳定入口** 为主。历史规划与清单见 [docs/archive/](docs/archive/)。

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

目标架构见 [docs/system_architecture.md](docs/system_architecture.md)。

## 快速开始

### 首屏试用一条主线（按顺序执行）

1. **环境**：`pip install -e .`（可选：venv、`cp .env.example .env`，见 [docs/operations.md](docs/operations.md)）。
2. **前置检查**：`python scripts/check_dev_prerequisites.py`。
3. **Demo**：`python cli.py demo NVDA --mock`，可见四块：研究结论、策略生成、回测结果、交易总结；输出中会标明「执行引擎: NautilusTrader」。
4. **E2E 校验**：`python scripts/run_e2e_check.py NVDA --mock`，校验 Pipeline 跑通且 Experience Store 有写入。
5. **OpenClaw 用户入口 smoke**：`openclaw-trading-intent-sync --message-json '{"message":"开始建仓"}'`；开发联调：`openclaw-agent-once`、`openclaw-approver-smoke`。详见 [AGENTS.md](AGENTS.md)、[docs/openclaw-project-setup.md](docs/openclaw-project-setup.md)、[docs/mvp-boundary.md](docs/mvp-boundary.md)。

**可选**：`python cli.py research NVDA --mock` 查看 Contract JSON；使用真实数据或 LLM 见下方命令示例。

### 命令示例

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env      # 开发前准备（见 docs/operations.md）

# 推荐：一句命令跑通 E2E（研究结论 → 策略生成 → 回测结果 → 交易总结）
python cli.py demo NVDA

# 可选：使用真实数据或 LLM
export OPENAI_API_KEY=your_key_here
python cli.py demo NVDA --llm
```

**兼容用法**：仍可使用 `python scripts/run_demo.py`、`scripts/run_research.py` 等脚本，与 `cli.py` 子命令对应关系见下方「统一 CLI」。

**开发前准备**：运行 `python scripts/check_dev_prerequisites.py` 核对环境；详见 [docs/operations.md](docs/operations.md)。

**阶段 1 验收**：`pip install -e .` 后运行 `.venv/bin/python scripts/verify_stage1.py`，确认 nautilus_trader、yfinance 与 strategy/backtest/experience/pipeline 可 import（首次运行 nautilus 的 import 可能需 30–60 秒）。

## 统一 CLI（Phase 2 推荐入口）

**一句命令跑通**：`python cli.py demo NVDA` 或 `python cli.py paper-cycle --symbols NVDA --mock`。CLI 与 OpenClaw 见 [docs/current-path.md](docs/current-path.md)、[docs/operations.md](docs/operations.md)。

| 子命令 | 用法 | 说明 |
|--------|------|------|
| **paper-cycle** | `python cli.py paper-cycle [--symbols A,B] [--mock] [--run_id ID]` | **推荐**：单周期 autonomous paper，落盘 runs/，含 rebalance_plan / portfolio_after |
| **demo** | `python cli.py demo [SYMBOL] [--mock] [--llm]` | E2E：研究 → 策略 → 回测 → 总结（四块） |
| **research** | `python cli.py research [SYMBOL] [--mock] [--llm]` | Research → 输出 Contract JSON |
| **backtest** | `python cli.py backtest [SYMBOL] [--start] [--end] [--mock] [--llm]` | Research → 回测 → Store，打印指标 |
| **paper** | `python cli.py paper [--symbol SYMBOL] [--mock] [--llm]` | 兼容：内部复用 paper-cycle；Kill Switch：STOP_PAPER / .paper_stop |

### OpenClaw 最快验证

无需打开集成文档即可完成一次 OpenClaw 风格调用：

```bash
python cli.py research NVDA --mock
# 或：python scripts/run_for_openclaw.py research NVDA --mock
```

- **输出**：stdout 为单条 JSON（含 task、run_id、rebalance_plan、order_intents 等）。字段与 Skill 调用见 [docs/current-path.md](docs/current-path.md)、[docs/operations.md](docs/operations.md)。
- **验证**：退出码 0 即成功；可 pipe 到 `jq` 解析。

## 脚本用法（兼容 / 高级）

前置：环境与依赖见 [docs/operations.md](docs/operations.md)；可选 `.env` 中 OPENAI_API_KEY 或 KIMI_CODE_API_KEY。上述 CLI 子命令与下列脚本对应，可按需选用。

| 脚本 | 用法 | 对应 CLI |
|------|------|----------|
| **run_research** | `python scripts/run_research.py [SYMBOL] [--mock] [--llm]` | `cli.py research` |
| **run_backtest** | `python scripts/run_backtest.py [SYMBOL] [--start] [--end] [--mock] [--llm]` | `cli.py backtest` |
| **run_pipeline** | `python scripts/run_pipeline.py [SYMBOL] [--start] [--end] [--mock] [--llm]` | `cli.py backtest`（同 pipeline） |
| **run_paper** | `python scripts/run_paper.py [--symbol SYMBOL] [--once] [--mock] [--llm]` | `cli.py paper` |
| **run_for_openclaw** | `python scripts/run_for_openclaw.py research\|backtest [SYMBOL] [--mock] [--llm]` | `cli.py research` / `cli.py backtest`（stdout JSON） |
| **run_backtest_windows** | `python scripts/run_backtest_windows.py [SYMBOL] [--windows] [--oos-days] [--mock] [--llm]` | 实盘前 L1/L2 多窗口回测 |
| **run_e2e_check** | `python scripts/run_e2e_check.py [SYMBOL] [--start] [--end] [--mock] [--llm]` | 阶段 6 联调、Experience Store 校验 |
| **run_scheduled** | `python scripts/run_scheduled.py [--once] [--symbol SYMBOL] [--backtest] [--mock] [--llm]` | 自动运行，见 [docs/archive/scheduling.md](docs/archive/scheduling.md) |
| **verify_ibkr** | `python scripts/verify_ibkr.py` | 实盘前 L7：IBKR 连通性 |

**OpenClaw 集成**：Skill 应调用 `cli.py` 或 `scripts/run_for_openclaw.py`（背后为 `openclaw.adapter`）；报告格式与契约见 [docs/operations.md](docs/operations.md)、`openclaw/contract.py`；control 为兼容层，退场中。

数据与存储：行情默认 yfinance；Experience Store 默认 `.experience/experience.db`（可通过 `EXPERIENCE_DB_PATH` 覆盖）。回测历史写入临时目录 `.backtest_catalog`。

## 文档（开发入口）

文档在 `docs/` 下，**入口 [docs/README.md](docs/README.md)** 仅列核心 4 篇；过程与历史在 [docs/archive/](docs/archive/)。

| 文档 | 说明 |
|------|------|
| [docs/README.md](docs/README.md) | **文档入口**（仅列核心） |
| [docs/current-path.md](docs/current-path.md) | **当前路径**：主入口、OpenClaw、paper、replay |
| [docs/system_architecture.md](docs/system_architecture.md) | 目标架构、数据落盘 |
| [docs/operations.md](docs/operations.md) | 能跑通什么、mock、验证、报告位置 |
| [docs/core_concepts.md](docs/core_concepts.md) | DecisionContract、StrategySpec、Experience Store |
| [docs/archive/](docs/archive/) | 历史与过程文档（不再维护） |

## 目录结构

```text
ai-trading-research-system/
├── cli.py                 # Phase 2：统一 CLI 入口（research / backtest / paper / demo）
├── docs/                  # 入口 docs/README.md；核心 current-path、system_architecture、operations、core_concepts；archive/ 为历史
├── scripts/
├── src/
│   └── ai_trading_research_system/
│       ├── config/
│       ├── application/   # Control Plane：commands（research_symbol、backtest_symbol、run_demo、weekly_paper、generate_weekly_report）
│       ├── presentation/  # CLI：参数解析 + 调用 application.commands + 打印
│       ├── openclaw/      # OpenClaw：adapter、persona、skills、commands 映射
│       ├── services/      # UC-09：benchmark_service、report_service、experience_service
│       ├── control/       # command_router、skill_interface（与 OpenClaw 打通）
│       ├── data/
│       ├── research/
│       ├── decision/
│       ├── portfolio/
│       ├── execution/
│       └── utils/
└── tests/
```

重构后的目标目录结构见 [docs/archive/restructuring_plan.md](docs/archive/restructuring_plan.md)。

## 当前包含

- **统一 CLI**（`cli.py`）：research / backtest / paper / demo，与 OpenClaw Skill 对齐
- **control 层**：`command_router`（意图→子命令）、`skill_interface`（执行并返回 JSON 报告）
- `DecisionContract` 数据结构
- 一个最小可运行 `ResearchOrchestrator`
- 多个示例 Agent（mock）
- `RuleEngine`、`PortfolioEngine`、`PaperTradingEngine`
- 演示：`python cli.py demo NVDA` 或 `scripts/run_demo.py`

## 后续路线（按重构方案）

1. Phase 1：基础重构与依赖（NautilusTrader、TradingAgents submodule）
2. Phase 2：TradingAgents Fork 集成与真实数据源
3. Phase 3：NautilusTrader 回测集成
4. Phase 4：经验累积与迭代闭环
5. Phase 5：实盘就绪（IBKR Paper/Live）

详见 [docs/archive/restructuring_plan.md](docs/archive/restructuring_plan.md)。
