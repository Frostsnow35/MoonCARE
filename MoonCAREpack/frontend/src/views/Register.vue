<template>
  <div class="register-page">
    <div class="max-w-lg mx-auto pb-16">
      <div class="px-4 pt-8">
        <div class="text-center mb-8">
          <div class="w-20 h-20 mx-auto mb-4 rounded-full bg-gradient-to-br from-pink-300 to-pink-400 flex items-center justify-center shadow-lg">
            <svg width="50" height="50" viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
              <ellipse cx="25" cy="28" rx="18" ry="15" fill="#FFD6E0"/>
              <ellipse cx="25" cy="28" rx="15" ry="12" fill="#FFB3C1"/>
              <circle cx="19" cy="25" r="3" fill="#5D4E60"/>
              <circle cx="31" cy="25" r="3" fill="#5D4E60"/>
              <circle cx="20" cy="24" r="1.2" fill="white"/>
              <circle cx="32" cy="24" r="1.2" fill="white"/>
              <ellipse cx="25" cy="31" rx="2.5" ry="1.5" fill="#FF6B8A"/>
              <ellipse cx="14" cy="16" rx="5" ry="3" fill="#FFD6E0" opacity="0.8"/>
              <ellipse cx="36" cy="16" rx="5" ry="3" fill="#FFD6E0" opacity="0.8"/>
            </svg>
          </div>
          <h1 class="text-xl font-bold text-gray-800">创建账号</h1>
          <p class="text-sm text-gray-500 mt-1">用邮箱验证码保护你的 MoonCARE 数据</p>
        </div>

        <form @submit.prevent="handleRegister" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
            <input
              v-model.trim="email"
              type="email"
              required
              autocomplete="email"
              placeholder="your@email.com"
              class="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-pink-400 focus:ring-2 focus:ring-pink-100 outline-none transition-all text-sm"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">邮箱验证码</label>
            <div class="flex gap-2">
              <input
                v-model.trim="emailCode"
                type="text"
                inputmode="numeric"
                required
                maxlength="6"
                placeholder="6位验证码"
                class="min-w-0 flex-1 px-4 py-3 rounded-xl border border-gray-200 focus:border-pink-400 focus:ring-2 focus:ring-pink-100 outline-none transition-all text-sm"
              />
              <button
                type="button"
                :disabled="codeLoading || !email || countdown > 0"
                class="shrink-0 px-4 py-3 rounded-xl border border-pink-200 text-sm font-medium text-pink-500 bg-white active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
                @click="sendRegisterCode"
              >
                {{ codeButtonText }}
              </button>
            </div>
          </div>

          <div class="p-3 bg-blue-50/70 border border-blue-100 rounded-xl">
            <label class="block text-xs font-medium text-blue-700 mb-1">
              服务器地址（APK / 手机直连时填写）
            </label>
            <input
              v-model.trim="serverBase"
              type="url"
              inputmode="url"
              autocomplete="url"
              placeholder="留空 = 与当前页面同源"
              class="w-full px-3 py-2 rounded-lg border border-blue-200 bg-white text-sm focus:border-blue-400 focus:outline-none"
            />
            <p class="text-[11px] text-blue-500 mt-1">
              例如 http://123.45.67.89:18000 。发送验证码前请先确认地址正确。
            </p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">昵称（可选）</label>
            <input
              v-model.trim="nickname"
              type="text"
              maxlength="100"
              placeholder="给自己起个昵称"
              class="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-pink-400 focus:ring-2 focus:ring-pink-100 outline-none transition-all text-sm"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">密码</label>
            <input
              v-model="password"
              type="password"
              required
              minlength="8"
              autocomplete="new-password"
              placeholder="至少8位，包含字母和数字"
              class="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-pink-400 focus:ring-2 focus:ring-pink-100 outline-none transition-all text-sm"
            />
            <p class="text-xs text-gray-400 mt-1">建议使用不与其他平台重复的密码。</p>
          </div>

          <div v-if="errorMessage" class="p-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-700">
            {{ errorMessage }}
          </div>

          <div v-if="successMessage" class="p-3 bg-green-50 border border-green-100 rounded-xl text-sm text-green-700">
            {{ successMessage }}
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full py-3 bg-gradient-to-r from-pink-400 to-pink-500 text-white font-medium rounded-full shadow-lg active:scale-[0.98] transition-transform disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ loading ? '注册中...' : '注册并进入' }}
          </button>
        </form>

        <div class="mt-6 text-center">
          <p class="text-sm text-gray-500">
            已有账号？
            <router-link to="/login" class="text-pink-500 font-medium hover:underline">立即登录</router-link>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { getStoredServerBase, setStoredServerBase } from '../config/runtime'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const nickname = ref('')
const emailCode = ref('')
const password = ref('')
const serverBase = ref(getStoredServerBase())
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
  return error.response?.data?.detail || error.response?.data?.message || fallback
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

  // Persist server address before the email-code request is sent.
  setStoredServerBase(serverBase.value)

  try {
    const response = await authStore.requestEmailCode(email.value, 'register')
    successMessage.value = response.message || '验证码已发送，请查收邮箱'
    startCountdown(response.data?.cooldown_seconds || 60)
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '验证码发送失败，请稍后再试')
  } finally {
    codeLoading.value = false
  }
}

async function handleRegister() {
  if (loading.value) return

  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    setStoredServerBase(serverBase.value)
    await authStore.register(email.value, password.value, nickname.value || undefined, emailCode.value)
    successMessage.value = '注册成功，正在进入 MoonCARE...'
    window.setTimeout(() => {
      router.push('/chat')
    }, 700)
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '注册失败，请检查邮箱、验证码和密码')
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
  background: linear-gradient(180deg, #fff5f7 0%, #ffffff 100%);
}
</style>
