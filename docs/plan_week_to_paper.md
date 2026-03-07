# 跑通链路并 Paper 试跑 — 执行计划

**目标**：完成整条链路（Research → Contract → Nautilus 回测/Paper），在 Paper 环境试跑。

**开发前准备**：权限、数据、环境、Paper 账号等前置条件见 [dev_prerequisites.md](dev_prerequisites.md)，用于各阶段成果验收前核对。

**范围裁剪**：
- Research：保留 mock Agent，只接 **yfinance 真实行情**；不做 TradingAgents Fork。
- Experience：最小实现（SQLite + 回测结果写入 + 注入接口 stub）。
- 实盘：仅 Paper（IBKR Paper 或 Nautilus 模拟）；风控做仓位上限 + 单日止损 stub。

---

## 执行顺序与阶段验收

### 阶段 1：基础与依赖

**顺序**：先做本阶段，再做阶段 2。

**任务**：
- 新增目录：`strategy/`、`backtest/`、`experience/`、`pipeline/`（空 `__init__.py`）。
- 更新 `pyproject.toml` / `requirements.txt`：加入 `nautilus_trader`、`yfinance`，Python ≥3.12。
- 本地可运行 NautilusTrader 官方 1 个最小 Backtest 示例。

**阶段验收**：`pip install -e .` 成功；`import nautilus_trader`、`import yfinance` 无报错；上述目录可 import。

---

### 阶段 2：数据层 + Research 出 Contract

**顺序**：依赖阶段 1。

**任务**：
- `data/providers.py`：实现 **YFinanceProvider**（`get_price(symbol)` 返回行情摘要，可复用 `PriceSnapshot`）。
- ResearchOrchestrator 支持切换：`use_mock=False` 时用 YFinanceProvider 构建 ResearchContext。
- `research/schemas.py`：DecisionContract 增加可选字段 `strategy_params`、`backtest_reference`、`experience_basis`。
- 脚本 `scripts/run_research.py`：指定 symbol → Research → 打印 Contract。

**阶段验收**：`python scripts/run_research.py NVDA` 输出 Contract；现有 demo 仍可跑。

---

### 阶段 3：Contract → 信号 + Nautilus 回测

**顺序**：依赖阶段 2。

**任务**：
- `strategy/translator.py`：ContractTranslator，逻辑与现有 `decision/rules.py` 一致，输出 Nautilus 可消费的信号结构。
- `strategy/ai_signal.py`：**AISignalStrategy** 继承 NautilusTrader Strategy，按 Contract/信号发单（先只做多、固定比例仓位）。
- `backtest/runner.py`：BacktestRunner 用 BacktestNode/BacktestEngine，加载历史行情（yfinance→Catalog 或示例数据），跑 AISignalStrategy，返回 Sharpe / max_drawdown / trade_count。
- 脚本 `scripts/run_backtest.py`：symbol + 可选 date range → Research → Translator → BacktestRunner → 打印指标。

**阶段验收**：`python scripts/run_backtest.py NVDA` 输出回测指标；Contract in → 预期 action/size 在策略侧一致。

---

### 阶段 4：Experience 最小 + Pipeline 串联

**顺序**：依赖阶段 3。

**任务**：
- `experience/store.py`：SQLite，表与 [experience_schema.md](experience_schema.md) 对齐（至少 strategy_run、backtest_result）；提供 `write_backtest_result(...)`。
- 回测结束后在 runner 或脚本中调用 store 写入结果。
- `research/experience_ctx.py`：ExperienceInjector 接口 `get_context(symbol) -> str`，首周实现返回空或占位（stub）。
- `pipeline/backtest_pipe.py`：`run(symbol, start_date, end_date)` = Research → Contract → Translator → BacktestRunner → Store，返回 Contract + 回测指标。

**阶段验收**：跑一次回测后 Experience Store 中有记录；单次调用 `backtest_pipe.run()` 完成 Research+回测+存库。

---

### 阶段 5：Nautilus Paper 连接 + 试跑入口

**顺序**：依赖阶段 3、4。

**任务**：
- 确认 Paper 环境：IBKR Paper 账号 + TWS/IB Gateway 可登录，或 Nautilus Paper/Sandbox 配置。
- `execution/live_runner.py`（或 `paper_runner.py`）：封装 TradingNode，配置 IBKR 适配器为 Paper，加载 AISignalStrategy，提供 start/stop。
- `pipeline/live_pipe.py`（或 `paper_pipe.py`）：Research → Contract → Translator → 信号注入已运行的 Paper 节点（或启动时注入 Contract）。
- 脚本 `scripts/run_paper.py`：symbol → 可选 Research 取 Contract → 启动 Paper 节点并注入；支持 `--once` 或持续运行。
- AISignalStrategy 或 Runner 侧：仓位上限、单日止损 stub。

**阶段验收**：`python scripts/run_paper.py --symbol NVDA --once` 完成一次 Research+Paper 注入；启动后策略挂载成功（可不要求立刻成交）。

---

### 阶段 6：联调与试跑准备

**顺序**：阶段 1–5 完成后。

**任务**：
- 端到端：run_research → run_backtest → backtest_pipe.run() 同一 symbol 跑通，Experience 有数据。
- Paper：run_paper 连接 IBKR Paper（或 Nautilus Paper）成功，至少 1 次「Research → Contract → 策略收到信号」。
- 更新 [live_readiness_checklist.md](live_readiness_checklist.md)：已达成项勾选，未达成注明后续补齐。
- README 或 docs：补充 `run_research.py`、`run_backtest.py`、`run_paper.py` 用法与前提（环境变量、IBKR 登录等）。

**阶段验收**：全链路无报错；可按文档在 Paper 环境试跑。

---

## 风险与回退

| 风险 | 缓解 |
|------|------|
| IBKR Paper 连接失败 | 回测用 Nautilus；Paper 先用本仓自研 `PaperTradingEngine` 做「Research → Contract → 脚本调 Paper」试跑，IBKR 后续补。 |
| Nautilus 历史数据耗时 | 先用 1 个月或官方示例数据跑通 BacktestRunner，再扩 yfinance 全量。 |
| 时间紧 | 优先保：阶段 1–3 + `run_backtest.py`；Paper 用自研 Paper 引擎作最小试跑。 |

---

## 涉及文件

- 新增/修改：`strategy/translator.py`、`strategy/ai_signal.py`、`backtest/runner.py`、`experience/store.py`、`research/experience_ctx.py`、`pipeline/backtest_pipe.py`、`execution/paper_runner.py`（或 `live_runner.py`）、`pipeline/paper_pipe.py`；脚本 `run_research.py`、`run_backtest.py`、`run_paper.py`。
- 文档：本计划、[dev_prerequisites.md](dev_prerequisites.md)、[live_readiness_checklist.md](live_readiness_checklist.md)、[experience_schema.md](experience_schema.md)。
