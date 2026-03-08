# OpenClaw Agent 接入说明

**几分钟内：用配置驱动 paper 模式跑一次或持续 loop。**

---

## 1. 通过哪个 adapter 接入？

- **推荐路径**：`OpenClaw 配置 → openclaw.agent_adapter → AutonomousTradingAgent`
- **模块**：`openclaw.agent_adapter`
  - `run_openclaw_agent_once(config)`：跑一次
  - `create_openclaw_agent(config)`：创建 agent，再调用 `run_loop(...)`
- OpenClaw 只依赖 **config + adapter**，不直接依赖 pipeline 或底层模块。

---

## 2. 配置文件放哪里？

- **示例配置**：`configs/openclaw_agent.paper.yaml`
- 支持 **YAML** 或 **JSON**，通过 `OpenClawAgentConfig.load(path)` 加载。
- 可复制该文件修改后作为自己的配置。

---

## 3. Paper 模式如何跑一次？

```bash
python -m ai_trading_research_system.presentation.cli openclaw-agent-once --config configs/openclaw_agent.paper.yaml
```

可选：`--context` 在输出中附带 health / 最近 experience 摘要。

---

## 4. Loop 模式如何跑？

```bash
python -m ai_trading_research_system.presentation.cli openclaw-agent-loop --config configs/openclaw_agent.paper.yaml
```

可选：`--context` 每轮输出附带 health/experience 摘要。

---

## 5. 输出写到哪里？

- **runs/**：与现有 agent 一致
  - `runs/<run_id>/`：snapshots、artifacts、execution、audit
  - `runs/index.json`、`runs/experience.jsonl`、`runs/agent_health.json`
- CLI 会打印 run summary（agent name、run_id、symbols、rebalance、risk_flags、orders、run_path）。

---

## 6. Health / Experience / Risk 在哪里看？

- **Health**：`runs/agent_health.json`（或通过 `build_openclaw_context_summary()` 的 `health` 字段）。
- **Experience**：`runs/experience.jsonl`；摘要通过 `build_openclaw_context_summary()`（`recent_runs`、`symbol_rebalance_summary`）。
- **Risk**：每轮 run 的 `risk_flags` 在 run summary 和 audit 中；pipeline 内 RiskPolicyEngine 执行前检查。

---

## 7. 哪些旧入口不要继续依赖？

- **不推荐**：直接调用 `run_autonomous_paper_cycle_report` 或零散传参、多入口并存的用法。
- **推荐**：用 **配置文件 + openclaw-agent-once / openclaw-agent-loop**，或编程时使用 **OpenClawAgentConfig + openclaw.agent_adapter**。

---

**配置字段说明**：见 `openclaw.config.OpenClawAgentConfig`；示例见 `configs/openclaw_agent.paper.yaml`。
