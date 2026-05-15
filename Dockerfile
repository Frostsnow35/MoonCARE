# ========== 阶段1：构建前端 ==========
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
# 复制前端依赖文件
COPY frontend/package*.json ./
RUN npm ci --only=production && npm cache clean --force
# 复制源码并构建
COPY frontend/ ./
RUN npm run build

# ========== 阶段2：后端基础依赖 ==========
FROM python:3.11-slim AS backend-base
WORKDIR /app
# 安装系统依赖（编译 psycopg2 所需）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install gunicorn uvloop

# ========== 阶段3：最终运行镜像 ==========
FROM python:3.11-slim
WORKDIR /app
# 创建非 root 用户
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

# 从 backend-base 复制已安装的依赖和可执行文件
COPY --from=backend-base --chown=appuser:appgroup /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-base --chown=appuser:appgroup /usr/local/bin /usr/local/bin

# 复制后端代码
COPY backend/ ./backend/
# 从前端构建阶段复制 dist
COPY --from=frontend-builder --chown=appuser:appgroup /app/frontend/dist ./frontend/dist

# 复制启动脚本并赋予执行权限
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

USER appuser
EXPOSE 8000

# 使用 gunicorn + uvicorn worker 运行，entrypoint 会先执行迁移
ENTRYPOINT ["./entrypoint.sh"]
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000", "--timeout", "120", "backend.app.main:app"]