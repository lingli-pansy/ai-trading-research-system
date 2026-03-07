# NautilusTrader 迁移与执行现状

回测与 Paper 已统一到 NautilusTrader；Live 待实盘清单通过后接入。当前实现详见 [../operations/current_state.md](../operations/current_state.md)。

---

## 现状概览

| 路径 | 当前实现 |
|------|----------|
| Strategy to Backtest | NautilusTrader：backtest/runner.run_backtest；backtest_pipe 串联 Research 到 ExperienceStore。 |
| Strategy to Paper | 默认 Nautilus 短窗口回测（run_paper_simulation + NautilusPaperRunner），与 backtest 同一套 AISignalStrategy。 |
| Strategy to Live | 实盘前清单见 [../archive/live_readiness_checklist.md](../archive/live_readiness_checklist.md)。 |

---

## 如何体验

- Demo：`python cli.py demo NVDA --mock`
- Paper：`python cli.py paper --symbol NVDA --mock`
- Backtest：`python cli.py backtest NVDA [--start] [--end] [--mock]`

---

## 参考

完整迁移规划：[../archive/nautilus_migration.md](../archive/nautilus_migration.md)。Paper 说明：[paper_trading.md](paper_trading.md)。
