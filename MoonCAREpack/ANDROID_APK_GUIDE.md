# 从部署到手机 APK 可用的全过程指南

> 目标：把 MoonCARE 部署到服务器后，在你的 Android 手机上得到一个**可以直接打开、连上服务器、正常聊天**的 APK。
> 全程不需要上架应用商店（侧载安装即可）。

## 一、整体架构（先看懂，再动手）

```
┌─────────────┐    HTTP/HTTPS    ┌──────────────────────┐
│  Android 手机 │ ──────────────► │  你的服务器            │
│  · PWA/浏览器 │   REST / WS     │  Docker:              │
│  · MoonCARE  │   / SSE         │   · FastAPI + 前端     │
│    APK       │                 │   · PostgreSQL         │
└─────────────┘                 └──────────────────────┘
```

关键点：
- APK 是"外壳 + 内置网页"：它内置了构建好的前端（dist），通过 Capacitor WebView 运行。
- 前端**在运行时**决定连哪台服务器：首次打开在登录页填"服务器地址"，或用 `--server` 参数打包时写死默认值。
- 因此 **APK 和服务器是解耦的**：同一份 APK 可以指向任意一台部署了 MoonCARE 的服务器。

## 二、先决条件

### A. 服务器已按 `DEPLOY_QUICKSTART.md` 部署好
验证：手机浏览器能打开 `http://服务器IP:18000` 并正常登录、聊天。

### B. 打包机器（你的电脑或一台有 Docker 的服务器）
APK 用 Gradle 编译，需要：

| 依赖 | 版本要求 |
| --- | --- |
| Node.js | ≥ 20（前端构建） |
| npm | ≥ 10 |
| JDK | 17 或 21（Capacitor 8 建议 21） |
| Android SDK | platform 36 + build-tools；通过 `ANDROID_HOME` 或 `frontend/android/local.properties` 指定 |

安装 Android SDK（Linux 示例，Mac 同理）：

```bash
# 下载 commandline-tools
mkdir -p ~/android-sdk/cmdline-tools && cd ~/android-sdk/cmdline-tools
curl -LO https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
unzip commandlinetools-linux-*.zip && mv cmdline-tools latest

# 安装所需组件
export ANDROID_HOME=~/android-sdk
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools
yes | sdkmanager --licenses
sdkmanager "platforms;android-36" "build-tools;36.0.0" "platform-tools"
```

## 三、在服务器上产出 APK（最快的验证路径）

> 服务器已装 Docker；我们用 Docker 跑 Node + Capacitor，再用宿主机的 JDK/Gradle 编译。
> 如果你的打包机器就是服务器本机且装好了 JDK+SDK，直接跳到第 2 步。

### 1. 生成 Android 工程（一次）

在 `frontend` 目录初始化 Capacitor Android 平台：

```bash
cd /www/wwwroot/MoonCARE/frontend
npm install                      # 安装 Capacitor 依赖
npm run build                    # 构建前端到 dist
npx cap add android              # 生成 android/ 原生工程（首次）
```

### 2. 一键构建 debug APK

```bash
cd /www/wwwroot/MoonCARE/frontend
npm run apk                       # = bash scripts/build-apk.sh
```

脚本会：重新构建前端 → `cap sync` → 打上 `usesCleartextTraffic` → Gradle 产出 APK。

产物在：`frontend/android/app/build/outputs/apk/debug/app-debug.apk`

把 APK 传到手机安装：
```bash
# 方式一：连 USB 直接装
adb install android/app/build/outputs/apk/debug/app-debug.apk

# 方式二：传到手机
scp android/app/build/outputs/apk/debug/app-debug.apk user@你手机可达的地址:/tmp/
# 手机上打开该文件，允许"安装未知来源应用"
```

### 3. 打开 APK 并连接服务器

1. 打开 MoonCARE APP → 登录页。
2. 在"服务器地址"填：`http://服务器IP:18000`（**先点保存，再填邮箱密码**）。
3. 登录 → 进入"聊聊" → 发消息，验证 AI 回复。

