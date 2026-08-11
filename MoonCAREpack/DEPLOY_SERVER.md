# MoonCAREpack 服务器部署指引

> 目标路径：`/www/wwwroot/MoonCARE`
> 部署方式：上传整个 `MoonCAREpack` 文件夹到 `/www/wwwroot`，改名为 `MoonCARE` 后部署
> 当前策略：一体化镜像；默认 IP + HTTP 直连（`APP_BIND_ADDR=0.0.0.0`，手机可访问）；可选用 Nginx 反代；默认不迁移数据库
> 快速上手：请优先阅读 `DEPLOY_QUICKSTART.md`（含 APK 指引见 `ANDROID_APK_GUIDE.md`）

## 0. 包内必须包含

部署前确认 `MoonCARE` 目录内有这些内容：

```text
Dockerfile
docker-compose.yml
entrypoint.sh
deploy.sh
diagnose.sh
.env.example
backend/app/
backend/requirements.txt
frontend/package.json
frontend/src/
deploy/nginx/mooncare-ip.conf
```

## 1. 上传和改名

```bash
mkdir -p /www/wwwroot
cd /www/wwwroot

# 如果上传后目录叫 MoonCAREpack，就改名为 MoonCARE
mv MoonCAREpack MoonCARE
cd /www/wwwroot/MoonCARE
```

如果之前已经有 `/www/wwwroot/MoonCARE`，先备份旧目录，不要删除 Docker volume：

```bash
cd /www/wwwroot
mv MoonCARE MoonCARE.bak.$(date +%Y%m%d%H%M%S)
mv MoonCAREpack MoonCARE
cd /www/wwwroot/MoonCARE
```

如果旧目录里已有可用 `.env`，复制回来沿用原数据库密码和密钥：

```bash
cd /www/wwwroot
OLD_DIR=$(ls -dt MoonCARE.bak.* | head -n 1)
cp "$OLD_DIR/.env" /www/wwwroot/MoonCARE/.env
chmod 600 /www/wwwroot/MoonCARE/.env
```

## 2. 创建并编辑 .env

```bash
cd /www/wwwroot/MoonCARE
cp .env.example .env
chmod 600 .env
vi .env
```

必须替换：

| 变量 | 要求 |
| --- | --- |
| `DB_PASSWORD` | PostgreSQL 强密码；如果要沿用旧数据库，必须和旧部署保持一致 |
| `SECRET_KEY` | 长随机字符串；如果要保持旧 token 可用，沿用旧值 |
| `RUN_DB_MIGRATIONS` | 保持 `false`，表示不执行 Alembic 迁移 |
| `APP_PORT` | 默认 `18000`；Nginx 样例也反代到 `127.0.0.1:18000` |
| `POSTGRES_PORT` | 默认 `15432`；仅绑定本机，避免和服务器已有 PostgreSQL 的 `5432` 冲突 |
| `PIP_INDEX_URL` | 默认 `https://pypi.tuna.tsinghua.edu.cn/simple`，用于解决 `files.pythonhosted.org` 下载超时 |
| `PIP_DEFAULT_TIMEOUT` / `PIP_RETRIES` | 默认 `300` / `10`，用于 Docker build 阶段 pip 下载 |
| `NVIDIA_API_KEY` | NVIDIA provider 的真实 API key |
| `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_FROM_EMAIL` | 邮箱验证码需要真实 SMTP 配置 |
| `APP_BIND_ADDR` | 直接手机访问填 `0.0.0.0`；Nginx 反代填 `127.0.0.1` |

当前默认配置（无需域名，手机通过 `http://IP:18000` 访问）：

```env
RUN_DB_MIGRATIONS=false
APP_BIND_ADDR=0.0.0.0
APP_PORT=18000
POSTGRES_PORT=15432
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
PIP_DEFAULT_TIMEOUT=300
PIP_RETRIES=10
```

## 3. 一条命令部署

```bash
cd /www/wwwroot/MoonCARE
bash deploy.sh
```

`deploy.sh` 会做这些事：

| 步骤 | 行为 |
| --- | --- |
| 包完整性检查 | 确认 `Dockerfile`、`docker-compose.yml`、`backend/app`、`frontend/package.json`、`frontend/src` 存在 |
| `.env` 检查 | 不允许占位符密钥直接部署 |
| 数据库策略 | 默认使用 PostgreSQL volume 持久化；空库由应用建表，设置 `RUN_DB_MIGRATIONS=true` 时会执行 Alembic |
| 端口检查 | 默认检查宿主机 `18000` 和 `15432` 是否已被占用 |
| Compose 检查 | 执行 `docker compose config` |
| 停旧容器 | 执行 `docker compose down`，不会删除 volume |
| 构建启动 | 执行 `docker compose build app` 和 `docker compose up -d` |
| 健康检查 | 等待 `http://127.0.0.1:18000/health` 返回成功 |

