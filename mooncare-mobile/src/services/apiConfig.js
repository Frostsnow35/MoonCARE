import { get_kv, set_kv } from './kv'

export const DEFAULT_API_BASE_URL = 'http://159.75.13.158:8000/api/v1'
export const MOBILE_BUILD_MARKER = '2026-06-06-mobile-auth-hotfix-1'
export const SHOW_DEBUG_SERVER_CONFIG =
  import.meta.env.DEV || import.meta.env.VITE_SHOW_DEBUG_TOOLS === 'true'

function trimTrailingSlashes(value) {
  return value.replace(/\/+$/, '')
}

export function normalizeApiBaseUrl(value) {
  const candidate = String(value || '').trim()
  if (!candidate) {
    return DEFAULT_API_BASE_URL
  }
  return trimTrailingSlashes(candidate)
}

export function getApiBaseUrlSync() {
  return normalizeApiBaseUrl(
    localStorage.getItem('api_base_url') ||
      import.meta.env.VITE_API_BASE_URL ||
      DEFAULT_API_BASE_URL
  )
}

export async function getApiBaseUrl() {
  const stored = await get_kv('api_base_url')
  const resolved = normalizeApiBaseUrl(
    stored || import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
  )

  if (stored !== resolved) {
    await set_kv('api_base_url', resolved)
  }

  return resolved
}

export async function saveApiBaseUrl(value) {
  const resolved = normalizeApiBaseUrl(value)
  await set_kv('api_base_url', resolved)
  return resolved
}

export function getHealthUrl(baseUrl = getApiBaseUrlSync()) {
  return `${baseUrl.replace(/\/api\/v1$/, '')}/healthz`
}

export function getBackendOrigin(baseUrl = getApiBaseUrlSync()) {
  return baseUrl.replace(/\/api\/v1$/, '')
}

export async function testApiConnection(baseUrl) {
  const normalized = normalizeApiBaseUrl(baseUrl)
  const healthUrl = getHealthUrl(normalized)
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), 8000)

  try {
    const response = await fetch(healthUrl, {
      method: 'GET',
      cache: 'no-store',
      signal: controller.signal,
    })
    const text = await response.text()
    return {
      ok: response.ok,
      status: response.status,
      url: healthUrl,
      body: text,
    }
  } catch (error) {
    return {
      ok: false,
      status: null,
      url: healthUrl,
      body: error?.message || 'Unknown error',
    }
  } finally {
    window.clearTimeout(timer)
  }
}
