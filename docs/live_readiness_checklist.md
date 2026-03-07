# 实盘前工作清单（Live Readiness Checklist）

策略进入实盘前必须通过本清单全部检查项。对应重构方案 Phase 5，见 [restructuring_plan.md](restructuring_plan.md#5-分阶段实施)。

**与 MVP 的关系**：MVP 5 条完成标准已达成；本清单为 **MVP 之后、实盘之前** 的必过工作，逐项完成并验收后方可进入实盘或 IBKR Live 验证。

---

## 检查项与状态

| # | 检查项 | 状态 | 交付标准 / 验收方式 | 补齐动作 |
|---|--------|------|----------------------|----------|
| 1 | **多时间窗口回测稳定** | 未达成 | 至少 2 个不同时间窗口（如 3 个月 / 6 个月）跑回测，结果可复现、无崩溃 | 增加多区间回测脚本或 `run_backtest` 多组 --start/--end；记录 Sharpe、回撤、交易次数 |
| 2 | **样本外表现可接受** | 未达成 | 有 OOS 区间定义与评估结论（如最近 N 日不参与训练，仅评估） | `run_backtest_windows.py --oos-days N` 跑最近 N 日单窗口；OOS_DAYS 见 .env.example；阈值需在流程中约定 |
| 3 | **最小交易次数阈值** | 未达成 | 回测或 Paper 周期内交易次数达到设定下限（避免样本过少） | 约定阈值与统计口径（如从 Experience Store 查询 trade_count），在文档或脚本中校验 |
| 4 | **最大回撤在风险容忍内** | 未达成 | 回测/Paper 最大回撤 ≤ 配置上限，且可监控 | 配置回撤上限（可与 PAPER_* 或新 env 联动），回测报告或 Store 中可查 |
| 5 | **纸面交易阶段完成** | 部分达成 | 本仓 Paper 试跑完成且 IBKR Paper 可下单（或明确仅用本仓 Paper） | 本仓 Paper 已达成；IBKR Paper 接入 execution 并验证至少 1 次下单成功后可勾选 |
| 6 | **Kill Switch 与风控已验证** | 已达成 | 仓位上限、单日止损生效且可配置 | 已实装：PAPER_MAX_POSITION_PCT、PAPER_DAILY_STOP_LOSS_PCT；可选：增加 Kill Switch 文件/开关验证 |
| 7 | **券商连通性已测试** | 未达成 | TWS/IB Gateway 端口可连、API 握手成功（或本仓不接 IBKR 则 N/A） | 运行 `python scripts/verify_ibkr.py` 验证端口可达；通过后可勾选 |

---

## 补齐任务汇总（可勾选推进）

- [x] **L1**：多时间窗口回测 — `run_backtest_windows.py [SYMBOL] [--windows 90,180]`，输出稳定性报告
- [x] **L2**：OOS 评估 — `run_backtest_windows.py --oos-days N`，OOS_DAYS 见 .env.example
- [x] **L3**：最小交易次数 — `run_backtest` 读取 MIN_TRADE_COUNT，不满足时退出码 1
- [x] **L4**：回撤上限 — `run_backtest` 读取 MAX_DRAWDOWN_PCT，超出时退出码 1
- [x] **L5**：IBKR Paper 下单 — 配置 IBKR_* 后 `run_paper` 走 ib_insync 向 TWS 下单（execution/ibkr_client.py）
- [x] **L6**：风控验证 — 已实装；Kill Switch：STOP_PAPER=1 或 `.paper_stop` 存在时 `run_paper` 不执行
- [x] **L7**：券商连通性 — `verify_ibkr.py` 检测 IBKR_HOST:IBKR_PORT 可达

---

## 相关文档

- [mvp_plan.md](mvp_plan.md) — MVP 完成标准与实盘前工作总览
- [deferred_authorization.md](deferred_authorization.md) — IBKR / OpenClaw / 生产密钥 / 风控对接步骤
- [restructuring_plan.md](restructuring_plan.md) — Phase 5 实盘就绪
- [architecture.md](architecture.md) — Execution Layer 与风控
- [dev_prerequisites.md](dev_prerequisites.md) — 开发前准备与验收
