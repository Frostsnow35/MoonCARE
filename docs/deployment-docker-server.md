# MoonCARE Docker + 服务器部署基础说明

> 变更日期：2026-05-21  
> 影响范围：`Dockerfile`、`docker-compose.yml`、`entrypoint.sh`、根目录 `.env.example`、服务器部署验证流程  
> 当前状态：已完成基础配置修正；已确认 Nginx 1.28.3、一体化镜像、临时 IP 访问、NVIDIA provider、`/www/backup` 30 日备份策略；NVIDIA 真实端点、服务器 Nginx 配置和恢复演练仍需要验证  

## 1. 部署目标

MoonCARE 当前默认部署方向是 Docker + 服务器。本文只覆盖工程部署基线，不改变业务功能、不处理硬件接口、不把旧 `/interview/*` 作为新主流程。

部署后的产品仍必须遵守既有安全边界：危机表达优先进入安全通道；AI 回复不做诊断、不替代医生；用户数据按登录身份隔离；日志不得输出完整聊天、日记、token、密钥或健康隐私。

## 2. 已确认部署决策

| 决策项 | 当前决定 | 状态 |
| --- | --- | --- |
| 反向代理 | Nginx 1.28.3 | 已确认，样例见 `deploy/nginx/mooncare-ip.conf` |
| 前端部署 | 一体化镜像 | 已确认，`Dockerfile` 构建 `frontend/dist` 并由 FastAPI 提供静态资源 |
| 访问方式 | 暂时用服务器 IP 访问 | 已确认；正式域名和 HTTPS 后续再接入 |
| 公开范围 | `/docs`、`/redoc`、`/openapi.json`、`/metrics` 公网关闭 | 已确认，Nginx 样例中返回 404 |
| LLM provider | NVIDIA | 已确认，`.env.example` 和 Compose 默认值为 `nvidia` |
| 数据库备份 | `/www/backup`，保留 30 日 | 已确认，备份脚本和恢复演练仍需后续补齐 |

## 3. Docker Compose 服务结构

| 服务 | 状态 | 作用 | 端口/网络 |
| --- | --- | --- | --- |
| `app` | 已完成基础配置 | 构建前端 `dist`，运行 FastAPI + gunicorn + uvicorn worker，并执行 Alembic 迁移 | 默认绑定 `127.0.0.1:8000`，加入 `mooncare-net` |
| `postgres` | 已完成基础配置 | PostgreSQL 15，保存用户、聊天、周期、日记、评估等持久化数据 | 默认绑定 `127.0.0.1:5432`，数据写入 `postgres_data` volume |
| `redis` | 计划中/可选 | 语义缓存或后续限流缓存 | 当前未加入 Compose；启用前需要隔离和容量评估 |
| `awareness` | 需要验证/可选 | 本地记忆服务 | 生产启用前必须完成多用户隔离审计 |

当前 Compose 健康检查：

| 服务 | 检查方式 | 说明 |
| --- | --- | --- |
| `postgres` | `pg_isready -U mooncare -d mooncare` | 使用 Postgres 镜像内置工具 |
| `app` | `curl -fsS http://127.0.0.1:8000/health` | 对齐 FastAPI 当前真实健康接口 `/health` |

## 4. 必填环境变量

根目录 `.env.example` 是 Docker + 服务器部署模板。复制为 `.env` 后必须替换占位值，不能提交真实密钥。

| 变量 | 类型 | 默认/示例 | 说明 |
| --- | --- | --- | --- |
| `DB_PASSWORD` | string | `replace_with_strong_postgres_password` | 必填，PostgreSQL 密码；生产必须使用强随机值 |
| `SECRET_KEY` | string | `replace_with_long_random_secret_key` | 必填，JWT 签名密钥；每个环境独立生成 |
| `LLM_PROVIDER` | enum | `nvidia` | 当前已确认使用 NVIDIA；可选值仍支持 `nvidia`、`openai`、`vllm`、`accelerated`、`zai` |
| `NVIDIA_API_KEY` | string | 空 | 必填，生产通过服务器环境或 `.env` 注入，不能写入仓库 |
| `ZAI_API_KEY` / `OPENAI_API_KEY` | string | 空 | 未使用 provider 保持空 |
| `APP_BIND_ADDR` / `APP_PORT` | string/int | `127.0.0.1` / `8000` | 建议只暴露给本机反向代理，不直接公网开放 |
| `POSTGRES_BIND_ADDR` / `POSTGRES_PORT` | string/int | `127.0.0.1` / `5432` | 建议只绑定本机；远程管理通过 SSH tunnel |
| `BACKUP_DIR` / `BACKUP_RETENTION_DAYS` | string/int | `/www/backup` / `30` | 服务器备份脚本使用；当前应用本身不读取 |
| `SEMANTIC_CACHE_ENABLED` / `REDIS_URL` | bool/string | `false` / 空 | Redis 未部署时保持关闭 |
| `AWARENESS_MEMORY_ENABLED` / `AWARENESS_BASE_URL` | bool/string | `false` / `host.docker.internal` | 生产启用前需做多用户隔离和隐私审查 |
| `LLM_REQUEST_TIMEOUT_SECONDS` / `CHAT_AGENT_REPLY_TIMEOUT_SECONDS` | number | `45` | 控制 LLM 等待时间，保留危机安全兜底和超时 fallback |

