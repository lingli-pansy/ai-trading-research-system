# OpenClaw Autonomous Paper 架构收敛交付说明

**第一轮**：RunStore、autonomous_paper_cycle 主路径、runs/ 落盘。  
**第二轮**：分阶段编排、RebalancePlan、portfolio_after、state-aware RunStore、replay_run、current-path 导航。见 [current-path.md](current-path.md)。

---

## 一、改动文件清单（第一轮 + 第二轮）

### 新增
- `src/ai_trading_research_system/state/__init__.py` — state 包入口
- `src/ai_trading_research_system/state/run_store.py` — RunStore：统一 run/snapshot/decision/execution/audit 落盘
- `src/ai_trading_research_system/pipeline/autonomous_paper_cycle.py` — 单周期编排（主路径）
- `src/ai_trading_research_system/application/commands/run_autonomous_paper_cycle.py` — 命令层入口
- `tests/test_run_store.py` — RunStore 单元测试
- `tests/test_autonomous_paper_cycle.py` — cycle 接口与落盘测试
- `docs/openclaw_autonomous_paper_convergence.md` — 本说明

### 修改
- `src/ai_trading_research_system/application/commands/__init__.py` — 导出 run_autonomous_paper_cycle
- `src/ai_trading_research_system/application/command_registry.py` — 注册 autonomous_paper_cycle handler
- `src/ai_trading_research_system/application/commands/run_paper.py` — 非 IBKR 路径复用 run_autonomous_paper_cycle，落盘 runs/
- `src/ai_trading_research_system/openclaw/contract.py` — AutonomousPaperCycleInput/Output，OPENCLAW_COMMANDS 增加 autonomous_paper_cycle
- `src/ai_trading_research_system/openclaw/registry.py` — 新增 autonomous_paper_cycle 元数据与 kwargs_for_task
- `src/ai_trading_research_system/openclaw/adapter.py` — format_result(autonomous_paper_cycle)、run_autonomous_paper_cycle_report
- `src/ai_trading_research_system/presentation/cli.py` — 新增 paper-cycle 子命令
- `src/ai_trading_research_system/presentation/renderers.py` — paper-cycle 渲染
- `scripts/run_for_openclaw.py` — 支持 --run_id，autonomous_paper_cycle 输出 ok/command
- `.gitignore` — 增加 runs/
- `docs/system_architecture.md` — 入口、数据落盘、主路径说明
- `tests/test_openclaw_contract.py` — OPENCLAW_COMMANDS 长度与 autonomous_paper_cycle 断言

---

## 二、核心抽象说明

| 抽象 | 职责 |
|------|------|
| **RunStore** | 唯一负责 runs/ 下路径、命名、读写；禁止各 service 直接写 run 相关文件。提供 create_run、write_meta、write_portfolio_snapshot、write_research_snapshot、write_candidate_decision、write_final_decision、write_order_intents、write_paper_execution、append_audit、read_*、list_runs、read_latest_run_id、read_run_summary。 |
| **CycleInput / CycleOutput** | 单周期输入/输出契约：run_id、symbol_universe、mode、use_mock、use_llm、execute_paper、capital、benchmark → ok、candidate_decision、final_decision、order_intents、no_trade_reason、rejected_reason、skipped_reason、write_paths、error。 |
| **run_autonomous_paper_cycle** | 单周期编排：读组合 → 研究 → 排名 → trigger → allocator → 订单意图 → 可选 paper 执行 → 全部落盘。 |
| **run_autonomous_paper_cycle (command)** | 应用层命令：生成 run_id（若未提供）、调用 pipeline、返回 CycleOutput。 |

---

## 三、运行命令（最小可运行示例）

```bash
# CLI 单周期（mock，不执行 paper）
uv run python -m ai_trading_research_system.presentation.cli paper-cycle --mock --symbols NVDA --no-execute

# CLI 单周期（mock，执行 paper，落盘 runs/<run_id>/）
uv run python -m ai_trading_research_system.presentation.cli paper-cycle --mock --symbols NVDA --run_id demo_run

# OpenClaw 脚本（与 agent 调用方式一致）
uv run python scripts/run_for_openclaw.py autonomous_paper_cycle NVDA --mock --run_id openclaw_demo
```

---

## 四、测试结果

- `uv run pytest tests/ -q --tb=line`：**141 passed, 1 skipped**（test_cycle_e2e_mock 为占位跳过）。

---

## 五、主入口、数据位置、OpenClaw 接入

- **主入口**：OpenClaw agent 唯一调用 **`autonomous_paper_cycle`**（canonical）。CLI 为 `paper-cycle`；脚本为 `scripts/run_for_openclaw.py autonomous_paper_cycle ...`。内部经 `command_registry.run("autonomous_paper_cycle", ...)` → `run_autonomous_paper_cycle` → `pipeline.autonomous_paper_cycle.run_autonomous_paper_cycle`。
- **数据存哪里**：默认 **`runs/`**（可设置 `PAPER_RUNS_ROOT`）。每轮 `runs/<run_id>/` 下：`meta.json`、`snapshots/`（portfolio_before、research）、`artifacts/`（candidate_decision、final_decision、order_intents）、`execution/paper_result.json`、`audit.json`。所有读写经 **`state.RunStore`**。
- **OpenClaw 怎么接**：Agent 调用 `run_for_openclaw.py autonomous_paper_cycle [symbol] --run_id <id> --mock` 或直接调用 `openclaw.adapter.run_autonomous_paper_cycle_report(run_id=..., symbol_universe=..., use_mock=...)`。返回 JSON 含 ok、run_id、candidate_decision、final_decision、order_intents、no_trade_reason、rejected_reason、skipped_reason、write_paths、error。

---

## 六、收敛项与未动项

### 已收敛
- Paper 单周期：**单一主路径** `autonomous_paper_cycle`，CLI `paper`（非 IBKR）复用该路径并落盘。
- 数据面：**RunStore 单一写入**，runs/ 目录统一，支持 replay（read_run_summary）。
- 控制面：**唯一入口** 为 command_registry + autonomous_paper_cycle；OpenClaw 只暴露 autonomous_paper_cycle 作为 agent 主入口。
- 边界对象：**CycleInput/CycleOutput** 与 **AutonomousPaperCycleInput/Output** 契约稳定。

### 未动（保留兼容）
- `run_paper` 的 **IBKR 路径**：仍走 paper_pipe.run + place_market_buy，未改为 cycle。
- **weekly_autonomous_paper**：未改为“多日循环调用 autonomous_paper_cycle”，仍为独立 pipe。
- **scripts/run_*.py**：未删除，保留为兼容入口；主路径为 CLI / run_for_openclaw + autonomous_paper_cycle。
- **Experience Store**（.experience/）：未与 runs/ 合并，仍用于 strategy_run、weekly 等。

### 已暴露风险点
- 单周期内 **get_account_snapshot** 非 mock 时依赖 IB/环境，失败会 fallback 或报错，需在 agent 侧处理。
- **ResearchOrchestrator** 与 **NautilusPaperRunner** 的异常会写入 audit 并返回 CycleOutput(ok=False, error=...)，便于排查，不吞掉。
