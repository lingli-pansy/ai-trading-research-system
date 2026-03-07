# 隐私与 Git 使用

## 切勿提交的内容

- **`.env`**：存放 API Key、券商账号相关配置等，已加入 `.gitignore`，请勿强制添加。
- **密钥文件**：`*.pem`、`*.key`、`secrets/`、`credentials/` 等已忽略。
- **本地数据库**：Experience Store 的 `*.db`、`*.sqlite` 及回测数据目录（如 `catalog/`、`*.parquet`）可能含本地运行数据，已忽略。
- **日志**：`logs/`、`*.log` 可能含标的、时间等运行信息，已忽略。

## 可提交的模板

- **`.env.example`**：仅含占位或空值，用于说明需要哪些环境变量，不包含真实密钥。

## 首次克隆后

复制 `.env.example` 为 `.env` 并填入本地/环境专用配置，不要将 `.env` 提交到仓库。

```bash
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY 等（仅本地使用）
```

## 本仓库 Git 身份（仅本地）

首次提交使用本仓库局部配置 `user.name` / `user.email`（未改全局）。若希望用自己身份提交，可在本仓执行：

```bash
git config user.name "你的名字"
git config user.email "你的邮箱"
```

## 相关

- 开发前准备与验收：[dev_prerequisites.md](dev_prerequisites.md)
- MVP 与实盘前工作：[mvp_plan.md](mvp_plan.md)、[live_readiness_checklist.md](live_readiness_checklist.md)