注意：当前 `backend/app/config.py` 仍允许默认 SQLite 和开发密钥。Docker 服务器部署必须以根目录 `.env` 和 Compose 注入为准，不得使用代码默认值作为生产配置。

Compose 已为 `app` 配置 `host.docker.internal:host-gateway`。如果后续把 vLLM、Awareness 或内部 LLM 网关跑在宿主机而不是同一个 Compose 网络中，可以用 `http://host.docker.internal:<port>` 访问；如果这些服务也容器化，优先改为服务名访问。

## 5. 前端部署三种分支

当前阶段已确认采用一体化镜像。下表保留其他分支作为后续扩展参考，但当前部署执行按一体化镜像推进。

| 分支 | 状态 | 适用场景 | 需要确认 |
| --- | --- | --- | --- |
| 一体化镜像 | 已确认 | 当前 `Dockerfile` 会构建 `frontend/dist` 并由 FastAPI 提供静态资源 | 需继续验证 Vue history fallback、静态缓存头、构建产物体积 |
| 前端独立静态容器 + Nginx/Caddy | 计划中 | 前后端独立扩缩容、缓存策略更清晰 | API/WS 反代、CORS、HTTPS、静态缓存、容器网络 |
| 前端独立托管平台 | 待确认 | 快速发布或 CDN 能力优先时可评估 | 不能默认使用；需要确认域名、CORS、鉴权、隐私和跨域 Cookie/Authorization 策略 |

## 6. Nginx 1.28.3 反向代理要求

当前已确认使用 Nginx 1.28.3，临时阶段通过服务器 IP 访问。样例配置位于 `deploy/nginx/mooncare-ip.conf`，安装后先执行 `nginx -t`，再 reload。由于暂时使用 IP，正式 HTTPS 证书和 HSTS 需要等域名确认后再启用。

| 项 | 要求 |
| --- | --- |
| HTTPS | IP 临时访问阶段暂不启用正式证书；接入域名后启用自动续期证书，并强制 HTTP -> HTTPS |
| API | `/api/v1/*` 转发到 `app:8000` 或本机 `127.0.0.1:8000` |
| WebSocket | `/api/v1/chat/ws/*` 必须设置 HTTP/1.1 upgrade 头，不能被普通 HTTP proxy 配置吞掉 |
| SSE | `/api/v1/chat/stream` 关闭或放宽代理缓冲，避免流式回复被整段缓存 |
| 静态资源缓存 | `assets/*` 可长缓存；`index.html` 不应长缓存 |
| CORS | IP 阶段需要按实际访问源收敛；当前代码仍是 `allow_origins=["*"]`，上线前必须改为白名单 |
| 上传/请求大小 | 结合日记、语音、硬件专项另行设置；本任务不处理硬件接口 |
| 内部入口 | `/docs`、`/redoc`、`/openapi.json`、`/metrics` 公网关闭；需要排障时用 SSH tunnel 或临时内网 allowlist |

## 7. 数据库、迁移和备份

| 项 | 状态 | 要求 |
| --- | --- | --- |
| Volume | 已完成基础配置 | `postgres_data` 保存 PostgreSQL 数据，删除 volume 会丢失用户、聊天、评估和日记数据 |
| 迁移 | 已接入 | `entrypoint.sh` 在 `/app/backend` 执行 `alembic upgrade head` |
| `pg_isready` | 已修正镜像依赖 | 最终镜像安装 `postgresql-client`，保证 entrypoint 等待数据库可用 |
| 备份 | 已确认目录和保留期 | 备份写入 `/www/backup`，保留 30 日；生产前需要补 `pg_dump` 脚本和恢复演练步骤 |
| 回滚 | 需要验证 | Alembic downgrade 策略和数据兼容性需要随每次 schema 变更记录 |

