# NautilusTrader 迁移规划

本文档说明当前仓库中「Strategy → Backtest / Paper / Live」与 NautilusTrader 的对应关系，以及迁移的现状与下一步。与 [CURRENT_STATE.md](CURRENT_STATE.md) 的 P2 方案 A、[restructuring_plan.md](restructuring_plan.md) Phase 3–5 一致。

---

## 1. 现状概览

| 路径 | 当前实现 | 目标 |
|------|----------|------|
| **Strategy → Backtest** | 已用 NautilusTrader：`backtest/runner.run_backtest` → BacktestNode、AISignalStrategy、ParquetDataCatalog；`backtest_pipe` 串联 Research → Contract → Translator → run_backtest → Experience Store。 | 保持。 |
| **Strategy → Paper** | **已迁移**：默认由 NautilusTrader 短窗口回测执行（`run_paper_simulation` + `NautilusPaperRunner`），与回测同一套 AISignalStrategy；`PaperRunner` 默认委托 `NautilusPaperRunner`，`use_nautilus=False` 时仍可用本仓 PaperTradingEngine（过渡层，将废弃）。 | 已完成。 |
| **Strategy → Live** | 实盘前清单见 [live_readiness_checklist.md](live_readiness_checklist.md)；IBKR 配置见 [dev_prerequisites.md](dev_prerequisites.md)、[deferred_authorization.md](deferred_authorization.md)。 | NautilusTrader LiveNode + IBKR 适配器。 |

**结论**：回测链与 Paper 链均已完成 NautilusTrader 迁移；Live 待实盘清单通过后接入。

---

## 1.1 如何体验 NautilusTrader

下面几件事能直接感受到「同一套引擎在跑」：

1. **一条命令里全是 Nautilus**  
   ```bash
   python cli.py demo NVDA --mock
   ```  
   输出里的 **【3】回测结果**（sharpe、max_drawdown、pnl、trade_count）全部来自 NautilusTrader 的 BacktestNode + AISignalStrategy，不是自研计算。

2. **Paper 也是 Nautilus 在跑**  
   ```bash
   IBKR_HOST= IBKR_PORT= python cli.py paper --symbol NVDA --mock
   ```  
   看到 `message: nautilus paper: trades=... pnl=... sharpe=...` 就说明这一笔 Paper 是 Nautilus 用最近几天数据跑的一小段回测，和上面 demo 里的回测是**同一套策略代码**。

3. **拉长回测窗口看「真回测」**  
   ```bash
   python cli.py backtest NVDA --start 2024-06-01 --end 2024-12-01
   ```  
   （不加重试时可能受网络影响）这里会拉 yfinance 历史 → 写成 Nautilus 的 ParquetDataCatalog → BacktestNode 按 bar 推进、策略按事件下单，最后得到 sharpe、回撤、胜率。数据量越大，越能体会 Nautilus 的事件驱动与 catalog 流水线。  
   **若看到 trades: 0、pnl: 0**：多半是本次 Research 输出为 `wait_confirmation` 或 `watch_only`，Contract 被译成「观望」不下单，属正常；想稳定看到有交易可用 `--mock`（mock 常出 probe_small）：  
   `python cli.py backtest NVDA --mock --start 2024-06-01 --end 2024-12-01`。

4. **代码里看「谁在干活」**  
   - 策略逻辑：[strategy/ai_signal.py](../src/ai_trading_research_system/strategy/ai_signal.py) 继承的是 Nautilus 的 `Strategy`，`on_bar` 里按 Contract 转成的 signal 下单。  
   - 回测/Paper 入口：[backtest/runner.py](../src/ai_trading_research_system/backtest/runner.py) 里的 `BacktestNode(configs=[run_config]).run()` 和 `run_paper_simulation()`，用的都是同一套配置与策略。

**一句话**：demo 的回测、paper 的「模拟」、以及将来的 Live，都是同一套 NautilusTrader + AISignalStrategy；你改策略逻辑一处，回测 / Paper / 日后实盘行为一致（backtest–live parity）。

---

## 2. 已迁移部分（回测链）

