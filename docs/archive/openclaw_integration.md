# OpenClaw 集成说明

本文说明如何通过 OpenClaw 触发研究或研究+回测任务，以及报告格式。

---

## 目标：标准接口层

**现状**：OpenClaw 通过 `run_for_openclaw.py` 或 `cli.py` 子进程调用本仓，已有报告格式与本文档约定。

**目标**：从「可调用脚本」升级为**标准接口层**，明确承接：

- **调用方**：OpenClaw Agent / Skill 或其他上游（如调度、HTTP 网关）。
- **契约**：入参（如 task、symbol、start/end、use_mock/use_llm）、出参（JSON 报告结构、错误码/超时约定）、调用方式（子进程 CLI 或薄 HTTP/本地 API）。
- **职责**：本仓提供稳定接口层，上游只依赖契约而非具体脚本路径；脚本或 control 层作为该接口的一种实现。

**本阶段**：仅文档约定目标；具体是「子进程 + 契约文档」还是「新增 HTTP/API」在后续阶段选定。当前 `run_for_openclaw.py` 与 `cli.py` 已满足子进程调用与报告格式，与上述目标兼容。

---

## 交互形态与 Skill 打通

**最终交互形态**：用户通过 **OpenClaw Agent**（聊天或命令）与系统交互，而非直接执行本仓脚本。例如用户说「analyse NVDA」「run backtest」「show experience」，由 OpenClaw Agent 理解意图并驱动本系统执行。

**CLI 与 Skill 打通**：本仓提供统一 CLI 入口（如 `cli.py` 或等价命令），与 **OpenClaw Skill** 对齐：

- **Skill** 作为 OpenClaw 侧的能力封装，通过调用本仓 CLI（或与 CLI 共用同一套命令/接口）执行 research、backtest、paper、demo 等；
- CLI 设计时需保证：命令形式、参数、stdout/报告格式与 OpenClaw Skill 的入参/出参一致，便于 Agent 调用 Skill 即完成一次完整能力调用；
- 这样既保留本地「一条命令跑通」的体验，又保证 OpenClaw Agent 通过 Skill 获得同一套能力。

**若 OpenClaw 已安装到本地**：可在 OpenClaw 中配置 Skill 调用本仓库的 CLI（或当前过渡方案：`run_for_openclaw.py` / `run_scheduled.py`），传入 symbol、task 等参数，从 stdout 或 REPORT_DIR 获取 JSON 报告。IB Gateway 已支持，配置后即可对接实盘/Paper 下单；配置见 [dev_prerequisites.md](dev_prerequisites.md)。

---

## Skill 调用方式（与 CLI 打通）

OpenClaw Skill 可通过两种方式调用本仓，入参/出参与 CLI 及现有报告格式一致：

**方式 A：子进程调用统一 CLI（推荐）**

在 Skill 中执行项目根目录下的 `cli.py`，子命令与参数与本地使用一致：

```bash
python cli.py research NVDA [--mock] [--llm]
python cli.py backtest NVDA [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--mock] [--llm]
python cli.py demo NVDA [--mock] [--llm]
python cli.py paper [--symbol NVDA] [--once] [--mock] [--llm]
```

- `research`：stdout 为 DecisionContract JSON；若 Skill 需要与 `run_for_openclaw.py` 相同的报告结构，可改用方式 B 或调用 `run_research_report()`。
- `backtest` / `demo`：若需机器可读的 JSON，建议用方式 B；否则可直接解析 CLI 的 stdout 文本。

**方式 B：Python API（推荐 openclaw.adapter）**

Skill 通过 HTTP 或本地调用本仓 Python API 时，**推荐直接使用 openclaw.adapter**（与 `run_for_openclaw.py` 一致，契约见 `openclaw/contract.py`）：

```python
from ai_trading_research_system.openclaw.adapter import (
    run_research_report,
    run_backtest_report,
    run_demo_report,
    run_weekly_paper_report,
)
report = run_research_report("NVDA", use_mock=False, use_llm=False)
report = run_backtest_report("NVDA", start_date="2024-01-01", end_date="2024-06-01")
report = run_demo_report("NVDA", use_mock=False, use_llm=False)  # 含 research/strategy/backtest/summary 四块
```

*兼容层（退场中）*：仍可使用 `control.route_intent` + `control.execute`，新代码请用上述 adapter。

```python
# 已废弃为新入口，仅兼容保留
from ai_trading_research_system.control import route_intent, execute
cmd = route_intent("analyse NVDA", use_mock=False, use_llm=False)
result = execute(cmd, as_json=True)  # dict，与 run_for_openclaw 报告格式兼容
```

入参（symbol、task、--mock/--llm 等）与出参（上述报告格式）与本文档「报告格式」及 `run_for_openclaw.py` 的 stdout JSON 一致。

---

## 触发方式

OpenClaw 可通过 **子进程调用** 本仓库脚本获取报告（协议以 OpenClaw 现有集成为准，如 CLI、HTTP、消息队列）。

**推荐入口**：统一 CLI `cli.py`（Phase 2），或过渡方案 `scripts/run_for_openclaw.py`。

```bash
# 统一 CLI（项目根）
python cli.py research [SYMBOL] [--mock] [--llm]
python cli.py backtest [SYMBOL] [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--mock] [--llm]
python cli.py demo [SYMBOL] [--mock] [--llm]

# 或沿用 run_for_openclaw（仅 stdout 输出结果 JSON，与 adapter 报告格式一致）
python scripts/run_for_openclaw.py research [SYMBOL] [--mock] [--llm]
python scripts/run_for_openclaw.py backtest [SYMBOL] [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--mock] [--llm]
python scripts/run_for_openclaw.py demo [SYMBOL] [--mock] [--llm]
```

