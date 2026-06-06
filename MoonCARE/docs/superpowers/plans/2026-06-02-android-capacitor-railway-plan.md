# MoonCARE Android V1 + Railway 测试后端执行计划

> 变更日期：2026-06-02  
> 影响范围：Android V1、Capacitor 包装、Railway 后端测试部署、硬件数据接入预留、应用商店上架准备  
> 当前状态：计划中；已确认 V1 使用 Capacitor 复用现有 Vue 前端，不影响网站端使用效果  

## 1. 已确认需求

| 问题 | 已确认答案 | 执行含义 |
| --- | --- | --- |
| 发布目标 | 准备应用商店上架 | V1 需要 release 构建、签名、隐私说明、权限最小化、测试包和正式包区分 |
| 技术路线 | 接受 Capacitor 复用 Vue | 不重写网站端；通过独立 Android shell 和环境变量接入现有前端 |
| 网站端影响 | 不能影响原本网站端使用效果 | Capacitor 配置必须独立；`npm run build` 和 Vite Web 访问继续可用 |
| 硬件数据 | V1 要允许接入硬件数据 | 先预留 Android 权限、Capacitor plugin/原生桥接边界和后端 `/api/v1/biometric/*` 数据入口 |
| 后端 | 先用局域网/测试服务器调试；尝试 Railway 部署后端 | 本地联调用 LAN 地址；远程测试用 Railway HTTPS API Base URL |
| 域名 | 暂无自有服务器域名 | 上架前可先用 Railway 域名验证；正式上架需评估稳定域名和隐私政策链接 |

## 2. 推荐架构

```text
Android App (Capacitor + Vue dist)
  -> app config: VITE_API_BASE_URL
  -> Railway HTTPS 后端 或 局域网测试后端
  -> FastAPI /api/v1/*
  -> JWT 用户隔离
  -> Chat / Cycle / Diary / Music / Breathing / Biometric
```

V1 不在 APK 内保存 LLM Key、数据库密码、`SECRET_KEY` 或 Railway token。所有 AI、数据库、用户数据写入都留在后端。

## 3. 第一阶段任务

| 阶段 | 内容 | 完成标准 |
| --- | --- | --- |
| M0 配置基线 | 补齐 Redis/后端环境变量基线；保留 Railway 后端测试部署配置 | `package.json` 无额外外部记忆服务脚本；`Procfile` 无额外记忆 worker；`railway.json` 可运行后端 |
| M1 Railway 后端 | 用 `Dockerfile` 部署 FastAPI，设置环境变量和数据库 | `/healthz` 可访问；登录、聊天、日记、周期 API 可用 |
| M2 Capacitor 骨架 | 在不破坏 Web build 的前提下新增 Android shell | `frontend/npm run build` 仍通过；Android debug APK 可安装 |
| M3 API 环境切换 | 支持 LAN、Railway 两套 API Base URL | 本地调试和 Railway 联调可切换，不改源码常量 |
| M4 硬件接入预留 | 明确蓝牙/USB/生理数据权限、桥接接口和后端上传格式 | App 可请求必要权限；硬件数据先写入现有 biometric 接口或新增兼容接口 |
| M5 上架准备 | 签名、隐私政策、权限说明、崩溃/日志脱敏、测试清单 | 可生成 release 包；无密钥和敏感原文进入 APK 或日志 |

## 4. 关键风险

| 风险 | 规避 |
| --- | --- |
| Capacitor 改动影响 Web 端 | Android 配置放在独立文件；Web 构建命令保持 `frontend/npm run build` |
| Railway 冷启动/不稳定 | App 显示加载和重试；聊天保留 REST/SSE 回退；LLM timeout fallback 必须保留 |
| 硬件权限过多影响上架 | V1 只申请真实使用的权限；未接入的硬件权限不提前声明 |
| 用户健康隐私泄露 | 日志不保存完整聊天、token、硬件原始敏感数据；APK 不内置密钥 |
| 危机安全链路被移动端绕过 | Android 只调用现有 `/api/v1/chat/*`，不得新增绕过 Perception/Router 的聊天入口 |

## 5. 下一步执行顺序

1. 验证当前后端配置清理和 Railway 配置：编译、后端单测、前端 build。
2. 若通过，安装 Capacitor 依赖并初始化 Android 工程。
3. 增加 Android 专用 API Base URL 配置，不改网站端默认行为。
4. 在局域网后端跑 Android debug APK，验证登录、聊天、日记、周期。
5. 部署 Railway 后端，切换 App 到 Railway HTTPS API。
6. 再设计硬件数据专项：先确定硬件协议、数据字段、权限和最小保存策略。
