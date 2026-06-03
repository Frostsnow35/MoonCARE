import { Capacitor, registerPlugin } from '@capacitor/core'

const MooncareUpdater = Capacitor.isNativePlatform()
  ? registerPlugin('MooncareUpdater')
  : null

function normalizeNativeError(error, fallbackCode = 'unknown_error') {
  if (!error) {
    return { code: fallbackCode, message: '未知错误' }
  }

  return {
    code: error.code || fallbackCode,
    message: error.message || String(error)
  }
}

export function isNativeAndroid() {
  return Capacitor.isNativePlatform() && Capacitor.getPlatform() === 'android'
}

export async function getNativeAppInfo() {
  if (!isNativeAndroid() || !MooncareUpdater) {
    return {
      platform: Capacitor.getPlatform(),
      appName: 'MoonCARE',
      versionName: import.meta.env.VITE_APP_VERSION_NAME || 'web',
      versionCode: Number(import.meta.env.VITE_APP_VERSION_CODE || 0),
      updateChannel: import.meta.env.VITE_APP_UPDATE_CHANNEL || 'beta',
      flavor: import.meta.env.VITE_APP_FLAVOR || 'web',
      selfUpdateEnabled: false,
      applicationId: 'web'
    }
  }

  try {
    return await MooncareUpdater.getAppInfo()
  } catch (error) {
    throw normalizeNativeError(error, 'app_info_failed')
  }
}

export async function downloadAndInstall(payload) {
  if (!isNativeAndroid() || !MooncareUpdater) {
    throw { code: 'unsupported_platform', message: '当前环境不支持应用内安装更新。' }
  }

  try {
    return await MooncareUpdater.downloadAndInstall(payload)
  } catch (error) {
    throw normalizeNativeError(error, 'download_install_failed')
  }
}

export async function openInstallPermissionSettings() {
  if (!isNativeAndroid() || !MooncareUpdater) return null

  try {
    return await MooncareUpdater.openInstallPermissionSettings()
  } catch (error) {
    throw normalizeNativeError(error, 'open_install_settings_failed')
  }
}

export async function exitNativeApp() {
  if (!isNativeAndroid() || !MooncareUpdater) return null

  try {
    return await MooncareUpdater.exitApp()
  } catch (error) {
    throw normalizeNativeError(error, 'exit_app_failed')
  }
}
