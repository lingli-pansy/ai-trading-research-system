# control/ 清理报告

## 1. 引用扫描结果

| 引用位置 | 类型 | 处置 |
|----------|------|------|
| `src/ai_trading_research_system/control/__init__.py` | 包内 | 已删除包 |
| `src/ai_trading_research_system/control/command_router.py` | 包内 | 已删除 |
| `src/ai_trading_research_system/control/skill_interface.py` | 包内 | 已删除 |
| `docs/archive/openclaw_integration.md` | 文档示例 | 已更新为仅推荐 openclaw.adapter，control 示例标注废弃 |
| `tests/test_control_deprecation.py` | 测试 | 已改为断言 control 非入口（不导入 control） |

**结论**：无 CLI、无 OpenClaw、无 scripts 引用 control；仅文档与测试提及。已删除整个 control 包。

## 2. 迁移说明

- **CLI**：从未引用 control，已改为仅通过 `application.command_registry` 调用。
- **OpenClaw / run_for_openclaw**：从未引用 control，已改为 `openclaw.registry` + `application.command_registry` + `openclaw.adapter.format_result`。
- **其他 scripts**：未发现对 control 的引用。

## 3. 删除内容

- `src/ai_trading_research_system/control/__init__.py`
- `src/ai_trading_research_system/control/command_router.py`
- `src/ai_trading_research_system/control/skill_interface.py`

## 4. 保留 / 兼容层

无。control 包已整体删除，不再保留兼容层。

## 5. 文档与测试更新

- `docs/archive/openclaw_integration.md`：方式 B 仅保留 openclaw.adapter 示例；control 示例标注「已废弃为新入口，仅兼容保留」；若后续删除该示例可整段移除。
- `tests/test_control_deprecation.py`：断言 control 包已删除（ModuleNotFoundError），且 run_for_openclaw 使用 registry + command_registry。

## 6. 目录处置

- 已删除 `src/ai_trading_research_system/control/` 下全部文件及目录本身，确保无空包残留。
