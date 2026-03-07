# 验证脚本

| 脚本 | 说明 |
|------|------|
| `python scripts/check_dev_prerequisites.py` | 开发前环境与权限核对 |
| `python scripts/run_e2e_check.py NVDA --mock` | E2E：Pipeline 与 ExperienceStore 有数据 |
| `python scripts/verify_experience_store.py` | 最新 strategy_run、backtest_result、strategy_spec_snapshot、trade_experience、experience_summary、Refiner 建议 |
