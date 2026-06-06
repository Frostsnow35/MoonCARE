<template>
  <div class="chat-page">
    <div class="chat-shell" :class="{ 'is-keyboard-open': keyboardOpen }">
      <header class="chat-header">
        <div class="brand-block">
          <span class="brand-mark">她语</span>
          <div class="brand-copy">
            <h1>陪伴聊天</h1>
            <p>慢慢说，我会陪你把当下的感受安放好。</p>
          </div>
        </div>

        <button type="button" class="history-button" @click="openSessionList">
          历史会话
        </button>
      </header>

      <section v-if="showConversationGuide" class="guide-card">
        <div class="guide-header">
          <div class="guide-copy">
            <strong>你可以直接开始说。</strong>
            <p>也可以先从轻一点的入口开始，比如倾诉、写日记、呼吸练习或听音乐。</p>
          </div>

          <button
            type="button"
            class="guide-dismiss"
            aria-label="关闭引导"
            @click="dismissConversationGuide"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M6 6L18 18M18 6L6 18"
                fill="none"
                stroke="currentColor"
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
              />
            </svg>
          </button>
        </div>

        <div class="guide-actions">
          <button type="button" class="guide-chip" @click="handleSuggestion('我想倾诉一下')">我想倾诉一下</button>
          <button type="button" class="guide-chip" @click="handleSuggestion('写日记')">写日记</button>
          <button type="button" class="guide-chip" @click="handleSuggestion('来个呼吸练习')">呼吸练习</button>
          <button type="button" class="guide-chip" @click="handleSuggestion('听音乐')">听音乐</button>
        </div>
      </section>

      <section
        ref="messagesContainer"
        class="chat-window"
        :class="{ 'is-keyboard-open': keyboardOpen }"
      >
        <article
          v-for="msg in messages"
          :key="msg.id"
          class="message-row"
          :class="msg.role === 'user' ? 'is-user' : 'is-assistant'"
        >
          <div class="message-bubble" :class="msg.role === 'user' ? 'bubble-user' : 'bubble-assistant'">
            <p v-if="!shouldRenderMarkdown(msg)" class="message-text">{{ msg.content }}</p>
            <div v-else class="message-text markdown-content" v-html="renderMarkdown(msg.content)"></div>

            <div
              v-if="msg.role === 'assistant' && msg.suggestions && msg.suggestions.length > 0"
              class="message-actions"
              aria-label="快捷回复"
            >
              <button
                v-for="suggestion in msg.suggestions"
                :key="suggestion"
                type="button"
                class="action-chip action-chip-soft"
                @click="handleSuggestion(suggestion)"
              >
                {{ suggestion }}
              </button>
            </div>

            <div
              v-if="msg.role === 'assistant' && msg.actions && msg.actions.length > 0"
              class="message-actions"
              aria-label="快捷功能"
            >
              <button
                v-for="action in msg.actions"
                :key="action.action"
                type="button"
                class="action-chip action-chip-strong"
                :title="action.description"
                @click="handleAction(action)"
              >
                {{ action.label }}
              </button>
            </div>

            <div class="message-meta" :class="msg.role === 'user' ? 'meta-user' : 'meta-assistant'">
              <time :datetime="msg.timestamp">{{ formatTime(msg.timestamp) }}</time>
              <span v-if="msg.replyStatus && msg.replyStatus !== 'ok'" class="status-pill">
                已使用兜底回复
              </span>
            </div>
          </div>
        </article>

        <div v-if="isTyping" class="message-row is-assistant">
          <div class="typing-bubble">
            <div class="typing-indicator" aria-label="正在回复">
              <span class="typing-dot" style="animation-delay: 0ms"></span>
              <span class="typing-dot" style="animation-delay: 140ms"></span>
              <span class="typing-dot" style="animation-delay: 280ms"></span>
            </div>
            <span class="typing-text">{{ waitingText }}</span>
          </div>
        </div>
      </section>

      <section v-if="errorText" class="status-card is-error">
        <div class="status-copy">
          <strong>发送失败</strong>
          <p>{{ errorText }}</p>
        </div>
        <button v-if="lastRetryMessage" type="button" class="status-button" @click="retryLastMessage">
          重试
        </button>
      </section>

      <section v-else-if="isBusy" class="status-card">
        <div class="status-copy">
          <strong>发送中</strong>
          <p>我正在整理回复，你可以稍等一下。</p>
        </div>
      </section>

      <section class="composer-panel" :class="{ 'is-keyboard-open': keyboardOpen }">
        <form class="composer-card" @submit.prevent="sendMessage()" @click="focusComposer">
          <span class="mode-badge">{{ currentModeLabel }}</span>

          <label class="sr-only" for="chat-input">输入消息</label>
          <textarea
            id="chat-input"
            ref="inputEl"
            v-model="inputMessage"
            :disabled="isBusy"
            rows="1"
            maxlength="800"
            class="composer-input"
            placeholder="慢慢说，我在听。"
            @focus="handleInputFocus"
            @blur="handleInputBlur"
            @input="resizeInput"
            @keydown.enter.exact.prevent="sendMessage()"
          ></textarea>

          <button
            type="submit"
            class="send-button"
            :class="canSend ? 'is-enabled' : 'is-disabled'"
            :disabled="!canSend"
            aria-label="发送消息"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M4 12 20 4l-4 16-4-6-8-2Z" fill="currentColor" opacity=".92" />
              <path d="m12 14 8-10" stroke="white" stroke-width="1.8" stroke-linecap="round" />
            </svg>
          </button>
        </form>

        <p class="composer-hint">
          需要更多帮助时，可以从 AI 的快捷建议进入写日记、呼吸练习或音乐疗愈。
        </p>
      </section>
    </div>

    <div v-if="showSessionList" class="overlay" @click.self="showSessionList = false">
      <div class="overlay-card">
        <div class="overlay-header">
          <div>
            <h3>历史会话</h3>
            <p>这里保存当前账号的聊天记录，你可以继续旧会话，也可以开始新会话。</p>
          </div>
          <button type="button" class="close-button" @click="showSessionList = false">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="overlay-body">
          <button type="button" class="session-item is-new" @click="startNewSession">
            <div class="session-copy">
              <strong>开始新会话</strong>
              <small>清空当前本地会话，重新开始这一轮聊天。</small>
            </div>
          </button>

          <div v-if="sessionListLoading" class="loading-block">
            <div class="typing-indicator">
              <span class="typing-dot" style="animation-delay: 0ms"></span>
              <span class="typing-dot" style="animation-delay: 140ms"></span>
              <span class="typing-dot" style="animation-delay: 280ms"></span>
            </div>
          </div>

          <div v-else-if="sessionList.length === 0" class="empty-block">
            还没有历史会话。等你完成几轮聊天后，这里会自动保存最近记录。
          </div>

          <button
            v-for="session in sessionList"
            :key="session.session_id"
            type="button"
            class="session-item"
            :class="session.session_id === chatStore.sessionId ? 'is-current' : ''"
            @click="loadSession(session.session_id)"
          >
            <div class="session-copy">
              <strong>{{ formatRelativeTime(session.last_message_at) }}</strong>
              <small>{{ session.message_count ? `${session.message_count} 条消息` : '暂无消息内容' }}</small>
            </div>
            <span v-if="session.session_id === chatStore.sessionId" class="session-tag">当前</span>
          </button>
        </div>
      </div>
    </div>

    <BottomNav />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { chatAPI, interviewAPI } from '../api'