- **backtest/runner.py**：使用 NautilusTrader 的 BacktestNode、BacktestRunConfig、ParquetDataCatalog、BarDataWrangler；策略为 `AISignalStrategy`（ImportableStrategyConfig），信号来自 `ContractTranslator.translate(contract)` 产出的 `AISignal`。
- **strategy/ai_signal.py**：NautilusTrader `Strategy` 子类，按 `action`、`allowed_position_size` 等下单。
- **strategy/translator.py**：DecisionContract → AISignal（与 RuleEngine 规则对齐，供 Nautilus 策略使用）。
- **pipeline/backtest_pipe.py**：Research → Contract → Translator → run_backtest → Experience Store，无本仓执行层。

可选收口（非必须）：数据目录约定（catalog 路径、清理策略）、策略配置（如 notional、bar_type）与 [strategy_spec.md](strategy_spec.md) 的长期约定对齐。

---

## 3. 待迁移部分

### 3.1 Paper 执行层（已完成）

- **实现**：`backtest/runner.run_paper_simulation(symbol, signal, lookback_days=5)` 对最近 N 天跑 Nautilus 回测；`execution/nautilus_paper_runner.NautilusPaperRunner` 实现与 `PaperRunner` 相同接口，`run_once(price)` 内部调用 `run_paper_simulation`。`PaperRunner` 默认 `use_nautilus=True`，委托 `NautilusPaperRunner`；`use_nautilus=False` 时仍使用本仓 `PaperTradingEngine`（过渡层）。
- **验收**：`python cli.py paper --symbol NVDA --mock`（且未配置 IBKR_*）输出含 `nautilus paper: trades=...` 即走 Nautilus 路径。

### 3.2 Live 执行层（实盘前）

- **当前**：IBKR 已支持，配置见 [dev_prerequisites.md](dev_prerequisites.md)；实盘清单见 [live_readiness_checklist.md](live_readiness_checklist.md)。
- **目标**：LiveRunner 基于 NautilusTrader TradingNode + IBKR 适配器；通过 [live_readiness_checklist.md](live_readiness_checklist.md) 后再上线。

### 3.3 过渡层标注（文档已落实）

- [CURRENT_STATE.md](CURRENT_STATE.md) 已标明：RuleEngine、PortfolioEngine、PaperTradingEngine、当前 backtest runner 为过渡层；长期保留 ResearchOrchestrator、DecisionContract、ContractTranslator、Experience Store、CLI/control、openclaw 约定。迁移时只替换执行与组合管理，不替换研究层与契约格式。

---

## 4. 建议执行顺序（与 P2 方案 A 对齐）

1. **收口回测链**：已通过 `run_paper_simulation` 与默认 catalog 路径收口。
2. **Paper 迁至 Nautilus**：已完成；`PaperRunner` 默认走 `NautilusPaperRunner`。
3. **Live 就绪**：在实盘清单通过后，接 NautilusTrader LiveNode + IBKR。

不并行大改 Research、Execution、Experience；先完成 Paper 迁移再推进 Live，与 CURRENT_STATE 的「先硬替换一个过渡层」一致。

---

## 5. 默认行为说明（Migration note）

- **默认主线**：所有与 Paper 相关的入口（CLI `paper`、`run_paper.py`）均**默认 use_nautilus=True**，即由 NautilusTrader 短窗口回测执行；无需配置即可走 Nautilus。
- **过渡路径**：本仓 PaperTradingEngine 仅在**显式传入 use_nautilus=False** 时使用（代码层 opt-in），无 silent fallback；文档与日志中标注为 fallback / legacy，后续将废弃。
- **一致性**：README、CURRENT_STATE、mock_vs_real、本文档均以「默认 Nautilus、本仓引擎为过渡层」表述一致。

---

## 6. 参考

- [CURRENT_STATE.md](CURRENT_STATE.md) — 当前状态与下一步优先级（P2 方案 A）
- [restructuring_plan.md](restructuring_plan.md) — NautilusTrader + 经验闭环、Phase 3–5
- [architecture.md](architecture.md) — 分层与目标架构
- [live_readiness_checklist.md](live_readiness_checklist.md) — 实盘前清单
- [deferred_authorization.md](deferred_authorization.md) — IBKR / OpenClaw 配置与对接
