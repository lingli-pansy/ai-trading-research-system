# OpenClaw Skills

每个 skill 对应一个 application.command，由 commands.py 映射执行。

| Skill | 说明 |
|-------|------|
| **research_symbol** | 对标的做研究，返回 DecisionContract |
| **backtest_symbol** | 对标的做研究 + 回测 + 写入 Experience Store |
| **run_demo** | E2E 演示：研究 → 策略 → 回测 → 总结 |
| **weekly_autonomous_paper** | UC-09 一周自治 Paper：mandate → snapshot → 多轮 research/allocator/paper → benchmark → 周报 |
| **weekly_report** | 生成周报（基于 mandate + benchmark 结果等，写入 JSON 文件） |

上述 skill 均通过 `openclaw.commands` 映射到 `application.commands` 中同名或对应 command。
