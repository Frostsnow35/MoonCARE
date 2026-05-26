import axios from 'axios'

const api_base_url = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

const api = axios.create({
  baseURL: api_base_url,
  timeout: 25000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

api.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
    }
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const authAPI = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  register: (email, password, nickname, emailCode) => api.post('/auth/register', {
    email,
    password,
    nickname,
    email_code: emailCode
  }),
  requestEmailCode: (email, purpose = 'register') => api.post('/auth/email-code/send', {
    email,
    purpose
  }),
  forgotPassword: (email) => api.post('/auth/password/forgot', { email }),
  resetPassword: (email, emailCode, newPassword) => api.post('/auth/password/reset', {
    email,
    email_code: emailCode,
    new_password: newPassword
  })
}

export const biometricAPI = {
  upload: (data) => api.post('/biometric/upload', data),
  query: (params) => api.get('/biometric/query', { params }),
  getLatest: () => api.get('/biometric/latest'),
  seed: (count = 50) => api.post('/biometric/seed', null, { params: { count } }),
  uploadRaw: (data, deviceId = 'DEVICE_001') => api.post('/biometric/raw', data, { params: { device_id: deviceId } })
}

export const emotionAPI = {
  predict: (days = 7) => api.get('/emotion/predict', { params: { days } }),
  getPhase: () => api.get('/emotion/phase'),
  recommend: (context) => api.get('/emotion/intervention/recommend', {
    params: { context }
  }),
  classify: () => api.get('/emotion/classify')
}

export const menstrualAPI = {
  createRecord: (data) => api.post('/menstrual/record', data),
  getRecords: (params) => api.get('/menstrual/records', { params }),
  predict: () => api.get('/menstrual/predict'),
  updateRecord: (id, data) => api.put(`/menstrual/record/${id}`, data),
  deleteRecord: (id) => api.delete(`/menstrual/record/${id}`)
}

export const diaryAPI = {
  create: (data) => api.post('/diary', data),
  today: () => api.get('/diary/today'),
  list: (params) => api.get('/diary', { params }),
  get: (id) => api.get(`/diary/${id}`),
  update: (id, data) => api.put(`/diary/${id}`, data),
  delete: (id) => api.delete(`/diary/${id}`)
}

export const chatAPI = {
  createSession: () => api.post('/chat/session'),
  getSessions: () => api.get('/chat/sessions'),
  getHistory: (sessionId) => api.get(`/chat/history/${sessionId}`),
  sendMessage: (message, sessionId = null, cyclePhase = null, agentMode = 'auto', clientContext = null) => {
    const formData = new URLSearchParams()
    formData.append('message', message)
    if (sessionId) formData.append('session_id', sessionId)
    if (cyclePhase) formData.append('cycle_phase', cyclePhase)
    if (agentMode) formData.append('agent_mode', agentMode)
    if (clientContext) formData.append('client_context', clientContext)
    return api.post('/chat/message', formData.toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
  },
  sendMessageStream: async function*(message, sessionId = null, cyclePhase = null, agentMode = 'auto', clientContext = null) {
    const params = new URLSearchParams()
    params.append('message', message)
    if (sessionId) params.append('session_id', sessionId)
    if (cyclePhase) params.append('cycle_phase', cyclePhase)
    if (agentMode) params.append('agent_mode', agentMode)
    if (clientContext) params.append('client_context', clientContext)

    const headers = {
      'Accept': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    // 添加 Authorization header
    const token = localStorage.getItem('access_token')
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${api_base_url}/chat/stream`, {
      method: 'POST',
      headers,
      body: params
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      while (buffer.includes('\n\n')) {
        const index = buffer.indexOf('\n\n')
        const chunk = buffer.substring(0, index)
        buffer = buffer.substring(index + 2)

        const dataLines = chunk
          .split('\n')
          .filter(line => line.startsWith('data: '))
          .map(line => line.substring(6))

        if (dataLines.length > 0) {
          const data = dataLines.join('\n')
          try {
            const json = JSON.parse(data)
            yield json
          } catch (e) {
            console.error('Failed to parse SSE data:', e)
          }
        }
      }
    }
  }
}

export const interviewAPI = {
  start: () => api.post('/interview/start'),
  turn: (messages) => api.post('/interview/turn', { messages })
}

export const musicAPI = {
  recommend: (emotionCategory = null) => api.get('/music/recommend', {
    params: { emotion_category: emotionCategory }
  }),
  list: (emotionCategory = null, limit = 20) => api.get('/music/list', {
    params: { emotion_category: emotionCategory, limit }
  }),
  upload: (formData) => api.post('/music/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  feedback: (payload) => api.post('/music/feedback', payload),
  seed: () => api.post('/music/seed')
}

export default api
