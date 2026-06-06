<template>
  <div class="app-page">
    <div class="page-content chat-shell">
      <header class="page-card-soft p-4">
        <div class="flex items-center justify-between">
          <div class="min-w-0 flex items-center gap-3">
            <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-pink-100">
              <svg class="h-8 w-8" viewBox="0 0 40 40" aria-hidden="true">
                <circle cx="20" cy="20" r="18" fill="#FFE4EC" />
                <path d="M11 23c2.7 5.4 15.3 5.4 18 0 2-4.1-.6-10.5-9-10.5S9 18.9 11 23Z" fill="#F9A8C7" />
                <circle cx="15" cy="20" r="2" fill="#4B3A46" />
                <circle cx="25" cy="20" r="2" fill="#4B3A46" />
                <path d="M17 25c1.8 1.2 4.2 1.2 6 0" stroke="#4B3A46" stroke-width="1.8" stroke-linecap="round" />
              </svg>
            </div>
            <div class="min-w-0">
              <p class="section-label">聊天</p>
              <h1 class="mt-2 text-lg font-semibold leading-tight text-slate-800">{{ headerTitle }}</h1>
              <p class="mt-1 truncate text-xs text-slate-500">{{ headerSubtitle }}</p>
              <p v-if="memoryStatusText" class="mt-1 truncate text-[11px] text-pink-500">{{ memoryStatusText }}</p>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <button
              type="button"
              class="icon-button h-10 w-10 min-w-10 shadow-none"
              title="历史会话"
              @click="openSessionList"
            >
              <svg class="h-5 w-5 text-rose-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </button>
            <button
              type="button"
              class="icon-button h-10 w-10 min-w-10 shadow-none"
              title="新建会话"
              @click="startNewSession"
            >
              <svg class="h-5 w-5 text-rose-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      <section class="chat-messages">
        <div ref="messagesContainer" class="chat-window">
          <article
            v-for="msg in messages"
            :key="msg.id"
            class="flex animate-fadeIn"
            :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
            @contextmenu.prevent="showMessageMenu($event, msg)"
          >
            <div
              class="message-bubble"
              :class="msg.role === 'user' ? 'message-user' : 'message-agent'"
              @click.right.prevent="showMessageMenu($event, msg)"
            >
              <p
                v-if="!shouldRenderMarkdown(msg)"
                class="break-words whitespace-pre-wrap text-sm leading-relaxed"
              >
                {{ msg.content }}
              </p>
              <div
                v-else
                class="markdown-content break-words text-sm leading-relaxed"
                v-html="renderMarkdown(msg.content)"
              ></div>

              <div
                v-if="msg.role === 'assistant' && msg.suggestions && msg.suggestions.length > 0"
                class="mt-2 flex flex-wrap gap-1.5"
                aria-label="快捷回复"
              >
                <button
                  v-for="suggestion in msg.suggestions"
                  :key="suggestion"
                  type="button"
                  class="min-h-9 rounded-full border border-pink-100 bg-pink-50 px-3 text-xs text-pink-600 active:scale-95"
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
                  class="min-h-9 rounded-full border border-blue-100 bg-gradient-to-r from-blue-50 to-purple-50 px-3 text-xs text-blue-600 transition-shadow hover:shadow-sm active:scale-95"
                  :title="action.description"
                  @click="handleAction(action)"
                >
                  {{ action.label }}
                </button>
              </div>

              <time
                class="mt-1 block text-[11px]"
                :class="msg.role === 'user' ? 'text-pink-100' : 'text-gray-400'"
                :datetime="msg.timestamp"
              >
                {{ formatTime(msg.timestamp) }}
              </time>
            </div>
          </article>

          <div v-if="isTyping" class="flex justify-start animate-fadeIn">
            <div class="rounded-2xl rounded-bl-md border border-gray-100 bg-white px-3 py-2 shadow-sm">
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

      <section v-if="errorText">
        <div class="flex items-center justify-between gap-3 rounded-xl border border-red-100 bg-red-50 p-3 text-xs text-red-700">
          <span class="leading-relaxed">{{ errorText }}</span>
          <button
            v-if="lastRetryMessage"
            type="button"
            class="min-h-9 shrink-0 rounded-lg bg-white px-3 text-red-600"
            @click="retryLastMessage"
          >
            重试
          </button>
        </div>
      </section>

      <section class="chat-composer">
        <form class="rounded-xl border border-gray-200 bg-white p-2 shadow-sm" @submit.prevent="sendMessage()">
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
              :aria-expanded="showModeMenu"
              aria-label="选择聊天模式"
              @click="toggleModeMenu"
            >
              +
            </button>
            <button type="button" class="mode-current" @click="toggleModeMenu">
              {{ chatStore.agentMode === 'auto' ? '自动' : chatStore.activeAgent.shortLabel }}
            </button>

            <label class="sr-only" for="chat-input">输入消息</label>
            <textarea
              id="chat-input"
              ref="inputEl"
              v-model="inputMessage"
              :disabled="isBusy"
              rows="1"
              maxlength="800"
              class="min-h-11 max-h-28 flex-1 resize-none border-0 px-2 py-2 text-base leading-relaxed text-gray-800 outline-none placeholder:text-gray-400"
              placeholder="慢慢说，我在听..."
              @input="resizeInput"
              @keydown.enter.exact.prevent="sendMessage()"
            ></textarea>

            <button
              type="submit"
              class="flex h-11 w-11 items-center justify-center rounded-lg transition-colors active:scale-95"
              :class="canSend ? 'bg-pink-500 text-white' : 'bg-gray-100 text-gray-400'"
              :disabled="!canSend"
              aria-label="发送消息"
            >
              <svg class="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 12 20 4l-4 16-4-6-8-2Z" fill="currentColor" opacity=".92" />
                <path d="m12 14 8-10" stroke="white" stroke-width="1.8" stroke-linecap="round" />
              </svg>
            </button>
          </div>
        </form>
      </section>
    </div>

    <div v-if="showSessionList" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30" @click.self="showSessionList = false">
      <div class="mx-4 flex max-h-[70vh] w-full max-w-sm flex-col rounded-2xl bg-white">
        <div class="flex items-center justify-between border-b border-gray-100 p-4">
          <h3 class="text-base font-bold text-gray-800">历史会话</h3>
          <button type="button" class="flex h-8 w-8 items-center justify-center rounded-full hover:bg-gray-100" @click="showSessionList = false">
            <svg class="h-5 w-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-2">
          <button
            type="button"
            class="w-full rounded-xl p-3 text-left transition-colors hover:bg-pink-50"
            @click="startNewSession"
          >
            <div class="flex items-center gap-3">
              <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-pink-100">
                <svg class="h-5 w-5 text-pink-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                </svg>
              </div>
              <div class="min-w-0 flex-1">
                <p class="text-sm font-medium text-gray-800">新建会话</p>
                <p class="text-xs text-gray-400">开始一段新的对话</p>
              </div>
            </div>
          </button>

          <div v-if="sessionListLoading" class="flex items-center justify-center py-8">
            <div class="flex gap-1">
              <span class="h-2 w-2 animate-bounce rounded-full bg-pink-400" style="animation-delay: 0ms"></span>
              <span class="h-2 w-2 animate-bounce rounded-full bg-pink-400" style="animation-delay: 140ms"></span>
              <span class="h-2 w-2 animate-bounce rounded-full bg-pink-400" style="animation-delay: 280ms"></span>
            </div>
          </div>

          <div v-else-if="sessionList.length === 0" class="py-8 text-center text-sm text-gray-400">
            暂无历史会话
          </div>

          <button
            v-for="session in sessionList"
            v-else
            :key="session.session_id"
            type="button"
            class="w-full rounded-xl p-3 text-left transition-colors hover:bg-pink-50"
            :class="session.session_id === chatStore.sessionId ? 'bg-pink-50' : ''"
            @click="loadSession(session.session_id)"
          >
            <div class="flex items-center gap-3">
              <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gray-100">
                <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
              <div class="min-w-0 flex-1">
                <div class="flex items-center justify-between gap-2">
                  <p class="truncate text-sm font-medium text-gray-800">{{ formatRelativeTime(session.last_message_at) }}</p>
                  <span v-if="session.session_id === chatStore.sessionId" class="shrink-0 text-xs text-pink-500">当前</span>
                </div>
                <p class="truncate text-xs text-gray-400">{{ session.message_count ? `${session.message_count} 条消息` : '暂无消息' }}</p>
              </div>
            </div>
          </button>
        </div>

        <div class="border-t border-gray-100 p-3">
          <button type="button" class="ghost-button w-full" @click="clearChatAndClose">
            清空当前会话
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="showContextMenu"
      class="fixed z-50 min-w-[140px] rounded-xl border border-gray-200 bg-white py-2 shadow-2xl"
      :style="{ left: `${contextMenuPosition.x}px`, top: `${contextMenuPosition.y}px` }"
      @click.stop
    >
      <button
        class="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-gray-700 transition-colors hover:bg-pink-50"
        @click="copyMessage(selectedMessage)"
      >
        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
        复制
      </button>
      <button
        class="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-gray-700 transition-colors hover:bg-pink-50"
        @click="revokeMessage(selectedMessage)"
      >
        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 14l9-5-9-5-9 5 9 5z" />
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" />
        </svg>
        撤回
      </button>
    </div>

    <div
      v-if="showCopyToast"
      class="fixed bottom-24 left-1/2 z-50 -translate-x-1/2 rounded-lg bg-gray-800 px-4 py-2 text-sm text-white shadow-lg"
    >
      已复制到剪贴板
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { chatAPI } from '../api'
import { useChatStore } from '../stores/chat'

