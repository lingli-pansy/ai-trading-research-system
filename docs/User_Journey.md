
# AI Trading Research System — User Journey & Use Cases

## 文档目的
本文件用于梳理 AI Trading Research System 的核心用户场景（User Cases）与完整用户旅程（User Journey）。
目标是帮助开发者、研究者以及系统设计者理解：

- 谁在使用系统
- 用户如何与系统交互
- 系统内部如何协同工作
- 从研究到交易的完整流程

本文件适合作为：
- 系统设计参考
- Agent 设计参考
- CLI / OpenClaw 设计参考
- 产品路线图参考

---

# 一、系统角色（System Actors）

系统涉及五类角色：

1. 开发者（Developer）
2. 研究员（Researcher / Analyst）
3. 交易员（Trader）
4. 自动运行系统（Scheduler / Automation）
5. AI Agents（Research / Strategy / Experience）

---

# 二、User Case 列表

UC-01 — 第一次运行系统（First Demo）  
UC-02 — AI 研究股票  
UC-03 — 研究转策略（Research → Strategy）  
UC-04 — 策略回测（Backtest）  
UC-05 — Paper Trading（模拟交易）  
UC-06 — OpenClaw 调用系统  
UC-07 — 定时自动运行  
UC-08 — 经验学习与策略进化  

---

# 三、User Case 详细说明

## UC-01 第一次运行系统

目标：
新用户快速验证系统能运行。

用户：
开发者 / 新贡献者

操作（与 README 首屏主线一致）：

    pip install -e .
    python scripts/check_dev_prerequisites.py
    python cli.py demo NVDA --mock
    python scripts/run_e2e_check.py NVDA --mock
    python cli.py research NVDA --mock   # 或 run_for_openclaw.py research NVDA --mock（OpenClaw 示例）

系统执行流程：

    Research Pipeline → DecisionContract → Strategy → Backtest → Experience Store → Summary

输出（四块）：

【1】研究结论（thesis、confidence、suggested_action 等）  
【2】策略生成（action、allowed_position_size、rationale）  
【3】回测结果（sharpe、max_drawdown、win_rate、pnl、trade_count）  
【4】交易总结（执行引擎: NautilusTrader；strategy_run_id）

说明：`--mock` 可免网络；真实数据可省略 `--mock`。回测 trade_count 可能为 0（如 suggested_action=wait_confirmation 时不下单），属正常。

价值：
3 分钟内理解系统价值。

---

## UC-02 AI 研究股票

目标：
让 AI 分析一个股票。

用户：
研究员 / AI 用户

操作：

    python cli.py research NVDA

系统执行：

News Agent  
Fundamental Agent  
Technical Agent  
Bull Agent  
Bear Agent  
Uncertainty Agent  

然后：

Synthesis Agent  
→ DecisionContract

输出示例：

symbol: NVDA  
thesis: AI demand accelerating  
confidence: medium  
suggested_action: wait_confirmation  

---

## UC-03 Research → Strategy

目标：
把研究转成可回测策略。

输入：
DecisionContract

Contract + 回测验证 → StrategySpec（entry_logic、exit_logic、stop_loss、position_size 等）→ StrategyCompiler → AISignalStrategy → Nautilus。

---

## UC-04 策略回测

目标：
验证策略质量。

用户：
交易员

操作：

    python cli.py backtest NVDA [--mock] [--start YYYY-MM-DD] [--end YYYY-MM-DD]

系统执行：

Research → Contract → ContractTranslator → AISignal → NautilusTrader Backtest → Experience Store

输出（CLI 打印）：

symbol、contract action、confidence、sharpe、max_drawdown、win_rate、pnl、trades、strategy_run_id

说明：若 Research 输出为 wait_confirmation 等观望信号，trade_count 可能为 0，属正常；见 [result_schema.md](result_schema.md) status=no_trade。

---

## UC-05 Paper Trading

目标：
在实时市场模拟交易。

用户：
交易员 / 系统

操作：

    python cli.py paper --symbol NVDA [--mock] [--llm]

说明：paper 子命令使用 `--symbol`，默认 NVDA 时可写 `python cli.py paper`。

系统执行：

DecisionContract → Strategy → NautilusTrader Paper（或配置 IBKR 时 TWS Paper）。

输出：

contract、signal、order_done、message（含回测/paper 指标）。

---

## UC-06 OpenClaw 调用系统

目标：
通过 AI 控制系统。

用户：
OpenClaw Agent

调用：

    python scripts/run_for_openclaw.py research NVDA [--mock] [--llm]
    python scripts/run_for_openclaw.py backtest NVDA [--mock]
    python scripts/run_for_openclaw.py demo NVDA [--mock]

成功时：退出码 0，**仅 stdout** 输出单条 JSON。失败时：退出码非 0，**仅 stderr** 输出错误 JSON（ok、command、error_code、error_message）。

返回 JSON（含以下核心字段，完整见 [openclaw_integration.md](openclaw_integration.md)）：

task、symbol、completed_at、contract_action、contract_confidence、thesis_snippet、raw_contract、engine_type、used_nautilus、status、reason（research 无 reason；backtest/demo 在 trade_count=0 时为 status=no_trade、reason=wait_confirmation）。

---

## UC-07 自动调度运行

目标：
每日自动执行研究与交易。

用户：
Scheduler

执行：

    run_scheduled.py

流程：

for symbol in watchlist:
    research
    decision
    paper trading
    store results

---

## UC-08 经验学习

目标：
让系统持续进化。

Experience Agent 消费 BacktestResult、Trade/Paper logs，产出 ExperienceRecord；回测/实盘结果驱动策略进化与下一轮研究注入。

---

# 四、完整 User Journey

User / Scheduler / OpenClaw Trigger  
        ↓
Research Orchestrator（Agents）  
        ↓
DecisionContract  
        ↓
Strategy（StrategySpec + StrategyCompiler）  
        ↓
NautilusTrader Engine（Backtest / Paper / Live）  
        ↓
Experience Store  
        ↓
Strategy Refinement / 下一轮研究注入

---

# 五、系统分层

Research Layer：News / Fundamental / Technical / Bull-Bear / Synthesis（或 LLMResearchAgent）→ DecisionContract  

Decision Layer：DecisionContract（见 [decision_contract.md](decision_contract.md)）  

Strategy Layer：StrategySpec、Strategy Generator、StrategyCompiler（见 [strategy_spec.md](strategy_spec.md)）  

Execution Layer：NautilusTrader（Backtest、Paper、Live）  

Learning Layer：Experience Store；Strategy Evolution / 经验注入

---

# 六、系统定位

AI Trading Research System 不是简单的 Trading Bot。

它的目标是：

AI Research Lab  
+  
Professional Trading Engine

LLM 负责：

- 研究
- 假设生成
- 策略设计
- 经验总结

NautilusTrader 负责：

- 回测
- 订单管理
- 交易执行
- Portfolio 管理

---

# 七、未来扩展

未来可以增加：

- Multi‑asset support（crypto / futures）
- Multi‑agent research
- Reinforcement learning policy
- Autonomous strategy evolution

---

# 八、总结

本系统通过以下闭环实现长期进化：

Research  
→ Strategy  
→ Backtest  
→ Paper  
→ Experience  
→ Strategy Evolution

目标：

构建一个能够持续学习和优化交易策略的 AI 研究系统。
