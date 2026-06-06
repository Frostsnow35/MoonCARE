import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authAPI } from '../api'
import { clearUserScopedKeys } from '../services/userScopedStorage'

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

  function applyAuthResponse(response) {
    token.value = response.access_token
    user.value = {
      ...(user.value || {}),
      id: response.user_id,
      email: response.email,
      nickname: response.nickname,
      notifications_enabled: user.value?.notifications_enabled ?? true,
      ai_assistant_enabled: user.value?.ai_assistant_enabled ?? true,
    }
    localStorage.setItem('access_token', response.access_token)
    localStorage.setItem('user', JSON.stringify(user.value))
    return response
  }

  async function login(email, password) {
    const response = await authAPI.login(email, password)
    user.value = {
      notifications_enabled: true,
      ai_assistant_enabled: true,
    }
    return applyAuthResponse(response)
  }

  async function register(email, password, nickname, emailCode) {
    const response = await authAPI.register(email, password, nickname, emailCode)
    user.value = {
      notifications_enabled: true,
      ai_assistant_enabled: true,
    }
    return applyAuthResponse(response)
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

  async function requestEmailChange(newEmail, currentPassword) {
    return authAPI.requestEmailChange(newEmail, currentPassword)
  }

  async function confirmEmailChange(newEmail, emailCode) {
    const response = await authAPI.confirmEmailChange(newEmail, emailCode)
    return applyAuthResponse(response)
  }

  async function deleteAccount(currentPassword, confirmText) {
    return authAPI.deleteAccount(currentPassword, confirmText)
  }

  async function fetchProfile() {
    const profile = await authAPI.getProfile()
    user.value = {
      ...(user.value || {}),
      ...profile,
    }
    localStorage.setItem('user', JSON.stringify(user.value))
    return user.value
  }

  async function updateProfile(payload) {
    const profile = await authAPI.updateProfile(payload)
    user.value = {
      ...(user.value || {}),
      ...profile,
    }
    localStorage.setItem('user', JSON.stringify(user.value))
    return user.value
  }

  function logout() {
    clearUserScopedKeys(['mooncare_chat_session', 'mooncare_liked_music'])
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
    requestEmailChange,
    confirmEmailChange,
    deleteAccount,
    fetchProfile,
    updateProfile,
    logout,
    initializeAuth
  }
})
