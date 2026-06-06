<template>
  <section class="server-config-card">
    <div class="server-config-header">
      <div>
        <h2 class="server-config-title">API Base URL</h2>
        <p class="server-config-subtitle">Default target is preconfigured for this deployment.</p>
      </div>
      <span class="server-config-badge">{{ buildMarker }}</span>
    </div>

    <label class="server-config-label" for="api-base-url">Current server</label>
    <input
      id="api-base-url"
      v-model.trim="draftValue"
      class="server-config-input"
      type="text"
      inputmode="url"
      :placeholder="defaultBaseUrl"
    />

    <div class="server-config-actions">
      <button class="server-config-button primary" type="button" @click="handleSave" :disabled="saving">
        {{ saving ? 'Saving...' : 'Save' }}
      </button>
      <button class="server-config-button" type="button" @click="handleTest" :disabled="testing">
        {{ testing ? 'Testing...' : 'Test connection' }}
      </button>
      <button class="server-config-button ghost" type="button" @click="handleReset">
        Reset default
      </button>
    </div>

    <div class="server-config-status">
      <div class="status-line">
        <span class="status-label">Resolved API URL</span>
        <span class="status-value">{{ resolvedValue }}</span>
      </div>
      <div class="status-line">
        <span class="status-label">Health URL</span>
        <span class="status-value">{{ healthUrl }}</span>
      </div>
      <div v-if="statusMessage" class="status-box" :class="statusTone">
        {{ statusMessage }}
      </div>
      <div v-if="lastTestSummary" class="status-box neutral">
        {{ lastTestSummary }}
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  DEFAULT_API_BASE_URL,
  MOBILE_BUILD_MARKER,
  getApiBaseUrl,
  getHealthUrl,
  saveApiBaseUrl,
  testApiConnection,
} from '../services/apiConfig'

const emit = defineEmits(['resolved'])

const buildMarker = MOBILE_BUILD_MARKER
const defaultBaseUrl = DEFAULT_API_BASE_URL
const draftValue = ref(DEFAULT_API_BASE_URL)
const resolvedValue = ref(DEFAULT_API_BASE_URL)
const saving = ref(false)
const testing = ref(false)
const statusMessage = ref('')
const statusTone = ref('neutral')
const lastTestSummary = ref('')

const healthUrl = computed(() => getHealthUrl(resolvedValue.value))

async function syncResolvedValue() {
  const resolved = await getApiBaseUrl()
  resolvedValue.value = resolved
  draftValue.value = resolved
  emit('resolved', resolved)
}

async function handleSave() {
  saving.value = true
  statusMessage.value = ''

  try {
    const resolved = await saveApiBaseUrl(draftValue.value)
    resolvedValue.value = resolved
    draftValue.value = resolved
    statusTone.value = 'success'
    statusMessage.value = `Saved API URL: ${resolved}`
    emit('resolved', resolved)
  } finally {
    saving.value = false
  }
}

async function handleTest() {
  testing.value = true
  statusMessage.value = ''
  lastTestSummary.value = ''

  try {
    const result = await testApiConnection(draftValue.value)
    const resolved = await saveApiBaseUrl(draftValue.value)
    resolvedValue.value = resolved
    draftValue.value = resolved
    emit('resolved', resolved)

    statusTone.value = result.ok ? 'success' : 'error'
    statusMessage.value = result.ok
      ? `Health check passed: ${result.status}`
      : `Health check failed: ${result.status ?? 'no-status'}`
    lastTestSummary.value = `Target: ${result.url} | Response: ${result.body}`
  } finally {
    testing.value = false
  }
}

async function handleReset() {
  draftValue.value = defaultBaseUrl
  await handleSave()
}

onMounted(async () => {
  await syncResolvedValue()
})
</script>

<style scoped>
.server-config-card {
  border: 1px solid rgb(251 207 232);
  border-radius: 1.25rem;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(255, 241, 242, 0.92));
  padding: 1rem;
  box-shadow: 0 20px 45px rgba(244, 114, 182, 0.08);
}

.server-config-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.server-config-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: rgb(136 19 55);
}

.server-config-subtitle {
  margin-top: 0.2rem;
  font-size: 0.75rem;
  color: rgb(113 113 122);
}

.server-config-badge {
  flex-shrink: 0;
  border-radius: 999px;
  background: rgb(255 228 230);
  color: rgb(190 24 93);
  font-size: 0.68rem;
  font-weight: 700;
  padding: 0.3rem 0.55rem;
}

.server-config-label {
  display: block;
  margin-bottom: 0.35rem;
  font-size: 0.78rem;
  font-weight: 600;
  color: rgb(63 63 70);
}

.server-config-input {
  width: 100%;
  border: 1px solid rgb(229 231 235);
  border-radius: 0.95rem;
  background: white;
  padding: 0.85rem 0.95rem;
  font-size: 0.85rem;
  color: rgb(15 23 42);
}

.server-config-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: 0.85rem;
}

.server-config-button {
  border-radius: 999px;
  border: 1px solid rgb(251 207 232);
  background: white;
  color: rgb(190 24 93);
  font-size: 0.8rem;
  font-weight: 700;
  padding: 0.6rem 0.95rem;
}

.server-config-button.primary {
  background: linear-gradient(135deg, rgb(251 113 133), rgb(236 72 153));
  border-color: transparent;
  color: white;
}

.server-config-button.ghost {
  color: rgb(71 85 105);
  border-color: rgb(226 232 240);
}

.server-config-button:disabled {
  opacity: 0.6;
}

.server-config-status {
  margin-top: 0.85rem;
  display: grid;
  gap: 0.5rem;
}

.status-line {
  display: grid;
  gap: 0.15rem;
}

.status-label {
  font-size: 0.72rem;
  font-weight: 700;
  color: rgb(113 113 122);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.status-value {
  word-break: break-all;
  font-size: 0.8rem;
  color: rgb(30 41 59);
}

.status-box {
  word-break: break-all;
  border-radius: 0.9rem;
  padding: 0.75rem 0.85rem;
  font-size: 0.78rem;
}

.status-box.success {
  background: rgb(240 253 244);
  color: rgb(22 101 52);
  border: 1px solid rgb(187 247 208);
}

.status-box.error {
  background: rgb(254 242 242);
  color: rgb(153 27 27);
  border: 1px solid rgb(254 202 202);
}

.status-box.neutral {
  background: rgb(248 250 252);
  color: rgb(51 65 85);
  border: 1px solid rgb(226 232 240);
}
</style>
