import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { chatAPI } from '../api'

export const useChatStore = defineStore('chat', () => {
  const AGENT_PROFILES = {
    auto: {
      label: '自动陪伴',
      shortLabel: '自动',
      helper: '由系统根据内容自动选择陪伴或知识支持',
      welcome: '我先在这里陪你。你可以随便说一点今天的感受，也可以问经前情绪、身体变化相关的问题。这里的内容仅供参考，不替代专业诊断。'
    },
    support: {
      label: '情绪宝宝',
      shortLabel: '陪伴',
      helper: '更适合倾诉、安抚和一起梳理感受',
      welcome: '我在。你不用整理得很清楚，先把此刻最重的一点说出来就好。我会慢慢陪你听，也会尽量温柔地回应。'
    },
    knowledge: {
      label: '知识宝宝',
      shortLabel: '知识',
      helper: '更适合了解 PMS、周期和情绪波动知识',
      welcome: '你好，我是知识宝宝。你可以问我经前情绪、周期变化或 PMS 相关问题，我会用容易理解的方式回答；内容仅供参考，不作为诊断。'
    }
  }

  // State
  const messages = ref([])
  const sessionId = ref(null)
  const isConnected = ref(false)
  const isLoading = ref(false)
  const isAwaitingReply = ref(false)
  const lastError = ref('')
  const websocket = ref(null)
  const reconnectAttempt = ref(0)
  const shouldReconnect = ref(true)
  const heartbeatTimer = ref(null)
  const assessmentState = ref(null)
  const assessmentSummary = ref(null)
  const memoryState = ref(null)
  const agentMode = ref('auto')
  const hasBootstrapped = ref(false)
  // Interview state
  const isInterviewMode = ref(false)
  const interviewPhase = ref(1)
  const activeAgent = computed(() => AGENT_PROFILES[agentMode.value] || AGENT_PROFILES.auto)

  function nextMessageId() {
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`
  }

  function getWebSocketUrl(userId) {
    const explicitBase = import.meta.env.VITE_WS_BASE_URL
    const apiBase = import.meta.env.VITE_API_BASE_URL || 'https://mooncare.onrender.com/api/v1'

    const base = explicitBase
      ? explicitBase
      : apiBase.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:').replace(/\/api\/v1\/?$/, '')

    const normalizedBase = base.replace(/\/$/, '')
    return `${normalizedBase}/api/v1/chat/ws/${userId}`
  }

  function startHeartbeat() {
    if (heartbeatTimer.value) return
    heartbeatTimer.value = window.setInterval(() => {
      if (websocket.value && isConnected.value) {
        websocket.value.send(JSON.stringify({ message: '' }))
      }
    }, 30000)
  }

  function stopHeartbeat() {
    if (!heartbeatTimer.value) return
    window.clearInterval(heartbeatTimer.value)
    heartbeatTimer.value = null
  }

  function scheduleReconnect(userId) {
    if (!shouldReconnect.value) return
    reconnectAttempt.value += 1

    const delay = Math.min(30000, 500 * (2 ** Math.min(reconnectAttempt.value, 6)))
    window.setTimeout(() => {
      if (!shouldReconnect.value) return
      connectWebSocket(userId)
    }, delay)
  }

  // Actions
  function addMessage(message, role = 'user') {
    messages.value.push({
      id: nextMessageId(),
      content: message,
      role,
      timestamp: new Date().toISOString()
    })
  }

  function addAssistantMessage(message, suggestions = [], actions = []) {
    messages.value.push({
      id: nextMessageId(),
      content: message,
      role: 'assistant',
      suggestions,
      actions,
      timestamp: new Date().toISOString()
    })
  }

  function bootstrapConversation() {
    if (hasBootstrapped.value || messages.value.length > 0 || isInterviewMode.value) return
    addAssistantMessage(activeAgent.value.welcome, ['我想倾诉一下', '了解经前情绪', '来个呼吸练习'])
    hasBootstrapped.value = true
  }

  function setAgentMode(mode) {
    agentMode.value = Object.prototype.hasOwnProperty.call(AGENT_PROFILES, mode) ? mode : 'auto'
  }

  async function createSession(userId = 1) {
    try {
      const result = await chatAPI.createSession(userId)
      sessionId.value = result.session_id
      return result.session_id
    } catch (error) {
      console.error('Failed to create session:', error)
      throw error
    }
  }

  function connectWebSocket(userId = 1) {
    if (websocket.value && (websocket.value.readyState === WebSocket.OPEN || websocket.value.readyState === WebSocket.CONNECTING)) {
      return
    }

    const wsUrl = getWebSocketUrl(userId)
    websocket.value = new WebSocket(wsUrl)

    websocket.value.onopen = () => {
      isConnected.value = true
      reconnectAttempt.value = 0
      console.log('WebSocket connected')
      startHeartbeat()
    }

    websocket.value.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.type === 'session') {
        sessionId.value = data.session_id
      } else if (data.type === 'assistant') {
        isAwaitingReply.value = false
        lastError.value = ''
        if (Object.prototype.hasOwnProperty.call(data, 'assessment_state')) {
          setAssessmentState(data.assessment_state)
        }
        if (Object.prototype.hasOwnProperty.call(data, 'memory_state')) {
          setMemoryState(data.memory_state)
        }
        if (data.reply_status === 'timeout_fallback') {
          lastError.value = 'GLM-5.1 这次响应偏慢，我先给了你一个承接回复；你可以重试继续等完整回答。'
        }
        addAssistantMessage(data.message, data.suggestions, data.actions || [])
      } else if (data.type === 'error') {
        console.error('WebSocket error:', data.message)
        isAwaitingReply.value = false
        lastError.value = data.message || '连接暂时不稳定，请稍后再试。'
      }
    }

    websocket.value.onclose = () => {
      isConnected.value = false
      console.log('WebSocket disconnected')
      stopHeartbeat()
      scheduleReconnect(userId)
    }

    websocket.value.onerror = (error) => {
      console.error('WebSocket error:', error)
      isConnected.value = false
      stopHeartbeat()
      isAwaitingReply.value = false
    }
  }

  function sendMessage(message) {
    if (websocket.value && isConnected.value) {
      isAwaitingReply.value = true
      lastError.value = ''
      websocket.value.send(JSON.stringify({ message, agent_mode: agentMode.value }))
    }
  }

  function disconnect() {
    shouldReconnect.value = false
    stopHeartbeat()
    if (websocket.value) {
      websocket.value.close()
      websocket.value = null
    }
    isConnected.value = false
  }

  function enableReconnect() {
    shouldReconnect.value = true
    reconnectAttempt.value = 0
  }

  function clearMessages() {
    messages.value = []
    hasBootstrapped.value = false
    lastError.value = ''
    isAwaitingReply.value = false
    memoryState.value = null
  }

  function setAssessmentState(state) {
    assessmentState.value = state || null
    if (state && state.summary_available) {
      assessmentSummary.value = state
    }
  }

  function clearAssessmentState() {
    assessmentState.value = null
    assessmentSummary.value = null
  }

  function setMemoryState(state) {
    memoryState.value = state || null
  }

  function setInterviewMode(enabled, phase = 1) {
    isInterviewMode.value = enabled
    interviewPhase.value = phase
  }

  function endInterview() {
    isInterviewMode.value = false
    interviewPhase.value = 1
  }

  return {
    // State
    messages,
    sessionId,
    isConnected,
    isLoading,
    isAwaitingReply,
    lastError,
    assessmentState,
    assessmentSummary,
    memoryState,
    agentMode,
    activeAgent,
    agentProfiles: AGENT_PROFILES,
    hasBootstrapped,
    isInterviewMode,
    interviewPhase,
    // Actions
    addMessage,
    addAssistantMessage,
    bootstrapConversation,
    setAgentMode,
    createSession,
    connectWebSocket,
    sendMessage,
    disconnect,
    enableReconnect,
    clearMessages,
    setAssessmentState,
    clearAssessmentState,
    setMemoryState,
    setInterviewMode,
    endInterview
  }
})
