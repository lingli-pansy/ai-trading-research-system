# Core Concepts（核心概念）

CLI、OpenClaw、Pipeline 统一使用的核心数据结构与约定。

---

## 1. ResultSchema（统一结果模型）

backtest / paper / demo / weekly-paper 输出字段对齐。

### 核心字段

| 字段 | 说明 |
|------|------|
| symbol | 标的 |
| action / suggested_action / confidence | 策略信号与契约 |
| trade_count | 成交笔数，0 表示未下单 |
| pnl, max_drawdown | 绩效 |
| engine_type, used_nautilus | 执行引擎 |
| status | "ok" 或 "no_trade" |
| reason | status=no_trade 时原因（如 wait_confirmation） |

### status 与 reason

- **status=ok**：正常执行，可有 trade_count=0。
- **status=no_trade**：未产生交易，非异常；reason=wait_confirmation 等。

### UC-09 周报输出（weekly-paper）

| 字段 | 说明 |
|------|------|
| ok | 是否成功 |
| mandate_id | 本次 mandate 标识 |
| status | 状态（如 completed_week） |
| capital_limit, benchmark | 资本与基准 |
| engine_type, used_nautilus | 执行引擎 |
| report_path | 周报 JSON 文件路径；分析结果、新闻、盘面指标在此文件内 |
| summary | portfolio_return, benchmark_return, excess_return, trade_count, pnl, daily_research_count, analysis_in_report |

周报文件还含 **daily_research** 数组与 **benchmark_source**（"yfinance" | "mock"）。主路径输出 JSON 含 **snapshot_source**、**market_data_source**、**benchmark_source**。

---

## 2. DecisionContract 规范

**DecisionContract** 是研究层与执行层之间的核心接口：多智能体产出研究结论，执行层只消费结构化契约。

### 用途

- 将研究结论结构化、可解释
- 供规则/Strategy Bridge 过滤与风控
- 支持回测复现与经验注入（目标架构）

### Schema（核心字段）

| 字段 | 说明 |
|------|------|
| symbol | 交易标的 |
| analysis_time | 分析时间 |
| thesis | 结论摘要 |
| key_drivers | 关键驱动 |
| supporting_evidence / counter_evidence / uncertainties | 证据与不确定性 |
| confidence | low / medium / high |
| suggested_action | forbid_trade / watch / wait_confirmation / probe_small / allow_entry |
| time_horizon | intraday / swing / position |
| risk_flags | 风险标签列表 |

扩展字段（目标架构）：strategy_params、backtest_reference、experience_basis。

---

## 3. StrategySpec 规范

**StrategySpec** 定义可复现的策略规则，由 Strategy Bridge 根据 DecisionContract 与回测验证结果产出，经 StrategyCompiler 编译为 NautilusTrader 策略。

### Schema

- strategy_id, symbol, thesis
- entry_logic, exit_logic, filters
- risk_controls（stop_loss_pct, take_profit_pct, max_position_pct）
- time_horizon（intraday | swing | position）
- regime_tag（可选）

### 与 DecisionContract 的关系

- **DecisionContract**：单次研究输出。
- **StrategySpec**：Contract + 回测/经验验证后沉淀的可执行策略规则；StrategyCompiler 将 StrategySpec 编译为 NautilusTrader Strategy。

---

## 4. Experience Store 写入口

- **模块**：`src/ai_trading_research_system/experience/writer.py`
- **接口**：`write_run_result(payload: RunResultPayload, *, db_path=None) -> int`
- **表**：strategy_run、backtest_result、trade_experience、experience_summary。

详见 [archive/experience_schema.md](archive/experience_schema.md)、[archive/next_phase_interface.md](archive/next_phase_interface.md)。
