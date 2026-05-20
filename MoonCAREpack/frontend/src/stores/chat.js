import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { apiBaseUrl, chatAPI } from '../api'

function getChatStorageKey() {
  const user = JSON.parse(localStorage.getItem('user') || 'null')
  const userId = user?.id || 'guest'
  return `mooncare_chat_session_${userId}`
}

export const useChatStore = defineStore('chat', () => {
  const AGENT_PROFILES = {
    auto: {
      label: '自动陪伴',
      shortLabel: '自动',
      helper: '自动衔接倾听、知识解释和经期照护建议',
      welcome: '我先在这里陪你。你可以随便说一点今天的感受，也可以问经前情绪、身体变化或今天怎么照顾自己。这里的内容仅供参考，不替代专业诊断。'
    },
    support: {
      label: '情绪宝宝',
      shortLabel: '陪伴',
      helper: '适合倾诉、安抚和轻量照护计划',
      welcome: '我在。你不用整理得很清楚，先把此刻最重的一点说出来就好。我会慢慢陪你听，也可以一起安排一点今天能做到的照顾。'
    },
    knowledge: {
      label: '知识宝宝',
      shortLabel: '知识',
      helper: '适合了解 PMS、周期、痛经和经期健康知识',
      welcome: '你好，我是知识宝宝。你可以问我经前情绪、周期变化、痛经或 PMS 相关问题，我会用容易理解的方式回答，并给出可尝试的小建议；内容仅供参考，不作为诊断。'
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

    const base = explicitBase
      ? explicitBase
      : apiBaseUrl.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:').replace(/\/api\/v1\/?$/, '')

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
    const msgId = nextMessageId()
    messages.value.push({
      id: msgId,
      content: message,
      role: 'assistant',
      suggestions,
      actions,
      timestamp: new Date().toISOString()
    })
    return msgId
  }

  function updateMessage(messageId, content) {
    const index = messages.value.findIndex(msg => msg.id === messageId)
    if (index !== -1) {
      messages.value[index].content = content
    }
  }

  function updateMessageActions(messageId, actions) {
    const index = messages.value.findIndex(msg => msg.id === messageId)
    if (index !== -1) {
      messages.value[index].actions = actions
    }
  }

  const EMOTION_GREETINGS = {
    '积极': '看到你今天心情不错呀～有什么想分享的吗？我在这里陪你聊聊～',
    '焦虑': '我注意到你今天有些烦躁，愿意说说发生了什么吗？我在这里陪你～',
    '难过': '看到你今天心情不太好的样子，我在这里陪着你...想说什么都可以～',
    '疲惫': '感觉你今天有些疲惫，先休息一下也好，想聊的时候我在～',
    '中性': null
  }

  async function getTodayDiaryGreeting() {
    try {
      const token = localStorage.getItem('access_token')
      if (!token) return null

      const response = await fetch(`${apiBaseUrl}/diary/today`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) return null

      const data = await response.json()

      if (!data.has_diary || !data.content) return null

      const content = data.content
      const emotionKeywords = {
        '积极': ['开心', '高兴', '快乐', '愉快', '幸福', '兴奋'],
        '焦虑': ['烦躁', '焦虑', '不安', '紧张', '担心', '压力'],
        '难过': ['难过', '伤心', '失落', '沮丧', '痛苦'],
        '疲惫': ['累', '疲惫', '困', '无力', '疲倦']
      }

      for (const [emotion, keywords] of Object.entries(emotionKeywords)) {
        for (const keyword of keywords) {
          if (content.includes(keyword)) {
            return EMOTION_GREETINGS[emotion]
          }
        }
      }

      return null
    } catch (error) {
      console.warn('Failed to get today diary:', error)
      return null
    }
  }

  async function bootstrapConversation() {
    if (hasBootstrapped.value || messages.value.length > 0 || isInterviewMode.value) return

    let welcomeMessage = activeAgent.value.welcome
    const personalizedGreeting = await getTodayDiaryGreeting()
    if (personalizedGreeting) {
      welcomeMessage = personalizedGreeting
    }

    addAssistantMessage(welcomeMessage, ['我想倾诉一下', '了解经前情绪', '来个呼吸练习'])
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
        addAssistantMessage(data.message, data.suggestions, data.actions || [])
      } else if (data.type === 'error') {
        console.error('WebSocket error:', data.message)
        isAwaitingReply.value = false
        lastError.value = data.message || '刚才连接断了一下。你可以直接继续说，我会接着听。'
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

  function persistToStorage() {
    try {
      const data = {
        sessionId: sessionId.value,
        messages: messages.value,
        agentMode: agentMode.value,
        hasBootstrapped: hasBootstrapped.value
      }
      localStorage.setItem(getChatStorageKey(), JSON.stringify(data))
    } catch (e) {
      console.warn('Failed to persist chat session:', e)
    }
  }

  function loadFromStorage() {
    try {
      const stored = localStorage.getItem(getChatStorageKey())
      if (!stored) return false
      const data = JSON.parse(stored)
      if (data.sessionId) {
        sessionId.value = data.sessionId
      }
      if (data.messages && data.messages.length > 0) {
        messages.value = data.messages
      }
      if (data.agentMode) {
        agentMode.value = data.agentMode
      }
      if (data.hasBootstrapped !== undefined) {
        hasBootstrapped.value = data.hasBootstrapped
      }
      return data.sessionId && data.messages && data.messages.length > 0
    } catch (e) {
      console.warn('Failed to load chat session from storage:', e)
      return false
    }
  }

  function clearSession() {
    sessionId.value = null
    messages.value = []
    hasBootstrapped.value = false
    lastError.value = ''
    isAwaitingReply.value = false
    memoryState.value = null
    localStorage.removeItem(getChatStorageKey())
  }

  watch([messages, sessionId, agentMode], () => {
    if (messages.value.length > 0 || sessionId.value) {
      persistToStorage()
    }
  }, { deep: true })

  const hasRestoredSession = loadFromStorage()

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
    hasRestoredSession,
    // Actions
    addMessage,
    addAssistantMessage,
    updateMessage,
    updateMessageActions,
    bootstrapConversation,
    setAgentMode,
    createSession,
    connectWebSocket,
    sendMessage,
    disconnect,
    enableReconnect,
    clearMessages,
    clearSession,
    setAssessmentState,
    clearAssessmentState,
    setMemoryState,
    setInterviewMode,
    endInterview
  }
})