import BottomNav from '../components/BottomNav.vue'
import { useChatStore } from '../stores/chat'
import { getUserScopedKey } from '../services/userScopedStorage'

const chatStore = useChatStore()

const CLIENT_CONTEXT_TURN_LIMIT = 12
const CLIENT_CONTEXT_TEXT_LIMIT = 500
const GUIDE_DISMISSED_STORAGE_PREFIX = 'mooncare_chat_guide_hidden'
const KEYBOARD_OPEN_THRESHOLD = 140

const messagesContainer = ref(null)
const inputEl = ref(null)
const inputMessage = ref('')
const localTyping = ref(false)
const lastRetryMessage = ref('')
const hasAssistantStarted = ref(false)
const showSessionList = ref(false)
const sessionList = ref([])
const sessionListLoading = ref(false)
const keyboardOpen = ref(false)
const guideDismissed = ref(false)

let blurTimer = null
let removeViewportListener = null

const messages = computed(() => chatStore.messages)
const isBusy = computed(() => chatStore.isAwaitingReply || localTyping.value)
const isTyping = computed(() => isBusy.value && !hasAssistantStarted.value)
const errorText = computed(() => chatStore.lastError)
const canSend = computed(() => inputMessage.value.trim().length > 0 && !isBusy.value)
const waitingText = computed(() => (
  chatStore.agentMode === 'knowledge' ? '正在整理相关解释...' : '正在组织回复...'
))
const currentModeLabel = computed(() => (
  chatStore.agentMode === 'auto' ? '自动陪伴' : chatStore.activeAgent.label
))
const showConversationGuide = computed(() => !guideDismissed.value && messages.value.length <= 1)

