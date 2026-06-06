<template>
  <div class="login-page">
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
            <ellipse cx="25" cy="31" rx="2.5" ry="1.5" fill="#FF6B8A" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-slate-800">欢迎回来</h1>
        <p class="mt-2 text-sm text-slate-500">登录 MoonCARE，继续你的周期陪伴记录。</p>
      </div>

      <div class="space-y-5">
        <ServerConfigCard v-if="showDebugServerConfig" />

        <form class="space-y-4 rounded-[1.5rem] bg-white/90 p-5 shadow-[0_24px_60px_rgba(244,114,182,0.12)]" @submit.prevent="handleLogin">
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">邮箱</label>
            <input
              v-model.trim="email"
              type="email"
              autocomplete="email"
              placeholder="your@email.com"
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-pink-400 focus:ring-2 focus:ring-pink-100"
            />
          </div>

          <div>
            <div class="mb-1 flex items-center justify-between">
              <label class="block text-sm font-medium text-slate-700">密码</label>
              <router-link class="text-xs font-medium text-pink-500 hover:underline" to="/forgot-password">
                忘记密码
              </router-link>
            </div>
            <input
              v-model="password"
              type="password"
              autocomplete="current-password"
              placeholder="请输入密码"
              class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-pink-400 focus:ring-2 focus:ring-pink-100"
            />
          </div>

          <div v-if="showDebugServerConfig" class="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">
            <div>Resolved API URL: {{ diagnostics.resolvedApiUrl }}</div>
            <div>Health URL: {{ diagnostics.resolvedHealthUrl }}</div>
            <div v-if="diagnostics.requestState" class="mt-2 break-all">{{ diagnostics.requestState }}</div>
          </div>

          <div v-if="errorMessage" class="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
            {{ errorMessage }}
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full rounded-full bg-gradient-to-r from-pink-400 to-pink-500 py-3 font-medium text-white shadow-lg transition-transform active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {{ loading ? '登录中...' : '登录' }}
          </button>
        </form>

        <div class="text-center text-sm text-slate-500">
          还没有账号？
          <router-link class="font-medium text-pink-500 hover:underline" to="/register">立即注册</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ServerConfigCard from '../components/ServerConfigCard.vue'
import { useGuestApiDiagnostics } from '../composables/useGuestApiDiagnostics'
import { SHOW_DEBUG_SERVER_CONFIG } from '../services/apiConfig'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const diagnostics = useGuestApiDiagnostics('login')
const showDebugServerConfig = SHOW_DEBUG_SERVER_CONFIG

const email = ref('')
const password = ref('')
const loading = ref(false)
const errorMessage = ref('')

function getErrorMessage(error, fallback) {
  return error.response?.data?.detail || error.response?.data?.message || error.userMessage || error.message || fallback
}

async function handleLogin() {
  if (loading.value) return

  loading.value = true
  errorMessage.value = ''
  diagnostics.beginRequest(JSON.stringify({ email: email.value.trim() }))

  try {
    const response = await authStore.login(email.value, password.value)
    diagnostics.completeRequest({
      user_id: response.user_id,
      email: response.email,
    })
    router.push(route.query.redirect || '/home')
  } catch (error) {
    diagnostics.failRequest(error)
    errorMessage.value = getErrorMessage(error, '登录失败，请检查邮箱和密码。')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background:
    radial-gradient(circle at top, rgba(251, 113, 133, 0.12), transparent 35%),
    linear-gradient(180deg, #fff5f7 0%, #ffffff 100%);
}
</style>
