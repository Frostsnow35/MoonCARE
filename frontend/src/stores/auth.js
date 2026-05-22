import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authAPI } from '../api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token') || null)
  const user = ref(null)
  
  // 初始化时安全解析用户数据
  try {
    const storedUser = localStorage.getItem('user')
    if (storedUser && storedUser !== 'undefined' && storedUser !== 'null') {
      user.value = JSON.parse(storedUser)
    }
  } catch (e) {
    console.warn('Failed to parse stored user:', e)
  }

  const isAuthenticated = computed(() => !!token.value)

  async function login(email, password) {
    const response = await authAPI.login(email, password)
    token.value = response.access_token
    user.value = {
      id: response.user_id,
      email: response.email,
      nickname: response.nickname
    }
    localStorage.setItem('access_token', response.access_token)
    localStorage.setItem('user', JSON.stringify(user.value))
    return response
  }

  async function register(email, password, nickname, emailCode) {
    const response = await authAPI.register(email, password, nickname, emailCode)
    token.value = response.access_token
    user.value = {
      id: response.user_id,
      email: response.email,
      nickname: response.nickname
    }
    localStorage.setItem('access_token', response.access_token)
    localStorage.setItem('user', JSON.stringify(user.value))
    return response
  }

  async function requestEmailCode(email, purpose = 'register') {
    return authAPI.requestEmailCode(email, purpose)
  }

  async function forgotPassword(email) {
    return authAPI.forgotPassword(email)
  }

  async function resetPassword(email, emailCode, newPassword) {
    return authAPI.resetPassword(email, emailCode, newPassword)
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
  }

  function initializeAuth() {
    const storedToken = localStorage.getItem('access_token')
    const storedUser = localStorage.getItem('user')
    if (storedToken) {
      token.value = storedToken
    }
    if (storedUser) {
      try {
        user.value = JSON.parse(storedUser)
      } catch (e) {
        user.value = null
      }
    }
  }

  return {
    token,
    user,
    isAuthenticated,
    login,
    register,
    requestEmailCode,
    forgotPassword,
    resetPassword,
    logout,
    initializeAuth
  }
})
