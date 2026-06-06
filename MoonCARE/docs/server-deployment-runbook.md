# MoonCARE 服务器部署运行手册

> 变更日期：2026-06-04  
> 影响范围：`docker-compose.yml`、`deploy/env/server.env.example`、`deploy/nginx/mooncare-ip.conf`、`deploy/scripts/*.sh`、服务器上线流程  
> 当前状态：已完成可执行运行手册；需要在真实 Linux 服务器上按本文替换密钥、执行部署并验证

## 1. 目标

本文把 MoonCARE 后端部署从“方案”落成“可执行操作”。目标是让以下链路在 Linux 服务器上成立：

```text
Public IP
  -> Nginx
  -> mooncare-app
  -> mooncare-postgres
  -> mooncare-redis
```

固定边界：

- 对外只公开 Nginx，不直接暴露 `app`、`postgres`、`redis`
- 后端主链路必须覆盖 `/api/v1/auth/*`、`/api/v1/chat/*`、`/api/v1/menstrual/*`、`/api/v1/diary/*`、`/api/v1/music/*`、`/api/v1/mobile/releases/android/*`
- `/api/v1/biometric/*` 与 `/api/v1/biometric/raw` 保持原样，不在本手册里改协议
- Redis 当前只作为基础设施加入，主功能仍可在 `SEMANTIC_CACHE_ENABLED=false` 下运行

## 2. 仓库内交付物

| 文件 | 用途 |
| --- | --- |
| `deploy/env/server.env.example` | 服务器生产 `.env` 模板 |
| `deploy/nginx/mooncare-ip.conf` | 当前 IP 阶段可直接安装的 Nginx 样例 |
| `deploy/scripts/backup_postgres.sh` | PostgreSQL 备份脚本 |
| `deploy/scripts/restore_postgres.sh` | PostgreSQL 恢复脚本 |
| `deploy/scripts/smoke_check.sh` | 部署后冒烟检查脚本 |
| `docs/deployment-docker-server.md` | 部署基线与配置说明 |

## 3. 服务器前提

服务器需满足：

- Linux
- Docker Engine
- Docker Compose plugin
- Nginx
- `curl`
- 能访问 MoonCARE 仓库代码

推荐目录：

```text
/srv/mooncare
/srv/mooncare/mobile_releases
/www/backup
```

## 4. 首次准备

### 4.1 拉取代码

```bash
sudo mkdir -p /srv/mooncare
sudo chown -R "$USER":"$USER" /srv/mooncare
cd /srv/mooncare
git clone <YOUR_REPO_URL> .
```

### 4.2 创建运行目录

```bash
sudo mkdir -p /www/backup
sudo mkdir -p /srv/mooncare/mobile_releases
sudo chown -R "$USER":"$USER" /www/backup /srv/mooncare/mobile_releases
```

### 4.3 生成服务器 `.env`

```bash
cd /srv/mooncare
cp deploy/env/server.env.example .env
```

至少替换这些值：

- `DB_PASSWORD`
- `SECRET_KEY`
- `NVIDIA_API_KEY`
- `SMTP_*`
- `MOBILE_RELEASES_PUBLIC_BASE_URL`

注意：

- 调试 IP 阶段可以先让 App 与 Web 调试走 HTTP，但 `MOBILE_RELEASES_PUBLIC_BASE_URL` 用于 Android release 下载时必须改成 HTTPS
- `RUN_DB_MIGRATIONS` 在 `.env` 里默认保持 `false`

## 5. 首次部署

### 5.1 静态检查 Compose

```bash
cd /srv/mooncare
docker compose --env-file .env config
```

### 5.2 首次启动并执行迁移

首次上线时，用一次性的环境覆盖打开迁移：

```bash
cd /srv/mooncare
RUN_DB_MIGRATIONS=true docker compose --env-file .env up -d --build
```

说明：

- 这一步会启动 `app`、`postgres`、`redis`
- `entrypoint.sh` 只会在 `RUN_DB_MIGRATIONS=true` 时执行 `alembic upgrade head`

### 5.3 确认服务状态

