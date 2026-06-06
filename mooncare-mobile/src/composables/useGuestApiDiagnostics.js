import { computed, ref } from 'vue'
import { getApiBaseUrlSync, getHealthUrl } from '../services/apiConfig'

export function useGuestApiDiagnostics(kind) {
  const requestState = ref('')
  const resolvedApiUrl = computed(() => getApiBaseUrlSync())
  const resolvedHealthUrl = computed(() => getHealthUrl(resolvedApiUrl.value))

  function beginRequest(payload) {
    requestState.value = `${kind} request started | api=${resolvedApiUrl.value} | health=${resolvedHealthUrl.value} | payload=${payload}`
    console.log(`[${kind}] request started`, {
      api: resolvedApiUrl.value,
      health: resolvedHealthUrl.value,
      payload,
    })
  }

  function completeRequest(response) {
    requestState.value = `${kind} request ok | api=${resolvedApiUrl.value} | response=${JSON.stringify(response)}`
    console.log(`[${kind}] request ok`, response)
  }

  function failRequest(error) {
    const detail =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      error?.userMessage ||
      error?.message ||
      'unknown error'
    const status = error?.response?.status || error?.code || 'unknown'
    requestState.value = `${kind} request failed | api=${resolvedApiUrl.value} | status=${status} | detail=${detail}`
    console.error(`[${kind}] request failed`, error)
  }

  return {
    requestState,
    resolvedApiUrl,
    resolvedHealthUrl,
    beginRequest,
    completeRequest,
    failRequest,
  }
}