watch(messages, async () => {
  await nextTick()
  scrollToBottom()
}, { deep: true })

watch(showSessionList, newValue => {
  if (newValue) {
    loadSessionList()
  }
})

function getGuideDismissedKey() {
  return getUserScopedKey(GUIDE_DISMISSED_STORAGE_PREFIX)
}

function loadGuideDismissedState() {
  try {
    guideDismissed.value = localStorage.getItem(getGuideDismissedKey()) === '1'
  } catch {
    guideDismissed.value = false
  }
}

function dismissConversationGuide() {
  guideDismissed.value = true
  try {
    localStorage.setItem(getGuideDismissedKey(), '1')
  } catch {
    // ignore storage failures in WebView private contexts
  }
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
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

function openSessionList() {
  showSessionList.value = true
}

function startNewSession() {
  chatStore.clearSession()
  chatStore.hasBootstrapped = false
  chatStore.bootstrapConversation()
  showSessionList.value = false
  guideDismissed.value = false
  focusComposer()
}

function focusComposer() {
  if (isBusy.value) return
  nextTick(() => {
    inputEl.value?.focus()
    resizeInput()
    scrollComposerIntoView()
  })
}

function handleInputFocus() {
  keyboardOpen.value = true
  scrollComposerIntoView()
}

function handleInputBlur() {
  if (blurTimer) {
    clearTimeout(blurTimer)
  }
  blurTimer = setTimeout(() => {
    syncKeyboardState()
  }, 120)
}

function syncKeyboardState() {
  if (typeof window === 'undefined') return
  if (window.visualViewport) {
    const diff = window.innerHeight - window.visualViewport.height
    keyboardOpen.value = diff > KEYBOARD_OPEN_THRESHOLD
    return
  }
  keyboardOpen.value = document.activeElement === inputEl.value
}

function scrollComposerIntoView() {
  setTimeout(() => {
    scrollToBottom()
    inputEl.value?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }, 80)
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

  try {
    if (chatStore.isInterviewMode) {
      localTyping.value = true
      chatStore.addMessage(text, 'user')
      const history = chatStore.messages.map(msg => ({ role: msg.role, content: msg.content }))
      const result = await interviewAPI.turn(history, 1)
      chatStore.addAssistantMessage(result.reply, [])

      if (result.crisis || result.is_complete) {
        chatStore.endInterview()
      }
      if (result.report) {
        chatStore.addAssistantMessage(
          `我整理好了这次聊天的小结，仅供你自我观察参考，不代表诊断。\n\n${result.report}`,
          [],
        )
      }
      return
    }

    chatStore.addMessage(text, 'user')
    chatStore.isAwaitingReply = true
    await sendStreamingMessage(text)
  } catch (error) {
    console.error('Failed to send message:', error)
    lastRetryMessage.value = text
    chatStore.isConnected = false
    chatStore.lastError = '当前网络不太稳定，这条消息还没有成功送达。'
  } finally {
    localTyping.value = false
    chatStore.isAwaitingReply = false
    hasAssistantStarted.value = false
    scrollComposerIntoView()
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
    clientContext,
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
            replyStatus: chunk.reply_status || 'ok',
            replyPhase: chunk.phase || 'answer',
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
          cacheSimilarity: chunk.cache_similarity || 0,
        })
      } else if (finalResponse) {
        chatStore.addAssistantMessage(finalResponse, chunk.suggestions || [], chunk.actions || [], {
          replyStatus: chunk.reply_status || 'ok',
          elapsedMs: chunk.elapsed_ms || 0,
          cacheHit: chunk.cache_hit || false,
          cacheSimilarity: chunk.cache_similarity || 0,
        })
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
    if (current.length >= 8 || '。！？?!\n'.includes(char)) {
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
      content: msg.content.replace(/\s+/g, ' ').trim().slice(0, CLIENT_CONTEXT_TEXT_LIMIT),
    }))

  while (turns.length > 0 && turns[turns.length - 1].role === 'user' && turns[turns.length - 1].content === current) {
    turns.pop()
  }

  return JSON.stringify(turns)
}