## 8. 日志脱敏和隐私

容器日志只应保留工程排障所需信息。禁止输出完整用户聊天、日记原文、健康隐私、JWT、数据库 URL、LLM API key。

需要验证的生产 TODO：

| TODO | 风险 | 建议 |
| --- | --- | --- |
| CORS 仍在代码中允许 `*` | 跨域访问面过大 | 增加生产 `ALLOWED_ORIGINS` 配置并按域名白名单加载 |
| `/metrics` 未鉴权 | 可能暴露服务状态或缓存错误 | 当前 Nginx 样例公网返回 404；后续如需访问，用 SSH tunnel 或内网 allowlist |
| `/docs` 默认开放 | 暴露接口结构 | 当前 Nginx 样例公网返回 404；后端是否按环境关闭仍需后续加固 |
| 部分业务接口仍需用户隔离审计 | 健康/情绪数据越权风险 | 后续 P0 单独做 JWT 用户隔离代码审查和测试 |
| LLM provider 未做真实压测 | 超时、fallback、代理网络不确定 | 部署前用低风险聊天、知识问答、危机样例分别验证 |

## 9. LLM Provider 配置

MoonCARE 使用 OpenAI-compatible 接口接入不同 provider。当前已确认使用 NVIDIA，生产 `.env` 必须填写 `NVIDIA_API_KEY`，并确认容器能访问 `NVIDIA_BASE_URL`。

| Provider | 关键变量 | 验证重点 |
| --- | --- | --- |
| `zai` | `ZAI_API_KEY`、`ZAI_BASE_URL`、`ZAI_MODEL_NAME` | GLM 端点连通性、首 token 超时、失败 fallback |
| `nvidia` | `NVIDIA_API_KEY`、`NVIDIA_BASE_URL`、`NVIDIA_MODEL_NAME` | 当前选定；需验证模型名称兼容性、API 限速、首 token 超时和 fallback |
| `openai` | `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`MODEL_NAME` | 账单、区域网络、超时设置 |
| `vllm` | `VLLM_BASE_URL`、`VLLM_API_KEY`、`VLLM_MODEL_NAME` | 容器访问宿主机或内网推理服务的地址 |
| `accelerated` | `ACCELERATED_LLM_BASE_URL`、`ACCELERATED_LLM_API_KEY`、`ACCELERATED_LLM_MODEL_NAME` | 内部网关兼容性和超时 |

危机表达必须优先走安全通道。部署验证不能只测普通聊天，还要覆盖危机样例在 REST、SSE、WebSocket 下不会绕过安全层。

## 10. 验证命令

基础配置验证：

```bash
docker compose config
```

构建与启动验证：

```bash
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f app
```

Nginx 配置验证：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

上线前还需要验证：

| 检查项 | 验证方式 |
| --- | --- |
| 健康接口 | IP 阶段使用 `curl http://SERVER_PUBLIC_IP/health`；域名接入后再验证 HTTPS |
| API | 登录、创建聊天 session、发送低风险消息 |
| WebSocket | 通过反向代理访问 `/api/v1/chat/ws/{user_id}` 并确认 upgrade |
| SSE | 访问 `/api/v1/chat/stream`，确认流式输出不被代理缓冲 |
| 前端刷新 | 若采用一体化或静态容器，刷新 `/chat`、`/cycle`、`/diary` 不应 404 |
| 数据持久化 | 重启 `app` 和 `postgres` 后确认用户、聊天、评估数据仍在 |
| 安全样例 | 危机表达触发干预兜底；健康建议保留“仅供参考”边界 |

## 11. 当前人工确认项

| 决策 | 状态 | 需要确认 |
| --- | --- | --- |
| 反向代理选型 | 已确认 | Nginx 1.28.3 |
| 前端最终部署方式 | 已确认 | 当前采用一体化镜像 |
| 访问方式 | 已确认 | 暂时用服务器 IP 访问；域名和 HTTPS 后续确认 |
| 生产 CORS 白名单 | 待确认 | IP 阶段的真实访问 origin；后续域名切换时同步调整 |
| LLM provider | 已确认 | NVIDIA；仍需注入真实 `NVIDIA_API_KEY` 并做真实端点验证 |
| 备份策略 | 部分确认 | `/www/backup`、30 日已确认；备份频率、执行用户、恢复演练负责人待确认 |
| `/docs` 与 `/metrics` 暴露策略 | 已确认 | 公网关闭；当前 Nginx 样例返回 404 |
