# MoonCARE 启动说明

## 一键启动（推荐）

### Windows 用户
1. 双击运行 `start_mooncare.py`
2. 或在终端中运行：`python start_mooncare.py`

### macOS / Linux 用户
1. 在终端中运行：`python3 start_mooncare.py`

## 手动启动

如果一键启动失败，可以手动依次启动：

### 1. 安装前端依赖
```bash
cd frontend
npm install
```

### 2. 启动 Awareness 记忆服务
```bash
npx --yes @awareness-sdk/local@latest start
```
这会在 `localhost:37800` 启动本地记忆服务，数据存储在 `.awareness/` 目录。

### 3. 启动后端
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. 启动前端
```bash
cd frontend
npm run dev
```

## 访问地址

- 前端：http://localhost:3000
- 后端：http://localhost:8000
- API 文档：http://localhost:8000/docs
- 记忆服务：http://localhost:37800

## 注意事项

1. **Node.js 和 Python 3.10+ 是必须的**
   - Node.js：https://nodejs.org/
   - Python：https://www.python.org/downloads/

2. **Awareness 记忆服务是可选的**
   - 它提供本地长期记忆功能
   - 如果启动失败，系统会自动回退到本地数据库
   - 无需账号，完全离线使用

3. **如果端口被占用**
   - 3000：前端
   - 8000：后端
   - 37800：记忆服务

## 使用 npm 脚本启动（需先安装依赖）

在项目根目录运行：
```bash
npm install
npm run dev  # 只启动 Awareness 服务
```
