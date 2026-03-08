# Trading Agent — 唯一入口

**用户 4 个动作**：开始建仓、查看投资组合、查看最新建议、确认执行。  
**唯一入口**：`openclaw.bridge.handle_trading_intent_sync(message, config_path=None)` → 返回 `{ status, summary, details }`。

- **status**：ok | pending_confirmation | no_proposal | error  
- **summary**：面向用户的简短说明，agent 直接或略作润色回复用户。  
- **details**：结构化数据，供系统/扩展用，不暴露路径/run_id 给用户话术。

Agent 只做：解析用户意图 → 调用该入口 → 仅用返回的 summary 生成自然语言回复，不得向用户输出 status/details 或任何内部词（如 bridge、platform、run_id、exec、shell）。禁止 exec、process:poll、shell。详见 docs/mvp-boundary.md。
