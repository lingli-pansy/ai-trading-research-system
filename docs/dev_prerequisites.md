# 开发前准备（用于阶段成果验收）

各阶段验收前需具备以下前置条件；未满足时验收无法通过或需回退到自研/模拟方案。

**快速核对**：在项目根目录执行 `python scripts/check_dev_prerequisites.py` 可自动核对环境、权限、依赖与配置；加 `--quick` 可跳过 yfinance 拉数（避免网络慢或限流）。未通过项需按下方清单补齐。

---

## 按阶段对照

| 阶段 | 验收前必须就绪 | 说明 |
|------|----------------|------|
| **1** | 本机 Python ≥3.12、可创建 venv、可访问 PyPI | 否则 `pip install -e .` 或 nautilus_trader 安装失败 |
| **1** | 网络可拉取 pypi.org、可下载 NautilusTrader 官方示例（若从文档/仓库复制） | 否则无法完成「运行 1 个最小 Backtest 示例」 |
| **2** | 网络可访问 Yahoo Finance（yfinance 数据源） | 否则 YFinanceProvider 拉不到数据，`run_research.py NVDA` 报错或超时 |
| **2** | （可选）`.env` 中 `DEFAULT_SYMBOL` 或脚本参数；现有 demo 若依赖 `OPENAI_API_KEY` 可留空（mock 路径不调用 LLM） | 便于验收「现有 demo 仍可跑」 |
| **3** | 同阶段 2；另需**历史行情可写入**：本机有写权限的目录用于 ParquetDataCatalog（或 Nautilus 示例数据所在路径） | 回测依赖历史 Bar/QuoteTick 数据 |
| **3** | 验收用标的（如 NVDA）在 yfinance 有历史数据、且与 Nautilus 所需时间范围一致（如过去 3 个月） | 避免回测无数据或空结果 |
| **4** | 本机有 SQLite 写权限（项目目录或约定目录下创建 `.db` 文件） | Experience Store 落库 |
| **5** | **IBKR Paper 账号**已开通、**TWS 或 IB Gateway** 已安装并可登录 Paper 模式 | 阶段验收为「连接 IBKR Paper 并注入 Contract」 |
| **5** | TWS/IB Gateway 中 **Enable Socket Clients**、**Paper 端口**（通常 7497）开放且与 Nautilus 配置一致 | 否则 Nautilus 连不上 |
| **5** | 本机与 TWS/IB Gateway 同机或端口可访问（若 Gateway 在另一台机器需开放对应端口） | 网络连通性 |
| **6** | 同阶段 1–5；文档/README 所需环境变量与运行前提已写明 | 便于他人或周一按文档试跑 |

---

## 清单汇总（开发前一次性核对）

### 环境与权限

- [ ] **Python**：版本 ≥3.12，可建 venv，`pip` 可用
- [ ] **网络**：可访问 PyPI、Yahoo Finance；若用公司网络需确认无拦截
- [ ] **磁盘**：项目目录可写（SQLite、ParquetDataCatalog、日志）
- [ ] **依赖**：`pyproject.toml` / `requirements.txt` 中已加入 `nautilus_trader`、`yfinance`（阶段 1 完成后勾选）

### 数据

- [ ] **行情**：yfinance 对验收标的（如 NVDA）能返回当前价与历史（阶段 2/3 验收前试跑一次）
- [ ] **历史范围**：回测用区间（如过去 3 个月）在数据源内可用；若用 Nautilus 示例数据则需示例已就绪

### Paper 试跑（阶段 5/6 验收前）

- [ ] **IBKR Paper 账号**：已注册并开通 Paper Trading
- [ ] **TWS 或 IB Gateway**：已安装，可登录且选择 **Paper** 模式
- [ ] **API 设置**：TWS → 配置 → API → 启用「Enable ActiveX and Socket Clients」，**Socket port** 以界面为准（常见 Paper 为 **7497**，部分 TWS/网关为 **4002**），并勾选「Allow connections from localhost only」或配置 Trusted IPs
- [ ] **连通性**：运行 `python scripts/verify_ibkr.py` 检测 IBKR_HOST:IBKR_PORT 可达（或本机 `nc -zv localhost <端口>`）；若用 Docker 版 IB Gateway 则容器已启动且端口映射正确
- [ ] **.env 配置**：在项目根 `.env` 中设置 `IBKR_HOST=127.0.0.1`、`IBKR_PORT=<TWS 中的 Socket port>`、`IBKR_CLIENT_ID=1`（端口与 TWS 一致，例如 4002）

### 配置与文档

- [ ] **.env**：复制 `cp .env.example .env`，按需填写 `APP_ENV`、`DEFAULT_SYMBOL`；LLM 二选一：`OPENAI_API_KEY` 或 `KIMI_CODE_API_KEY`（Kimi 可选 `KIMI_BASE_URL`、`KIMI_MODEL`，见 `.env.example`）
- [ ] **README / docs**：已注明 `run_research.py`、`run_backtest.py`、`run_paper.py` 的用法与前提（阶段 6 验收前完成）

---

## 与阶段验收的对应关系

- **阶段 1 验收**：依赖「环境与权限」前 3 项 + 依赖文件更新。
- **阶段 2 验收**：依赖「环境与权限」+「数据」中 yfinance 可用。
- **阶段 3 验收**：依赖阶段 2 +「数据」中历史范围 + Catalog 写权限。
- **阶段 4 验收**：依赖阶段 3 + SQLite 写权限。
- **阶段 5 验收**：依赖「Paper 试跑」整块；若不满足则按计划回退到自研 Paper 引擎试跑。
- **阶段 6 验收**：依赖阶段 1–5 全部前置 +「配置与文档」中 README/docs 已更新。

---

## 相关文档

- MVP 与实盘前工作：[mvp_plan.md](mvp_plan.md)、[live_readiness_checklist.md](live_readiness_checklist.md)
- 实盘前检查（后续补齐）：[live_readiness_checklist.md](live_readiness_checklist.md)

## 一键核对脚本

在项目根目录执行：

```bash
python scripts/check_dev_prerequisites.py      # 含 yfinance 拉数检查
python scripts/check_dev_prerequisites.py --quick   # 跳过拉数，仅环境与依赖
```
