# UC-09 实施计划

## 计划修改/新增文件列表

### 新增（autonomous 层）
- `src/ai_trading_research_system/autonomous/__init__.py`
- `src/ai_trading_research_system/autonomous/schemas.py` — AccountSnapshot, WeeklyTradingMandate
- `src/ai_trading_research_system/autonomous/account_snapshot.py` — get_account_snapshot (paper/mock)
- `src/ai_trading_research_system/autonomous/mandate.py` — mandate_from_cli, mandate_from_nl (stub)
- `src/ai_trading_research_system/autonomous/allocator.py` — PortfolioAllocator
- `src/ai_trading_research_system/autonomous/state_machine.py` — AutonomousExecutionStateMachine
- `src/ai_trading_research_system/autonomous/benchmark.py` — BenchmarkComparator
- `src/ai_trading_research_system/autonomous/weekly_report.py` — WeeklyReportGenerator

### 新增（pipeline + 入口）
- `src/ai_trading_research_system/pipeline/weekly_paper_pipe.py` — 一周自治 paper 编排
- `scripts/run_weekly_autonomous_paper.py` — 独立脚本入口
- `scripts/verify_uc09_weekly_autonomous_paper.py` — UC-09 验证脚本

### 修改
- `cli.py` — 增加 weekly-paper 子命令
- `src/ai_trading_research_system/control/command_router.py` — 增加 weekly_autonomous_paper
- `src/ai_trading_research_system/pipeline/openclaw_adapter.py` — run_weekly_paper_report
- `docs/operations.md` — UC-09 支持说明
- `docs/uc09_weekly_autonomous_paper.md` — weekly_autonomous_paper 入口
- `docs/core_concepts.md` — 周报/UC-09 输出字段

## 分步执行（已完成）
1. 第一阶段：autonomous/* 六个能力 ✓
2. 第二阶段：CLI weekly-paper + run_weekly_autonomous_paper.py + OpenClaw adapter ✓
3. 第三阶段：weekly_paper_pipe 接入 research/nautilus/experience ✓
4. 第四阶段：verify_uc09 脚本 ✓
5. 第五阶段：文档收敛 ✓

---

## 最终交付物

### 1. 修改过的文件列表
- **新增**：`src/ai_trading_research_system/autonomous/`（schemas, account_snapshot, mandate, allocator, state_machine, benchmark, weekly_report, __init__.py）；`pipeline/weekly_paper_pipe.py`；`scripts/run_weekly_autonomous_paper.py`；`scripts/verify_uc09_weekly_autonomous_paper.py`
- **修改**：`cli.py`（weekly-paper）；`control/command_router.py`（RoutedCommand + route_intent）；`control/skill_interface.py`（execute weekly_autonomous_paper）；`pipeline/openclaw_adapter.py`（run_weekly_paper_report）；`docs/operations.md`；`docs/uc09_weekly_autonomous_paper.md`；`docs/core_concepts.md`；`docs/archive/next_phase_interface.md`

### 2. 新增入口命令
- CLI：`python cli.py weekly-paper [--capital 10000] [--benchmark SPY] [--days 5] [--mock]`
- 脚本：`python scripts/run_weekly_autonomous_paper.py --capital 10000 --benchmark SPY`
- OpenClaw：`execute(RoutedCommand("weekly_autonomous_paper", capital=10000, benchmark="SPY", ...))` 或 `run_weekly_paper_report(...)`

### 3. UC-09 验证脚本
- `python scripts/verify_uc09_weekly_autonomous_paper.py` — 验证 mandate、snapshot、allocation、paper 主线、benchmark、report、Experience Store、完整 run；通过则输出 UC-09 VERIFY PASS 并 exit 0。**前提**：项目已安装依赖（如 `pip install -e .`）。

### 4. 示例运行输出（stdout JSON）
```json
{"ok": true, "mandate_id": "...", "status": "completed_week", "capital_limit": 10000.0, "benchmark": "SPY", "engine_type": "paper", "used_nautilus": true, "report_path": "reports/weekly_report_....json", "summary": {"portfolio_return": 0.0, "benchmark_return": 0.0, "excess_return": 0.0, "trade_count": 0, "pnl": 0.0}}
```

### 5. 仍为 stub / mock 的能力
- **mandate_from_nl**：自然语言转 mandate 为规则占位，未接 LLM。
- **一周执行**：用 duration_days 次迭代在单进程内跑完，非真实日历一周调度。

### 6. Real 路径切换（主路径默认真实）

- **默认**：CLI / OpenClaw / run_weekly_autonomous_paper 默认 **use_mock=False**（真实数据、真实 benchmark）；AccountSnapshot 优先 IBKR paper（需 IBKR_HOST/IBKR_PORT），失败则 fallback mock 并标记 snapshot_source=mock。
- **输出**：JSON 增加 snapshot_source、market_data_source、benchmark_source。
- **验证**：`verify_uc09_mock.py`（CI/回归）、`verify_uc09_real.py`（真实联调）。盘点见 [UC09_REAL_PATH_MOCK_INVENTORY.md](UC09_REAL_PATH_MOCK_INVENTORY.md)。
