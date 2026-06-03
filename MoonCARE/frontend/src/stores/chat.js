import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { chatAPI, diaryAPI } from '../api'

function getChatStorageKey() {
  const user = JSON.parse(localStorage.getItem('user') || 'null')
  const userId = user?.id || 'guest'
  return `mooncare_chat_session_${userId}`
}

function nextMessageId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function normalizeMessage(raw = {}) {
  return {
    id: raw.id || nextMessageId(),
    content: String(raw.content || ''),
    role: raw.role || 'assistant',
    timestamp: raw.timestamp || new Date().toISOString(),
    suggestions: Array.isArray(raw.suggestions) ? raw.suggestions : [],
    actions: Array.isArray(raw.actions) ? raw.actions : [],
    replyStatus: raw.replyStatus || raw.reply_status || 'ok',
    elapsedMs: raw.elapsedMs || raw.elapsed_ms || 0,
    cacheHit: Boolean(raw.cacheHit || raw.cache_hit),
    cacheSimilarity: raw.cacheSimilarity || raw.cache_similarity || 0,
    cacheMatchType: raw.cacheMatchType || raw.cache_match_type || '',
    firstTokenLatencyMs: raw.firstTokenLatencyMs || raw.first_token_latency_ms || 0
  }
}

export const useChatStore = defineStore('chat', () => {
  const AGENT_PROFILES = {
    auto: {
      label: '自动模式',
      shortLabel: '自动',
      helper: '自动衔接倾听、知识解释和经期照护建议',
      welcome: '我先在这里陪你。你可以随便说一点今天的感受，也可以问身体变化或怎么照顾自己。我们慢慢来，不急着整理清楚。'
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

  const messages = ref([])
  const sessionId = ref(null)
  const isConnected = ref(false)
  const isLoading = ref(false)
  const isAwaitingReply = ref(false)
  const lastError = ref('')
  const assessmentState = ref(null)
  const assessmentSummary = ref(null)
  const memoryState = ref(null)
  const agentMode = ref('auto')
  const hasBootstrapped = ref(false)

  const activeAgent = computed(() => AGENT_PROFILES[agentMode.value] || AGENT_PROFILES.auto)

  function addMessage(message, role = 'user', metadata = {}) {
    messages.value.push(normalizeMessage({
      ...metadata,
      content: message,
      role,
      suggestions: metadata.suggestions || [],
      actions: metadata.actions || []
    }))
  }

  function addAssistantMessage(message, suggestions = [], actions = [], metadata = {}) {
    const normalized = normalizeMessage({
      ...metadata,
      content: message,
      role: 'assistant',
      suggestions,
      actions
    })
    messages.value.push(normalized)
    const msgId = normalized.id
    return msgId
  }

  function updateMessage(messageId, content) {
    const index = messages.value.findIndex(msg => msg.id === messageId)
    if (index !== -1) {
      messages.value[index].content = content
    }
  }

  function updateMessageActions(messageId, actions) {
    updateMessageMetadata(messageId, { actions })
  }

  function updateMessageMetadata(messageId, metadata = {}) {
    const index = messages.value.findIndex(msg => msg.id === messageId)
    if (index !== -1) {
      messages.value[index] = {
        ...messages.value[index],
        ...metadata
      }
    }
  }

  function deleteMessage(messageId) {
    const index = messages.value.findIndex(msg => msg.id === messageId)
    if (index !== -1) {
      messages.value.splice(index, 1)
    }
  }

  function revokeMessagePair(messageId) {
    const index = messages.value.findIndex(msg => msg.id === messageId)
    if (index === -1) return

    const message = messages.value[index]

    if (message.role === 'user') {
      const messagesToRemove = [messageId]

      let nextIndex = index + 1
      if (nextIndex < messages.value.length) {
        const nextMessage = messages.value[nextIndex]
        if (nextMessage.role === 'assistant') {
          messagesToRemove.push(nextMessage.id)
        }
      }

      for (const id of messagesToRemove) {
        const removeIndex = messages.value.findIndex(msg => msg.id === id)
        if (removeIndex !== -1) {
          messages.value.splice(removeIndex, 1)
        }
      }
    } else {
      deleteMessage(messageId)
    }
  }

  async function getTodayDiaryGreeting() {
    try {
      const token = localStorage.getItem('access_token')
      if (!token) return null

      const data = await diaryAPI.today?.()
      if (!data?.has_diary || !data?.content) return null

      const content = data.content
      const greetings = [
        { keywords: ['开心', '高兴', '快乐', '愉快', '幸福', '兴奋'], text: '看到你今天心情不错呀。有什么想分享的吗？我在这里陪你聊聊。' },
        { keywords: ['烦躁', '焦虑', '不安', '紧张', '担心', '压力'], text: '我注意到你今天有些紧绷。愿意说说发生了什么吗？我在这里陪你。' },
        { keywords: ['难过', '伤心', '失落', '沮丧', '痛苦'], text: '看到你今天心情不太好，我在这里陪着你。想说什么都可以。' },
        { keywords: ['累', '疲惫', '困', '无力', '疲劳'], text: '感觉你今天有些疲惫，先休息一下也好；想聊的时候我在。' }
      ]

      return greetings.find(item => item.keywords.some(keyword => content.includes(keyword)))?.text || null
    } catch (error) {
      console.warn('Failed to get today diary:', error)
      return null
    }
  }

  async function bootstrapConversation() {
    if (hasBootstrapped.value || messages.value.length > 0) return

    const personalizedGreeting = await getTodayDiaryGreeting()
    addAssistantMessage(
      personalizedGreeting || activeAgent.value.welcome,
      ['我想倾诉一下', '了解经前情绪', '来个呼吸练习']
    )
    hasBootstrapped.value = true
  }

  function setAgentMode(mode) {
    agentMode.value = Object.prototype.hasOwnProperty.call(AGENT_PROFILES, mode) ? mode : 'auto'
  }

  async function createSession() {
    const result = await chatAPI.createSession()
    sessionId.value = result.session_id
    return result.session_id
  }

  function clearMessages() {
    messages.value = []
    hasBootstrapped.value = false
    lastError.value = ''
    isAwaitingReply.value = false
    memoryState.value = null
    assessmentState.value = null
    assessmentSummary.value = null
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

  function restoreSessionFromHistory(session, turns = []) {
    sessionId.value = session || null
    messages.value = Array.isArray(turns)
      ? turns
        .filter(turn => typeof turn?.content === 'string' && turn.content.trim())
        .map(turn => normalizeMessage({
          content: turn.content,
          role: turn.role,
          timestamp: turn.created_at || turn.timestamp,
          suggestions: turn.suggestions || [],
          actions: turn.actions || [],
          replyStatus: turn.reply_status,
          elapsedMs: turn.elapsed_ms,
          cacheHit: turn.cache_hit,
          cacheSimilarity: turn.cache_similarity,
          cacheMatchType: turn.cache_match_type,
          firstTokenLatencyMs: turn.first_token_latency_ms
        }))
      : []
    hasBootstrapped.value = messages.value.length > 0
    const assistantTurns = turns.filter(turn => turn?.role === 'assistant')
    const latestAssistantTurn = assistantTurns[assistantTurns.length - 1] || null
    assessmentState.value = latestAssistantTurn?.assessment_state || null
    assessmentSummary.value = latestAssistantTurn?.assessment_state?.summary_available
      ? latestAssistantTurn.assessment_state
      : null
    memoryState.value = latestAssistantTurn?.memory_state || null
    lastError.value = ''
    isAwaitingReply.value = false
  }

  function persistToStorage() {
    try {
      const data = {
        sessionId: sessionId.value,
        messages: messages.value,
        agentMode: agentMode.value,
        hasBootstrapped: hasBootstrapped.value,
        assessmentState: assessmentState.value,
        assessmentSummary: assessmentSummary.value,
        memoryState: memoryState.value
      }
      localStorage.setItem(getChatStorageKey(), JSON.stringify(data))
    } catch (error) {
      console.warn('Failed to persist chat session:', error)
    }
  }

  function loadFromStorage() {
    try {
      const stored = localStorage.getItem(getChatStorageKey())
      if (!stored) return false
      const data = JSON.parse(stored)

      sessionId.value = data.sessionId || null
      messages.value = Array.isArray(data.messages) ? data.messages.map(normalizeMessage) : []
      agentMode.value = data.agentMode || 'auto'
      hasBootstrapped.value = Boolean(data.hasBootstrapped)
      assessmentState.value = data.assessmentState || null
      assessmentSummary.value = data.assessmentSummary || null
      memoryState.value = data.memoryState || null

      return Boolean(sessionId.value && messages.value.length > 0)
    } catch (error) {
      console.warn('Failed to load chat session from storage:', error)
      return false
    }
  }

  function clearSession() {
    sessionId.value = null
    messages.value = []
    hasBootstrapped.value = false
    lastError.value = ''
    isAwaitingReply.value = false
    isConnected.value = false
    memoryState.value = null
    assessmentState.value = null
    assessmentSummary.value = null
    localStorage.removeItem(getChatStorageKey())
  }

  watch([messages, sessionId, agentMode, assessmentState, assessmentSummary, memoryState], () => {
    if (messages.value.length > 0 || sessionId.value) {
      persistToStorage()
    }
  }, { deep: true })

  const hasRestoredSession = loadFromStorage()

  return {
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
    hasRestoredSession,
    addMessage,
    addAssistantMessage,
    updateMessage,
    updateMessageActions,
    updateMessageMetadata,
    deleteMessage,
    revokeMessagePair,
    bootstrapConversation,
    setAgentMode,
    createSession,
    clearMessages,
    clearSession,
    setAssessmentState,
    clearAssessmentState,
    setMemoryState,
    restoreSessionFromHistory
  }
})
