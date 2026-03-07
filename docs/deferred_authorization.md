# 暂缓项与授权就绪后对接清单

本清单为 **实盘前工作** 的一部分，与 [live_readiness_checklist.md](live_readiness_checklist.md) 配合使用：MVP 已按 5 条标准交付，以下能力在**授权/权限满足后**按本清单逐项对接；当前状态与具体步骤如下。

---

## 1. IBKR Paper / 券商连通性

- **内容**：run_paper 接 Interactive Brokers Paper（TWS 或 IB Gateway），真实订单路径与端口连通。
- **前置**：IBKR Paper 账号、TWS 或 IB Gateway 已安装并开启 Socket API（如端口 7497）、本机或网络可访问。
- **参考**：[dev_prerequisites.md](dev_prerequisites.md) 中「Paper 试跑」、[live_readiness_checklist.md](live_readiness_checklist.md) 第 7 项。

**IBKR Paper 已启动时，先做这些配置：**

- 在 TWS/IB Gateway 中确认 **API → Settings** 里 **Socket port**（你当前为 **4002**）、**Allow connections from localhost only** 已勾选、**Trusted IPs** 含 `127.0.0.1`。
- 在项目根 `.env` 中增加（端口与 TWS 中一致）：
  ```bash
  IBKR_HOST=127.0.0.1
  IBKR_PORT=4002
  IBKR_CLIENT_ID=1
  ```
- 验证端口可达：运行 `python scripts/verify_ibkr.py`（或 `nc -zv 127.0.0.1 4002`，若系统无 telnet）。

**授权就绪后对接步骤：**

1. 确认 TWS/IB Gateway 已启用 API，端口可访问（见上）。
2. 本仓当前执行层为自研 `PaperTradingEngine`，未直接连 IBKR。对接方式二选一：
   - **方案 A**：引入 NautilusTrader 的 Live/Paper 适配（或 ib_insync），在 `execution/` 下新增 IBKR 执行适配器，由 `PaperRunner` 或新 `IBKRPaperRunner` 在配置为 IBKR 时调用。
   - **方案 B**：保持本仓 Paper 为模拟盘，另起进程/服务用 Nautilus 或 ib_insync 连 TWS，从本仓报告（如 `run_for_openclaw` 输出或 REPORT_DIR）读取信号再下单。
3. 在 `.env` 或配置中增加 IBKR 相关项（如 `IBKR_HOST`、`IBKR_PORT`、`IBKR_CLIENT_ID`），并在文档中说明生产环境不提交敏感信息。

---

## 2. OpenClaw 服务端 / 生产对接

- **内容**：OpenClaw 控制层在生产环境调用本系统（如 HTTP、消息队列），或本系统回调 OpenClaw 通知。
- **前置**：OpenClaw 服务端地址与调用方式、生产环境网络与鉴权授权。
- **当前**：CLI 报告（`run_for_openclaw.py` stdout JSON）与 REPORT_DIR、NOTIFY_FILE 占位已可用。

**授权就绪后对接步骤：**

1. **调用方式**：OpenClaw 通过子进程调用 `run_for_openclaw.py`（或调度脚本 `run_scheduled.py`）即可获取 JSON 报告；协议以 OpenClaw 现有集成为准。
2. **可选**：若需 HTTP 触发，可在本仓或网关层增加轻量 HTTP 服务，接收 task（research/backtest）、symbol 等参数，内部调用 `run_for_openclaw` 或 `openclaw_adapter`，将报告 JSON 返回或写入 REPORT_DIR。
3. **通知**：报告落盘后若设置了 `NOTIFY_FILE`，每次写入报告会追加一行 `{timestamp}\t{report_path}`，便于 OpenClaw 或 cron 轮询/消费。生产可配置 NOTIFY_FILE 路径。
4. 生产环境在 .env 或配置中设置 `REPORT_DIR`、`NOTIFY_FILE`（可选），并确保 OpenClaw 服务端可访问该目录或回调 URL（若实现 HTTP）。

---

## 3. 生产用 API Key 与密钥管理

- **内容**：OPENAI_API_KEY、KIMI_CODE_API_KEY、券商 API、新闻/数据源 API 等在生产环境的安全配置与轮换。
- **前置**：密钥管理策略、环境变量或保密存储的权限与流程。
- **当前**：本地 .env 与 dev 用法见 [dev_prerequisites.md](dev_prerequisites.md)；生产密钥不入库。

**授权就绪后对接步骤：**

1. 在生产环境使用环境变量或保密存储（如云厂商 Secret Manager、HashiCorp Vault）注入 `OPENAI_API_KEY` 或 `KIMI_CODE_API_KEY`（及可选 `KIMI_BASE_URL`、`KIMI_MODEL`、`KIMI_USER_AGENT`）。
2. 确保运行 `run_research` / `run_for_openclaw` / `run_paper` 的进程能读取上述变量，且不在日志或报告中打印 key。
3. 若有券商、新闻等 API，同上方式配置，并在文档中注明生产密钥由运维/授权流程管理。

---

## 4. 风控与 Kill Switch 实装

- **内容**：仓位上限、单日止损从 stub 改为可配置并接入执行层；Circuit Breaker、Kill Switch 可按需扩展。
- **前置**：风控策略与人工干预流程的确认、与实盘/Paper 执行层联调的权限。
- **参考**：[live_readiness_checklist.md](live_readiness_checklist.md) 第 6 项、[mock_vs_real.md](mock_vs_real.md) P3。

**当前状态（已实装）：**

- **仓位上限**：`PaperRunner` 在每次下单前检查：下单后该标的市值占组合权益比例不得超过 `max_position_pct`（0~100）。未配置时不限制。
- **单日止损**：若传入 `daily_pnl_pct` 且当日亏损达到 `daily_stop_loss_pct`（如 2 表示 -2% 触发），则禁止新开仓。`run_paper` 暂不传 `daily_pnl_pct`（需上游按日初权益与当前权益计算后传入）；可通过环境变量配置阈值。
- **配置方式**：`run_paper.py` 从环境变量读取：
  - `PAPER_MAX_POSITION_PCT`：单标的仓位上限（百分比，如 20 表示 20%）。
  - `PAPER_DAILY_STOP_LOSS_PCT`：单日止损触发线（正数，如 2 表示当日亏损 ≥2% 时禁止新开仓）。
- **Kill Switch / Circuit Breaker**：可在同一 Runner 或上层调度中增加“全局暂停”开关（如读取文件或配置），在风控或人工干预时停止执行；接口预留，可按需实现。

---

## 汇总

| 项 | 授权就绪后动作 | 当前状态 |
|----|----------------|----------|
| IBKR Paper | 接 TWS/Gateway 端口，新增或选用 IBKR 执行适配器，配置 IBKR_* 环境变量 | 本仓 Paper 可用；IBKR 未接 |
| OpenClaw 服务端 | 以 CLI/子进程调用 run_for_openclaw；可选 HTTP 层；配置 REPORT_DIR、NOTIFY_FILE | CLI 报告 + NOTIFY_FILE 占位可用 |
| 生产 API Key | 通过环境变量或保密存储注入 LLM/券商等 key，不落库 | 本地 .env 已文档化 |
| 风控实装 | 已实装仓位上限与单日止损；可选配置 PAPER_*；Kill Switch 可扩展 | 已接入 PaperRunner，可配置 |

授权就绪后，按上表逐项对接即可；无需改动 MVP 完成标准与已交付脚本/文档。
