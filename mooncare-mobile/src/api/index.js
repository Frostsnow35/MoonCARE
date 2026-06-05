import axios from 'axios'
import { get_kv, remove_kv } from '../services/kv'

const DEFAULT_API_BASE_URL = 'http://159.75.13.158:8000/api/v1'

export async function create_api() {
  const api_base_url = (await get_kv('api_base_url')) || import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL

  const api = axios.create({
    baseURL: api_base_url,
    timeout: 25000,
    headers: { 'Content-Type': 'application/json' },
  })

  api.interceptors.request.use(async (config) => {
    const token = await get_kv('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  api.interceptors.response.use(
    (response) => response.data,
    async (error) => {
      if (error.response?.status === 401) {
        await remove_kv('access_token')
        await remove_kv('user')
      }
      return Promise.reject(error)
    },
  )

  return api
}

export async function biometric_upload_raw(payload, device_id) {
  const api = await create_api()
  return api.post('/biometric/raw', payload, { params: { device_id: device_id || 'DEVICE_001' } })
}

export async function auth_login(email, password) {
  const api = await create_api()
  return api.post('/auth/login', { email, password })
}
