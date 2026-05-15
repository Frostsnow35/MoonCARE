# Railway 部署指南

## 概述

Railway 是一个现代化的云部署平台，支持：
- ✅ Python 后端（FastAPI/uvicorn）
- ✅ Node.js 前端
- ✅ 后台进程（如 Awareness 守护进程）
- ✅ SQLite 数据库
- ✅ 环境变量管理
- ✅ 免费额度：每月 500 小时

## 部署步骤

### 1. 准备 Railway 账号

1. 访问 [Railway.app](https://railway.app)
2. 使用 GitHub 账号登录
3. 创建新项目

### 2. 部署后端 + Awareness 服务

后端包含 API 服务和 Awareness 记忆服务：

1. 在 Railway 中点击 **New Project** → **Deploy from GitHub repo**
2. 选择你的 MoonCARE 仓库
3. Railway 会自动检测 Python 项目并部署

**环境变量配置：**

在 Railway 项目设置中添加以下环境变量：

```
# 后端配置
APP_NAME=MoonCARE
DEBUG=false
SECRET_KEY=your-production-secret-key-change-this

# LLM 提供商（选择其中一个）
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=your-nvidia-api-key

# 或者使用 OpenAI
# LLM_PROVIDER=openai
# OPENAI_API_KEY=your-openai-api-key

# Awareness 配置
AWARENESS_MEMORY_ENABLED=true
AWARENESS_BASE_URL=http://localhost:37800
AWARENESS_MCP_PATH=/mcp

# 数据库（使用 Railway 提供的 SQLite）
DATABASE_URL=sqlite:///./healthai.db

# JWT 配置
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

4. 部署命令：
```
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. 启动 Awareness 服务

Railway 支持后台进程。你可以在 `Procfile` 中定义：

```procfile
web: cd backend && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
awareness: npx --yes @awareness-sdk/local@latest start
```

或者在 Railway 的 **Background Workers** 中添加 Awareness 服务。

### 4. 部署前端（可选：也可以单独部署到 Vercel）

如果你想使用 Vercel 部署前端，需要：

1. 在 `frontend/vite.config.js` 中更新 API 地址：
```javascript
// 将这个
const api_base_url = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

// 改为 Railway 提供的后端地址
const api_base_url = 'https://your-railway-app.railway.app/api/v1'
```

2. 然后部署到 Vercel（按照之前修复的 vercel.json 配置）

### 5. 配置前端环境变量

在 Vercel 中设置：
```
VITE_API_BASE_URL=https://your-railway-app.railway.app/api/v1
```

## 更简单的方案：全部部署到 Railway

如果不想分开部署前端和后端，Railway 可以托管整个应用：

1. 创建一个 `start.sh` 启动脚本：
```bash
#!/bin/bash

# 启动 Awareness 服务（后台）
npx --yes @awareness-sdk/local@latest start &
AWareness_PID=$!

# 等待 Awareness 启动
sleep 5

# 启动后端
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

2. 在 Railway 中配置：
- Build: `npm install && cd frontend && npm install && npm run build`
- Start: `cd frontend && npm run preview`

## Railway 免费额度说明

- **500 小时/月**（足够个人使用）
- **2 个项目**免费
- **100 GB 带宽/月**
- SQLite 数据库免费（512 MB 存储）

## 注意事项

1. **Awareness 服务**：默认情况下，Railway 的免费版不支持需要长期运行的守护进程。如果需要 Awareness 功能，可能需要：
   - 使用 Railway 的付费版（$5/月）
   - 或者将 `AWARENESS_MEMORY_ENABLED` 设为 `false`，系统会使用本地数据库

2. **休眠**：Railway 免费版在 24 小时无活动后会休眠，首次访问可能需要等待几秒启动

3. **HTTPS**：Railway 自动提供 HTTPS，无需额外配置

## 获取帮助

- Railway 文档：https://docs.railway.app
- Railway Discord：https://discord.gg/railway

## 快速部署链接

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new)
