# UC-10 Stage-1 实验迭代 01 — Improve First Autonomous Experiment Quality

## 目标

提升首次自治实验的**决策信息量**和**可交易机会识别能力**，在不修改 IB/snapshot/benchmark/execution/CLI/experience schema 的前提下，仅通过 research / policy / trace / opportunity scoring 改进。

---

## 实现摘要

### 一、Decision Trace 拆分（Portfolio vs Symbol）

- **PortfolioDecisionTrace**：组合级
  - `allocator_reason`、`trigger_context`、`health_context`、`policy_constraints`
- **SymbolDecisionTrace**：标的级
  - `symbol`、`research_thesis`、`opportunity_score`、`key_drivers`、`risk_factors`、`final_action`

周报 `decision_traces_summary` 现同时包含：

- `portfolio_traces`：组合层原因与风险上下文
- `symbol_traces`：每标的的研究结论与机会分数、最终动作（entry / replace / rejected / retain / no_trade）

### 二、wait_confirmation 与 Probe Position

- 当 **confidence ≥ medium** 且 **opportunity_score ≥ threshold**（默认 0.4）时，允许 **probe position**。
- Probe 仓位：`capital_limit × 2%–5%`（实现取 3%），不改变既有风控与 guardrails。
- Policy 新增 `opportunity_score_probe_threshold`（默认 0.4）。

### 三、Opportunity Score 归一化 [0, 1]

- 在 research → decision 路径上，`OpportunityRanking` 输出 **0.0–1.0** 的 `opportunity_score`。
- 计算基于：confidence、thesis strength、risk flags（及既有逻辑），归一化公式：`max(0, min(1, (raw - 0.5) / 2.5))`。
- Symbol trace 中必含 `opportunity_score`。

### 四、Research 输出与 Trace 写入

- 保证 symbol research 输出：`thesis`、`key_drivers`、`risk_factors`。
- 写入 decision trace（SymbolDecisionTrace）及周报的 `research_reasoning_summary` / `symbol_traces`。

---

## 实验命令与条件

```bash
python -m ai_trading_research_system.cli weekly-paper \
  --symbols SPY,QQQ,NVDA \
  --days 5 \
  --llm
```

验证用短跑（mock，1 天）：

```bash
python -m ai_trading_research_system.cli weekly-paper \
  --symbols SPY,QQQ,NVDA \
  --days 1 \
  --mock
```

---

## 实验结果（Mock 1 天）

- **trade_count**: 0（mock 路径下 Nautilus run_once 未产生成交，属预期）
- **opportunity_score 分布**：三标的均为 **0.574**（mock 下 research 输出一致，confidence=medium, risk=high → 归一化后同分）
- **decision_traces_summary**：含 `portfolio_traces` 与 `symbol_traces`，信息完整

### Decision Trace 示例

**Portfolio 级（1 条）**

```json
{
  "trace_type": "portfolio",
  "timestamp": "2026-03-08T09:37:44.619914+00:00",
  "allocator_reason": "positions=3 cash_reserve_pct=0.1",
  "trigger_context": {
    "trigger_fired": true,
    "trigger_type": "risk_event_trigger",
    "trigger_reason": "opportunity_risk_high_SPY",
    "health_context": { "concentration_index": 0.0, "beta_vs_spy": 0.0, "max_drawdown": 0.0 },
    "severity": "high"
  },
  "health_context": {
    "portfolio_return": 0.0,
    "benchmark_return": 0.0,
    "concentration_index": 0.0,
    "max_drawdown": 0.0
  },
  "policy_constraints": {
    "minimum_score_gap_for_replacement": 0.3,
    "max_replacements_per_rebalance": 2,
    "turnover_budget": 0.5,
    "retain_threshold": 0.0
  }
}
```

**Symbol 级（每标的 1 条，示例 SPY）**

```json
{
  "trace_type": "symbol",
  "timestamp": "2026-03-08T09:37:44.619913+00:00",
  "symbol": "SPY",
  "research_thesis": "Market may still be repricing stronger medium-term growth rather than just reacting to short-term momentum.",
  "opportunity_score": 0.574,
  "key_drivers": ["revenue growth", "margin resilience"],
  "risk_factors": ["valuation_risk"],
  "final_action": "entry"
}
```

---

## Trade / No-Trade 原因分析

### 本轮 Mock 实验

- **No-trade 的直接原因**：mock 下 `run_once` 使用固定价格与短窗口，未触发 Nautilus 实际下单，故 `trade_count=0`。
- **决策层**：allocator 已产生 3 个 `entry` 目标（SPY、QQQ、NVDA），`final_action=entry`，说明「可交易机会」已被识别并写入 symbol trace；未 trade 来自执行层/数据条件，而非 wait_confirmation 或 no_trade 决策。

### 真实/LLM 实验下常见 no-trade 原因

1. **wait_confirmation**  
   - 任一标的 `suggested_action in (wait_confirmation, watch)` 且不满足 probe 条件（confidence < medium 或 opportunity_score < threshold）时，整轮 `wait_any=True` → allocator 返回 no_trade，仅写 portfolio trace（reason=wait_confirmation）。  
   - **改进后**：若该标的 confidence ≥ medium 且 opportunity_score ≥ threshold，会走 **probe position**，不再整轮 no_trade。

2. **no_signals**  
   - 无 research 输出或 ranking 无有效信号 → 仅 portfolio trace，reason=no_signals。

3. **no_trigger**  
   - 日内 trigger 未触发（如 opportunity_risk 未达阈值）→ 该日不进入 allocator，无调仓。

4. **policy / health 约束**  
   - 替换被 min_gap、max_replacements、turnover_budget 或 health 收紧（如 concentration、beta、drawdown）限制 → symbol trace 中可见 `rejected` 或 `retain`，portfolio trace 中有 rationale。

### 验收要点（与任务目标对齐）

- 实验**不必强制产生交易**，但需满足：
  - **Symbol-level traces**：每个被研究的标的有对应 symbol trace（thesis、opportunity_score、key_drivers、risk_factors、final_action）。
  - **合理的 opportunity scoring**：分数在 [0, 1]，并能区分不同 confidence/risk/thesis 组合。
  - **更丰富的 research reasoning**：周报与 trace 中可见 thesis、key_drivers、risk_factors，便于事后分析 trade/no-trade 原因。

---

## 涉及文件（仅允许修改范围）

| 区域 | 文件 |
|------|------|
| research / policy / trace / opportunity | `autonomous/decision_trace.py`（PortfolioDecisionTrace, SymbolDecisionTrace） |
| | `autonomous/allocator.py`（双轨 trace、entry/retain symbol trace） |
| | `autonomous/opportunity_ranking.py`（score 归一化 0–1） |
| | `autonomous/portfolio_policy.py`（opportunity_score_probe_threshold） |
| | `pipeline/weekly_paper_pipe.py`（probe 逻辑、wait_any、symbol trace 补全） |
| | `services/weekly_finish_service.py`（portfolio_traces / symbol_traces 拆分） |
| | `services/replay_service.py`（兼容 key_drivers/risk_factors 与 trace_type） |

---

## 后续建议

1. 使用 **--llm** 跑 5 天实验，观察真实 research 下 opportunity_score 分布与 symbol trace 密度。
2. 若仍多日 no_trade，可微调 `opportunity_score_probe_threshold`（如 0.35）或检查 LLM 的 suggested_action/confidence 分布。
3. 可增加简单统计：周报中输出 `opportunity_score` 的 min/max/mean 及按 final_action 分组的数量，便于迭代策略与阈值。