```bash
cd /srv/mooncare
docker compose --env-file .env ps
docker compose --env-file .env logs --tail=200 app
docker compose --env-file .env logs --tail=100 postgres
docker compose --env-file .env logs --tail=100 redis
```

### 5.4 后续常规重启

迁移完成后，正常运行保持 `.env` 中 `RUN_DB_MIGRATIONS=false`：

```bash
cd /srv/mooncare
docker compose --env-file .env up -d
```

## 6. 安装 Nginx IP 配置

当前阶段先用仓库内 IP 样例：

```bash
cd /srv/mooncare
sudo cp deploy/nginx/mooncare-ip.conf /etc/nginx/conf.d/mooncare.conf
sudo nginx -t
sudo systemctl reload nginx
```

样例行为：

- `/api/v1/*` 反代到 `127.0.0.1:8000`
- `/api/v1/chat/ws/*` 保留 WebSocket upgrade
- `/api/v1/chat/stream` 关闭代理缓冲
- `/docs`、`/redoc`、`/openapi.json`、`/metrics` 公网返回 `404`

## 7. 部署后冒烟检查

### 7.1 匿名检查

```bash
cd /srv/mooncare
BASE_URL=http://SERVER_PUBLIC_IP bash deploy/scripts/smoke_check.sh
```

### 7.2 带登录的检查

```bash
cd /srv/mooncare
BASE_URL=http://SERVER_PUBLIC_IP \
LOGIN_EMAIL=your-test-account@example.com \
LOGIN_PASSWORD='your-password' \
bash deploy/scripts/smoke_check.sh
```

脚本会检查：

- `/healthz`
- `/docs`
- `/redoc`
- `/openapi.json`
- `/metrics`
- `/api/v1/auth/login`
- `/api/v1/chat/session`

## 8. 备份与恢复

### 8.1 执行备份

```bash
cd /srv/mooncare
bash deploy/scripts/backup_postgres.sh .env
```

默认行为：

- 输出到 `.env` 中的 `BACKUP_DIR`
- 文件名格式为 `mooncare-postgres-YYYYMMDD-HHMMSS.sql.gz`
- 按 `BACKUP_RETENTION_DAYS` 清理旧备份

### 8.2 执行恢复

恢复会覆盖目标库，只能在维护窗口执行：

```bash
cd /srv/mooncare
bash deploy/scripts/restore_postgres.sh /www/backup/mooncare-postgres-YYYYMMDD-HHMMSS.sql.gz .env --yes
```

建议：

- 先在测试环境演练一次恢复
- 正式恢复前先停止对外写入或进入维护窗口

## 9. Android 更新目录

若你要启用应用内更新：

1. 把生成好的 `android-internal.json` / `android-public.json` 和 APK 放到 `MOBILE_RELEASES_DIR`
2. 把 `MOBILE_RELEASES_PUBLIC_BASE_URL` 设成 HTTPS 域名
3. 再验证：

```text
GET /api/v1/mobile/releases/android/internal
GET /api/v1/mobile/releases/android/internal/download
```

在正式 HTTPS 前，不要把这条链路作为 release APK 的最终方案。

## 10. 上线后核对清单

上线后你应逐项确认：

1. `docker compose --env-file .env ps` 中 `app`、`postgres`、`redis` 正常
2. `http://SERVER_PUBLIC_IP/healthz` 返回 `200`
3. `http://SERVER_PUBLIC_IP/docs` 返回 `404`
4. 登录接口可返回 token
5. `POST /api/v1/chat/session` 可返回 `session_id`
6. WebSocket 与 SSE 经过 Nginx 后可用
7. 备份脚本能产出 `.sql.gz`
8. `/api/v1/biometric/*` 仍按原契约工作

## 11. 仍需你在服务器侧完成的事

这些事我已经在仓库里准备好模板，但不能替你远程执行：

1. 替换 `.env` 中真实密钥和邮件配置
2. 把仓库代码同步到 Linux 服务器
3. 安装 Nginx 配置并 reload
4. 用你的服务器 IP 或域名执行冒烟验证
5. 真正发布 Android release 前补域名和 HTTPS
