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
          <button
            v-if="messages.length > 0"
            type="button"
            class="min-h-10 px-3 text-xs text-gray-500 rounded-lg active:bg-gray-100"
            @click="clearChat"
          >
            清空
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

    <BottomNav />
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { chatAPI, interviewAPI } from '../api'
import { useChatStore } from '../stores/chat'
import BottomNav from '../components/BottomNav.vue'

const chatStore = useChatStore()
const CHAT_REPLY_TIMEOUT_MS = 40000

const messagesContainer = ref(null)
const inputEl = ref(null)
const inputMessage = ref('')
const localTyping = ref(false)
const showModeMenu = ref(false)
const lastRetryMessage = ref('')

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
    const result = await withTimeout(
      chatAPI.sendMessage(
        text,
        1,
        chatStore.sessionId,
        null,
        chatStore.agentMode
      ),
      CHAT_REPLY_TIMEOUT_MS
    )
    chatStore.sessionId = result.session_id
    if (Object.prototype.hasOwnProperty.call(result, 'assessment_state')) {
      chatStore.setAssessmentState(result.assessment_state)
    }
    if (Object.prototype.hasOwnProperty.call(result, 'memory_state')) {
      chatStore.setMemoryState(result.memory_state)
    }
    chatStore.addAssistantMessage(result.reply, result.suggestions || [], result.actions || [])
  } catch (error) {
    console.error('Failed to send message:', error)
    lastRetryMessage.value = text
    chatStore.lastError = error.message === 'CHAT_REPLY_TIMEOUT'
      ? '这次回复等得有点久，我先停止等待了。你可以重试，或者换成“陪伴”模式继续聊。'
      : '刚才连接不太稳定，我没有发出回复。你可以重试一次。'
  } finally {
    localTyping.value = false
    chatStore.isAwaitingReply = false
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

  chatStore.bootstrapConversation()

  try {
    if (!chatStore.sessionId) {
      await chatStore.createSession()
    }
  } catch (error) {
    console.log('Session will be created on first message')
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
