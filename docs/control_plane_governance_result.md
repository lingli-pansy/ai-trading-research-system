# 控制面一致性治理结果

## 1️⃣ Command 命名统一结果

- **Canonical 命令**（与 `openclaw.contract.OPENCLAW_COMMANDS` 一致）：
  - `research_symbol`
  - `backtest_symbol`
  - `run_demo`
  - `weekly_autonomous_paper`
  - `weekly_report`
- **CLI 子命令**：保留别名 `research` / `backtest` / `demo` / `weekly-paper`，以及无别名的 `paper`、`weekly_report`。
- **command_registry**：`resolve(alias)` → canonical；`run(command, **kwargs)` 先解析再按 canonical 派发；`_HANDLERS` 仅按 canonical 注册（含 `paper` 用于 run_paper）。

## 2️⃣ Alias → Canonical 映射

| CLI / 入参 | Canonical |
|------------|-----------|
| `research` | `research_symbol` |
| `backtest` | `backtest_symbol` |
| `demo` | `run_demo` |
| `weekly-paper` | `weekly_autonomous_paper` |
| `paper` | `paper`（无别名，仅 CLI） |
| `weekly_report` | `weekly_report`（无别名） |

## 3️⃣ weekly_report Handler 实现

- **位置**：`application/commands/run_weekly_report.py`
- **职责**：在给定 `report_dir`（默认 `Path.cwd()/"reports"`）下查找 `weekly_report_*.json`，按 mtime 取最新一份，读取 JSON 填 `summary`，返回 `WeeklyReportCommandResult(ok, report_path, mandate_id, summary)`。**不执行任何 pipeline**，与 UC-09 execution 分离。
- **路由**：`command_registry` 中 `weekly_report` → `run_weekly_report`（不再指向 `run_weekly_autonomous_paper`）。
- **契约**：`openclaw.contract.WeeklyReportInput`（`report_dir` 可选）、`WeeklyReportOutput`（`ok`, `mandate_id`, `report_path`, `summary`）；adapter `format_result("weekly_report", result)` 输出上述结构。

## 4️⃣ CLI 删除的业务逻辑

- **删除**：`PROJECT_ROOT`、`_project_root()` 及基于项目根的 `.env` 加载改为 `Path.cwd() / ".env"`。
- **删除**：在 `main()` 中根据 `args.command` 构造 `report_dir`、`project_root` 并传入 `command_run(..., report_dir=..., project_root=...)`。现由 `kwargs_from_cli_args(args.command, args)` 在 command_registry 侧按 canonical 注入 `report_dir` / `project_root`，CLI 仅调用 `command_run(args.command, **kwargs)`。
- **删除**：针对 `weekly-paper` / `paper` 的单独 return code 分支，统一为 `getattr(result, "paused", False)` 与 `getattr(result, "ok", True) is False` 决定退出码。
- **保留**：CLI 仅负责 parse args → `command_registry.run` → `renderers.render`，不直接构造业务参数。

## 5️⃣ Registry / Contract / Command_registry 职责边界

| 层级 | 职责 | 内容 |
|------|------|------|
| **registry** | Skill 表面（single source） | `list_skills()`：name、description、canonical_command、input_schema、output_schema、example；`get_skill_names()` 仅返回 canonical 列表；`kwargs_for_task(canonical, args)` 为 run 构建 kwargs。`run_for_openclaw` 仅从 registry 获取 skill，禁止硬编码 skill 名。 |
| **contract** | Schema | `OPENCLAW_COMMANDS`、各命令的 Input/Output Pydantic 模型；校验与机器可读契约。 |
| **command_registry** | Handler 映射 | `resolve(alias→canonical)`、`run(canonical, **kwargs)` 派发到 `application.commands` 中对应 handler；`kwargs_from_cli_args` 为 CLI 构建 kwargs（含 report_dir/project_root）。 |

**目标状态**：

```
OpenClaw / CLI
       ↓
command_registry (resolve → run)
       ↓
application.commands
       ↓
pipeline / services
```

- **registry** = skill surface（元数据 + canonical 名 + schema 引用）
- **contract** = schema（输入/输出定义）
- **command_registry** = handler mapping（别名解析 + 派发）