function handleSuggestion(suggestion) {
  const text = {
    我想倾诉一下: '我现在想倾诉一下',
    写日记: '我想先写下一段日记',
    来个呼吸练习: '我想做一个简单的呼吸练习',
    听音乐: '我想听一些更舒缓的音乐',
    了解经前情绪: '我想了解为什么经前情绪会更敏感',
  }[suggestion] || suggestion

  inputMessage.value = text
  nextTick(() => {
    resizeInput()
    focusComposer()
  })
}

function handleAction(action) {
  if (action.route) {
    window.location.href = action.route
  }
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
    ALLOWED_ATTR: ['href', 'target', 'rel'],
  })
}

onMounted(async () => {
  loadGuideDismissedState()

  if (typeof window !== 'undefined' && window.visualViewport) {
    const listener = () => syncKeyboardState()
    window.visualViewport.addEventListener('resize', listener)
    window.visualViewport.addEventListener('scroll', listener)
    removeViewportListener = () => {
      window.visualViewport?.removeEventListener('resize', listener)
      window.visualViewport?.removeEventListener('scroll', listener)
    }
  }

  if (chatStore.isInterviewMode || chatStore.hasRestoredSession) {
    await nextTick()
    resizeInput()
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
  } finally {
    await nextTick()
    resizeInput()
  }
})

onBeforeUnmount(() => {
  if (blurTimer) {
    clearTimeout(blurTimer)
  }
  removeViewportListener?.()
})
</script>

<style scoped>
.chat-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #fff8fb 0%, #f8fafc 42%, #f8fafc 100%);
}

.chat-shell {
  display: flex;
  flex-direction: column;
  width: min(100%, 448px);
  min-height: 100vh;
  margin: 0 auto;
  padding: 16px 16px calc(88px + env(safe-area-inset-bottom, 0));
  gap: 12px;
}

.chat-shell.is-keyboard-open {
  padding-bottom: 148px;
}

.chat-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  border-radius: 16px;
  background: linear-gradient(135deg, #fb7185, #ec4899);
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
}

.brand-copy h1 {
  margin: 0;
  color: #1f2937;
  font-size: 18px;
  font-weight: 800;
}

.brand-copy p {
  margin: 3px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
}

