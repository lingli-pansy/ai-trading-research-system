# IB Snapshot 完整验证报告

**验证时间**: 2026-03-08  
**命令**: `LOG_LEVEL=INFO python -m ai_trading_research_system.cli weekly-paper --symbols SPY --days 1`

---

## 验证结果总览

| 项目 | 状态 | 说明 |
|------|------|------|
| IB 单连接 session 创建 | ✅ | 出现 "Connecting to IB"、"IB session connected" |
| Session 进入 context | ✅ | "(IB session in context: True)" |
| Snapshot 走 session 路径 | ✅ | [ib] 日志来自 `ibkr_session`，account_summary/positions/open_orders 分步完成 |
| Account snapshot 真实数据 | ✅ | `Account snapshot: source=ibkr, equity=1000086` |
| 结果 JSON snapshot_source | ✅ | `"snapshot_source": "ibkr"` |
| Session 收尾断开 | ✅ | "IB session disconnected" |

---

## 修复项（验证过程中完成）

1. **ibkr_session.py 语法错误 (line 170)**  
   `except Exception as e:` 缩进错误，导致导入失败、session 无法创建。已改为与上方 `try`/`except` 对齐。

2. **session 路径未 await 协程**  
   `_get_account_snapshot_async` 内调用 `self._fetch_positions_session(pos_timeout)` 未加 `await`，导致 `'coroutine' object is not iterable` 与 fallback mock。已改为 `await self._fetch_positions_session(...)`。

3. **Pipeline 未创建 session 时的可观测性**  
   增加：未配置 IB 时提示、connect 失败时提示、import/异常时提示，便于排查。

---

## 推荐验证命令

```bash
# 激活 venv 后执行（1 天、单标的、无 LLM，约 15–20 秒）
source .venv/bin/activate
LOG_LEVEL=INFO python -m ai_trading_research_system.cli weekly-paper --symbols SPY --days 1
```

**期望输出要点**：
- `[weekly-paper] Connecting to IB (single session for this run)...`
- `[weekly-paper] IB session connected, reusing for account & market data.`
- `[weekly-paper] (IB session in context: True)`
- `[ib] account_summary start` / `[ib] account_summary end (latency=...s)`
- `[ib] positions start` / `[ib] positions end (latency=...s)`
- `[ib] open_orders start` / `[ib] open_orders end (latency=...s)`
- `[weekly-paper] Account snapshot: source=ibkr, equity=...`
- 结果 JSON 中 `"snapshot_source": "ibkr"`
- `[weekly-paper] IB session disconnected.`

---

## 已知无关问题（未在本次修复）

- **Error 10314 (End Date/Time invalid)**：请求历史 K 线时传给 IB 的 `endDateTime` 格式不符合要求，需在 `market_data_service` / `ibkr_session._fetch_bars_async` 中按 IB 要求格式化日期时间（如 `yyyymmdd hh:mm:ss US/Eastern` 或 UTC 格式）。不影响 snapshot 与本次验证结论。
