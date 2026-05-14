<template>
  <div class="login-page">
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
          <h1 class="text-xl font-bold text-gray-800">欢迎回来</h1>
          <p class="text-sm text-gray-500 mt-1">登录到 MoonCARE</p>
        </div>

        <form @submit.prevent="handleLogin" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
            <input
              v-model="email"
              type="email"
              required
              placeholder="your@email.com"
              class="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-pink-400 focus:ring-2 focus:ring-pink-100 outline-none transition-all text-sm"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">密码</label>
            <input
              v-model="password"
              type="password"
              required
              placeholder="输入密码"
              class="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-pink-400 focus:ring-2 focus:ring-pink-100 outline-none transition-all text-sm"
            />
          </div>

          <div v-if="errorMessage" class="p-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-700">
            {{ errorMessage }}
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full py-3 bg-gradient-to-r from-pink-400 to-pink-500 text-white font-medium rounded-full shadow-lg active:scale-[0.98] transition-transform disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ loading ? '登录中...' : '登录' }}
          </button>
        </form>

        <div class="mt-6 text-center">
          <p class="text-sm text-gray-500">
            还没有账户？
            <router-link to="/register" class="text-pink-500 font-medium hover:underline">立即注册</router-link>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const loading = ref(false)
const errorMessage = ref('')

async function handleLogin() {
  if (loading.value) return

  loading.value = true
  errorMessage.value = ''

  try {
    await authStore.login(email.value, password.value)
    router.push('/')
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || '登录失败，请检查邮箱和密码'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #FFF5F7 0%, #FFFFFF 100%);
}
</style>
