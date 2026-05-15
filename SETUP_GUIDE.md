# MoonCARE 本地开发环境设置指南

## 前置要求

确保你的电脑已安装：
- **Node.js** (v16 或更高) - https://nodejs.org/
- **Python** (3.10 或更高) - https://www.python.org/downloads/

## 快速开始

### 1. 克隆项目
```bash
git clone <你的仓库地址>
cd MoonCARE
```

### 2. 一键启动（推荐）

Windows 用户：
```bash
python start_mooncare.py
```

macOS / Linux 用户：
```bash
python3 start_mooncare.py
```

启动脚本会自动：
- 检查环境
- 启动 Awareness 记忆服务
- 启动后端 API 服务
- 启动前端开发服务器

### 3. 访问应用

打开浏览器访问：
- **前端界面**: http://localhost:3000
- **后端 API 文档**: http://localhost:8000/docs
- **Awareness 记忆服务**: http://localhost:37800

## 手动启动（如需要）

如果一键启动失败，可以按以下步骤手动启动：

### 安装依赖

**前端依赖：**
```bash
cd frontend
npm install
cd ..
```

**后端依赖：**
```bash
cd backend
pip install -r requirements.txt
cd ..
```

### 启动服务

**1. 启动 Awareness 记忆服务（可选但推荐）**
```bash
npx --yes @awareness-sdk/local@latest start
```

**2. 启动后端服务（新终端）**
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**3. 启动前端服务（新终端）**
```bash
cd frontend
npm run dev
```

## 项目结构说明

```
MoonCARE/
├── frontend/          # Vue 3 前端项目
│   ├── src/
│   │   ├── views/    # 页面组件
│   │   ├── components/ # 可复用组件
│   │   └── stores/   # Pinia 状态管理
│   └── package.json
├── backend/          # FastAPI 后端项目
│   ├── app/
│   │   ├── api/     # API 路由
│   │   ├── models/  # 数据模型
│   │   └── services/ # 业务逻辑
│   └── requirements.txt
├── .awareness/       # Awareness 记忆数据（自动生成）
└── start_mooncare.py # 一键启动脚本
```

## 常用开发命令

### 前端
```bash
cd frontend
npm run dev      # 启动开发服务器
npm run build    # 构建生产版本
npm run preview  # 预览构建结果
```

### 后端
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload  # 开发模式（自动重载）
```

## 环境变量配置

如需配置环境变量，在 `backend/` 目录创建 `.env` 文件（参考 `.env.railway`）：

```env
# 后端配置
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Awareness 记忆服务
AWARENESS_MEMORY_ENABLED=true
AWARENESS_BASE_URL=http://localhost:37800
```

## 开发注意事项

1. **数据库文件**: SQLite 数据库文件会在首次运行时自动创建，已在 `.gitignore` 中忽略
2. **端口占用**: 确保 3000、8000、37800 端口未被占用
3. **Awareness 服务**: 可选但推荐，如无法启动，系统会自动回退到数据库存储
4. **代码提交**: 提交前确保所有功能正常，不要提交 `.env`、数据库文件等敏感数据

## 常见问题

**Q: npm install 很慢？**
A: 使用国内镜像：`npm install --registry=https://registry.npmmirror.com`

**Q: pip install 很慢？**
A: 使用国内镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

**Q: 端口被占用？**
A: 可以修改启动端口，或关闭占用端口的进程

**Q: Awareness 服务启动失败？**
A: 不影响使用，系统会自动使用本地数据库，只是缺少长期记忆功能

## 获取帮助

- API 文档：http://localhost:8000/docs
- 提交 Issue：在 GitHub 仓库中提问题