如果出现 pip 超时，例如 `ReadTimeoutError: HTTPSConnectionPool(host='files.pythonhosted.org')`，保留 `.env` 里的默认镜像设置后重建：

```bash
cd /www/wwwroot/MoonCARE
FORCE_REBUILD=1 bash deploy.sh
```

如果清华镜像在你的服务器不可用，改用阿里云：

```env
PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple
PIP_TRUSTED_HOST=mirrors.aliyun.com
PIP_DEFAULT_TIMEOUT=300
PIP_RETRIES=10
```

如果服务器上已经有旧失败镜像，强制重建：

```bash
cd /www/wwwroot/MoonCARE
FORCE_REBUILD=1 bash deploy.sh
```

不要执行：

```bash
docker compose down -v
docker volume rm mooncare_postgres_data
```

这两类命令会删除数据库 volume；当前 Compose 还会使用 `music_data` 保存内置和上传音乐，执行 `down -v` 也会删除该音乐 volume。

## 4. 成功后的验证

```bash
cd /www/wwwroot/MoonCARE
docker compose ps
curl -fsS http://127.0.0.1:18000/health
curl -fsS http://127.0.0.1:18000/healthz
```

如果只是本地 clone 后给测试人员体验登录流程，保持 `DEBUG=true` 或不创建 `.env`，可用：

| 邮箱 | 密码 |
| --- | --- |
| `test@mooncare.local` | `test123456` |

公开服务器部署必须保持 `DEBUG=false`，不要开放该测试账号。

正常启动日志应包含：

```text
Checking application import path...
Application import check passed.
RUN_DB_MIGRATIONS is not true; skipping database migrations.
```

如果看到 `ModuleNotFoundError: No module named 'app'`，说明服务器仍在运行旧镜像或旧包，执行：

```bash
cd /www/wwwroot/MoonCARE
FORCE_REBUILD=1 bash deploy.sh
```

## 5. 失败诊断

部署失败时直接运行：

```bash
cd /www/wwwroot/MoonCARE
bash diagnose.sh
```

重点看输出里的：

```text
== App import inside image ==
Application import check passed.
== Recent app logs ==
```

如果 `App import inside image` 失败，把这一段和 `Recent app logs` 发给开发者继续排查。

## 6. Nginx 1.28.3 反向代理

暂时用 IP 访问时：

```bash
cp /www/wwwroot/MoonCARE/deploy/nginx/mooncare-ip.conf /etc/nginx/conf.d/mooncare.conf
nginx -t
systemctl reload nginx
```

Nginx 样例会：

| 路径 | 行为 |
| --- | --- |
| `/` | 代理到 `127.0.0.1:18000`，由一体化镜像提供前端 |
| `/api/v1/*` | 代理 REST API |
| `/api/v1/chat/ws/*` | 启用 WebSocket upgrade |
| `/api/v1/chat/stream` | 关闭代理缓冲，支持 SSE |
| `/docs`、`/redoc`、`/openapi.json`、`/metrics` | 公网返回 404 |

## 7. 数据库和备份

当前部署默认使用 Docker volume `postgres_data` 保存数据库，使用 `music_data` 保存内置和上传音乐。目录 `/www/backup` 和 30 日保留策略已经写入 `.env.example`，但备份脚本需要单独执行或后续接入定时任务。

立即手动备份示例：

```bash
mkdir -p /www/backup
docker exec mooncare-postgres pg_dump -U mooncare mooncare > /www/backup/mooncare_$(date +%Y%m%d%H%M%S).sql
find /www/backup -name 'mooncare_*.sql' -mtime +30 -delete
```

## 8. 安全边界

MoonCARE 是女性经前情绪陪伴与健康护航产品。部署后仍需保留：

| 风险 | 要求 |
| --- | --- |
| 危机表达 | 聊天入口必须继续走危机优先安全链路 |
| 医疗边界 | AI 回复不能诊断，健康建议必须保持“仅供参考”边界 |
| 敏感日志 | 不记录完整聊天、日记、验证码、token、API key |
| 公开入口 | `/docs`、`/metrics` 暂不公网开放 |
