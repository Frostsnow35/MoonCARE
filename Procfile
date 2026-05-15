# Railway 启动配置

# 后端 API 服务
web: cd backend && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

# Awareness 记忆服务（后台守护进程）
# 注意：Railway 免费版不支持后台进程，需要付费版或使用本地数据库
awareness: npx --yes @awareness-sdk/local@latest start
