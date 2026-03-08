# UC-09 Weekly Autonomous Paper

一周自治 Paper 组合：用户下达目标后系统自动建仓/调仓、执行一周、产出周报与 benchmark 对比。

---

## 入口（默认真实路径）

```bash
python cli.py weekly-paper --capital 10000 --benchmark SPY
# 或
python scripts/run_weekly_autonomous_paper.py --capital 10000 --benchmark SPY
```

加 `--mock` 仅用于 CI/回归。stdout 单条 JSON，含 snapshot_source、market_data_source、benchmark_source；周报落盘 `reports/weekly_report_<mandate_id>.json`。

---

## OpenClaw

- command：`weekly_autonomous_paper`、`weekly_report`；args: capital, benchmark, days；默认 use_mock=False。
- 入口：`python scripts/run_for_openclaw.py weekly_autonomous_paper [--capital 10000] [--benchmark SPY] [--days 5] [--mock]`；Skill 可调用 `openclaw.adapter.run_weekly_paper_report` 或上述 CLI。

---

## 验证

- Mock 回归：`.venv/bin/python scripts/verify_uc09_mock.py`
- 真实联调：`.venv/bin/python scripts/verify_uc09_real.py`

---

## 参考

- 实施计划与交付说明：[archive/UC09_IMPLEMENTATION_PLAN.md](archive/UC09_IMPLEMENTATION_PLAN.md)、[archive/UC09_REAL_PATH_DELIVERY.md](archive/UC09_REAL_PATH_DELIVERY.md)
- Mock 盘点：[archive/UC09_REAL_PATH_MOCK_INVENTORY.md](archive/UC09_REAL_PATH_MOCK_INVENTORY.md)
