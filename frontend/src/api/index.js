import axios from 'axios'

const api_base_url = import.meta.env.VITE_API_BASE_URL || 'https://mooncare.onrender.com/api/v1'

const api = axios.create({
  baseURL: api_base_url,
  timeout: 60000,  // 60 seconds for LLM API calls
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
api.interceptors.request.use(
  config => {
    // Add auth token if available
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

// Response interceptor
api.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// Biometric APIs
export const biometricAPI = {
  upload: (data) => api.post('/biometric/upload', data),
  query: (params) => api.get('/biometric/query', { params }),
  getLatest: (userId) => api.get('/biometric/latest', { params: { user_id: userId } }),
  seed: (count = 50) => api.post('/biometric/seed', null, { params: { count } }),
  uploadRaw: (data, userId = 1, deviceId = 'DEVICE_001') => api.post('/biometric/raw', data, { params: { user_id: userId, device_id: deviceId } })
}

// Emotion APIs
export const emotionAPI = {
  predict: (userId, days = 7) => api.get('/emotion/predict', { params: { user_id: userId, days } }),
  getPhase: (userId) => api.get('/emotion/phase', { params: { user_id: userId } }),
  recommend: (userId, context) => api.get('/emotion/intervention/recommend', {
    params: { user_id: userId, context }
  }),
  classify: (userId) => api.get('/emotion/classify', { params: { user_id: userId } })
}

// Menstrual APIs
export const menstrualAPI = {
  createRecord: (data) => api.post('/menstrual/record', data),
  getRecords: (params) => api.get('/menstrual/records', { params }),
  predict: (userId) => api.get('/menstrual/predict', { params: { user_id: userId } }),
  updateRecord: (id, data) => api.put(`/menstrual/record/${id}`, data),
  deleteRecord: (id) => api.delete(`/menstrual/record/${id}`)
}

// Diary APIs
export const diaryAPI = {
  create: (data) => api.post('/diary', data),
  list: (params) => api.get('/diary', { params }),
  get: (id) => api.get(`/diary/${id}`),
  update: (id, data) => api.put(`/diary/${id}`, data),
  delete: (id) => api.delete(`/diary/${id}`)
}

// Chat APIs
export const chatAPI = {
  createSession: (userId) => api.post('/chat/session', null, { params: { user_id: userId } }),
  getSessions: (userId) => api.get('/chat/sessions', { params: { user_id: userId } }),
  getHistory: (sessionId) => api.get(`/chat/history/${sessionId}`),
  sendMessage: (message, userId = 1, sessionId = null, cyclePhase = null, agentMode = 'auto') => {
    const params = { message, user_id: userId }
    if (sessionId) params.session_id = sessionId
    if (cyclePhase) params.cycle_phase = cyclePhase
    if (agentMode) params.agent_mode = agentMode
    return api.post('/chat/message', null, { params })
  }
}

// Interview APIs
export const interviewAPI = {
  start: (userId = 1) => api.post('/interview/start', null, { params: { user_id: userId } }),
  turn: (messages, userId = 1) => api.post('/interview/turn', { messages }, { params: { user_id: userId } })
}

// Music APIs
export const musicAPI = {
  recommend: (userId, emotionCategory = null) => api.get('/music/recommend', {
    params: { user_id: userId, emotion_category: emotionCategory }
  }),
  list: (emotionCategory = null, limit = 20) => api.get('/music/list', {
    params: { emotion_category: emotionCategory, limit }
  }),
  seed: () => api.post('/music/seed')
}

export default api
