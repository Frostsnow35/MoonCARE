<template>
  <div class="chat-page">
    <div class="max-w-lg mx-auto pb-16">
      <header class="px-4 pt-4 pb-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-11 h-11 rounded-full bg-pink-100 flex items-center justify-center shrink-0">
              <svg class="w-8 h-8" viewBox="0 0 40 40" aria-hidden="true">
                <circle cx="20" cy="20" r="18" fill="#FFE4EC" />
                <path d="M11 23c2.7 5.4 15.3 5.4 18 0 2-4.1-.6-10.5-9-10.5S9 18.9 11 23Z" fill="#F9A8C7" />
                <circle cx="15" cy="20" r="2" fill="#4B3A46" />
                <circle cx="25" cy="20" r="2" fill="#4B3A46" />
                <path d="M17 25c1.8 1.2 4.2 1.2 6 0" stroke="#4B3A46" stroke-width="1.8" stroke-linecap="round" />
              </svg>
            </div>
            <div class="min-w-0">
              <h1 class="text-lg font-bold text-gray-800 leading-tight">{{ chatStore.activeAgent.label }}</h1>
              <p class="text-xs text-gray-500 truncate">{{ chatStore.activeAgent.helper }}</p>
              <p v-if="memoryStatusText" class="text-[11px] text-pink-500 truncate">{{ memoryStatusText }}</p>
            </div>
          </div>
          <div class="flex items-center gap-1">
            <button
              type="button"
              class="w-10 h-10 flex items-center justify-center rounded-full hover:bg-pink-50 transition-colors"
              @click="showMoreMenu = !showMoreMenu"
              title="更多选项"
            >
              <svg class="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
              </svg>
            </button>
          </div>
        </div>
        <div
          v-if="showMoreMenu"
          class="mt-2 py-2 bg-white rounded-2xl shadow-lg border border-gray-100 animate-fadeIn"
        >
          <button
            type="button"
            class="w-full flex items-center gap-3 px-4 py-3 hover:bg-pink-50 transition-colors text-left"
            @click="startNewSession"
          >
            <svg class="w-5 h-5 text-pink-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            <span class="text-sm text-gray-700">新建会话</span>
          </button>
          <button
            type="button"
            class="w-full flex items-center gap-3 px-4 py-3 hover:bg-pink-50 transition-colors text-left"
            @click="openSessionList"
          >
            <svg class="w-5 h-5 text-pink-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <span class="text-sm text-gray-700">历史会话</span>
          </button>
          <button
            v-if="messages.length > 0"
            type="button"
            class="w-full flex items-center gap-3 px-4 py-3 hover:bg-pink-50 transition-colors text-left"
            @click="clearChat"
          >
            <svg class="w-5 h-5 text-pink-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            <span class="text-sm text-gray-700">清空当前会话</span>
          </button>
        </div>
      </header>

      <section class="px-4 mt-3">
        <div ref="messagesContainer" class="chat-window">
          <article
            v-for="msg in messages"
            :key="msg.id"
            class="flex animate-fadeIn"
            :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div
              class="message-bubble"
              :class="msg.role === 'user' ? 'message-user' : 'message-agent'"
            >
              <p class="text-sm leading-relaxed whitespace-pre-wrap break-words">{{ msg.content }}</p>

              <div
                v-if="msg.role === 'assistant' && msg.suggestions && msg.suggestions.length > 0"
                class="mt-2 flex flex-wrap gap-1.5"
                aria-label="快捷回复"
              >
                <button
                  v-for="suggestion in msg.suggestions"
                  :key="suggestion"
                  type="button"
                  class="min-h-9 px-3 text-xs rounded-full bg-pink-50 text-pink-600 border border-pink-100 active:scale-95"
                  @click="handleSuggestion(suggestion)"
                >
                  {{ suggestion }}
                </button>
              </div>

              <div
                v-if="msg.role === 'assistant' && msg.actions && msg.actions.length > 0"
                class="mt-3 flex flex-wrap gap-2"
                aria-label="功能建议"
              >
                <button
                  v-for="action in msg.actions"
                  :key="action.action"
                  type="button"
                  class="min-h-9 px-3 text-xs rounded-full bg-gradient-to-r from-blue-50 to-purple-50 text-blue-600 border border-blue-100 active:scale-95 hover:shadow-sm transition-shadow"
                  :title="action.description"
                  @click="handleAction(action)"
                >
                  {{ action.label }}
                </button>
              </div>

              <time
                class="text-[11px] mt-1 block"
                :class="msg.role === 'user' ? 'text-pink-100' : 'text-gray-400'"
                :datetime="msg.timestamp"
              >
                {{ formatTime(msg.timestamp) }}
              </time>
            </div>
          </article>

          <div v-if="isTyping" class="flex justify-start animate-fadeIn">
            <div class="bg-white border border-gray-100 rounded-2xl rounded-bl-md px-3 py-2 shadow-sm">
              <div class="flex items-center gap-2" aria-label="正在回复">
                <div class="flex gap-1">
                  <span class="typing-dot" style="animation-delay: 0ms"></span>
                  <span class="typing-dot" style="animation-delay: 140ms"></span>
                  <span class="typing-dot" style="animation-delay: 280ms"></span>
                </div>
                <span class="text-xs text-gray-400">{{ waitingText }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section v-if="errorText" class="px-4 mt-4">
        <div class="flex items-center justify-between gap-3 bg-red-50 border border-red-100 rounded-xl p-3 text-xs text-red-700">
          <span class="leading-relaxed">{{ errorText }}</span>
          <button
            v-if="lastRetryMessage"
            type="button"
            class="shrink-0 min-h-9 px-3 rounded-lg bg-white text-red-600"
            @click="retryLastMessage"
          >
            重试
          </button>
        </div>
      </section>

      <section class="px-4 mt-6">
        <form class="bg-white rounded-xl border border-gray-200 shadow-sm p-2" @submit.prevent="sendMessage()">
          <div class="relative flex items-end gap-2">
            <div v-if="showModeMenu" class="mode-menu">
              <button
                v-for="(profile, mode) in chatStore.agentProfiles"
                :key="mode"
                type="button"
                class="mode-menu-item"
                :class="chatStore.agentMode === mode ? 'active' : ''"
                @click="selectMode(mode)"
              >
                <span>{{ profile.label }}</span>
                <small>{{ profile.helper }}</small>
              </button>
            </div>
            <button
              type="button"
              class="mode-plus"
              aria-label="选择聊天模式"
              :aria-expanded="showModeMenu"
              @click="toggleModeMenu"
            >
              +
            </button>
            <button
              type="button"
              class="mode-current"
              @click="toggleModeMenu"
            >
              {{ chatStore.activeAgent.shortLabel }}
            </button>
            <label class="sr-only" for="chat-input">输入消息</label>
            <textarea
              id="chat-input"
              ref="inputEl"
              v-model="inputMessage"
              :disabled="isTyping"
              rows="1"
              maxlength="800"
              class="flex-1 min-h-11 max-h-28 resize-none border-0 outline-none px-2 py-2 text-base leading-relaxed text-gray-800 placeholder:text-gray-400"
              placeholder="慢慢说，我在听..."
              @input="resizeInput"
              @keydown.enter.exact.prevent="sendMessage()"
            ></textarea>
            <button
              type="submit"
              class="w-11 h-11 rounded-lg flex items-center justify-center transition-colors active:scale-95"
              :class="canSend ? 'bg-pink-500 text-white' : 'bg-gray-100 text-gray-400'"
              :disabled="!canSend"
              aria-label="发送消息"
            >
              <svg class="w-5 h-5" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 12 20 4l-4 16-4-6-8-2Z" fill="currentColor" opacity=".92" />
                <path d="m12 14 8-10" stroke="white" stroke-width="1.8" stroke-linecap="round" />
              </svg>
            </button>
          </div>
        </form>
      </section>
    </div>

    <div v-if="showSessionList" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30" @click.self="showSessionList = false">
      <div class="bg-white rounded-2xl w-full max-w-sm mx-4 max-h-[70vh] flex flex-col">
        <div class="flex items-center justify-between p-4 border-b border-gray-100">
          <h3 class="text-base font-bold text-gray-800">历史会话</h3>
          <button type="button" class="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100" @click="showSessionList = false">
            <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="flex-1 overflow-y-auto p-2">
          <button
            type="button"
            class="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-pink-50 transition-colors text-left"
            @click="startNewSession"
          >
            <div class="w-10 h-10 rounded-full bg-pink-100 flex items-center justify-center shrink-0">
              <svg class="w-5 h-5 text-pink-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
            </div>
            <div class="min-w-0 flex-1">
              <p class="text-sm font-medium text-gray-800">新建会话</p>
              <p class="text-xs text-gray-400">开始一段新的对话</p>
            </div>
          </button>
          <div v-if="sessionListLoading" class="flex items-center justify-center py-8">
            <div class="flex gap-1">
              <span class="w-2 h-2 rounded-full bg-pink-400 animate-bounce" style="animation-delay: 0ms"></span>
              <span class="w-2 h-2 rounded-full bg-pink-400 animate-bounce" style="animation-delay: 140ms"></span>
              <span class="w-2 h-2 rounded-full bg-pink-400 animate-bounce" style="animation-delay: 280ms"></span>
            </div>
          </div>
          <div v-else-if="sessionList.length === 0" class="text-center py-8 text-sm text-gray-400">
            暂无历史会话
          </div>
          <button
            v-for="session in sessionList"
            v-else
            :key="session.session_id"
            type="button"
            class="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-pink-50 transition-colors text-left"
            :class="session.session_id === chatStore.sessionId ? 'bg-pink-50' : ''"
            @click="loadSession(session.session_id)"
          >
            <div class="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center shrink-0">
              <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <div class="min-w-0 flex-1">
              <div class="flex items-center justify-between gap-2">
                <p class="text-sm font-medium text-gray-800 truncate">{{ formatRelativeTime(session.last_message_at) }}</p>
                <span v-if="session.session_id === chatStore.sessionId" class="text-xs text-pink-500 shrink-0">当前</span>
              </div>
              <p class="text-xs text-gray-400 truncate">{{ session.message_count ? `${session.message_count}条消息` : '暂无消息' }}</p>
            </div>
          </button>
        </div>
      </div>
    </div>

    <BottomNav />
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { apiBaseUrl, chatAPI, interviewAPI } from '../api'
import { useChatStore } from '../stores/chat'
import { useAuthStore } from '../stores/auth'
import BottomNav from '../components/BottomNav.vue'

const chatStore = useChatStore()
const authStore = useAuthStore()
const CHAT_REPLY_TIMEOUT_MS = 50000
const STREAM_FIRST_CHUNK_TIMEOUT_MS = 25000
const STREAM_OVERALL_TIMEOUT_MS = 90000

const messagesContainer = ref(null)
const inputEl = ref(null)
const inputMessage = ref('')
const localTyping = ref(false)
const showModeMenu = ref(false)
const showMoreMenu = ref(false)
const lastRetryMessage = ref('')
const streamingMessageId = ref(null)

const messages = computed(() => chatStore.messages)
const isTyping = computed(() => chatStore.isAwaitingReply || localTyping.value)
const errorText = computed(() => chatStore.lastError)
const canSend = computed(() => inputMessage.value.trim().length > 0 && !isTyping.value)
const waitingText = computed(() => chatStore.agentMode === 'knowledge' ? '正在查找合适的解释...' : '正在组织回复...')
const memoryStatusText = computed(() => {
  if (!chatStore.memoryState?.has_memory && !chatStore.memoryState?.updated) return ''
  if (chatStore.memoryState.updated) return '已延续你刚提到的状态'
  return '延续上次聊到的状态'
})

watch(messages, async () => {
  await nextTick()
  scrollToBottom()
}, { deep: true })

function formatTime(timestamp) {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatRelativeTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffHours < 24) return `${diffHours}小时前`
  if (diffDays < 7) return `${diffDays}天前`
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

const showSessionList = ref(false)
const sessionList = ref([])
const sessionListLoading = ref(false)

async function loadSessionList() {
  sessionListLoading.value = true
  try {
    const result = await chatAPI.getSessions(1)
    sessionList.value = Array.isArray(result) ? result : (result.sessions || [])
  } catch (error) {
    console.error('Failed to load session list:', error)
    sessionList.value = []
  } finally {
    sessionListLoading.value = false
  }
}

async function loadSession(sessionId) {
  try {
    const result = await chatAPI.getHistory(sessionId)
    const turns = result.turns || []
    if (turns.length > 0) {
      chatStore.clearSession()
      chatStore.sessionId = sessionId
      chatStore.hasBootstrapped = true
      for (const msg of turns) {
        if (msg.role === 'user') {
          chatStore.addMessage(msg.content, 'user')
        } else if (msg.role === 'assistant') {
          chatStore.addAssistantMessage(msg.content, msg.suggestions || [], msg.actions || [])
        }
      }
    }
    showSessionList.value = false
  } catch (error) {
    console.error('Failed to load session:', error)
  }
}

function startNewSession() {
  chatStore.clearSession()
  chatStore.hasBootstrapped = false
  chatStore.bootstrapConversation()
  showSessionList.value = false
}

function selectMode(mode) {
  chatStore.setAgentMode(mode)
  showModeMenu.value = false
  inputEl.value?.focus()
}

function toggleModeMenu() {
  showModeMenu.value = !showModeMenu.value
}

async function sendMessage(messageOverride = '') {
  const inputValue = typeof inputMessage.value === 'string' ? inputMessage.value : ''
  const text = String(messageOverride || inputValue).trim()
  if (!text || isTyping.value) return

  if (!messageOverride) inputMessage.value = ''
  resetInputHeight()
  chatStore.lastError = ''
  lastRetryMessage.value = ''
  showModeMenu.value = false

  try {
    if (chatStore.isInterviewMode) {
      localTyping.value = true
      chatStore.addMessage(text, 'user')
      const history = chatStore.messages.map(m => ({ role: m.role, content: m.content }))
      const result = await interviewAPI.turn(history, 1)
      chatStore.addAssistantMessage(result.reply, [])

      if (result.crisis || result.is_complete) {
        chatStore.endInterview()
      }
      if (result.report) {
        chatStore.addAssistantMessage(`我整理好这次聊天的小结了，仅供你自我观察参考，不代表诊断。\n\n${result.report}`, [])
      }
      return
    }

    chatStore.addMessage(text, 'user')

    chatStore.isAwaitingReply = true
    await sendStreamingMessage(text)
    
  } catch (error) {
    console.error('Failed to send message:', error)
    lastRetryMessage.value = text
    chatStore.lastError = error.message === 'CHAT_REPLY_TIMEOUT'
      ? '刚才没有顺利接上。你可以直接继续说一句，我会接着听。'
      : '刚才连接不太稳定，我没有发出回复。你可以直接继续说，我会接着听。'
  } finally {
    localTyping.value = false
    chatStore.isAwaitingReply = false
  }
}

async function sendStreamingMessage(text) {
  const controller = new AbortController()
  let firstChunkReceived = false
  const firstChunkTimer = window.setTimeout(() => {
    if (!firstChunkReceived) controller.abort()
  }, STREAM_FIRST_CHUNK_TIMEOUT_MS)
  const overallTimer = window.setTimeout(() => controller.abort(), STREAM_OVERALL_TIMEOUT_MS)

  try {
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

    const response = await fetch(`${apiBaseUrl}/chat/stream`, {
      method: 'POST',
      headers,
      signal: controller.signal,
      body: new URLSearchParams({
        message: text,
        user_id: authStore.user?.id || 1,
        session_id: chatStore.sessionId || '',
        agent_mode: chatStore.agentMode,
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    if (!response.body) {
      throw new Error('STREAM_BODY_UNAVAILABLE')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    let fullResponse = ''
    let messageId = null

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      if (!firstChunkReceived) {
        firstChunkReceived = true
        window.clearTimeout(firstChunkTimer)
      }

      buffer += decoder.decode(value, { stream: true })
      
      while (buffer.includes('\n\n')) {
        const index = buffer.indexOf('\n\n')
        const chunkStr = buffer.substring(0, index)
        buffer = buffer.substring(index + 2)

        if (chunkStr.startsWith('data: ')) {
          const dataStr = chunkStr.substring(5)
          try {
            const chunk = JSON.parse(dataStr)
            
            if (chunk.type === 'start') {
              chatStore.sessionId = chunk.session_id
            } else if (chunk.type === 'token') {
              fullResponse += chunk.token
              chatStore.lastError = ''
              
              if (!messageId) {
                messageId = chatStore.addAssistantMessage(chunk.token, [], [])
              } else {
                chatStore.updateMessage(messageId, fullResponse)
              }
            } else if (chunk.type === 'end') {
              chatStore.sessionId = chunk.session_id
              
              if (chunk.full_response && messageId) {
                chatStore.updateMessage(messageId, chunk.full_response)
              } else if (chunk.full_response && !messageId) {
                messageId = chatStore.addAssistantMessage(chunk.full_response, [], [])
              }
              
              if (messageId && chunk.actions && chunk.actions.length > 0) {
                chatStore.updateMessageActions(messageId, chunk.actions)
              }
              
              if (chunk.memory_state) {
                chatStore.setMemoryState(chunk.memory_state)
              }
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', e)
          }
        }
      }
    }

  } catch (error) {
    console.error('Streaming error:', error)
    
    try {
      const result = await withTimeout(
        chatAPI.sendMessage(
          text,
          authStore.user?.id || 1,
          chatStore.sessionId,
          null,
          chatStore.agentMode
        ),
        CHAT_REPLY_TIMEOUT_MS
      )
      
      chatStore.sessionId = result.session_id
      if (Object.prototype.hasOwnProperty.call(result, 'memory_state')) {
        chatStore.setMemoryState(result.memory_state)
      }
      if (result.reply_status === 'timeout_fallback') {
        lastRetryMessage.value = text
      }
      chatStore.addAssistantMessage(result.reply, result.suggestions || [], result.actions || [])
    } catch (fallbackError) {
      console.error('Fallback error:', fallbackError)
      chatStore.addAssistantMessage('我在。刚才没有顺利接上完整回复，但你可以直接继续说，我会接着听。', [], [])
    }
  } finally {
    window.clearTimeout(firstChunkTimer)
    window.clearTimeout(overallTimer)
  }
}

function handleSuggestion(suggestion) {
  const text = {
    '我想倾诉一下': '我现在想倾诉一下',
    '了解经前情绪': '我想了解为什么经前情绪会变得敏感或烦躁',
    '来个呼吸练习': '我想做一个简单的呼吸练习',
    '深呼吸': '我想试试深呼吸练习',
    '散步': '我想出门走走',
    '听音乐': '我想听点舒缓的音乐'
  }[suggestion] || suggestion

  inputMessage.value = text
  nextTick(() => {
    resizeInput()
    inputEl.value?.focus()
  })
}

function handleAction(action) {
  if (action.route) {
    window.location.href = action.route
  } else if (action.action === 'rest') {
    inputMessage.value = '我需要休息一下'
    nextTick(() => {
      resizeInput()
      inputEl.value?.focus()
    })
  }
}

function clearChat() {
  chatStore.clearMessages()
  chatStore.clearAssessmentState()
  chatStore.bootstrapConversation()
}

function dismissError() {
  chatStore.lastError = ''
}

function openSessionList() {
  showMoreMenu.value = false
  showSessionList.value = true
}

function retryLastMessage() {
  const retryText = lastRetryMessage.value
  if (!retryText) return
  sendMessage(retryText)
}

function withTimeout(promise, timeoutMs) {
  let timerId
  const timeoutPromise = new Promise((_, reject) => {
    timerId = window.setTimeout(() => reject(new Error('CHAT_REPLY_TIMEOUT')), timeoutMs)
  })
  return Promise.race([promise, timeoutPromise]).finally(() => {
    window.clearTimeout(timerId)
  })
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

function resizeInput() {
  if (!inputEl.value) return
  inputEl.value.style.height = 'auto'
  inputEl.value.style.height = `${Math.min(inputEl.value.scrollHeight, 112)}px`
}

function resetInputHeight() {
  if (!inputEl.value) return
  inputEl.value.style.height = '44px'
}

onMounted(async () => {
  if (chatStore.isInterviewMode) {
    await nextTick()
    scrollToBottom()
    return
  }

  if (chatStore.hasRestoredSession) {
    await nextTick()
    scrollToBottom()
    return
  }

  chatStore.bootstrapConversation()

  try {
    if (!chatStore.sessionId) {
      await chatStore.createSession()
    }
  } catch (error) {
    console.log('Session will be created on first message')
  }
})

watch(showSessionList, (newVal) => {
  if (newVal) {
    loadSessionList()
  }
})

onUnmounted(() => {
  if (!chatStore.isInterviewMode) {
    chatStore.disconnect()
  }
})
</script>

<style scoped>
.chat-page {
  min-height: 100vh;
  background: #f9fafb;
  display: flex;
  flex-direction: column;
}

.chat-page > .max-w-lg {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.chat-window {
  flex: 1;
  min-height: 400px;
  max-height: 60vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  border: 1px solid #f3f4f6;
  border-radius: 16px;
  background: linear-gradient(180deg, #fff7fb 0%, #ffffff 62%);
  padding: 20px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}

.message-bubble {
  max-width: 82%;
  border-radius: 18px;
  padding: 10px 12px 8px;
}

.message-agent {
  border: 1px solid #f3f4f6;
  border-bottom-left-radius: 6px;
  background: #ffffff;
  color: #374151;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
}

.message-user {
  border-bottom-right-radius: 6px;
  background: linear-gradient(135deg, #ec4899, #db2777);
  color: #ffffff;
  box-shadow: 0 4px 16px rgba(236, 72, 153, 0.2);
}

.typing-dot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: #9ca3af;
  animation: typing 900ms infinite ease-in-out;
}

.mode-plus {
  width: 40px;
  height: 40px;
  flex: 0 0 auto;
  border: 0;
  border-radius: 10px;
  background: #fce7f3;
  color: #be185d;
  font-size: 24px;
  line-height: 1;
  font-weight: 500;
}

.mode-current {
  min-width: 48px;
  height: 40px;
  flex: 0 0 auto;
  border: 0;
  border-radius: 999px;
  background: #f9fafb;
  color: #be185d;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 700;
}

.mode-menu {
  position: absolute;
  left: 0;
  right: 52px;
  bottom: calc(100% + 10px);
  z-index: 20;
  display: grid;
  gap: 8px;
  border: 1px solid #f3f4f6;
  border-radius: 12px;
  background: #ffffff;
  padding: 8px;
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.16);
}

.mode-menu-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  min-height: 48px;
  border: 0;
  border-radius: 10px;
  padding: 8px 10px;
  text-align: left;
  color: #374151;
}

.mode-menu-item.active {
  background: #fce7f3;
  color: #be185d;
}

.mode-menu-item span {
  font-size: 14px;
  font-weight: 700;
}

.mode-menu-item small {
  color: #6b7280;
  font-size: 12px;
  line-height: 1.35;
}

@keyframes typing {
  0%, 100% {
    opacity: .35;
    transform: translateY(0);
  }
  50% {
    opacity: 1;
    transform: translateY(-3px);
  }
}

@media (max-height: 700px) {
  .chat-window {
    height: 32vh;
    min-height: 220px;
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 1ms !important;
    transition-duration: 1ms !important;
  }
}
</style>
