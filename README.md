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
5. **FeedEvent 投喂**：`pondId`、`fedAt`、`feedType`、`amountKg`、`operatorName`；登记前强制核对投喂窗口与溶氧（见下）
6. **FeedWindow 投喂窗口**：`pondId`、`startAt`、`endAt`、`enabled`；同塘口窗口时间段相交返回 **409**
7. **Dashboard**：塘总数、quarantine 数、近 24h 采样数、近 7 日投喂总量 kg

### 投喂窗口与溶氧规则

- **窗口外禁止投喂**：登记投喂时，该塘口必须存在一条**启用**且覆盖投喂时刻的窗口（`startAt <= fedAt <= endAt`），否则返回 **409**「投喂时刻不在该塘口任何启用的投喂窗口内」。
- **窗口内核对溶氧**：通过窗口校验后，要求该塘在投喂时刻**前 6 小时内**有一条 `doMgL >= 5` 的水质样，否则返回 **400**「投喂前6小时内无溶氧≥5 mg/L的水质样」。
- 两项判定顺序固定：**先窗口（409），后溶氧（400）**，错误码与正文可区分；均由后端强制拦截，前端不做灰按钮式规避。
- 塘口列表每行返回 `inOpenWindow`，表示当前是否处于启用投喂窗，与投喂登记共用同一套窗口核对逻辑。
- 种子数据：B-01 预置一个启用窗口（覆盖当前时刻），但其最近水质样在 10 小时前（超出 6 小时），对 B-01 登记投喂可复现 **400**；对其他塘口登记投喂可复现 **409**。

## 前端页面

Login · Dashboard · Hatcheries · Ponds · WaterSamples · FeedEvents · FeedWindows

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
