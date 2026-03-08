# AI Trading Research System

AI Trading Research System 是一个面向个人交易者的 **AI 研究与决策增强系统**。

系统目标不是让 LLM 直接接管交易，而是：

- 用多智能体研究系统处理不确定信息
- 输出结构化的 `DecisionContract`
- 由规则系统做信号过滤与风险控制
- 支持 OpenClaw 作为自动运行与交互入口
- 先打通 research → signal → paper trading 的完整闭环

## 项目状态

当前仓库 **MVP 已达成**；**Phase 2（Interactive Research System）** 已达成：统一 CLI（`cli.py`）、E2E demo、control 层与 OpenClaw Skill 打通。**文档入口**：[docs/README.md](docs/README.md)。**当前状态**：[docs/operations.md](docs/operations.md)。**实盘前工作**见 [docs/archive/live_readiness_checklist.md](docs/archive/live_readiness_checklist.md)；IBKR/OpenClaw/生产密钥见 [docs/archive/deferred_authorization.md](docs/archive/deferred_authorization.md)。后续按 [docs/archive/restructuring_plan.md](docs/archive/restructuring_plan.md) 演进：

- **NautilusTrader**：统一回测与实盘引擎，保证 backtest-live parity
- **TradingAgents（Fork）**：主动研究、多 Agent 协作，输出 DecisionContract
- **经验闭环**：回测/实盘结果写入 Experience Store，下一轮研究注入历史经验，持续迭代决策信号
- **多市场**：先美股（yfinance + IBKR），架构预留 A 股/加密货币扩展

详见 [docs/README.md](docs/README.md) 与 [docs/archive/restructuring_plan.md](docs/archive/restructuring_plan.md)。

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
5. **OpenClaw 调用示例**：`python cli.py research NVDA --mock` 或 `python scripts/run_for_openclaw.py research NVDA --mock`，stdout 为单条 JSON；完整报告见 [docs/core_concepts.md](docs/core_concepts.md) 与 [docs/uc09_weekly_autonomous_paper.md](docs/uc09_weekly_autonomous_paper.md)。

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

**一句命令跑通**：`python cli.py demo NVDA` 可看到研究结论、策略生成、回测结果、交易总结四块输出。CLI 与 OpenClaw Skill 打通，见 [docs/uc09_weekly_autonomous_paper.md](docs/uc09_weekly_autonomous_paper.md) 与 [docs/operations.md](docs/operations.md)。

| 子命令 | 用法 | 说明 |
|--------|------|------|
| **demo** | `python cli.py demo [SYMBOL] [--mock] [--llm]` | E2E：研究 → 策略 → 回测 → 总结（四块） |
| **research** | `python cli.py research [SYMBOL] [--mock] [--llm]` | Research → 输出 Contract JSON |
| **backtest** | `python cli.py backtest [SYMBOL] [--start] [--end] [--mock] [--llm]` | Research → 回测 → Store，打印指标 |
| **paper** | `python cli.py paper [--symbol SYMBOL] [--once] [--mock] [--llm]` | Research → Contract → **默认 Nautilus 短窗口回测**；Kill Switch：STOP_PAPER / .paper_stop |

### OpenClaw 最快验证

无需打开集成文档即可完成一次 OpenClaw 风格调用：

```bash
python cli.py research NVDA --mock
# 或：python scripts/run_for_openclaw.py research NVDA --mock
```

- **输出**：stdout 为单条 JSON（含 task、symbol、contract_action、contract_confidence、thesis_snippet、raw_contract 等）。完整字段见 [docs/uc09_weekly_autonomous_paper.md](docs/uc09_weekly_autonomous_paper.md) 与 [docs/operations.md](docs/operations.md)。
- **验证**：退出码 0 即成功；可 pipe 到 `jq` 或 Python 解析。Skill 调用方式与报告格式见 [docs/core_concepts.md](docs/core_concepts.md)。

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

**OpenClaw 集成**：Skill 可调用 `cli.py` 或 control 层；报告格式见 [docs/uc09_weekly_autonomous_paper.md](docs/uc09_weekly_autonomous_paper.md) 与 [docs/operations.md](docs/operations.md)。

数据与存储：行情默认 yfinance；Experience Store 默认 `.experience/experience.db`（可通过 `EXPERIENCE_DB_PATH` 覆盖）。回测历史写入临时目录 `.backtest_catalog`。

## 文档（开发入口）

所有文档在 `docs/` 下，**入口为 [docs/README.md](docs/README.md)**；历史文档在 `docs/archive/`。

| 文档 | 说明 |
|------|------|
| [docs/README.md](docs/README.md) | **文档入口** |
| [docs/operations.md](docs/operations.md) | **当前状态总表**：能跑通什么、mock、过渡层、下一步 |
| [docs/system_architecture.md](docs/system_architecture.md) | 目标架构总览 |
| [docs/core_concepts.md](docs/core_concepts.md) | ResultSchema、DecisionContract、StrategySpec、Experience Store |
| [docs/uc09_weekly_autonomous_paper.md](docs/uc09_weekly_autonomous_paper.md) | UC-09 周自治 Paper |
| [docs/execution_pipeline.md](docs/execution_pipeline.md) | 执行流水线（Backtest/Paper/Live） |
| [docs/archive/](docs/archive/) | 历史文档（restructuring_plan、mvp_plan、live_readiness_checklist、PRD 等） |

## 目录结构

```text
ai-trading-research-system/
├── cli.py                 # Phase 2：统一 CLI 入口（research / backtest / paper / demo）
├── docs/                  # 入口 docs/README.md；核心文档 system_architecture、core_concepts、execution_pipeline、uc09、operations；archive/
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
