# Mock 与真实实现对照

各模块 Mock vs 真实实现及替换优先级。

---

## 按模块

- **数据**：use_mock=True 时 MockDataProvider；未配 API Key 时 LLM 占位。
- **Research Agent**：Bull/Bear 等可写死；可与 use_llm=True 的 LLMResearchAgent 二选一；News/Technical/Synthesis 为实逻辑。
- **IB Gateway、LLM API**：已支持；配置见 [dev_prerequisites.md](dev_prerequisites.md)。

---

## 参考

- 当前状态：[../operations.md](../operations.md)、[CURRENT_STATE.md](CURRENT_STATE.md)