- **SYMBOL**：默认 `NVDA`。
- **--mock**：使用 mock 研究数据。
- **--llm**：使用 LLM Agent（需配置 `OPENAI_API_KEY` 或 `KIMI_CODE_API_KEY`）。
- **成功时**：退出码 0，**仅 stdout** 输出单条报告 JSON；日志与调试信息不写入 stdout，便于管道解析。
- **失败时**：退出码非 0，**仅 stderr** 输出一行错误 JSON，格式如下。

**错误格式（stderr 单行 JSON）**：

```json
{"ok": false, "command": "research", "error_code": 1, "error_message": "..."}
```

| 字段 | 说明 |
|------|------|
| ok | 固定 false |
| command | 本次请求的 task：research / backtest / demo |
| error_code | 非 0 退出码（通常 1） |
| error_message | 异常信息摘要 |

**最小验证示例**（仅验证 stdout 为合法 JSON）：

```bash
python scripts/run_for_openclaw.py research NVDA --mock
# 期望：退出码 0，stdout 为单条 JSON；可 pipe 到 jq 或 python -c "import sys,json; json.load(sys.stdin)"
```

### LLM 与 OpenClaw 模型对应

OpenClaw 中 Kimi Coding 的模型标识为 **`kimi-coding/k2p5`**（provider/model）。本仓与之对齐：

| OpenClaw | 本仓环境变量 | 说明 |
|----------|--------------|------|
| 认证 `kimi-code-api-key` | `KIMI_CODE_API_KEY` | 同一 key（来自 [Kimi Code 控制台](https://www.kimi.com/code/console)） |
| 端点 | `KIMI_BASE_URL` 默认 `https://api.kimi.com/coding/v1` | Kimi Code API |
| 模型 `k2p5` | `KIMI_MODEL` 默认 `k2p5` | Kimi K2.5 |

不配置 `OPENAI_API_KEY` 且配置了 `KIMI_CODE_API_KEY` 时，`--llm` 会使用上述 Kimi Code 端点与模型。

**为何 OpenClaw 可用、本仓直接调用曾 403？** Kimi Code 服务端按 **User-Agent 白名单**放行（仅允许 Kimi CLI、Claude Code、Roo Code、Kilo Code 等）。OpenClaw 或其它网关在请求中带上受认可的 User-Agent（如 `KimiCLI/1.3`）即可通过。本仓已对齐该方式：请求 Kimi Code 时默认增加 `User-Agent: KimiCLI/1.3`，可通过环境变量 `KIMI_USER_AGENT` 覆盖。参考：[CLIProxyAPI #1280](https://github.com/router-for-me/CLIProxyAPI/issues/1280)、OpenClaw 使用 Kimi CLI 凭证或相同 UA 的实践。

---

## 报告格式

### research 任务

| 字段 | 类型 | 说明 |
|------|------|------|
| task | string | `"research"` |
| symbol | string | 标的 |
| completed_at | string | ISO 时间 |
| contract_action | string | suggested_action（如 wait_confirmation, probe_small） |
| contract_confidence | string | confidence（low / medium / high） |
| thesis_snippet | string | thesis 前 200 字符 |
| raw_contract | object | 完整 DecisionContract（JSON 序列化后） |

### backtest 任务

在 research 字段基础上增加：

| 字段 | 类型 | 说明 |
|------|------|------|
| sharpe | number | Sharpe 比率 |
| max_drawdown | number | 最大回撤 |
| win_rate | number | 胜率 |
| pnl | number | 累计盈亏 |
| trade_count | number | 交易次数 |
| strategy_run_id | number | Experience Store 中的 strategy_run id |

### demo 任务（E2E 四块）

`run_demo_report()` 或 `execute(RoutedCommand(subcommand="demo"), as_json=True)` 返回：

| 字段 | 类型 | 说明 |
|------|------|------|
| task | string | `"demo"` |
| symbol | string | 标的 |
| completed_at | string | ISO 时间 |
| research | object | 研究结论（thesis、key_drivers、confidence、suggested_action、raw_contract 等） |
| strategy | object | 策略生成（action、allowed_position_size、rationale） |
| backtest | object | 回测结果（sharpe、max_drawdown、win_rate、pnl、trade_count） |
| summary | object | 交易总结（strategy_run_id、sentence） |

---

## 报告示例（backtest）

```json
{
  "task": "backtest",
  "symbol": "NVDA",
  "completed_at": "2026-03-07T10:00:00.000000Z",
  "contract_action": "probe_small",
  "contract_confidence": "medium",
  "thesis_snippet": "Market may still be repricing stronger medium-term growth...",
  "sharpe": 0.0,
  "max_drawdown": 0.0,
  "win_rate": 0.0,
  "pnl": 0.0,
  "trade_count": 1,
  "strategy_run_id": 6,
  "raw_contract": { ... }
}
```

---

## 程序化调用

若不通过 CLI，可在 Python 中直接调用 adapter：

```python
from ai_trading_research_system.pipeline.openclaw_adapter import (
    run_research_report,
    run_backtest_report,
)

report = run_research_report("AAPL", use_mock=False, use_llm=False)
# report 为 dict，可 json.dumps(report) 或回传 OpenClaw

report = run_backtest_report("AAPL", start_date="2024-01-01", end_date="2024-06-01")
```

---

## 相关文档

- 脚本用法汇总：[README.md](../README.md#脚本用法research--回测--paper--联调)
- MVP 完成标准：[mvp_plan.md](mvp_plan.md)
