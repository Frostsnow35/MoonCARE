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
          <h1 class="text-xl font-bold text-gray-800">创建账户</h1>
          <p class="text-sm text-gray-500 mt-1">加入 MoonCARE 大家庭</p>
        </div>

        <form @submit.prevent="handleRegister" class="space-y-4">
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
            <label class="block text-sm font-medium text-gray-700 mb-1">昵称（可选）</label>
            <input
              v-model="nickname"
              type="text"
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
              minlength="6"
              placeholder="至少6位密码"
              class="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-pink-400 focus:ring-2 focus:ring-pink-100 outline-none transition-all text-sm"
            />
            <p class="text-xs text-gray-400 mt-1">密码至少6位字符</p>
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
            {{ loading ? '注册中...' : '注册' }}
          </button>
        </form>

        <div class="mt-6 text-center">
          <p class="text-sm text-gray-500">
            已有账户？
            <router-link to="/login" class="text-pink-500 font-medium hover:underline">立即登录</router-link>
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
const nickname = ref('')
const password = ref('')
const loading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

async function handleRegister() {
  if (loading.value) return

  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    await authStore.register(email.value, password.value, nickname.value || undefined)
    successMessage.value = '注册成功！正在跳转...'
    setTimeout(() => {
      router.push('/chat')
    }, 1000)
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || '注册失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #FFF5F7 0%, #FFFFFF 100%);
}
</style>
