# 命令面单一真相收口 — 治理结果

## 1. Canonical commands 列表

| Canonical | 说明 |
|-----------|------|
| `research_symbol` | 对标的做研究，返回 DecisionContract |
| `backtest_symbol` | 研究 + 回测 + Experience Store |
| `run_demo` | E2E 演示：研究 → 策略 → 回测 → 总结 |
| `run_paper` | Research → Contract → Paper inject（once or runner） |
| `weekly_autonomous_paper` | UC-09 一周自治 Paper |
| `weekly_report` | 读取已有周报或报告摘要（无执行） |

共 6 个 canonical 命令。

---

## 2. Aliases 列表

| Alias | Canonical |
|-------|-----------|
| `research` | `research_symbol` |
| `backtest` | `backtest_symbol` |
| `demo` | `run_demo` |
| `paper` | `run_paper` |
| `weekly-paper` | `weekly_autonomous_paper` |

`weekly_report` 无别名，CLI 子命令名即 canonical。

---

## 3. Single source of truth 的实现位置

**唯一实现位置**：`src/ai_trading_research_system/openclaw/registry.py`。

- **维护内容**：每个命令的 `canonical`、`aliases`、`description`、`input_schema`、`output_schema`、`example`、`handler_target`、`needs_report_dir`、`expose_for_openclaw`。
- **alias→canonical 解析**：仅在此实现（`resolve(command)`）；CLI 与 `run_for_openclaw.py` 不维护任何命令列表或别名表。
- **command_registry**：只从 registry 读取（`resolve`、`get_metadata`、`kwargs_for_task`），做 handler 绑定与派发，不重复维护命令/别名。

---

## 4. Paper 命令如何被统一

- **Canonical 名**：`run_paper`（与 `application.commands.run_paper` 一致）。
- **CLI alias**：`paper` → `run_paper`；CLI 子命令仍为 `paper`，内部解析后派发到 `run_paper`。
- **Registry**：在 `_COMMAND_METADATA` 中增加一项，`canonical="run_paper"`，`aliases=["paper"]`，`handler_target="run_paper"`，`expose_for_openclaw=False`。
- **Contract**：新增 `RunPaperInput`、`RunPaperOutput`（schema 仅用于契约一致性；OpenClaw 当前不暴露 run_paper）。
- **效果**：paper 与其余命令同一套命名与解析体系，不再作为 CLI 特例。

---

## 5. 新增/更新测试列表

| 测试 | 文件 | 说明 |
|------|------|------|
| `test_registry_single_source_of_truth` | test_registry_single_source.py | 所有命令元数据在 registry，且含 required 字段 |
| `test_alias_resolution_for_all_commands` | test_registry_single_source.py | 所有 alias 与 canonical 经 resolve 一致 |
| `test_paper_command_is_canonicalized` | test_registry_single_source.py | paper→run_paper，metadata 正确，run("paper", ...) 可派发 |
| `test_openclaw_registry_matches_command_registry` | test_registry_single_source.py | OpenClaw 列表 ⊆ 全量 canonical；run_paper 不在 OpenClaw；command_names/cli 与 registry 一致 |
| `test_openclaw_commands_match_registry` | test_openclaw_contract.py | `contract.OPENCLAW_COMMANDS` == `registry.get_canonical_commands_for_openclaw()` |
| `test_resolve_paper_alias_to_run_paper` | test_command_alias_resolution.py | resolve("paper") == "run_paper" |
| `test_canonical_commands_include_run_paper` | test_command_alias_resolution.py | get_canonical_commands() 含 run_paper |
| `test_aliases_mapping` | test_command_alias_resolution.py | 含 paper→run_paper（数据来源改为 registry.get_aliases()） |

---

## 6. 仍存在的命令面风险

- **contract.OPENCLAW_COMMANDS 与 registry 双份列表**：目前通过测试 `test_openclaw_commands_match_registry` 强制一致；若有人只改 contract 不改 registry 会失败。长期可考虑让 OPENCLAW_COMMANDS 由 registry 派生（需避免 contract→registry 循环依赖）。
- **handler_target 与 application.commands 函数名耦合**：registry 中 `handler_target` 为字符串，command_registry 内用 `_HANDLERS` 映射；新增 command 时需同时改 registry 与 command_registry 的 _HANDLERS，否则 run 会报 "no handler"。
- **kwargs_for_task 与 registry 中命令分支同步**：新增 canonical 时需在 `registry.kwargs_for_task` 中增加分支，否则 OpenClaw/CLI 传参可能不完整。
