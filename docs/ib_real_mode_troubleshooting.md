# IB Real Mode 排障与验证

## Timeout 根因

- **现象**：日志出现 `positions request timed out`，随后 `Account snapshot: source=mock`。
- **根因**：
  1. **API 调用**：超时发生在 **positions** 子步骤。`ib_insync` 在连接后会同步 account summary、positions、open orders；其中 `positions` 由 TWS/Gateway 汇总计算，在账户/合约较多或 Gateway 负载高时容易超过默认等待时间。
  2. **历史**：此前连接与 account/positions 共用同一 timeout（且默认偏小），一次超时即整段失败，直接 fallback mock。
- **当前设计**：
  - Snapshot 拆成 **account_summary**、**positions**、**open_orders** 三步，每步单独超时与日志。
  - **account_summary** 成功即可返回真实 equity/cash；**positions** 单独超时仅导致 positions=[]，并记录 `failed_steps`，source 为 `partial_real` 而非全量 mock。
  - 增加 **IBKR_POSITIONS_TIMEOUT**（默认 45s）、**IBKR_WARMUP_DELAY**（connect 后等待 2s 再发首包），减少「刚连上就大量请求」导致的超时。

## weekly-paper real mode 当前阻塞点

1. **Snapshot 全失败**：若 account_summary 也失败（或连接失败），则无真实 equity，会 fallback mock。
2. **positions 超时**：仅 positions 超时时会得到 `source=partial_real`、positions=[]，流程可继续；若下游强依赖持仓列表，需视业务决定是否接受 partial_real。
3. **Regime / Benchmark 慢**：SPY/VIX 与 benchmark 数据也走 IB；若 Gateway 慢，会看到 `regime context latency`、`benchmark latency` 偏高，一般不阻塞主链，仅影响耗时。

## 日志区分

- **IB snapshot**：`account_summary start/end`、`positions start/end`、`open_orders start/end`、`IB snapshot total`；超时时会打 `positions request timed out (source: positions step, timeout=Xs)`。
- **Regime**：`regime context latency: X.XXs`。
- **Benchmark**：`benchmark latency: X.XXs`。
- **结果**：`Account snapshot: source=ibkr|partial_real|mock`。

## 环境变量（可选调优）

| 变量 | 含义 | 默认 |
|------|------|------|
| IBKR_CONNECT_TIMEOUT | 连接超时（秒） | 60 |
| IBKR_POSITIONS_TIMEOUT | positions 请求超时（秒） | 45 |
| IBKR_WARMUP_DELAY | connect 后等待秒数 | 2 |
| IBKR_DISCONNECT_DELAY | 断开后等待秒数 | 1 |

## 最短验证命令（修复后）

```bash
python -m ai_trading_research_system.cli weekly-paper --symbols SPY,QQQ,NVDA --llm
```

- 需已配置 `IBKR_HOST`、`IBKR_PORT`，且 Gateway 已启动、API 已开启。
- 不加 `--mock` 时走 real 路径；日志中应出现 `IB session connected`、`account_summary start/end`、`positions start/end`，以及 `Account snapshot: source=ibkr` 或 `source=partial_real`（positions 超时时为 partial_real）。

---

## 性能预期：为什么比富途慢？是用法问题吗？

**结论：既有平台差异，也有我们为“求稳”加的延迟；用法上可以减掉一部分人为延迟。**

### 1. 平台差异（IB vs 富途）

| 方面 | IB Gateway / TWS | 富途等 |
|------|------------------|--------|
| 定位 | 通用经纪 + 多市场，合规与灵活性优先 | 往往针对零售/量化，接口更集中 |
| 数据接口 | 请求/应答式，历史数据有频率限制（如 60 次/10 分钟/合约类型） | 常见 WebSocket/推送、本地缓存，延迟更低 |
| 连接模型 | connect 后同步 account/positions 等，一步慢易整段超时 | 多为订阅制，数据就绪即推 |

所以**即使用法最优，IB 这边也很难做到和富途同级别的“传统量化”低延迟**，尤其是依赖 Gateway 逐次拉历史/账户时。

### 2. 我们人为加的延迟（可调）

为降低“刚连上就狂发请求”导致的断连/超时，当前实现里加了：

- **`IBKR_WARMUP_DELAY`**：connect 后等 2 秒再发首包（默认 2s）。
- **Snapshot 步骤间**：account_summary 后 `sleep(0.2)`，再请求 positions/open_orders。

这些在**连接/网关不稳时**能减少 timeout，但会直接拉高首包和 snapshot 的耗时。若你本地 Gateway 已稳定，可以优先把“人为延迟”降下来（见下）。

### 3. 请求模式（weekly-paper 为何更慢）

当前 weekly-paper 是**批量、按步骤串行**的用法，不是“高频、低延迟”的用法：

- 一次 snapshot：account_summary → positions → open_orders，三步串行。
- Regime：SPY 历史 + VIX 历史，两次拉取（可考虑后续并行）。
- 每个标的、每个 day：research 里 `get_latest_price` → 各标的单独拉 3 日线。
- Benchmark 已做内存缓存，同一 symbol+lookback 不会重复打 IB。

所以**同一轮里 IB 请求次数多、且全是串行**，总耗时 = 连接/预热 + 多次 round-trip。这和“传统高频/做市”的用法（长连、订阅、本地缓存）本身就不是一类场景。

### 4. 建议：在“求稳”和“能接受的速度”之间调参

- **先确认稳定**：能稳定拿到 `source=ibkr` 或 `partial_real`、不再频繁 timeout 后，再追求速度。
- **再减人为延迟**（按需在 `.env` 或环境变量里设）：
  - `IBKR_WARMUP_DELAY=0`：取消 connect 后 2s 等待（首包会更快，若之后出现 timeout 再改回 1～2）。
  - 代码里已把 snapshot 步骤间的 0.2s 改为 0.05s（仅 session 路径），在“稍留一点缓冲”和“少等一点”之间折中。
- **长期**：若要做“传统量化级”低延迟，更合适的是：
  - 用 IB 的**流式/订阅接口**（如 tick/account 订阅）配合本地缓存；或
  - 行情/执行分离，行情用更快的数据源，执行仍走 IB。

当前设计面向的是**周频/日频 paper**：一轮跑完以“分钟级”计是可接受的；若你希望“几十秒内跑完”，需要在上面的延迟和请求次数上继续压（以及接受一定稳定性风险）。
