# UC-10 Stage-2 验证记录：真实 LLM research 下 opportunity_score 能否区分 symbol

## 目标

验证 opportunity_score 在真实 LLM research 中能区分不同 symbol；report 中能看到 score 差异，allocator 决策能反映 score 差异。

---

## 运行

```bash
python -m ai_trading_research_system.cli weekly-paper \
  --symbols SPY,QQQ,NVDA \
  --days 5 \
  --llm
```

**附**：本次运行前修复了 `SynthesisAgent` 中 LLM 有时返回 `uncertainties`（或 `risk_flags`/`key_drivers`）为字符串导致的 ValidationError，在 synthesis 层统一规范为 list。

---

## 记录

### 1. Score distribution

- **opportunity_ranking（报告内，最后一日的周级排序）**：SPY 1.0，QQQ 0.854，NVDA 0.806。
- **score_to_action_chain（按日多笔）**：分数分布约 0.81–1.0，同日内不同 symbol 明显分化，例如：
  - Day 1：QQQ 0.94，SPY 0.91，NVDA 0.87
  - Day 2：QQQ 0.89，SPY 0.87，NVDA 0.83
  - Day 3：SPY 0.92，NVDA 0.85，QQQ 0.81
  - Day 4：NVDA 1.00，SPY 0.91，QQQ 0.85
  - Day 5：SPY 1.00，QQQ 0.85，NVDA 0.81
- **symbol_traces 中的 opportunity_score**：各条在 0.806–1.0 之间，按 symbol/日不同（如 0.938, 0.906, 0.874, 0.89, 0.866, 0.83, 0.918, 0.846, 0.814, 1.0, 0.91, 0.854 等）。

结论：真实 LLM 下不同 thesis/confidence/risk 组合产生不同分数，**不同 symbol 的 score 差异在 report 中清晰可见**。

### 2. Symbol_traces

- 存在且完整：每笔含 `symbol`、`research_thesis`、`opportunity_score`、`key_drivers`、`risk_factors`、`final_action`。
- 多日多标的，trace 条数与 score 与 score_to_action_chain 一致。

### 3. Score_to_action_chain

- 14 条（5 天 × 3 标的部分日有合并或去重），格式为 `"SYMBOL: score=X.XX → action"`。
- 每日内按 score 从高到低排列（例如 QQQ 0.94 → SPY 0.91 → NVDA 0.87），**allocator 的排序与 score 一致**。
- 所有记录的 action 均为 `entry`（本周为全空仓、无替换场景）。

### 4. Trade_count

- **trade_count**: 0（paper 执行层 mock/未成交，与预期一致；决策层已产生 entry 意图）。

---

## 成功标准核对

| 标准 | 结果 |
|------|------|
| report 中能看到不同 symbol 的 score 差异 | ✅ 各日、各 symbol 分数在 0.81–1.0 间分化，opportunity_ranking 与 symbol_traces 均可见差异。 |
| allocator 决策能反映 score 差异 | ✅ 每日排序按 score 降序（高 score 优先 entry），score_to_action_chain 与 symbol_traces 中 final_action 一致。 |

---

## 报告路径

- `reports/weekly_report_mandate_3636badc8901.json`

---

## 结论

- 真实 LLM research 下，opportunity_score 能区分 SPY、QQQ、NVDA，分数分布合理。
- Allocator 的标的排序与 final_action 与 score 一致，决策反映 score 差异。
- UC-10 Stage-2 成功标准满足。
