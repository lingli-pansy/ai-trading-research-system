# CLI 用法

统一入口：项目根 **`cli.py`**。脚本用法见仓库根 [README 快速开始](../../README.md#快速开始)。

---

## 子命令

| 命令 | 说明 |
|------|------|
| `python cli.py research [SYMBOL] [--mock] [--llm]` | 输出 DecisionContract JSON |
| `python cli.py backtest [SYMBOL] [--start] [--end] [--mock] [--llm]` | Research → 回测 → ExperienceStore |
| `python cli.py demo [SYMBOL] [--mock] [--llm]` | E2E 四块（研究、策略、回测、总结） |
| `python cli.py paper [--symbol SYMBOL] [--once] [--mock] [--llm]` | Paper（默认 Nautilus 短窗口） |

---

## 开发前准备

- 环境与权限、数据、IBKR Paper 配置等见 [../archive/dev_prerequisites.md](../archive/dev_prerequisites.md)。
- 一键核对：`python scripts/check_dev_prerequisites.py`
