# OpenClaw 集成

通过 OpenClaw 触发 research / backtest / demo；报告格式与 **ResultSchema** 对齐。

---

## 入口

- **CLI**：`python cli.py research|backtest|demo|paper|weekly-paper [SYMBOL] [--mock] [--llm]`
- **weekly-paper (UC-09)**：`python cli.py weekly-paper [--capital 10000] [--benchmark SPY] [--days 5] [--mock]`；或 `python scripts/run_weekly_autonomous_paper.py --capital 10000 --benchmark SPY`。stdout 仅 JSON：ok, mandate_id, status, capital_limit, benchmark, engine_type, used_nautilus, report_path, summary。
- **OpenClaw command**：`weekly_autonomous_paper`；args: capital, benchmark, duration_days, auto_confirm。Skill 可调用 `execute(RoutedCommand("weekly_autonomous_paper", ...))` 或上述 CLI。
- **run_for_openclaw**：`python scripts/run_for_openclaw.py research|backtest|demo [SYMBOL] [--mock]`，stdout 单条 JSON。

---

## 报告格式（核心字段）

- task, symbol, completed_at, contract_action, contract_confidence, thesis_snippet, raw_contract
- engine_type, used_nautilus, status, reason（no_trade 时 reason=wait_confirmation 等）
- 完整字段见 **ResultSchema**：[../core_concepts/result_schema.md](../core_concepts/result_schema.md)

---

## 参考

- 完整说明与程序化调用：[../archive/openclaw_integration.md](../archive/openclaw_integration.md)
- CLI 用法：[cli_usage.md](cli_usage.md)
