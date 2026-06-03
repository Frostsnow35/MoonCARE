# MoonCARE Android 自建更新说明

> 变更日期：2026-06-03  
> 影响范围：Android `internal/public` flavor、版本清单接口、自建 APK 更新、签名与发布脚本  
> 当前状态：已完成基础实现；需要真实 keystore、HTTPS 域名和 release 包验证

## 1. 已完成

| 项目 | 状态 | 说明 |
| --- | --- | --- |
| Android 双 flavor | 已完成 | `internal` 支持应用内 APK 更新；`public` 预留未来商店包 |
| 发布元数据接口 | 已完成 | `GET /api/v1/mobile/releases/android/{channel}` |
| APK 下载路由 | 已完成 | `GET /api/v1/mobile/releases/android/{channel}/download` |
| App 内更新入口 | 已完成 | 启动后台检查 + 个人中心手动检查 + 强更弹层 |
| 原生安装桥接 | 已完成 | Android 原生下载、SHA256 校验、拉起安装 |
| MoonCARE 包装资源 | 已完成 | 替换默认图标、启动图、标题与测试包名残留 |

## 2. 环境变量与目录

| 变量 / 路径 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `MOBILE_RELEASES_DIR` | string | `PROJECT_ROOT/mobile_releases` | 存放 canonical APK 与 `android-{channel}.json` 的服务器目录 |
| `MOBILE_RELEASES_PUBLIC_BASE_URL` | string | `None` | 对外 HTTPS 域名基址；客户端生成 `apk_url` 时优先使用 |
| `VITE_APP_UPDATE_CHANNEL` | string | `beta` | 前端默认查询通道，`internal` 建议 `beta`，`public` 建议 `stable` |
| `VITE_APP_UPDATE_CHECK_URL` | string | `${VITE_API_BASE_URL}/mobile/releases/android` | 前端查询更新元数据的 URL 前缀 |
| `frontend/android/keystore.properties` | file | 无 | 本地 release 签名配置，不进仓库 |

`MOBILE_RELEASES_PUBLIC_BASE_URL` 必须使用 HTTPS。  
如果未设置，后端会退回到当前请求 base URL；非 HTTPS 时会拒绝返回可用更新元数据。

## 3. 发布步骤

1. 先准备签名文件。
2. 在 `frontend/android/keystore.properties` 填写：

```properties
storeFile=D:\\Android\\keystores\\mooncare-release.jks
storePassword=replace_with_store_password
keyAlias=mooncare
keyPassword=replace_with_key_password
```

3. 构建 release APK。

```powershell
cd frontend
npm run cap:sync:android
cd android
.\gradlew.bat assembleInternalRelease
.\gradlew.bat assemblePublicRelease
```

4. 用脚本生成 canonical APK 和 `android-{channel}.json`。

```powershell
python frontend\scripts\prepare_android_release.py `
  --apk frontend\android\app\build\outputs\apk\internal\release\MoonCARE-internal-1.1.0-2.apk `
  --channel beta `
  --flavor internal `
  --version-name 1.1.0 `
  --version-code 2 `
  --min-supported-version-code 1 `
  --base-url https://updates.example.com `
  --release-note "修复聊天历史恢复" `
  --release-note "新增应用内更新入口"
```

5. 把 `mobile_releases/` 目录部署到服务器可访问位置，并保证 API 服务读取同一目录。

## 4. 需要验证

| 项目 | 状态 | 说明 |
| --- | --- | --- |
| `internalRelease` 真机安装升级 | 需要验证 | 需真实 keystore + HTTPS 下载链路 |
| 安装权限拒绝后的恢复 | 需要验证 | 应能跳转“允许安装未知应用”设置页后继续 |
| 强更阻断 | 需要验证 | `min_supported_version_code` 高于当前版本时必须阻断使用 |
| 服务器回滚 | 需要验证 | 替换 `android-beta.json` 后旧包不能进入错误循环更新 |

## 5. 注意事项

- 不要把 `SECRET_KEY`、数据库密码、LLM API Key、发布后台凭据写进 APK 或仓库。
- `internal` flavor 才允许 `REQUEST_INSTALL_PACKAGES`；未来上架商店时请使用 `public` flavor。
- 自建更新只支持完整 APK，不支持静默替换 Web bundle。
- 如果修改版本规则或更新协议，需要同步更新本文件和移动端测试清单。