const router = useRouter()
const chatStore = useChatStore()
const CLIENT_CONTEXT_TURN_LIMIT = 12
const CLIENT_CONTEXT_TEXT_LIMIT = 500

const messagesContainer = ref(null)
const inputEl = ref(null)
const inputMessage = ref('')
const localTyping = ref(false)
const showModeMenu = ref(false)
const lastRetryMessage = ref('')
const hasAssistantStarted = ref(false)
const showContextMenu = ref(false)
const contextMenuPosition = ref({ x: 0, y: 0 })
const selectedMessage = ref(null)
const showCopyToast = ref(false)

const showSessionList = ref(false)
const sessionList = ref([])
const sessionListLoading = ref(false)

const messages = computed(() => chatStore.messages)
const isBusy = computed(() => chatStore.isAwaitingReply || localTyping.value)
const isTyping = computed(() => isBusy.value && !hasAssistantStarted.value)
const errorText = computed(() => chatStore.lastError)
const canSend = computed(() => inputMessage.value.trim().length > 0 && !isBusy.value)
const waitingText = computed(() => chatStore.agentMode === 'knowledge' ? '正在整理更合适的解释...' : '正在组织回复...')
const headerTitle = computed(() => chatStore.agentMode === 'auto' ? 'MoonCARE 陪伴对话' : chatStore.activeAgent.label)
const headerSubtitle = computed(() => chatStore.agentMode === 'auto' ? '先聊感受、身体变化和周期里的波动，再决定要不要继续细化。' : chatStore.activeAgent.helper)
const memoryStatusText = computed(() => {
  if (!chatStore.memoryState?.has_memory && !chatStore.memoryState?.updated) return ''
  if (chatStore.memoryState.updated) return '已延续你刚刚提到的状态'
  return '继续上次聊到的状态'
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
  if (diffMins < 60) return `${diffMins} 分钟前`
  if (diffHours < 24) return `${diffHours} 小时前`
  if (diffDays < 7) return `${diffDays} 天前`
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

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
    chatStore.clearSession()
    chatStore.restoreSessionFromHistory(sessionId, turns)
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

function clearChatAndClose() {
  chatStore.clearMessages()
  chatStore.clearAssessmentState()
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
  if (!text || isBusy.value) return

  if (!messageOverride) inputMessage.value = ''
  resetInputHeight()
  chatStore.lastError = ''
  lastRetryMessage.value = ''
  hasAssistantStarted.value = false
  showModeMenu.value = false

  try {
    chatStore.addMessage(text, 'user')
    chatStore.isAwaitingReply = true
    await sendStreamingMessage(text)
  } catch (error) {
    console.error('Failed to send message:', error)
    lastRetryMessage.value = text
    chatStore.isConnected = false
    chatStore.lastError = '连接有点不稳。你刚才说的内容还在，我们可以继续围着它慢慢来。'
  } finally {
    localTyping.value = false
    chatStore.isAwaitingReply = false
    hasAssistantStarted.value = false
  }
}

async function sendStreamingMessage(text) {
  const clientContext = buildClientContext(text)
  let fullResponse = ''
  let messageId = null

  for await (const chunk of chatAPI.sendMessageStream(
    text,
    chatStore.sessionId,
    null,
    chatStore.agentMode,
    clientContext
  )) {
    if (chunk.type === 'start') {
      chatStore.sessionId = chunk.session_id
      chatStore.isConnected = true
      continue
    }

    if (chunk.type === 'token') {
      hasAssistantStarted.value = true
      chatStore.lastError = ''
      const displayTokens = splitDisplayToken(chunk.token || '')

      for (const tokenPart of displayTokens) {
        fullResponse += tokenPart

        if (!messageId) {
          messageId = chatStore.addAssistantMessage(fullResponse, [], [], {
            replyPhase: chunk.phase || 'answer'
          })
        } else {
          chatStore.updateMessage(messageId, fullResponse)
        }

        if (displayTokens.length > 1) {
          await new Promise(resolve => setTimeout(resolve, 18))
        }
      }
      continue
    }

    if (chunk.type === 'end') {
      chatStore.sessionId = chunk.session_id
      const finalResponse = chunk.full_response || fullResponse

      if (messageId) {
        chatStore.updateMessage(messageId, finalResponse)
        chatStore.updateMessageMetadata(messageId, {
          suggestions: chunk.suggestions || [],
          actions: chunk.actions || [],
          replyStatus: chunk.reply_status || 'ok',
          elapsedMs: chunk.elapsed_ms || 0,
          cacheHit: chunk.cache_hit || false,
          cacheSimilarity: chunk.cache_similarity || 0
        })
      } else if (finalResponse) {
        messageId = chatStore.addAssistantMessage(
          finalResponse,
          chunk.suggestions || [],
          chunk.actions || [],
          {
            replyStatus: chunk.reply_status || 'ok',
            elapsedMs: chunk.elapsed_ms || 0,
            cacheHit: chunk.cache_hit || false,
            cacheSimilarity: chunk.cache_similarity || 0
          }
        )
      }

      if (Object.prototype.hasOwnProperty.call(chunk, 'assessment_state')) {
        chatStore.setAssessmentState(chunk.assessment_state)
      }
      if (Object.prototype.hasOwnProperty.call(chunk, 'memory_state')) {
        chatStore.setMemoryState(chunk.memory_state)
      }
      if (chunk.reply_status && chunk.reply_status !== 'ok') {
        lastRetryMessage.value = text
      }
    }
  }
}

function splitDisplayToken(token) {
  const text = String(token || '')
  if (!text) return []
  if (text.length <= 10) return [text]

  const chunks = []
  let current = ''
  for (const char of text) {
    current += char
    if (current.length >= 8 || '。！？；?\n'.includes(char)) {
      chunks.push(current)
      current = ''
    }
  }
  if (current) chunks.push(current)
  return chunks
}

function buildClientContext(currentText = '') {
  const current = String(currentText || '').trim()
  const turns = chatStore.messages
    .filter(msg => ['user', 'assistant'].includes(msg.role) && typeof msg.content === 'string' && msg.content.trim())
    .slice(-CLIENT_CONTEXT_TURN_LIMIT)
    .map(msg => ({
      role: msg.role,
      content: msg.content.replace(/\s+/g, ' ').trim().slice(0, CLIENT_CONTEXT_TEXT_LIMIT)
    }))

  while (turns.length > 0 && turns[turns.length - 1].role === 'user' && turns[turns.length - 1].content === current) {
    turns.pop()
  }

  return JSON.stringify(turns)
}

function handleSuggestion(suggestion) {
  const text = {
    '我想倾诉一下': '我现在想倾诉一下',
    '了解经前情绪': '我想了解为什么经前情绪会变得敏感或低落',
    '来个呼吸练习': '我想做一个简单的呼吸练习',
    深呼吸: '我想试试深呼吸练习',
    散步: '我想出门走走',
    听音乐: '我想听点舒缓的音乐'
  }[suggestion] || suggestion

  inputMessage.value = text
  nextTick(() => {
    resizeInput()
    inputEl.value?.focus()
  })
}

function handleAction(action) {
  if (action.route) {
    router.push(action.route)
  } else if (action.action === 'rest') {
    inputMessage.value = '我需要休息一下'
    nextTick(() => {
      resizeInput()
      inputEl.value?.focus()
    })
  }
}

function openSessionList() {
  showSessionList.value = true
}

function retryLastMessage() {
  const retryText = lastRetryMessage.value
  if (!retryText) return
  sendMessage(retryText)
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

function shouldRenderMarkdown(msg) {
  return msg.role === 'assistant' && /[\*#\[\]\(\)_~`]/.test(msg.content)
}

function renderMarkdown(content) {
  const rawHtml = marked.parse(content, { breaks: true, gfm: true })
  return DOMPurify.sanitize(rawHtml, {
    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 's', 'a', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'code', 'pre', 'blockquote'],
    ALLOWED_ATTR: ['href', 'target', 'rel']
  })
}

function showMessageMenu(event, message) {
  selectedMessage.value = message
  const x = Math.min(event.clientX, window.innerWidth - 160)
  const y = Math.min(event.clientY, window.innerHeight - 120)
  contextMenuPosition.value = { x, y }
  showContextMenu.value = true
}

function hideMessageMenu() {
  showContextMenu.value = false
  selectedMessage.value = null
}

function copyMessage(message) {
  if (!message) return
  navigator.clipboard.writeText(message.content).then(() => {
    showCopyToast.value = true
    setTimeout(() => {
      showCopyToast.value = false
    }, 1500)
  })
  hideMessageMenu()
}

function revokeMessage(message) {
  if (!message) return
  chatStore.revokeMessagePair(message.id)
  hideMessageMenu()
}

function handleWindowClick() {
  hideMessageMenu()
}

onMounted(async () => {
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

  window.addEventListener('click', handleWindowClick)
})

onUnmounted(() => {
  window.removeEventListener('click', handleWindowClick)
})

watch(showSessionList, (newVal) => {
  if (newVal) {
    loadSessionList()
  }
})
</script>

<style scoped>
.chat-shell {
  flex: 1;
  display: flex;
  min-height: 0;
  flex-direction: column;
  gap: 0.85rem;
}

.chat-messages {
  flex: 1;
  min-height: 0;
}

.chat-composer {
  position: sticky;
  bottom: calc(0.5rem + env(safe-area-inset-bottom));
}

.chat-window {
  display: flex;
  min-height: 400px;
  max-height: 60vh;
  flex: 1;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
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
  min-height: 48px;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
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
  0%,
  100% {
    opacity: 0.35;
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

@media (min-width: 1024px) {
  .chat-composer {
    bottom: 0;
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

.markdown-content :deep(p) {
  margin-bottom: 0.5em;
}

.markdown-content :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-content :deep(strong),
.markdown-content :deep(b) {
  font-weight: 600;
}

.markdown-content :deep(em),
.markdown-content :deep(i) {
  font-style: italic;
}

.markdown-content :deep(a) {
  color: #db2777;
  text-decoration: underline;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin-bottom: 0.5em;
  margin-left: 1.5em;
}

.markdown-content :deep(li) {
  list-style: disc;
}

.markdown-content :deep(ol li) {
  list-style: decimal;
}

.markdown-content :deep(code) {
  border-radius: 0.25em;
  background: #fce7f3;
  padding: 0.125em 0.375em;
  font-size: 0.875em;
}

.markdown-content :deep(pre) {
  margin-bottom: 0.5em;
  overflow-x: auto;
  border-radius: 0.5em;
  background: #1f2937;
  padding: 0.75em;
  color: #f9fafb;
}

.markdown-content :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
  margin-top: 0.75em;
  margin-bottom: 0.5em;
  font-weight: 600;
}

.markdown-content :deep(blockquote) {
  margin-left: 0;
  border-left: 3px solid #ec4899;
  padding-left: 1em;
  color: #6b7280;
}
</style>
