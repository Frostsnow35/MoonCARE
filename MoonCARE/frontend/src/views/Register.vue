<template>
  <div class="auth-page">
    <div class="auth-shell">
      <section class="auth-card p-6 sm:p-8">
        <div class="text-center">
          <div class="auth-brand-mark">
            <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <ellipse cx="25" cy="28" rx="18" ry="15" fill="#FFD6E0" />
              <ellipse cx="25" cy="28" rx="15" ry="12" fill="#FFB3C1" />
              <circle cx="19" cy="25" r="3" fill="#5D4E60" />
              <circle cx="31" cy="25" r="3" fill="#5D4E60" />
              <circle cx="20" cy="24" r="1.2" fill="white" />
              <circle cx="32" cy="24" r="1.2" fill="white" />
              <ellipse cx="25" cy="31" rx="2.5" ry="1.5" fill="#FF6B8A" />
              <ellipse cx="14" cy="16" rx="5" ry="3" fill="#FFD6E0" opacity="0.8" />
              <ellipse cx="36" cy="16" rx="5" ry="3" fill="#FFD6E0" opacity="0.8" />
            </svg>
          </div>
          <p class="section-label">创建账号</p>
          <h1 class="auth-title mt-3">用邮箱验证码保护你的数据</h1>
          <p class="auth-copy">
            注册后会直接进入聊天主链路。MoonCARE 会继续围绕情绪、周期和身体状态陪你往下走。
          </p>
        </div>

        <form class="mt-8 grid gap-4" @submit.prevent="handleRegister">
          <div class="auth-field">
            <label for="register-email">邮箱</label>
            <input
              id="register-email"
              v-model.trim="email"
              type="email"
              required
              autocomplete="email"
              placeholder="your@email.com"
              class="input-surface px-4 py-3 text-sm"
            />
          </div>

          <div class="auth-field">
            <label for="register-code">邮箱验证码</label>
            <div class="flex gap-2">
              <input
                id="register-code"
                v-model.trim="emailCode"
                type="text"
                inputmode="numeric"
                required
                maxlength="6"
                placeholder="6 位验证码"
                class="input-surface min-w-0 flex-1 px-4 py-3 text-sm"
              />
              <button
                type="button"
                :disabled="codeLoading || !email || countdown > 0"
                class="secondary-button min-w-[7.5rem] shrink-0 disabled:cursor-not-allowed disabled:opacity-60"
                @click="sendRegisterCode"
              >
                {{ codeButtonText }}
              </button>
            </div>
          </div>

          <div class="auth-field">
            <label for="register-nickname">昵称</label>
            <input
              id="register-nickname"
              v-model.trim="nickname"
              type="text"
              required
              maxlength="100"
              placeholder="给自己起一个昵称"
              class="input-surface px-4 py-3 text-sm"
            />
          </div>

          <div class="auth-field">
            <label for="register-password">密码</label>
            <input
              id="register-password"
              v-model="password"
              type="password"
              required
              minlength="8"
              autocomplete="new-password"
              placeholder="至少 8 位，建议包含字母和数字"
              class="input-surface px-4 py-3 text-sm"
            />
            <p class="auth-help-text">建议使用不与其他平台重复的密码。</p>
          </div>

          <div v-if="errorMessage" class="auth-feedback auth-feedback-error">
            {{ errorMessage }}
          </div>

          <div v-if="successMessage" class="auth-feedback auth-feedback-success">
            {{ successMessage }}
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="primary-button mt-1 w-full disabled:cursor-not-allowed disabled:opacity-60"
          >
            {{ loading ? '正在注册...' : '注册并进入聊天' }}
          </button>
        </form>

        <p class="mt-6 text-center text-sm text-slate-500">
          已有账号？
          <router-link to="/login" class="auth-link">立即登录</router-link>
        </p>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

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

  try {
    const response = await authStore.requestEmailCode(email.value, 'register')
    successMessage.value = response.message || '验证码已发送，请注意查收邮箱。'
    if (response.data?.debug_email_code) {
      emailCode.value = response.data.debug_email_code
      successMessage.value = '开发模式已自动填入验证码，无需查收邮箱。'
    }
    startCountdown(response.data?.cooldown_seconds || 60)
  } catch (error) {
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

  try {
    await authStore.register(email.value, password.value, nickname.value, emailCode.value)
    successMessage.value = '注册成功，正在进入 MoonCARE...'
    window.setTimeout(() => {
      router.push(route.query.redirect || '/chat')
    }, 700)
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '注册失败，请检查邮箱、验证码和密码。')
  } finally {
    loading.value = false
  }
}

onUnmounted(() => {
  if (countdownTimer) window.clearInterval(countdownTimer)
})
</script>
