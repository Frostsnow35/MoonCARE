<template>
  <div class="register-page">
    <div class="mx-auto max-w-lg px-4 pb-16 pt-8">
      <div class="mb-8 text-center">
        <div class="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-pink-300 to-pink-500 shadow-lg">
          <svg width="50" height="50" viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
            <ellipse cx="25" cy="28" rx="18" ry="15" fill="#FFD6E0" />
            <ellipse cx="25" cy="28" rx="15" ry="12" fill="#FFB3C1" />
            <circle cx="19" cy="25" r="3" fill="#5D4E60" />
            <circle cx="31" cy="25" r="3" fill="#5D4E60" />
            <circle cx="20" cy="24" r="1.2" fill="white" />
            <circle cx="32" cy="24" r="1.2" fill="white" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-slate-800">创建账号</h1>
        <p class="mt-2 text-sm text-slate-500">验证码会发到你的邮箱，用来完成注册。</p>
      </div>

      <div class="space-y-5">
        <ServerConfigCard v-if="showDebugServerConfig" />

        <form class="space-y-4 rounded-[1.5rem] bg-white/90 p-5 shadow-[0_24px_60px_rgba(244,114,182,0.12)]" @submit.prevent="handleRegister">
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">邮箱</label>
            <input
              v-model.trim="email"
              type="email"
              required
              autocomplete="email"
              placeholder="your@email.com"
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-pink-400 focus:ring-2 focus:ring-pink-100"
            />
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">邮箱验证码</label>
            <div class="flex gap-2">
              <input
                v-model.trim="emailCode"
                type="text"
                inputmode="numeric"
                required
                maxlength="6"
                placeholder="6 位验证码"
                class="min-w-0 flex-1 rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-pink-400 focus:ring-2 focus:ring-pink-100"
              />
              <button
                type="button"
                :disabled="codeLoading || !email || countdown > 0"
                class="shrink-0 rounded-2xl border border-pink-200 bg-white px-4 py-3 text-sm font-medium text-pink-500 disabled:cursor-not-allowed disabled:opacity-50"
                @click="sendRegisterCode"
              >
                {{ codeButtonText }}
              </button>
            </div>
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">昵称（可选）</label>
            <input
              v-model.trim="nickname"
              type="text"
              maxlength="100"
              placeholder="给自己起一个昵称"
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-pink-400 focus:ring-2 focus:ring-pink-100"
            />
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">密码</label>
            <input
              v-model="password"
              type="password"
              required
              minlength="8"
              autocomplete="new-password"
              placeholder="至少 8 位，包含字母和数字"
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-pink-400 focus:ring-2 focus:ring-pink-100"
            />
            <p class="mt-1 text-xs text-slate-400">建议使用不与其他平台重复的密码。</p>
          </div>

          <div v-if="showDebugServerConfig" class="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">
            <div>Resolved API URL: {{ diagnostics.resolvedApiUrl }}</div>
            <div>Health URL: {{ diagnostics.resolvedHealthUrl }}</div>
            <div v-if="diagnostics.requestState" class="mt-2 break-all">{{ diagnostics.requestState }}</div>
          </div>

          <div v-if="errorMessage" class="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
            {{ errorMessage }}
          </div>

          <div v-if="successMessage" class="rounded-2xl border border-green-100 bg-green-50 px-4 py-3 text-sm text-green-700">
            {{ successMessage }}
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full rounded-full bg-gradient-to-r from-pink-400 to-pink-500 py-3 font-medium text-white shadow-lg transition-transform active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {{ loading ? '注册中...' : '注册并进入 MoonCARE' }}
          </button>
        </form>

        <div class="text-center text-sm text-slate-500">
          已有账号？
          <router-link class="font-medium text-pink-500 hover:underline" to="/login">立即登录</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import ServerConfigCard from '../components/ServerConfigCard.vue'
import { useGuestApiDiagnostics } from '../composables/useGuestApiDiagnostics'
import { SHOW_DEBUG_SERVER_CONFIG } from '../services/apiConfig'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const diagnostics = useGuestApiDiagnostics('register-code')
const showDebugServerConfig = SHOW_DEBUG_SERVER_CONFIG

const email = ref('')
const nickname = ref('')
const emailCode = ref('')
const password = ref('')
const loading = ref(false)
const codeLoading = ref(false)
const countdown = ref(0)
const errorMessage = ref('')
const successMessage = ref('')
let countdownTimer = null

const codeButtonText = computed(() => {
  if (codeLoading.value) return '发送中...'
  if (countdown.value > 0) return `${countdown.value}s`
  return '发送验证码'
})

function getErrorMessage(error, fallback) {
  return error.response?.data?.detail || error.response?.data?.message || error.userMessage || error.message || fallback
}

function startCountdown(seconds) {
  countdown.value = seconds
  if (countdownTimer) window.clearInterval(countdownTimer)
  countdownTimer = window.setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0 && countdownTimer) {
      window.clearInterval(countdownTimer)
      countdownTimer = null
    }
  }, 1000)
}

async function sendRegisterCode() {
  if (codeLoading.value || !email.value) return

  codeLoading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  diagnostics.beginRequest(JSON.stringify({ email: email.value.trim(), purpose: 'register' }))

  try {
    const response = await authStore.requestEmailCode(email.value, 'register')
    successMessage.value = response.__message || '验证码已发送，请查收邮箱。'
    diagnostics.completeRequest(response)
    startCountdown(response.cooldown_seconds || 60)
  } catch (error) {
    diagnostics.failRequest(error)
    errorMessage.value = getErrorMessage(error, '验证码发送失败，请稍后再试。')
  } finally {
    codeLoading.value = false
  }
}

async function handleRegister() {
  if (loading.value) return

  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  diagnostics.beginRequest(JSON.stringify({ email: email.value.trim(), action: 'register' }))

  try {
    const response = await authStore.register(email.value, password.value, nickname.value || undefined, emailCode.value)
    diagnostics.completeRequest({
      user_id: response.user_id,
      email: response.email,
    })
    successMessage.value = '注册成功，正在进入 MoonCARE...'
    window.setTimeout(() => {
      router.push('/home')
    }, 700)
  } catch (error) {
    diagnostics.failRequest(error)
    errorMessage.value = getErrorMessage(error, '注册失败，请检查邮箱、验证码和密码。')
  } finally {
    loading.value = false
  }
}

onUnmounted(() => {
  if (countdownTimer) window.clearInterval(countdownTimer)
})
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  background:
    radial-gradient(circle at top, rgba(251, 113, 133, 0.12), transparent 35%),
    linear-gradient(180deg, #fff5f7 0%, #ffffff 100%);
}
</style>
