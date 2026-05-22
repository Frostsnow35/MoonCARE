<template>
  <div class="forgot-page">
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
            </svg>
          </div>
          <h1 class="text-xl font-bold text-gray-800">重置密码</h1>
          <p class="text-sm text-gray-500 mt-1">通过邮箱验证码重新设置登录密码</p>
        </div>

        <form @submit.prevent="handleResetPassword" class="space-y-4">
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
                @click="sendResetCode"
              >
                {{ codeButtonText }}
              </button>
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">新密码</label>
            <input
              v-model="newPassword"
              type="password"
              required
              minlength="8"
              autocomplete="new-password"
              placeholder="至少8位，包含字母和数字"
              class="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-pink-400 focus:ring-2 focus:ring-pink-100 outline-none transition-all text-sm"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">确认新密码</label>
            <input
              v-model="confirmPassword"
              type="password"
              required
              minlength="8"
              autocomplete="new-password"
              placeholder="再次输入新密码"
              class="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-pink-400 focus:ring-2 focus:ring-pink-100 outline-none transition-all text-sm"
            />
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
            {{ loading ? '提交中...' : '重置密码' }}
          </button>
        </form>

        <div class="mt-6 text-center">
          <router-link to="/login" class="text-sm text-pink-500 font-medium hover:underline">返回登录</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const emailCode = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
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

async function sendResetCode() {
  if (codeLoading.value || !email.value) return

  codeLoading.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const response = await authStore.forgotPassword(email.value)
    successMessage.value = response.message || '验证码已发送，请查收邮箱'
    startCountdown(response.data?.cooldown_seconds || 60)
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '验证码发送失败，请稍后再试')
  } finally {
    codeLoading.value = false
  }
}

async function handleResetPassword() {
  if (loading.value) return
  if (newPassword.value !== confirmPassword.value) {
    errorMessage.value = '两次输入的新密码不一致'
    return
  }

  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const response = await authStore.resetPassword(email.value, emailCode.value, newPassword.value)
    successMessage.value = response.message || '密码已重置，请重新登录'
    window.setTimeout(() => {
      router.push('/login')
    }, 900)
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '重置失败，请检查验证码和新密码')
  } finally {
    loading.value = false
  }
}

onUnmounted(() => {
  if (countdownTimer) window.clearInterval(countdownTimer)
})
</script>

<style scoped>
.forgot-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #fff5f7 0%, #ffffff 100%);
}
</style>
