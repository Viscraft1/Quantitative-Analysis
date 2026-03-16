# 量化分析平台

这是一个基于 `FastAPI + React + SQLite/PostgreSQL` 的量化选股系统骨架，当前已经可以直接跑通以下链路：

- 读取真实历史数据
- 计算技术因子
- 生成选股榜单
- 通过前端页面查看榜单、个股详情和任务状态

## 当前数据源优先级

`MARKET_DATA_PROVIDER=auto` 时，按下面顺序选择：

1. 本地通达信目录 `TDX_ROOT`
2. `AkShare`
3. `Tushare`（仅在显式指定时建议使用）

默认 `.env.example` 已配置：

```env
MARKET_DATA_PROVIDER=auto
TDX_ROOT=E:/Tongdaxin/vipdoc
```

如果你的机器上存在 `E:\Tongdaxin\vipdoc`，首次启动时会优先导入本地通达信历史日线；实时监控继续使用 `AkShare`。

## 目录结构

```text
backend/      FastAPI、SQLAlchemy 模型、CLI、服务层
frontend/     React + Vite 页面
infra/sql/    数据库初始化脚本
docker-compose.yml
```

后端服务层现在按功能继续细分：

- `backend/app/services/data_fetching/`：数据抓取、A 股导出
- `backend/app/services/technical_analysis/`：技术指标、K 线形态
- `backend/app/services/stock_judgement/`：买卖判断逻辑，例如 `kdj/`

## 已有能力

### 后端接口

- `GET /api/v1/health`
- `GET /api/v1/rankings/daily`
- `GET /api/v1/stocks/{symbol}`
- `GET /api/v1/stocks/{symbol}/factors`
- `GET /api/v1/jobs/latest`

### 前端页面

- `/rankings` 榜单页
- `/stocks/:symbol` 个股详情页
- `/jobs` 任务状态页

### CLI

- `python -m app.cli launch`
- `python -m app.cli init-db`
- `python -m app.cli fetch-daily-bars`
- `python -m app.cli compute-factors`
- `python -m app.cli run-screening`
- `python -m app.cli publish-results`
- `python -m app.cli export-a-share-datasets`
- `python -m app.cli seed-demo`

`seed-demo` 仍然保留，但现在只是可选调试命令，不是默认启动路径。

## 一键启动

Windows 下直接双击根目录的 `launch.cmd`。

如果你想在终端里用命令启动：

- `launch`
- `python backend/.venv/Scripts/python.exe -m app.cli launch`

说明：

- `launch.cmd` 现在是唯一主启动脚本，支持双击一键启动 UI
- `start.bat` 保留为兼容入口，内部会自动转发到 `launch.cmd`
- 首次运行 `start.bat`、`launch.cmd` 或 `python bootstrap.py` 时，会自动安装全局 `launch` 命令到 `C:\Users\你的用户名\.local\bin\launch.cmd`
- 安装完成后，在 `cmd` 和 PowerShell 中都可以直接输入 `launch`
- 如果你只想在当前项目目录临时启动，也可以执行 `.\launch.cmd`

首次运行会自动完成：

- 创建 `backend/.venv`
- 安装 `backend/requirements.txt`
- 检查数据库是否已有真实数据
- 如果没有数据，则自动执行：
  - `python -m app.cli fetch-daily-bars --provider auto`
  - `python -m app.cli compute-factors --provider auto`
  - `python -m app.cli run-screening`
- 构建 `frontend/dist`
- 启动后端并托管前端页面
- 自动打开独立应用窗口（不再依赖浏览器标签页进入系统）

启动成功后：

- 默认会直接打开独立应用窗口
- 本地页面地址：`http://127.0.0.1:8000`
- API 文档：`http://127.0.0.1:8000/docs`

## 手动运行

### 1. 准备环境变量

```powershell
Copy-Item .env.example .env
```

推荐至少确认下面几项：

```env
MARKET_DATA_PROVIDER=auto
TDX_ROOT=E:/Tongdaxin/vipdoc
TUSHARE_TOKEN=
```

### 2. 初始化真实数据

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.cli fetch-daily-bars --provider auto
.\.venv\Scripts\python.exe -m app.cli compute-factors --provider auto
.\.venv\Scripts\python.exe -m app.cli run-screening
```

常见用法：

```powershell
# 指定日期
.\.venv\Scripts\python.exe -m app.cli fetch-daily-bars --provider tdx_local --trade-date 2026-03-09

# 指定区间
.\.venv\Scripts\python.exe -m app.cli fetch-daily-bars --provider tdx_local --start-date 2026-02-01 --end-date 2026-03-09

# 指定股票
.\.venv\Scripts\python.exe -m app.cli fetch-daily-bars --provider tdx_local --symbols 600000.SH,000001.SZ

# 导出 A 股关键日度数据，并生成可扩展的 daily_snapshot
.\.venv\Scripts\python.exe -m app.cli export-a-share-datasets `
  --datasets daily_snapshot,daily,financial,lhb,fund_flow_stock,dividend,dzjy,qiangchou,zt_pool,etf_daily `
  --symbols 600519,000001 `
  --daily-trade-date 2026-03-13 `
  --dzjy-start-date 2026-03-01 `
  --dzjy-end-date 2026-03-13 `
  --zt-trade-date 2026-03-13
```

说明：

- `daily_snapshot` 会基于本次导出的 `daily / financial / fund_flow_stock / dividend / lhb / dzjy / qiangchou / zt_pool` 自动汇总成单表，便于后续扩展自选字段。
- 完整数据集参数可用 `python -m app.cli export-a-share-datasets --help` 查看。

### 3. 本地开发

后端：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

## 当前实现说明

- 通达信本地模式支持读取 `vipdoc/*/lday/*.day`
- 通达信代码名称来自本地 `T0002/hq_cache/shm.tnf` 和 `szm.tnf`
- 本地通达信只提供历史日线，不提供实时行情和完整财务因子
- 因此本地回退模式下，榜单主要基于技术面和量能因子
- 实时监控页仍依赖外部实时源

## 当前状态

这套程序现在已经不是 mock 或 demo 驱动：

- 榜单接口读数据库真实结果
- 个股详情读数据库真实 K 线
- 因子页读 `factor_snapshot`
- 默认启动会优先导入本地通达信历史数据，实时监控继续走 `AkShare`