.history-button {
  min-width: 78px;
  height: 38px;
  flex: 0 0 auto;
  border: 1px solid #fbcfe8;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.94);
  color: #db2777;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 700;
}

.guide-card,
.status-card,
.composer-card,
.chat-window,
.overlay-card {
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
}

.guide-card {
  border: 1px solid #fde2e8;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.94);
  padding: 14px;
}

.guide-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.guide-copy {
  min-width: 0;
}

.guide-copy strong {
  color: #1f2937;
  font-size: 14px;
}

.guide-copy p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.55;
}

.guide-dismiss {
  width: 30px;
  height: 30px;
  flex: 0 0 auto;
  border: 0;
  border-radius: 999px;
  background: #fff1f5;
  color: #db2777;
  display: grid;
  place-items: center;
}

.guide-dismiss svg {
  width: 16px;
  height: 16px;
}

.guide-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.guide-chip,
.action-chip {
  min-height: 34px;
  border-radius: 999px;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 600;
}

.guide-chip,
.action-chip-soft {
  border: 1px solid #fbcfe8;
  background: #fff6f8;
  color: #db2777;
}

.action-chip-strong {
  border: 1px solid #dbeafe;
  background: #eff6ff;
  color: #2563eb;
}

.chat-window {
  flex: 1;
  min-height: calc(100vh - 308px);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  border: 1px solid #f1f5f9;
  border-radius: 24px;
  background: linear-gradient(180deg, #fff8fb 0%, #ffffff 62%);
  padding: 18px 14px 22px;
}

.chat-window.is-keyboard-open {
  min-height: auto;
}

.message-row {
  display: flex;
}

.message-row.is-user {
  justify-content: flex-end;
}

.message-row.is-assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: min(86%, 320px);
  border-radius: 20px;
  padding: 12px 13px 10px;
  overflow-wrap: anywhere;
}

.bubble-assistant {
  border: 1px solid #f1f5f9;
  border-bottom-left-radius: 8px;
  background: #ffffff;
  color: #334155;
}

.bubble-user {
  border-bottom-right-radius: 8px;
  background: linear-gradient(135deg, #f472b6, #ec4899);
  color: #ffffff;
}

.message-text {
  margin: 0;
  font-size: 14px;
  line-height: 1.75;
  white-space: pre-wrap;
  word-break: break-word;
}

.message-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.message-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-top: 8px;
  font-size: 11px;
}

.meta-assistant {
  color: #94a3b8;
}

.meta-user {
  color: rgba(255, 255, 255, 0.82);
}

.status-pill {
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.16);
  padding: 2px 8px;
}

.typing-bubble {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid #f1f5f9;
  border-radius: 18px;
  background: #ffffff;
}

.typing-indicator {
  display: flex;
  gap: 4px;
}

.typing-dot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: #94a3b8;
  animation: typing 900ms infinite ease-in-out;
}

.typing-text {
  color: #94a3b8;
  font-size: 12px;
}

.status-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.96);
  padding: 12px 14px;
}

.status-card.is-error {
  border-color: #fecaca;
  background: #fff5f5;
}

.status-copy strong {
  display: block;
  color: #1f2937;
  font-size: 13px;
}

.status-copy p {
  margin: 3px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
}

.status-card.is-error .status-copy strong,
.status-card.is-error .status-copy p {
  color: #b91c1c;
}

.status-button {
  min-height: 34px;
  border: 0;
  border-radius: 12px;
  background: #ffffff;
  color: #dc2626;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 700;
}

.composer-panel {
  position: sticky;
  bottom: calc(58px + env(safe-area-inset-bottom, 0));
  z-index: 20;
}

.composer-panel.is-keyboard-open {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  width: min(calc(100% - 24px), 416px);
  bottom: calc(12px + env(safe-area-inset-bottom, 0));
}

.composer-panel.is-keyboard-open .composer-hint {
  display: none;
}

.composer-card {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.98);
  padding: 8px;
}

