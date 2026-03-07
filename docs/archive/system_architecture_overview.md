
# AI Trading Research System — System Architecture Overview

This document defines the **target architecture** of the AI Trading Research System.

Goals:
- Align Research / Strategy / Execution layers
- Define Portfolio Autonomous Control
- Integrate Experience Learning Loop
- Provide a stable architecture reference for development

Core principles:

1. **LLM handles research, reasoning, and strategy evolution**
2. **Deterministic services control accounts, risk limits, and execution**
3. **NautilusTrader provides the unified trading engine**

---

# High-Level Architecture

User / OpenClaw
        │
        ▼
Mandate Interpreter (LLM)
        │
        ▼
Autonomous Portfolio Controller
        │
 ┌──────┴───────────────────────────────┐
 │                                      │
 ▼                                      ▼
Account Snapshot                 Execution State Machine
 │                                      │
 ▼                                      ▼
Research Agents (TradingAgents)         │
 │                                      │
 ▼                                      │
Decision Contract                       │
 │                                      │
 ▼                                      │
Strategy Generator / StrategySpec       │
 │                                      │
 ▼                                      │
Portfolio Allocator                     │
 │                                      │
 ▼                                      ▼
Risk Guard Rails                NautilusTrader Engine
                                      │
                                      ▼
                                Result Schema
                                      │
            ┌─────────────────────────┴────────────────────────┐
            ▼                                                  ▼
     Benchmark Comparator                               Experience Store
            │                                                  │
            ▼                                                  ▼
       Weekly Report                                   Strategy Refiner

---

# Layer Descriptions

## 1. User / OpenClaw

The system entry point.

Example user command:

"Allocate 10k USD to the paper account, trade automatically for one week, compare performance with SPY."

OpenClaw forwards this instruction to the system.

---

## 2. Mandate Interpreter (LLM)

Converts natural language goals into a structured object:

WeeklyTradingMandate

Typical fields:

- capital_limit
- benchmark
- duration
- auto_confirm
- rebalance_policy
- risk_profile
- max_positions
- stop_conditions

---

## 3. Autonomous Portfolio Controller

The central coordinator of the system.

Responsibilities:

- Read account state
- Generate execution plans
- Trigger research and strategy pipelines
- Manage the execution state machine
- Trigger reporting and experience storage

---

## 4. Account Snapshot

Provides a consistent view of the account:

- cash
- equity
- positions
- open_orders
- risk_budget

---

## 5. Research Layer (LLM Agents)

Typically implemented using TradingAgents.

Agents may include:

- News Agent
- Fundamental Agent
- Technical Agent
- Bull Thesis Agent
- Bear Thesis Agent
- Uncertainty Agent
- Synthesis Agent

Output:

DecisionContract

---

## 6. Strategy Layer

Transforms research into executable strategies.

Components:

- Strategy Generator
- StrategySpec
- Strategy Refiner
- Strategy Compiler

---

## 7. Portfolio Allocation

PortfolioAllocator determines target positions.

Responsibilities:

- Position sizing
- Position limits
- Cash reserve management
- Translating signals into portfolio allocation

Output:

target_positions

---

## 8. Risk Guard Rails

Hard safety constraints:

- max account exposure
- max position size
- daily loss limit
- weekly drawdown stop
- kill switch

These limits must be deterministic and cannot be overridden by LLM decisions.

---

## 9. Execution Engine

Provided by NautilusTrader.

Responsibilities:

- Backtesting
- Paper trading
- Live trading
- Order lifecycle management
- Portfolio tracking

---

## 10. Result Schema

Defines a unified output format for trading results.

Example fields:

- engine_type
- used_nautilus
- trade_count
- pnl
- drawdown
- status
- no_trade_reason

---

## 11. Benchmark Comparator

Evaluates portfolio performance relative to a benchmark.

Outputs:

- portfolio_return
- benchmark_return
- excess_return
- drawdown

---

## 12. Experience Store

Stores system learning signals.

Tables typically include:

- strategy_run
- backtest_result
- trade_experience
- experience_summary

---

## 13. Strategy Evolution

Experience-driven improvement loop.

Experience → StrategyRefiner → Improved StrategySpec

Full learning loop:

Research
→ Strategy
→ Execution
→ Experience
→ Strategy Evolution

---

# System Goal

Build an **AI-driven autonomous trading research system** capable of:

- Market research
- Strategy generation
- Trade execution
- Performance evaluation
- Experience accumulation
- Continuous strategy evolution
