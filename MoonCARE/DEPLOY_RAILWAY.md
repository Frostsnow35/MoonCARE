# Railway 后端测试部署指南

> 变更日期：2026-06-02  
> 影响范围：后端测试部署、Android App / Web 前端 API 地址、环境变量、数据持久化  
> 当前状态：计划中；需要用真实 Railway 项目、数据库和 LLM Key 验证  

## 1. 定位

Railway 当前只作为 MoonCARE 后端 API 的测试部署方案，用于给 Android V1 和现有 Web 前端提供临时 HTTPS API 地址。它不是 Awareness 后台服务部署方案，也不在 APK 中保存任何后端密钥。

当前推荐链路：

```text
Android App / Web 前端
  -> Railway HTTPS 域名
  -> FastAPI /api/v1/*
  -> SQLite 临时数据 或 Railway PostgreSQL
  -> OpenAI-compatible LLM provider
```

## 2. 部署方式

| 文件 | 用途 | 状态 |
| --- | --- | --- |
| `railway.json` | 使用 `Dockerfile` 构建并检查 `/healthz` | 已有，需要真实部署验证 |
| `Dockerfile` | 构建前端 `dist` 并运行 FastAPI/gunicorn | 已有，需要确认 Railway build 环境 |
| `Procfile` | 兼容简单后端启动 | 已清理为后端 API 单进程 |
| `.env.example` | 本地/服务器环境变量模板 | 已移除 Awareness 配置 |

## 3. Railway 环境变量

在 Railway 项目中至少配置：

```env
APP_NAME=MoonCARE
DEBUG=false
SECRET_KEY=replace-with-strong-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

LLM_PROVIDER=nvidia
NVIDIA_API_KEY=replace-with-your-provider-key

SEMANTIC_CACHE_ENABLED=false
STREAMING_ENABLED=true
ENABLE_GZIP_COMPRESSION=true
HTTP2_ENABLED=false
```

数据库二选一：

| 方案 | 环境变量 | 适用性 |
| --- | --- | --- |
| Railway PostgreSQL | `DATABASE_URL=postgresql://...` 或平台注入值 | 推荐用于多人测试和 Android 联调 |
| SQLite 临时验证 | `DATABASE_URL=sqlite:///./healthai.db` | 只适合短期功能验证；重部署、迁移和并发需要谨慎 |

## 4. 前端和 Android 连接方式

Railway 部署成功后会得到一个 HTTPS 地址，例如：

```text
https://your-mooncare-backend.up.railway.app
```

Web 前端和 Android Capacitor App 应通过环境变量设置：

```env
VITE_API_BASE_URL=https://your-mooncare-backend.up.railway.app/api/v1
```

Android App 不应内置 LLM Key、数据库密码、`SECRET_KEY` 或 Railway token。APK 只保存公开的 API Base URL，并通过 JWT 登录后访问后端。

## 5. 验证清单

| 检查项 | 方式 | 通过标准 |
| --- | --- | --- |
| 健康接口 | 访问 `/healthz` | 返回健康状态，Railway healthcheck 不失败 |
| API 文档 | 访问 `/docs` | 测试环境可访问；正式环境是否暴露需另行确认 |
| 登录注册 | 调用 `/api/v1/auth/*` | JWT 正常返回，token 失效后可重新登录 |
| 聊天安全 | 发送低风险和危机样例 | 普通样例走聊天链路；危机样例进入安全兜底 |
| WebSocket/SSE | 测试聊天实时链路 | Railway 域名下可连接或明确回退 REST |
| 数据持久化 | 重启/重部署后查看用户、日记、周期 | PostgreSQL 方案数据不丢失 |
| 日志脱敏 | 查看 Railway logs | 不输出完整聊天原文、token、LLM Key 或健康隐私 |

## 6. 风险与规避

| 风险 | 影响 | 规避 |
| --- | --- | --- |
| 冷启动或实例休眠 | Android 首次请求慢，聊天等待变长 | 前端显示加载/重试态；后端保留 LLM timeout fallback |
| SQLite 持久化不足 | 重部署或并发测试可能丢数据/锁库 | Android 联调尽早切 Railway PostgreSQL |
| CORS 过宽 | Web 端存在跨站调用风险 | 测试期记录来源；正式域名确定后收敛 CORS |
| WebSocket 兼容性 | 聊天实时体验受影响 | 保留 REST/SSE 回退路径并单独验证 |
| 敏感信息泄露 | 用户健康隐私和密钥风险 | Railway logs、异常日志、前端构建产物都不得包含敏感信息 |

## 7. 当前不使用项

| 项 | 处理 |
| --- | --- |
| Awareness Local / 后台守护进程 | 已从部署路线移除；记忆使用 MoonCARE 自有数据库记忆系统 |
| Railway 内运行前端预览服务 | 不作为 Android V1 必要项；前端可本地构建或独立部署 |
| 生产正式域名 | 当前没有自己的域名，先使用 Railway HTTPS 域名联调 |
