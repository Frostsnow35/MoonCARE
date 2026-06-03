# MoonCARE 移动端开发指南

本项目使用 **Vue.js** 作为前端框架，并通过 **Capacitor** 适配 Android 平台。后端采用 **FastAPI**。

## 项目结构
- `frontend/`: Vue.js 前端项目
  - `android/`: Android Studio 原生工程
  - `capacitor.config.json`: Capacitor 配置文件
- `backend/`: FastAPI 后端项目

## 开发环境准备
1. **Node.js**: 建议使用 v16+
2. **Python**: 建议使用 3.10+
3. **Android Studio**: 用于编译和运行 Android 应用
4. **JDK 17**: Android 开发必需

## 快速开始

### 1. 后端启动
```bash
cd backend
pip install -r requirements.txt
python run.py
```
默认运行在 `http://localhost:8000`。如果是真机调试，请确保手机与电脑在同一局域网，并修改前端配置。

### 2. 前端开发环境
```bash
cd frontend
npm install
npm run dev
```

### 3. 移动端编译与运行 (Android)
1. **配置环境变量**:
   修改 `frontend/.env.android` 中的 `VITE_API_BASE_URL` 为你电脑的局域网 IP。
   
2. **同步并构建**:
   ```bash
   cd frontend
   npm run build
   npx cap sync android
   ```

3. **打开 Android Studio**:
   ```bash
   npx cap open android
   ```
   在 Android Studio 中点击 "Run" 按钮即可在模拟器或真机上运行。

## 注意事项
- **局域网访问**: 真机调试时，API 地址不能是 `localhost`，必须是电脑的局域网 IP（如 `http://192.168.x.x:8000`）。
- **HTTPS**: 如果后端没有配置 SSL，Android 可能需要 `network_security_config.xml` 配置（已在项目中包含）。
- **资源更新**: 每次修改 Vue 代码后，需要运行 `npm run build` 和 `npx cap copy android` 来更新 Android 原生工程中的资源。
