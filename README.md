# AI Trading Research System

AI Trading Research System 是一个面向个人交易者的 **AI 研究与决策增强系统**。

系统目标不是让 LLM 直接接管交易，而是：

- 用多智能体研究系统处理不确定信息
- 输出结构化的 `DecisionContract`
- 由规则系统做信号过滤与风险控制
- 支持 OpenClaw 作为自动运行与交互入口
- 先打通 research → signal → paper trading 的完整闭环

## 项目状态

当前仓库是 **MVP skeleton**。后续将按 [重构方案](docs/restructuring_plan.md) 演进为：

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
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export OPENAI_API_KEY=your_key_here   # 可选
python scripts/run_demo.py
```

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
| [docs/live_readiness_checklist.md](docs/live_readiness_checklist.md) | 实盘前检查项 |
| [docs/mvp_plan.md](docs/mvp_plan.md) | MVP 8 周 + Post-MVP 路线 |
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
