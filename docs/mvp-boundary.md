# Trading Agent MVP 边界（冻结）

## MVP 支持的 4 个用户动作

1. **开始建仓** — 运行一轮建仓 cycle，返回方案与建议，status = pending_confirmation  
2. **查看投资组合** — 返回当前组合摘要，status = ok  
3. **查看最新建议** — 读取最新待处理 proposal，返回方案与建议，status = pending_confirmation 或 no_proposal  
4. **确认执行** — 对最新 proposal 写入 approve 并执行，返回执行结果，status = ok 或 error  

## 系统分层

- **runtime**：负责交易逻辑（research / proposal / approval / execution）。  
- **bridge**：唯一用户入口 `handle_trading_intent_sync(message, config_path=None)`，统一调用 runtime，返回 `{ status, summary, details }`。  
- **agent**：只做自然语言输入输出（解析意图 → 调用 bridge → 把 status/summary/details 翻译成自然语言回复用户）。  

## 明确禁止

- agent 自己实现交易逻辑  
- agent 自己扫描 runs/ 或拼 artifact 路径  
- agent 暴露 exec / poll / shell / run_id 给用户  
- 新增新的用户面向 CLI 入口（唯一用户入口为 bridge 的 `handle_trading_intent_sync`，CLI 仅 `openclaw-trading-intent-sync` 作为对应该入口的 smoke）  
