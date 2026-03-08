# OpenClaw 项目接入与部署说明

面向“让 OpenClaw 识别并接入本仓库”的配置与**部署步骤**（参考 [OpenClaw 官方文档](https://docs.openclaw.ai) 最新版本）。

---

## 一、路径与识别

### 1. OpenClaw 如何识别这个项目

- OpenClaw 通过 **agent workspace** 加载项目：工作区根目录下的 `AGENTS.md` 会在会话开始时被加载，`skills/` 为工作区技能目录。
- **本仓库作为 workspace**：将 **本仓库根目录** 设为 OpenClaw 的 agent workspace，则 `AGENTS.md`、`skills/trading-approver/SKILL.md` 会被正确识别。

### 2. AGENTS.md 与 skill 路径

- **AGENTS.md**：仓库根目录（即 workspace 根目录）。  
- **Workspace skill**：`skills/trading-approver/SKILL.md`（proposal approval，不写泛化交易）。  
- 若工具链需要 `CLAUDE.md`：在仓库根执行 `ln -sf AGENTS.md CLAUDE.md`。

---

## 二、部署步骤（按最新 OpenClaw 流程）

### 前置

- **Node**：22 或更高（`node --version`）。
- **本仓**：已克隆到本地，例如 `~/ai-trading-research-system`（下用 `REPO_ROOT` 表示）。

### 步骤 1：安装 OpenClaw

**macOS / Linux：**

```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

**Windows (PowerShell)：**

```powershell
iwr -useb https://openclaw.ai/install.ps1 | iex
```

其他方式见：<https://docs.openclaw.ai/install>。

### 步骤 2：运行引导并安装服务（可选）

```bash
openclaw onboard --install-daemon
```

向导会配置认证、网关与可选渠道。若仅本地验证本仓配置，可先跳过渠道，仅完成基础配置。

### 步骤 3：将 agent workspace 设为本仓库根目录

让 OpenClaw 使用本仓的 `AGENTS.md` 和 `skills/`：

**方式 A：通过配置文件**

编辑 `~/.openclaw/openclaw.json`，设置 workspace 为**本仓库的绝对路径**（当前 OpenClaw 使用 `agents.defaults`，不再使用已弃用的 `agent`）：

```json5
{
  agents: {
    defaults: {
      workspace: "/Users/你的用户名/ai-trading-research-system",
      skipBootstrap: true,
    },
  },
}
```

**或直接在本仓执行脚本（推荐）**：

```bash
uv run python scripts/set_openclaw_workspace.py
```

**方式 B：通过 CLI（若支持）**

```bash
openclaw setup --workspace /path/to/ai-trading-research-system
```

（具体以当前版本 `openclaw setup --help` 为准。）

### 步骤 4：补全工作区文件（可选）

OpenClaw 首次使用 workspace 时可能会创建默认的 `IDENTITY.md`、`SOUL.md` 等。本仓已有 `AGENTS.md` 和 `skills/`，若希望保留本仓内容且避免被覆盖，在 `agents.defaults` 中设置 `skipBootstrap: true`（脚本已包含）。

然后确认本仓根目录存在 `AGENTS.md`、`skills/trading-approver/SKILL.md`。

### 步骤 5：启动网关并验证

```bash
openclaw gateway status   # 若已安装 daemon，检查状态
# 或前台运行
openclaw gateway --port 18789
```

打开控制界面：

```bash
openclaw dashboard
```

浏览器访问默认地址：<http://127.0.0.1:18789/>。此时 OpenClaw 会使用你配置的 workspace（本仓根目录），加载 `AGENTS.md` 与 `skills/trading-approver/`。

### 步骤 6：本仓内验证（不依赖 live 对话）

在**本仓库根目录**执行：

1. **最小配置检查**  
   ```bash
   uv run python scripts/verify_openclaw_setup.py
   ```  
   确认输出中 `AGENTS.md`、`skills/trading-approver/SKILL.md`、`docs/openclaw-project-setup.md` 均存在。

2. **单轮 approver smoke**  
   ```bash
   uv run python -m ai_trading_research_system.presentation.cli openclaw-approver-smoke --config configs/openclaw_agent.paper.yaml
   ```  
   可选：`--raw "I recommend approving this trade"` 验证解析为 approve。  
   用于确认 proposal → prompt input → user message → raw output → parsed/normalized 链在本仓可跑通。

3. **主链路单次运行**  
   ```bash
   uv run python -m ai_trading_research_system.presentation.cli openclaw-agent-once --config configs/openclaw_agent.paper.yaml
   ```

---

## 三、入口汇总

| 用途             | 入口 |
|------------------|------|
| 项目接入准备     | `AGENTS.md`，`skills/trading-approver/SKILL.md` |
| OpenClaw 路径    | 将 **agent workspace** 设为本仓库根目录 |
| 项目内 smoke     | `openclaw-approver-smoke --config configs/openclaw_agent.paper.yaml` |
| 运行主链路       | `openclaw-agent-once --config configs/openclaw_agent.paper.yaml` |

---

## 四、当前尚未完成

- **Live invocation**：通过飞书/网关等渠道在 OpenClaw 里“对话触发本仓 skill”的端到端尚未正式接好；当前以**项目内配置 + smoke 就绪**为主。  
- **多轮对话 / 复杂编排**：未做；仅单轮 proposal → approval → execution。

---

## 五、验证配置成功

在**本仓库根目录**依次执行下面 3 步，全部通过即表示配置成功。

**1. 项目文件检查**

```bash
uv run python scripts/verify_openclaw_setup.py
```

期望：输出 `OK AGENTS.md`、`OK skills/trading-approver/SKILL.md`、`OK docs/openclaw-project-setup.md`，最后一行 `Project is ready for OpenClaw onboarding`。

**2. Approver 联调 smoke（不接 live）**

```bash
uv run python -m ai_trading_research_system.presentation.cli openclaw-approver-smoke --config configs/openclaw_agent.paper.yaml
```

期望：有 `RUN_ID`、`PROMPT_INPUT_PATH`、`USER_MESSAGE_PATH`、`NORMALIZED_DECISION` 等输出，且无报错。

**3. 在 OpenClaw 控制界面里确认 workspace**

- **TUI**：运行 `openclaw tui` 后，按 **Ctrl+G** 打开 agent 选择器，选择 **trading**（本仓专用 agent），再问「这个项目是做什么的？我的 agent 角色是什么？」。若选的是默认的 main，会读到 OpenClaw 安装目录的文档，而不是本仓 `AGENTS.md`。
- **Dashboard**：若用浏览器控制界面，同样需在会话里选择 agent 为 **trading**（若有选择器）。
- 若 agent 能根据 `AGENTS.md` 回答「AI trading runtime」「proposal approver」等，说明已正确加载本仓 workspace。

以上 1～3 都通过，即表示 **OpenClaw + 本仓 agent 配置验证成功**。

---

## 六、沙盒与 Core Files 说明

**沙盒模式（Sandbox）**  
- 若在配置中开启了 `agents.defaults.sandbox`，OpenClaw 会在沙箱副本（如 `~/.openclaw/sandboxes`）中执行工具，而不是直接读写本仓。  
- 对本仓的**只读**（如 agent 读 `AGENTS.md`、`skills/`）一般仍可用；若发现 agent 读不到本仓文件，可检查 Gateway 配置中的 sandbox / workspaceAccess。  
- 本仓仅作 proposal approver，不依赖沙箱内写文件，通常**不开启沙箱也可用**。

**应用新 agent（trading）而不是 main**  
- 本仓脚本会在 `agents.list` 里加入 **trading** agent（workspace 指向本仓），并设 `default: true`，这样 Dashboard/TUI 会优先用 trading 而不是 main。  
- 若 Dashboard 里仍只看到 main：请**重启 Gateway** 后刷新；或在 TUI 里按 **Ctrl+G** 选择 **trading**。  
- main 的 workspace 多为 `~/.openclaw/workspace`，会读 OpenClaw 自带文档；trading 的 workspace 才是本仓，会读 `AGENTS.md`。

**Core Files 的「MISSING」与替换结果**  
- 我们设置了 `skipBootstrap: true`，**故意**不生成 SOUL.md、USER.md、BOOTSTRAP.md 等，避免覆盖本仓。  
- 本仓已提供最小 **IDENTITY.md**、**SOUL.md**（身份与行为约束），Dashboard 的 Core Files 里这两项会显示为存在；其余项（如 TOOLS.md、USER.md）保持「MISSING」即可，不影响本仓 approver 能力。  
- 若在 Dashboard 里点了「Save」自动生成过 IDENTITY.md，可能覆盖本仓内容；可重新从本仓恢复或再次运行 `scripts/set_openclaw_workspace.py` 后重启 Gateway。

---

## 七、参考链接

- OpenClaw 快速开始：<https://docs.openclaw.ai/start/quickstart>  
- Agent 工作区：<https://docs.openclaw.ai/concepts/agent-workspace>  
- OpenClaw CLI：<https://docs.openclaw.ai/cli/agents>  
- 本仓 OpenClaw 飞书等渠道说明：`docs/openclaw-agent.md`