> 想让 APK **默认就指向你的服务器**（用户无需填写），打包时加参数：
> ```bash
> npm run apk -- --server http://服务器IP:18000
> ```
> 这样首次启动会自动预填该地址，用户仍可在"我的 → 服务器地址"里改。

## 四、把"调试 APK"升级为"可分享的 Release APK"

调试包（debug）可以安装使用，但体积大、无签名优化，不适合长期分发。正式发布请用 release：

### 1. 生成签名证书（只做一次，务必备份）

```bash
cd /www/wwwroot/MoonCARE/frontend
sh scripts/create-keystore.sh
# 按提示设置密码（keystore 密码 和 key 密码用同一个，便于脚本使用）
# 产物：android/mooncare-release.keystore
```

### 2. 构建签名 Release APK

```bash
cd /www/wwwroot/MoonCARE/frontend
npm run apk -- --release \
  --server http://服务器IP:18000 \
  --keystore android/mooncare-release.keystore \
  --store-pass '你的密码' \
  --alias mooncare
```

产物：`frontend/android/app/build/outputs/apk/release/app-release.apk`

> 之后的每次更新，都用**同一把 keystore** 签名，否则无法覆盖安装（Android 要求签名一致）。

## 五、（可选）进阶：在本地电脑用 Android Studio 开发调试

1. `cd frontend && npx cap open android`（自动打开 Android Studio）。
2. 用 Android Studio 的 Device Manager 创建模拟器或连接真机。
3. Run 即可边改前端边实时预览（`npm run dev` 配合 `server.url` 指向本地 Vite）。

## 六、验证清单（上线前逐项确认）

| # | 检查项 | 怎么验证 |
| --- | --- | --- |
| 1 | 登录/注册 | APK 内注册新账号（需 SMTP 验证码），或登录已有账号 |
| 2 | AI 聊天 | 发消息能收到流式回复；断网重连后会话可续 |
| 3 | 周期记录 | 新增周期记录，预测显示正常 |
| 4 | 日记 | 写日记 → 列表可见 → 情绪标签正常 |
| 5 | 音乐 | 内置音乐可播放（音频 URL 已按服务器地址解析） |
| 6 | 服务器地址切换 | "我的 → 服务器地址"改成错误地址后再改回来，功能恢复 |
| 7 | 数据备份 | 服务器上能 `pg_dump` 出数据库 |

## 七、常见问题

| 现象 | 原因/处理 |
| --- | --- |
| APK 打开白屏 | 前端没构建进 APK；重跑 `npm run build` + `npm run apk` |
| 登录提示网络错误 | 服务器地址没填/填错；APK 内 WebView 对纯 HTTP 需 `usesCleartextTraffic`（脚本已自动打补丁） |
| 聊天一直转圈 | 检查服务器 18000 端口放行；确认 Nginx（如用）已配 WebSocket upgrade |
| 音乐播放失败 | 服务器上 `backend/music` 是否有音频文件；手机与服务器网络互通 |
| 覆盖安装失败"应用未安装" | 签名不一致：必须用同一 keystore |
| 手机上提示"仅可安装受信任应用" | 系统设置里临时允许"安装未知来源"，或用 Android Studio 直装 |

## 八、PWA 作为 APK 之外的备选

- 服务器升级到 HTTPS（见 DEPLOY_QUICKSTART.md 第 8 节）后，手机浏览器打开站点即可"添加到主屏幕"。
- 效果接近 APK（独立窗口、图标、离线壳），但依赖浏览器，且每次打开需联网加载数据。
- APK 与 PWA 二选一即可；两者共用同一套前端代码和服务器。

## 九、安全边界提醒

- 公网部署必须 `DEBUG=false`，否则测试账号和日志验证码会暴露。
- `.env`、keystore 绝不上传 Git / 不外传。
- AI 回复仅作参考、不作诊断；危机表达走产品内置安全链路。