.composer-card:focus-within {
  border-color: #f9a8d4;
  box-shadow: 0 0 0 4px rgba(244, 114, 182, 0.12);
}

.mode-badge {
  min-width: 74px;
  height: 40px;
  flex: 0 0 auto;
  border-radius: 999px;
  background: #fff1f5;
  color: #be185d;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}

.composer-input {
  flex: 1;
  min-height: 44px;
  max-height: 112px;
  border: 0;
  outline: none;
  resize: none;
  background: transparent;
  padding: 10px 4px;
  color: #1f2937;
  font-size: 16px;
  line-height: 1.5;
}

.composer-input::placeholder {
  color: #94a3b8;
}

.send-button {
  width: 44px;
  height: 44px;
  flex: 0 0 auto;
  border: 0;
  border-radius: 14px;
  display: grid;
  place-items: center;
}

.send-button svg {
  width: 20px;
  height: 20px;
}

.send-button.is-enabled {
  background: #ec4899;
  color: #ffffff;
}

.send-button.is-disabled {
  background: #e5e7eb;
  color: #94a3b8;
}

.composer-hint {
  margin: 8px 4px 0;
  color: #94a3b8;
  font-size: 11px;
  line-height: 1.45;
}

.overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.32);
  padding: 16px;
}

.overlay-card {
  display: flex;
  flex-direction: column;
  width: min(100%, 380px);
  max-height: 70vh;
  border-radius: 24px;
  background: #ffffff;
}

.overlay-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid #f1f5f9;
}

.overlay-header h3 {
  margin: 0;
  color: #1f2937;
  font-size: 16px;
  font-weight: 800;
}

.overlay-header p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
}

.close-button {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 999px;
  background: #f8fafc;
  color: #64748b;
}

.close-button svg {
  width: 18px;
  height: 18px;
}

.overlay-body {
  overflow-y: auto;
  padding: 10px;
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 66px;
  border: 0;
  border-radius: 16px;
  background: transparent;
  padding: 12px;
  text-align: left;
}

.session-item.is-new {
  background: #fff6f8;
}

.session-item:hover,
.session-item.is-current {
  background: #fdf2f8;
}

.session-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.session-copy strong {
  color: #1f2937;
  font-size: 14px;
}

.session-copy small {
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
}

.session-tag {
  color: #ec4899;
  font-size: 12px;
  font-weight: 700;
}

.loading-block,
.empty-block {
  display: grid;
  place-items: center;
  min-height: 120px;
  color: #94a3b8;
  padding: 0 16px;
  text-align: center;
  font-size: 13px;
  line-height: 1.5;
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
  margin-left: 1.5em;
  margin-bottom: 0.5em;
}

.markdown-content :deep(li) {
  list-style: disc;
}

.markdown-content :deep(ol li) {
  list-style: decimal;
}

.markdown-content :deep(code) {
  background: #fce7f3;
  padding: 0.125em 0.375em;
  border-radius: 0.25em;
  font-size: 0.875em;
}

.markdown-content :deep(pre) {
  background: #1f2937;
  color: #f8fafc;
  padding: 0.75em;
  border-radius: 0.5em;
  overflow-x: auto;
  margin-bottom: 0.5em;
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
  font-weight: 600;
  margin-top: 0.75em;
  margin-bottom: 0.5em;
}

.markdown-content :deep(blockquote) {
  border-left: 3px solid #ec4899;
  padding-left: 1em;
  margin-left: 0;
  color: #64748b;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
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

@media (max-width: 380px) {
  .chat-shell {
    padding-right: 12px;
    padding-left: 12px;
  }

  .message-bubble {
    max-width: 90%;
  }

  .history-button {
    min-width: 68px;
    padding: 0 10px;
  }

  .composer-panel.is-keyboard-open {
    width: calc(100% - 20px);
  }
}

@media (max-height: 760px) {
  .chat-window {
    min-height: calc(100vh - 294px);
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
