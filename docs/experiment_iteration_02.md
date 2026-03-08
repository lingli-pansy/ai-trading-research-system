# UC-10 Stage-1 实验迭代 02 — 基于现有结果的内部分析摘要

## 阅读的现有结果

- **experiment_iteration_01.md**：已实现 portfolio/symbol 双轨 trace、probe 条件（confidence≥medium, score≥0.4）、opportunity score [0,1] 归一化。
- **backtest_result_20250308.md**：回测命令与 mock 结果（非 weekly-paper）。
- **weekly_report_test_mandate_real_1.json**（real）：trade_count=0，daily_research/opportunity_ranking/decision_traces 均为空或 traces=[]，research_reasoning_summary 为空。
- **weekly_report_mandate_998b9689cdfc.json**（mock）：有 daily_research（NVDA/AAPL）、opportunity_ranking（两标的均为 0.574），但 **symbol_traces 为空**，decision_traces_summary 仅有 portfolio_traces。
- **weekly_report_mandate_25bb50054341.json**：单标的 SPY，score=1.935（未归一化？），symbol_traces 未查看完整。

## 明确结论

### 1. 当前 no_trade 的主要原因

- **Real 报告**：no_trade_reasons 为空，且无 decision_traces，可能整周未进入 allocator（例如全部 no_trigger）或 report 未正确聚合原因。
- **Mock 报告**：有 trigger（opportunity_risk_high），进入 allocator；若 wait_any=True 则 no_trade_reason=wait_confirmation；若 no_trigger 则 no_trade_reasons 仅含 "no_trigger"。当前 report 在“有 trigger 且 wait_confirmation”时，no_trade_reasons 会得到 "wait_confirmation"。
- **结论**：no_trade 主要来自 (1) no_trigger，(2) wait_confirmation（任一标的不满足 probe 且 suggest wait/watch），(3) no_signals，(4) no_valid_signals（allocator 跑完但 targets 为空）。Report 需能明确写出这些原因。

### 2. Symbol-level trace 是否足够丰富

- **不足**。现有 JSON 中 symbol_traces 常为空。原因：(1) wait_confirmation 时 allocator 直接 return，不产出 symbol trace，仅 pipe 在 `wait_any and alloc_result.no_trade` 时补全；(2) 补全的 trace 缺少 **no_trade_reason** 字段，无法区分“因 wait_confirmation”还是“因 score 低/health 约束”；(3) 非 wait 但 no_trade（如 no_valid_signals）时，allocator 可能只产出 portfolio trace，无每标的说明。

### 3. Probe 是否真的触发过

- 条件：confidence in (medium, high) 且 opportunity_score ≥ 0.4（或 policy 的 opportunity_score_probe_threshold）。Mock 下 NVDA/AAPL 均为 0.574、probe_small，会走 probe，wait_any=False，allocator 会收到 size_fraction=0.03 的 signals。若 real 下 research 常返回 wait_confirmation/watch 且 score<0.4，则 probe 不会触发。

### 4. opportunity_score 是否真正影响 allocator

- **有影响**：allocator 按 score 排序、做替换时用 score_gap。但 (1) 归一化公式 `(raw-0.5)/2.5` 易使多标的聚在 0.5 附近（如 0.574, 0.574），区分度不足；(2) report 中 symbol_traces 为空时，无法在周报里“看到”谁因 score 被拒/谁被替换。

### 5. Report 中最缺的信息

- 为什么没交易（no_trade 的明确原因：no_trigger / wait_confirmation / score_too_low / health_constraint / trigger_rejected / probe_threshold_not_met）。
- 每标的的 thesis、opportunity_score、final_action、以及 **no_trade_reason**（当未交易时）。
- 哪些 symbol 被拒绝、rejection/replacement 的理由（score_gap、max_replacements、turnover_budget 等）。

---

## 最小问题集合（本轮锁定）

| 序号 | 问题 | 优先级 |
|------|------|--------|
| A | symbol_traces 常为空；no_trade 时缺少 no_trade_reason 字段 | 高 |
| B | opportunity_score 区分度不足，多标的同分 | 中 |
| C | report 的 decision_traces_summary.summary 无法直接读出“为什么没交易” | 高 |
| D | research_reasoning 从 daily_research 未落入 research_reasoning_summary | 中 |

---

## 本轮小步优化方向

1. **Symbol-level trace**：确保每次有 ranking 时周报必有 symbol_traces；SymbolDecisionTrace 增加可选 no_trade_reason；pipe 在补全 no_trade 的 symbol trace 时写入 no_trade_reason（如 wait_confirmation）。
2. **Opportunity score**：微调归一化或 thesis_strength 权重，拉开分数差距，避免全部聚在 0.5–0.6。
3. **Weekly report**：decision_traces_summary.summary 在 no_trade 时根据 no_trade_reasons 生成一句可读解释；research_reasoning_summary 可从 daily_research 回填 per_symbol。
4. **Probe**：不放宽 guardrails，仅确保逻辑清晰、在 trace/report 中可辨认“probe 已触发”或“未触发因 score/confidence 不足”。

---

## 本轮已做（小步优化）

1. **SymbolDecisionTrace 增加 no_trade_reason**
   - 当 final_action=no_trade 时可选填：wait_confirmation / score_too_low / no_valid_signals 等；to_dict 仅在有值时输出该字段。

2. **Pipe 补全 symbol traces 并写入 no_trade_reason**
   - wait_any 且 no_trade 时：为每个 ranked 标的追加 symbol trace，no_trade_reason=alloc_result.no_trade_reason（如 wait_confirmation）。
   - 非 wait 但 no_trade（如 no_valid_signals）且 allocator 未产出该标的 trace 时：按 ranked 补全 symbol trace 并写入 no_trade_reason。

3. **Opportunity score 区分度**
   - thesis_strength 分母 200→150、raw 中 thesis 权重 1.0→1.2、归一化分母 2.5→2.0，使典型分数更分散（如 0.5–0.6 → 约 0.65–0.88）。

4. **Weekly report 可解释 no_trade**
   - decision_traces_summary.summary：当 no_trade_reasons 非空时，前缀「未交易原因：no_trigger、wait_confirmation、…」。
   - research_reasoning_summary：从 daily_research 补全 per_symbol（thesis、key_drivers），避免 symbol_traces 为空时周报无 research 摘要。

5. **测试**
   - test_finish_week_no_trade_reasons_in_summary：no_trade_reasons 非空时 summary 含「未交易原因」及具体原因。
   - test_symbol_decision_trace_no_trade_reason：SymbolDecisionTrace 含 no_trade_reason 时 to_dict 输出该字段。
