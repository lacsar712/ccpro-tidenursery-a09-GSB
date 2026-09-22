# TideNursery-01 · 潮汐育苗台账

海水育苗场「塘口水质采样与投喂事件」台账种子项目（非库存 / 电商 / 医院）。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.11 · FastAPI · SQLAlchemy 2 · Pydantic v2 · python-jose · passlib(bcrypt) · uvicorn |
| 前端 | React 18 · Vite · TypeScript · React Router v6 |
| 数据库 | PostgreSQL 15 |
| 部署 | docker-compose · 前端 Nginx 反代 `/api` |

## 端口与账号

| 服务 | 端口 |
| --- | --- |
| 前端 | **3400** |
| 后端 API | **8400** |
| PostgreSQL | **5434** |

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| `admin` | `123456` | 场长 |
| `technician` | `123456` | 水质技术员 |

## 一键启动

```bash
cd TideNursery-01
docker compose up --build
```

启动后访问：

- 前端：http://localhost:3400
- 后端健康检查：http://localhost:8400/api/health
- API 文档：http://localhost:8400/docs

后端 entrypoint 流程：等待数据库就绪 → `create_all` 建表 → seed 初始数据 → 启动 uvicorn。

## 功能模块

1. **Auth**：JWT 登录（OAuth2 Password），`/api/auth/login`、`/api/auth/me`
2. **Hatchery 育苗场**：`name`、`seawaterSource`、`notes`
3. **Pond 育苗塘**：`hatcheryId`、`pondCode`、`species`、`volumeM3`、`status(stocked|dry|quarantine)`；同场 `pondCode` 唯一
4. **WaterSample 水质样**：`pondId`、`sampledAt`、`tempC`、`salinityPpt`、`doMgL`、`ph`、`notes`；`doMgL > 0` 且 `ph ∈ [6,9]`，否则返回 **400**
5. **FeedEvent 投喂**：`pondId`、`fedAt`、`feedType`、`amountKg`、`operatorName`
6. **FeedWindow 投喂窗口**：`pondId`、`startAt`、`endAt`、`enabled`
7. **Dashboard**：塘总数、quarantine 数、近 24h 采样数、近 7 日投喂总量 kg

### 投喂窗口与溶氧规则

投喂登记（`POST /api/feed-events`）在后端强制两道校验，**顺序固定、先窗口后溶氧**，前端不做禁用按钮之类的纯前端拦截：

1. **窗口校验**：投喂时刻 `fedAt` 必须被该塘口一条**启用中**的窗口闭区间覆盖（`startAt ≤ fedAt ≤ endAt`）。不存在覆盖窗口时返回 **409** `投喂时刻不在该塘口的启用投喂窗口内，禁止投喂`。
2. **溶氧校验**（仅窗口通过后执行）：该塘口在 `[fedAt - 6h, fedAt]` 内必须存在水质样，且最近一条 `doMgL ≥ 5`。无样或溶氧不足时返回 **400**，正文区分「6 小时内无水质样」与「溶解氧低于 5 mg/L」。

窗口管理规则：

- 同一塘口窗口时间轴**相交（含边界相接的时间重叠判断）即拒绝**，返回 **409** `同塘口投喂窗口时间相交`；停用窗口也参与相交判断，避免重新启用后产生重叠。不同塘口窗口互不影响。
- `GET /api/feed-windows/open` 返回当前时刻处于启用状态的窗口；塘口列表 `GET /api/ponds` 每行带 `inFeedWindow`，口径与该接口完全一致（每个开窗塘口一行 ↔ open 中该塘口一条）。
- 种子数据为 B-01 塘准备了一条覆盖当前时刻的启用窗口，但其最近水质样在 10 小时前：此时对 B-01 登记投喂会得到窗口通过、溶氧 **400** 的失败结果，可直接验证规则。

## 前端页面

Login · Dashboard · Hatcheries · Ponds · WaterSamples · FeedWindows · FeedEvents

## 本地开发（可选）

```bash
# 数据库（或用 compose 只起 db）
docker compose up -d db

# 后端
cd backend
pip install -r requirements.txt
set DATABASE_URL=postgresql+psycopg2://tidenursery:tidenursery@localhost:5434/tidenursery
python -c "from app.database import Base, engine; from app import models; Base.metadata.create_all(bind=engine)"
python -c "from app.seed import seed; seed()"
uvicorn app.main:app --reload --port 8400

# 前端
cd frontend
npm install
npm run dev
```

## 目录结构

```
TideNursery-01/
├── docker-compose.yml
├── README.md
├── .gitignore
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── auth.py
│       ├── seed.py
│       ├── models/
│       ├── schemas/
│       └── routers/
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── pages/
        ├── components/
        └── api/
```
