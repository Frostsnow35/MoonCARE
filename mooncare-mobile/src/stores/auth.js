import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { auth_login } from '../api'
import { get_kv, set_kv, remove_kv } from '../services/kv'

export const useAuthStore = defineStore('auth', () => {
  const access_token = ref('')
  const user = ref(null)
  const status = ref('idle')
  const error_msg = ref('')

  const is_authed = computed(() => Boolean(access_token.value))

  async function initialize_auth() {
    access_token.value = (await get_kv('access_token')) || ''
    const raw_user = await get_kv('user')
    user.value = raw_user ? JSON.parse(raw_user) : null
  }

  async function login(email, password) {
    status.value = 'loading'
    error_msg.value = ''
    try {
      const resp = await auth_login(email, password)
      access_token.value = resp.access_token
      user.value = resp.user || null

      await set_kv('access_token', access_token.value)
      await set_kv('user', JSON.stringify(user.value))
      status.value = 'ok'
      return true
    } catch (err) {
      status.value = 'error'
      error_msg.value = err?.response?.data?.detail || err?.message || '登录失败'
      return false
    }
  }

  async function logout() {
    access_token.value = ''
    user.value = null
    await remove_kv('access_token')
    await remove_kv('user')
  }

  return {
    access_token,
    user,
    status,
    error_msg,
    is_authed,
    initialize_auth,
    login,
    logout,
  }
})

