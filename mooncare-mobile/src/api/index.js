import axios from 'axios'
import { getApiBaseUrlSync, getBackendOrigin } from '../services/apiConfig'

const api = axios.create({
  timeout: 25000,
  headers: {
    'Content-Type': 'application/json',
  },
})

function getCurrentApiBaseUrl() {
  return getApiBaseUrlSync()
}

function normalizeEnvelope(body) {
  if (!body || typeof body !== 'object' || !Object.prototype.hasOwnProperty.call(body, 'code')) {
    return body
  }

  const meta = {
    __code: body.code,
    __message: body.message,
  }

  if (Array.isArray(body.data)) {
    return {
      items: body.data,
      ...meta,
    }
  }

  if (body.data && typeof body.data === 'object') {
    return {
      ...body.data,
      ...meta,
    }
  }

  return meta
}

function resolveMediaUrl(url) {
  if (!url) return url
  if (/^https?:\/\//i.test(url)) return url
  if (url.startsWith('/')) {
    return `${getBackendOrigin()}${url}`
  }
  return `${getBackendOrigin()}/${url.replace(/^\/+/, '')}`
}

function normalizeMusicSong(song) {
  if (!song || typeof song !== 'object') return song
  return {
    ...song,
    url: resolveMediaUrl(song.url),
  }
}

function attachAuthHeader(config) {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}

api.interceptors.request.use(
  config => {
    config.baseURL = getCurrentApiBaseUrl()
    return attachAuthHeader(config)
  },
  error => Promise.reject(error)
)

api.interceptors.response.use(
  response => normalizeEnvelope(response.data),
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
    }

    if (!error.response) {
      const currentBaseUrl = getCurrentApiBaseUrl()
      error.userMessage =
        error.code === 'ECONNABORTED'
          ? `Request timed out. Please check server access: ${currentBaseUrl}`
          : `Cannot connect to server. Check the API Base URL and confirm the backend is reachable: ${currentBaseUrl}`
    }

    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

async function* streamChatResponse(message, sessionId = null, cyclePhase = null, agentMode = 'auto', clientContext = null) {
  const params = new URLSearchParams()
  params.append('message', message)
  if (sessionId) params.append('session_id', sessionId)
  if (cyclePhase) params.append('cycle_phase', cyclePhase)
  if (agentMode) params.append('agent_mode', agentMode)
  if (clientContext) params.append('client_context', clientContext)

  const headers = {
    Accept: 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Content-Type': 'application/x-www-form-urlencoded',
  }

  const token = localStorage.getItem('access_token')
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${getCurrentApiBaseUrl()}/chat/stream`, {
    method: 'POST',
    headers,
    body: params,
  })

  if (!response.ok) {
    const bodyText = await response.text()
    throw new Error(`HTTP ${response.status}: ${bodyText}`)
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
      const chunk = buffer.slice(0, index)
      buffer = buffer.slice(index + 2)

      const dataLines = chunk
        .split('\n')
        .filter(line => line.startsWith('data: '))
        .map(line => line.slice(6))

      if (!dataLines.length) continue

      try {
        yield JSON.parse(dataLines.join('\n'))
      } catch (error) {
        console.error('Failed to parse SSE data:', error)
      }
    }
  }
}

export const authAPI = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  register: (email, password, nickname, emailCode) =>
    api.post('/auth/register', {
      email,
      password,
      nickname,
      email_code: emailCode,
    }),
  requestEmailCode: (email, purpose = 'register') =>
    api.post('/auth/email-code/send', {
      email,
      purpose,
    }),
  forgotPassword: email => api.post('/auth/password/forgot', { email }),
  resetPassword: (email, emailCode, newPassword) =>
    api.post('/auth/password/reset', {
      email,
      email_code: emailCode,
      new_password: newPassword,
    }),
  requestEmailChange: (newEmail, currentPassword) =>
    api.post('/auth/email-change/request', {
      new_email: newEmail,
      current_password: currentPassword,
    }),
  confirmEmailChange: (newEmail, emailCode) =>
    api.post('/auth/email-change/confirm', {
      new_email: newEmail,
      email_code: emailCode,
    }),
  deleteAccount: (currentPassword, confirmText) =>
    api.post('/auth/me/delete', {
      current_password: currentPassword,
      confirm_text: confirmText,
    }),
  getProfile: () => api.get('/auth/me'),
  updateProfile: payload => api.put('/auth/me', payload),
}

export const biometricAPI = {
  upload: data => api.post('/biometric/upload', data),
  query: params => api.get('/biometric/query', { params }),
  getLatest: () => api.get('/biometric/latest'),
  seed: (count = 50) => api.post('/biometric/seed', null, { params: { count } }),
  uploadRaw: (data, deviceId = 'DEVICE_001') =>
    api.post('/biometric/raw', data, { params: { device_id: deviceId } }),
}

export function biometric_upload_raw(payload, deviceId) {
  return biometricAPI.uploadRaw(payload, deviceId)
}

export const emotionAPI = {
  predict: (days = 7) => api.get('/emotion/predict', { params: { days } }),
  getPhase: () => api.get('/emotion/phase'),
  recommend: context =>
    api.get('/emotion/intervention/recommend', {
      params: { context },
    }),
  classify: () => api.get('/emotion/classify'),
}

export const menstrualAPI = {
  createRecord: data => api.post('/menstrual/record', data),
  getRecords: params => api.get('/menstrual/records', { params }),
  predict: () => api.get('/menstrual/predict'),
  updateRecord: (id, data) => api.put(`/menstrual/record/${id}`, data),
  deleteRecord: id => api.delete(`/menstrual/record/${id}`),
  checkIrregularity: () => api.get('/menstrual/irregularity'),
}

export const diaryAPI = {
  create: data => api.post('/diary', data),
  today: () => api.get('/diary/today'),
  list: params => api.get('/diary', { params }),
  get: id => api.get(`/diary/${id}`),
  update: (id, data, options = {}) => {
    const params = options.skip_nlp ? { skip_nlp: options.skip_nlp } : {}
    return api.put(`/diary/${id}`, data, { params })
  },
  delete: id => api.delete(`/diary/${id}`),
  saveDraft: data => api.post('/diary/draft', data),
  getDraft: () => api.get('/diary/draft'),
  deleteDraft: () => api.delete('/diary/draft'),
  publishDraft: () => api.post('/diary/draft/publish'),
}

export const chatAPI = {
  createSession: () => api.post('/chat/session'),
  getSessions: () => api.get('/chat/sessions'),
  getHistory: sessionId => api.get(`/chat/history/${sessionId}`),
  sendMessage: (message, sessionId = null, cyclePhase = null, agentMode = 'auto', clientContext = null) => {
    const formData = new URLSearchParams()
    formData.append('message', message)
    if (sessionId) formData.append('session_id', sessionId)
    if (cyclePhase) formData.append('cycle_phase', cyclePhase)
    if (agentMode) formData.append('agent_mode', agentMode)
    if (clientContext) formData.append('client_context', clientContext)
    return api.post('/chat/message', formData.toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },
  sendMessageStream: streamChatResponse,
}

export const interviewAPI = {
  start: () => api.post('/interview/start'),
  turn: messages => api.post('/interview/turn', { messages }),
}

export const musicAPI = {
  recommend: (emotionCategory = null) =>
    api.get('/music/recommend', {
      params: { emotion_category: emotionCategory },
    }).then(result => ({
      ...result,
      recommended_songs: Array.isArray(result.recommended_songs)
        ? result.recommended_songs.map(normalizeMusicSong)
        : [],
    })),
  list: (emotionCategory = null, limit = 20) =>
    api.get('/music/list', {
      params: { emotion_category: emotionCategory, limit },
    }).then(result => ({
      ...result,
      music_list: Array.isArray(result.music_list)
        ? result.music_list.map(normalizeMusicSong)
        : [],
    })),
  upload: formData =>
    api.post('/music/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(normalizeMusicSong),
  feedback: payload => api.post('/music/feedback', payload),
  seed: () => api.post('/music/seed'),
}

export default api
