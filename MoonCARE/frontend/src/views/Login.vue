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
            </svg>
          </div>
          <p class="section-label">欢迎回来</p>
          <h1 class="auth-title mt-3">继续你的 MoonCARE 陪伴记录</h1>
          <p class="auth-copy">
            登录后会回到首页，再从聊天、日记和周期状态里继续上一次的节奏。
          </p>
        </div>

        <form class="mt-8 grid gap-4" @submit.prevent="handleLogin">
          <div class="auth-field">
            <label for="login-email">邮箱或昵称</label>
            <input
              id="login-email"
              v-model.trim="email"
              type="text"
              autocomplete="username"
              placeholder="请输入邮箱或昵称，例如 adminMC"
              class="input-surface px-4 py-3 text-sm"
            />
          </div>

          <div class="auth-field">
            <div class="flex items-center justify-between gap-3">
              <label for="login-password">密码</label>
              <router-link to="/forgot-password" class="auth-link text-xs">忘记密码</router-link>
            </div>
            <input
              id="login-password"
              v-model="password"
              type="password"
              autocomplete="current-password"
              placeholder="请输入密码"
              class="input-surface px-4 py-3 text-sm"
            />
          </div>

          <div v-if="errorMessage" class="auth-feedback auth-feedback-error">
            {{ errorMessage }}
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="primary-button mt-1 w-full disabled:cursor-not-allowed disabled:opacity-60"
          >
            {{ loading ? '正在登录...' : '登录' }}
          </button>
        </form>

        <p class="mt-6 text-center text-sm text-slate-500">
          还没有账号？
          <router-link to="/register" class="auth-link">立即注册</router-link>
        </p>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const loading = ref(false)
const errorMessage = ref('')

function getErrorMessage(error, fallback) {
  return error.response?.data?.detail || error.response?.data?.message || fallback
}

async function handleLogin() {
  if (loading.value) return

  loading.value = true
  errorMessage.value = ''

  try {
    await authStore.login(email.value, password.value)
    router.push(route.query.redirect || '/home')
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '登录失败，请检查邮箱、昵称或密码。')
  } finally {
    loading.value = false
  }
}
</script>
