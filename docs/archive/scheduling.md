# 研究任务自动运行（调度）

研究或研究+回测可通过定时任务或本仓调度脚本自动执行，报告落盘到指定目录。

---

## 方式一：cron 调用脚本（推荐）

使用系统 cron 或 launchd 定期调用 `run_for_openclaw.py` 或 `run_scheduled.py`，将 stdout 或报告文件写入固定目录。

**示例：每天 09:00 执行一次研究+回测，报告写入 `.reports`**

```bash
# 使用 run_scheduled（报告自动落盘）
0 9 * * * cd /path/to/ai-trading-research-system && .venv/bin/python scripts/run_scheduled.py --once --backtest >> .reports/cron.log 2>&1
```

**示例：仅研究，每 6 小时一次**

```bash
0 */6 * * * cd /path/to/ai-trading-research-system && .venv/bin/python scripts/run_for_openclaw.py research NVDA > .reports/research_$(date +\%Y\%m\%d_\%H\%M).json 2>> .reports/cron.log
```

---

## 方式二：run_scheduled.py 内建循环

通过环境变量配置后，运行 `run_scheduled.py` 不传 `--once`，并按 `SCHEDULE_INTERVAL_MINUTES` 循环执行（需本进程常驻）。

| 环境变量 | 说明 | 默认 |
|----------|------|------|
| SCHEDULE_INTERVAL_MINUTES | 间隔分钟数；0 表示只跑一次（与 --once 等价） | 0 |
| DEFAULT_SYMBOL | 默认标的 | NVDA |
| RUN_BACKTEST | 是否执行研究+回测（true / false） | false |
| REPORT_DIR | 报告落盘目录 | .reports |
| NOTIFY_FILE | 可选；报告写入后追加一行「时间戳\t报告路径」供下游 tail/轮询 | 未设置则不写 |

**示例：每 60 分钟跑一次研究，报告写入 `.reports`**

```bash
export SCHEDULE_INTERVAL_MINUTES=60
export REPORT_DIR=.reports
python scripts/run_scheduled.py
```

**示例：只跑一次研究+回测**

```bash
python scripts/run_scheduled.py --once --backtest --symbol AAPL
```

报告文件名格式：`{task}_{symbol}_{YYYYMMDD_HHMMSS}.json`。

---

## 验收

- 在不手动执行脚本的前提下，通过 cron 或 `run_scheduled.py` 在约定时间完成至少 1 次「研究」或「研究+回测」。
- 在 `REPORT_DIR`（或 `.reports`）下可查到对应 JSON 报告文件。

---

## 通知（占位）

当前无推送或 Webhook：报告落盘至 `REPORT_DIR`，可选设置 `NOTIFY_FILE` 在每次写报告后追加一行 `{timestamp}\t{report_path}`，便于 cron 或 OpenClaw 轮询/消费。邮件、移动通知等需授权或第三方服务后另行对接。

---

## 相关文档

- [openclaw_integration.md](openclaw_integration.md) — 报告格式与 OpenClaw 触发
- [README.md](../README.md) — 脚本用法汇总
