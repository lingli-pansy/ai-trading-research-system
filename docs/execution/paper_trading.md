# Paper Trading

Paper 路径默认由 NautilusTrader 短窗口回测执行，与 backtest 同一套 AISignalStrategy。

---

## 入口

```bash
python cli.py paper [--symbol SYMBOL] [--once] [--mock] [--llm]
```

默认 symbol=NVDA。配置 IBKR_* 后可走 TWS Paper。

---

## 执行流

Research 到 DecisionContract 到 ContractTranslator 到 AISignal 到 NautilusPaperRunner；结果见 [../core_concepts/result_schema.md](../core_concepts/result_schema.md)。

---

## 参考

当前状态：[../operations/current_state.md](../operations/current_state.md)。迁移说明：[nautilus_migration.md](nautilus_migration.md)。
