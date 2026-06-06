import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { mobileAPI } from '../api'
import {
  downloadAndInstall,
  exitNativeApp,
  getNativeAppInfo,
  isNativeAndroid,
  openInstallPermissionSettings
} from '../plugins/mooncareUpdater'

const explicitUpdateCheckUrl = (import.meta.env.VITE_APP_UPDATE_CHECK_URL || '').trim()
const secureUpdateChecksEnabled =
  explicitUpdateCheckUrl.startsWith('https://') &&
  (import.meta.env.VITE_APP_UPDATE_AUTO_CHECK || 'true') === 'true'

function mapReleaseError(error) {
  const detail = error?.response?.data?.detail
  return detail || error?.message || '检查更新失败，请稍后再试。'
}

function mapInstallError(error) {
  const message = error?.message || '下载安装更新包失败，请稍后再试。'
  const code = error?.code || 'download_install_failed'
  return { code, message }
}

export const useAppUpdateStore = defineStore('appUpdate', () => {
  const appInfo = ref({
    platform: 'web',
    appName: 'MoonCARE',
    versionName: 'web',
    versionCode: 0,
    updateChannel: import.meta.env.VITE_APP_UPDATE_CHANNEL || 'beta',
    flavor: import.meta.env.VITE_APP_FLAVOR || 'web',
    selfUpdateEnabled: false,
    applicationId: 'web'
  })
  const latestRelease = ref(null)
  const status = ref('idle')
  const lastCheckedAt = ref(null)
  const errorMessage = ref('')
  const errorCode = ref('')
  const promptVisible = ref(false)
  const isChecking = ref(false)
  const isUpdating = ref(false)
  const initialized = ref(false)

  const supportsSelfUpdate = computed(() => isNativeAndroid() && appInfo.value.selfUpdateEnabled)
  const hasUpdateAvailable = computed(() => {
    if (!latestRelease.value) return false
    return Number(latestRelease.value.version_code || 0) > Number(appInfo.value.versionCode || 0)
  })
  const isForceUpdate = computed(() => {
    if (!latestRelease.value) return false
    return Boolean(latestRelease.value.force_update) ||
      Number(appInfo.value.versionCode || 0) < Number(latestRelease.value.min_supported_version_code || 0)
  })
  const canDismissPrompt = computed(() => !isForceUpdate.value)
  const needsInstallPermission = computed(() => errorCode.value === 'install_permission_required')
  const currentVersionLabel = computed(() => `${appInfo.value.versionName} (${appInfo.value.versionCode})`)
  const latestVersionLabel = computed(() => {
    if (!latestRelease.value) return '暂无可用版本'
    return `${latestRelease.value.version_name} (${latestRelease.value.version_code})`
  })
  const latestPublishedAtLabel = computed(() => {
    if (!latestRelease.value?.published_at) return 'N/A'
    return new Date(latestRelease.value.published_at).toLocaleString('zh-CN', {
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  })
  const downloadUrl = computed(() => latestRelease.value?.apk_url || '')
  const releaseNotes = computed(() => latestRelease.value?.release_notes || [])
  const statusLabel = computed(() => {
    switch (status.value) {
      case 'checking':
        return '正在检查更新'
      case 'up_to_date':
        return '当前已经是最新版本'
      case 'update_available':
        return '发现新版本，可以稍后更新'
      case 'force_update':
        return '当前版本已停止支持，更新后才能继续使用'
      case 'installer_opened':
        return '安装界面已经打开'
      case 'error':
        return errorMessage.value || '检查失败'
      case 'unsupported':
        return '当前环境不支持应用内更新'
      default:
        return '尚未检查更新'
    }
  })

  async function initialize() {
    if (initialized.value) return

    initialized.value = true
    await loadAppInfo()
    if (appInfo.value.platform === 'android' && secureUpdateChecksEnabled) {
      await checkForUpdates({ silent: true })
    } else {
      status.value = 'unsupported'
    }
  }

  async function loadAppInfo() {
    try {
      appInfo.value = await getNativeAppInfo()
    } catch (error) {
      const normalized = mapInstallError(error)
      errorCode.value = normalized.code
      errorMessage.value = normalized.message
      status.value = 'error'
    }
  }

  async function checkForUpdates({ silent = false } = {}) {
    if (appInfo.value.platform !== 'android') {
      status.value = 'unsupported'
      lastCheckedAt.value = new Date().toISOString()
      return null
    }

    if (!secureUpdateChecksEnabled) {
      errorMessage.value = '当前调试环境未配置 HTTPS 更新地址'
      errorCode.value = 'update_endpoint_unavailable'
      status.value = 'unsupported'
      lastCheckedAt.value = new Date().toISOString()
      if (!silent) promptVisible.value = false
      return null
    }

    isChecking.value = true
    errorMessage.value = ''
    errorCode.value = ''

    try {
      const response = await mobileAPI.getAndroidRelease(appInfo.value.updateChannel || 'beta')
      const release = response.data || response
      latestRelease.value = release
      lastCheckedAt.value = new Date().toISOString()

      if (!hasUpdateAvailable.value) {
        status.value = 'up_to_date'
        if (!silent) promptVisible.value = false
        return null
      }

      status.value = isForceUpdate.value ? 'force_update' : 'update_available'
      promptVisible.value = true
      return release
    } catch (error) {
      errorMessage.value = mapReleaseError(error)
      errorCode.value = error?.code || ''
      status.value = 'error'
      lastCheckedAt.value = new Date().toISOString()
      if (!silent) promptVisible.value = false
      return null
    } finally {
      isChecking.value = false
    }
  }

  async function startUpdate() {
    if (!supportsSelfUpdate.value || !latestRelease.value) return null

    isUpdating.value = true
    errorMessage.value = ''
    errorCode.value = ''

    try {
      const fileName = `MoonCARE-${appInfo.value.flavor}-${latestRelease.value.version_name}-${latestRelease.value.version_code}.apk`
      const result = await downloadAndInstall({
        url: latestRelease.value.apk_url,
        sha256: latestRelease.value.sha256,
        fileName
      })
      status.value = 'installer_opened'
      promptVisible.value = isForceUpdate.value
      lastCheckedAt.value = new Date().toISOString()
      return result
    } catch (error) {
      const normalized = mapInstallError(error)
      errorCode.value = normalized.code
      errorMessage.value = normalized.message
      status.value = 'error'
      promptVisible.value = true
      return null
    } finally {
      isUpdating.value = false
    }
  }

  function dismissPrompt() {
    if (isForceUpdate.value) return
    promptVisible.value = false
  }

  async function openInstallerSettings() {
    return openInstallPermissionSettings()
  }

  async function exitForUpdate() {
    return exitNativeApp()
  }

  function openDownloadPage() {
    if (!downloadUrl.value || typeof window === 'undefined') return null
    window.open(downloadUrl.value, '_blank', 'noopener,noreferrer')
    return downloadUrl.value
  }

  return {
    appInfo,
    latestRelease,
    status,
    lastCheckedAt,
    errorMessage,
    errorCode,
    promptVisible,
    isChecking,
    isUpdating,
    supportsSelfUpdate,
    hasUpdateAvailable,
    isForceUpdate,
    canDismissPrompt,
    needsInstallPermission,
    currentVersionLabel,
    latestVersionLabel,
    latestPublishedAtLabel,
    downloadUrl,
    releaseNotes,
    statusLabel,
    initialize,
    loadAppInfo,
    checkForUpdates,
    startUpdate,
    dismissPrompt,
    openInstallerSettings,
    exitForUpdate,
    openDownloadPage
  }
})
