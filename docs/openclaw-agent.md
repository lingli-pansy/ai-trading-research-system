# OpenClaw Agent 接入说明

**几分钟内：用配置驱动 paper 模式跑一次或持续 loop。**

**推荐入口（OpenClaw 项目接入）**：见仓库根 **AGENTS.md** 与 **docs/openclaw-project-setup.md**。三类入口：  
1）项目接入准备：AGENTS.md、skills/trading-approver/SKILL.md；  
2）项目内 smoke：openclaw-approver-smoke；  
3）运行主链路：openclaw-agent-once --config configs/openclaw_agent.paper.yaml。

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

- **不推荐（compat）**：直接调用 `run_autonomous_paper_cycle_report`、`scripts/run_for_openclaw.py` 零散传参或多入口并存的用法；仅保留兼容，不作为官方入口。
- **推荐**：用 **配置文件 + openclaw-agent-once / openclaw-agent-loop**，或编程时使用 **OpenClawAgentConfig + openclaw.agent_adapter**。项目接入与 smoke 见 **AGENTS.md** 与 **docs/openclaw-project-setup.md**。

---

## 8. OpenClaw 飞书（Feishu）渠道配置

通过飞书与 OpenClaw 对话、进而触发本仓 Skill 时，需在 **OpenClaw 侧** 配置飞书 channel（本仓 `configs/openclaw_agent.paper.yaml` 仅负责 Agent 运行参数，不包含渠道）。

### 快速步骤

1. **安装飞书插件**
   ```bash
   openclaw plugins install @openclaw/feishu
   ```

2. **创建飞书应用**（[飞书开放平台](https://open.feishu.cn/app)）
   - 创建企业自建应用，获取 **App ID**（如 `cli_xxx`）和 **App Secret**
   - 权限管理：批量导入官方文档中的权限 JSON（含 `im:message`、`im:message:send_as_bot` 等）
   - 应用能力 → 机器人：开启机器人能力
   - 事件订阅：添加 `im.message.receive_v1`，选择 **使用长连接接收事件（WebSocket）**
   - 发布应用

3. **在 OpenClaw 中添加飞书渠道**
   ```bash
   openclaw channels add
   ```
   选择 Feishu，按提示输入 App ID 和 App Secret。或直接编辑 `~/.openclaw/openclaw.json`：

   ```json
   {
     "channels": {
       "feishu": {
         "enabled": true,
         "dmPolicy": "pairing",
         "accounts": {
           "main": {
             "appId": "cli_xxx",
             "appSecret": "xxx",
             "botName": "我的AI助手"
           }
         }
       }
     }
   }
   ```

4. **启动网关并配对**
   ```bash
   openclaw gateway
   ```
   在飞书里给机器人发消息后，若为私聊需批准配对：
   ```bash
   openclaw pairing approve feishu <配对码>
   ```

### 环境变量方式

```bash
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"
```

### 将飞书从 main 改为 trading（bindings）

飞书默认会路由到 **main** agent。要让飞书使用本仓的 **trading** agent，需在 `~/.openclaw/openclaw.json` 里配置 **bindings**（与 `channels`、`agents` 同级）。

1. **确认已有 trading agent**  
   本仓脚本 `scripts/set_openclaw_workspace.py` 会在 `agents.list` 里加入 `id: "trading"`。若未跑过，先执行一次：  
   `uv run python scripts/set_openclaw_workspace.py`

2. **获取要绑定的 ID**  
   - **私聊**：用户 Open ID 格式为 `ou_xxx`。可运行 `openclaw pairing list feishu` 查看待审批列表中的用户 ID；或 `openclaw logs --follow` 后在飞书发一条消息，从日志里看 `open_id`。  
   - **群组**：群组 ID 格式为 `oc_xxx`。在群组里 @ 机器人发一条消息，从 `openclaw logs --follow` 的日志里看 `chat_id`。

3. **在 openclaw.json 中添加 bindings**  
   在文件顶层增加 `"bindings"` 数组（若已有则追加一条），例如：

   **绑定某个飞书私聊到 trading：**
   ```json
   "bindings": [
     {
       "agentId": "trading",
       "match": {
         "channel": "feishu",
         "peer": { "kind": "dm", "id": "ou_你的用户open_id" }
       }
     }
   ]
   ```

   **绑定某个飞书群组到 trading：**
   ```json
   "bindings": [
     {
       "agentId": "trading",
       "match": {
         "channel": "feishu",
         "peer": { "kind": "group", "id": "oc_群组id" }
       }
     }
   ]
   ```

   可同时存在多条，分别绑定不同用户或群组到 `trading`。

4. **重启网关并验证**  
   ```bash
   openclaw gateway restart
   ```
   验证绑定是否生效：  
   ```bash
   openclaw agents list --bindings
   ```  
   再在飞书里发消息，应由 **trading** agent 回复（会按本仓 AGENTS.md / skills 作答）。

> 官方说明：[飞书 - 多 Agent 路由](https://docs.openclaw.ai/zh-CN/channels/feishu)。未匹配到任何 binding 时，飞书消息会继续走 **main** agent。

### 更多说明

- 群组策略、@ 提及、多 Agent 绑定等见官方文档：[飞书 - OpenClaw](https://docs.openclaw.ai/zh-CN/channels/feishu)
- 常用命令：`openclaw gateway status`、`openclaw logs --follow`

### 故障排除

**1. 插件加载失败：`Cannot find module '@larksuiteoapi/node-sdk'`**

飞书插件依赖 `@larksuiteoapi/node-sdk`，若通过 Homebrew 安装 OpenClaw，运行时可能使用自带扩展目录且未安装依赖。在**实际加载的扩展目录**下执行 `npm install` 安装依赖即可。

- 若日志显示从 Homebrew 路径加载（如 `/opt/homebrew/lib/node_modules/openclaw/extensions/feishu`）：
  ```bash
  cd /opt/homebrew/lib/node_modules/openclaw/extensions/feishu && npm install
  ```
- 若使用用户安装的扩展（`~/.openclaw/extensions/feishu`）：
  ```bash
  cd ~/.openclaw/extensions/feishu && npm install
  ```
  完成后执行 `openclaw gateway restart` 再试。

**2. “feishu does not support onboarding yet”**

飞书渠道当前不支持 `openclaw channels add` 的交互式引导。请跳过向导，**直接编辑** `~/.openclaw/openclaw.json`，在 `channels` 下添加上述 `feishu` 配置（App ID、App Secret、botName 等），保存后启动网关。

**3. 安全提示 “dangerous code patterns”**

安装时若出现 “Environment variable access combined with network send” 等提示，为插件代码的静态检查告警，不影响正常使用。若需仅允许受信插件，可在配置中设置 `plugins.allow: ["feishu"]`。

---

**配置字段说明**：见 `openclaw.config.OpenClawAgentConfig`；示例见 `configs/openclaw_agent.paper.yaml`。
