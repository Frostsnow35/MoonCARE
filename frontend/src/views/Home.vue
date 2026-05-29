<template>
  <div class="home-page">
    <div class="max-w-lg mx-auto pb-16">
      <!-- Header -->
      <div class="px-4 pt-4 pb-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-lg font-bold text-gray-800">女性情绪周期</span>
            <span class="px-2 py-0.5 text-xs bg-pink-100 text-pink-600 rounded-full">发现</span>
          </div>
          <div class="flex items-center gap-3">
            <button @click="goToNotifications" class="text-gray-500 hover:text-pink-500 transition-colors">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
              </svg>
            </button>
            <button @click="goToProfile" class="text-gray-500 hover:text-pink-500 transition-colors">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- AI Chat Entry - Main Focus (Visual Design) -->
      <div class="px-4 mt-6">
        <!-- Avatar Circle -->
        <div class="flex justify-center mb-3">
          <div class="relative">
            <div class="w-28 h-28 rounded-full bg-gradient-to-br from-pink-300 to-pink-400 flex items-center justify-center shadow-lg">
              <svg width="80" height="80" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
                <ellipse cx="40" cy="45" rx="30" ry="25" fill="#FFD6E0"/>
                <ellipse cx="40" cy="45" rx="25" ry="20" fill="#FFB3C1"/>
                <circle cx="30" cy="40" r="5" fill="#5D4E60"/>
                <circle cx="50" cy="40" r="5" fill="#5D4E60"/>
                <circle cx="31.5" cy="38.5" r="2" fill="white"/>
                <circle cx="51.5" cy="38.5" r="2" fill="white"/>
                <ellipse cx="40" cy="50" rx="4" ry="2.5" fill="#FF6B8A"/>
                <ellipse cx="25" cy="30" rx="7" ry="5" fill="#FFD6E0" opacity="0.8"/>
                <ellipse cx="55" cy="30" rx="7" ry="5" fill="#FFD6E0" opacity="0.8"/>
              </svg>
            </div>
            <!-- Online indicator -->
            <div class="absolute bottom-1 right-1 w-4 h-4 bg-green-400 rounded-full border-2 border-white"></div>
          </div>
        </div>

        <!-- Greeting -->
        <div class="text-center mb-2">
          <h2 class="text-base font-semibold text-gray-800">{{ greetingMessage }}</h2>
          <p class="text-xs text-gray-500">{{ currentDate }}</p>
        </div>

        <!-- Subtitle -->
        <div class="text-center mb-6">
          <p class="text-sm text-pink-500">发现你的情绪空间</p>
        </div>

        <!-- Chat Button -->
        <router-link
          to="/chat"
          class="flex items-center justify-center gap-2 w-full py-3 bg-gradient-to-r from-pink-400 to-pink-500 rounded-full shadow-lg active:scale-[0.98] transition-transform"
        >
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
          </svg>
          <span class="text-white font-medium">和情绪宝宝聊聊</span>
        </router-link>
      </div>

      <!-- Quick Actions -->
      <div class="px-4 mt-6">
        <div class="bg-gradient-to-r from-purple-100 to-pink-100 rounded-2xl p-4">
          <div class="grid grid-cols-3 gap-3">
            <router-link
              to="/diary"
              class="flex flex-col items-center gap-1 p-3 bg-white rounded-xl border border-gray-100 active:scale-95 transition-transform"
            >
              <span class="text-2xl">📝</span>
              <span class="text-xs font-semibold text-gray-700">今日日记</span>
            </router-link>
            <router-link
              to="/music"
              class="flex flex-col items-center gap-1 p-3 bg-white rounded-xl border border-gray-100 active:scale-95 transition-transform"
            >
              <span class="text-2xl">🎵</span>
              <span class="text-xs font-semibold text-gray-700">音乐疗愈</span>
            </router-link>
            <router-link
              to="/breathing"
              class="flex flex-col items-center gap-1 p-3 bg-white rounded-xl border border-gray-100 active:scale-95 transition-transform"
            >
              <span class="text-2xl">🌬️</span>
              <span class="text-xs font-semibold text-gray-700">呼吸引导</span>
            </router-link>
          </div>
        </div>
      </div>

      <!-- Status Cards -->
      <div class="px-4 mt-6 space-y-3">
        <!-- Phase & PMS Risk -->
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-3">
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <span class="text-xl">{{ phaseEmoji }}</span>
              <span class="font-medium text-gray-700 text-sm">{{ phaseName }}</span>
              <span class="text-xs text-pink-500">{{ phasePredictionText }}</span>
            </div>
            <span
              class="text-xs font-medium px-2 py-0.5 rounded-full"
              :class="riskClass"
            >
              {{ riskLabel }}
            </span>
          </div>
          <div class="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-500"
              :class="riskBarClass"
              :style="{ width: `${pmsRisk * 100}%` }"
            ></div>
          </div>
        </div>

        <!-- Mood Level -->
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-3">
          <div class="flex items-center gap-3">
            <span class="text-xl">☀️</span>
            <div class="flex-1">
              <div class="font-medium text-gray-700 text-sm">今日情绪</div>
              <div class="flex items-center gap-1">
                <span class="font-semibold text-gray-800">{{ moodLevel.toFixed(1) }}</span>
                <span class="text-xs text-gray-400">/ 10</span>
              </div>
            </div>
            <div class="text-xs text-gray-500">
              {{ moodDescription }}
            </div>
          </div>
        </div>
      </div>

      <!-- 波动曲线 & 经前状态了解 -->
      <div class="px-4 mt-4 grid grid-cols-2 gap-3">
        <router-link
          to="/wave"
          class="flex flex-col items-center justify-center gap-1 p-3 bg-white rounded-xl border border-gray-100 active:scale-95 transition-transform"
        >
          <span class="text-2xl">📈</span>
          <span class="text-xs text-gray-700">波动曲线</span>
        </router-link>
        <div
          @click="startStateChat"
          class="flex flex-col items-center justify-center gap-1 p-3 bg-white rounded-xl border border-gray-100 active:scale-95 transition-transform cursor-pointer"
        >
          <span class="text-2xl">🩷</span>
          <span class="text-xs text-gray-700">经前状态聊聊</span>
        </div>
      </div>

    </div>

    <!-- Bottom Navigation -->
    <BottomNav />
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useHealthStore } from '../stores/health'
import { useChatStore } from '../stores/chat'
import { useRouter } from 'vue-router'
import BottomNav from '../components/BottomNav.vue'

const router = useRouter()
const healthStore = useHealthStore()
const chatStore = useChatStore()

const currentDate = computed(() => {
  return new Date().toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    weekday: 'short'
  })
})

const greetingMessage = computed(() => {
  const level = moodLevel.value
  const risk = healthStore.riskLevel
  const phase = cyclePrediction.value?.current_phase

  if (level >= 8) {
    return '今天心情很棒，继续保持 💖'
  }
  if (level >= 6) {
    return '今天感觉不错哦 ✨'
  }
  if (level >= 4) {
    return '今天感觉怎么样？'
  }
  if (risk === 'high' || risk === 'critical') {
    return '今天有点艰难，我在这里陪你 💙'
  }
  if (phase === 'luteal' || phase === 'menstrual') {
    return '特殊时期，对自己好一点 🌸'
  }
  return '今天感觉怎么样？'
})

const phaseEmoji = computed(() => healthStore.phaseEmoji)
const phaseName = computed(() => healthStore.phaseName)
const pmsRisk = computed(() => healthStore.pmsRisk)
const moodLevel = computed(() => healthStore.moodLevel)
const cyclePrediction = computed(() => healthStore.cyclePrediction)

const moodEmoji = computed(() => {
  if (moodLevel.value >= 8) return '😊'
  if (moodLevel.value >= 6) return '🙂'
  if (moodLevel.value >= 4) return '😐'
  if (moodLevel.value >= 2) return '😔'
  return '😢'
})

const phasePredictionText = computed(() => {
  // Use healthStore.currentPhase which is set by emotion API
  if (healthStore.currentPhase !== 'luteal') return ''

  const pred = cyclePrediction.value
  if (!pred) return ''

  if (pred.predicted_start) {
    const date = new Date(pred.predicted_start)
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    // If predicted date is in the future, use it
    if (date >= today) {
      return `${date.getMonth() + 1}月${date.getDate()}日可能来潮`
    }
  }
  // Fallback: calculate from phase_days_remaining
  if (pred.phase_days_remaining !== undefined) {
    const futureDate = new Date()
    futureDate.setDate(futureDate.getDate() + pred.phase_days_remaining)
    return `${futureDate.getMonth() + 1}月${futureDate.getDate()}日可能来潮`
  }
  return ''
})

const riskLabel = computed(() => {
  const labels = {
    critical: '危险',
    high: '高风险',
    medium: '中等',
    low: '低风险'
  }
  return labels[healthStore.riskLevel] || '未知'
})

const riskClass = computed(() => {
  const classes = {
    critical: 'bg-red-100 text-red-700',
    high: 'bg-orange-100 text-orange-700',
    medium: 'bg-yellow-100 text-yellow-700',
    low: 'bg-green-100 text-green-700'
  }
  return classes[healthStore.riskLevel] || 'bg-gray-100 text-gray-700'
})

const riskBarClass = computed(() => {
  const classes = {
    critical: 'bg-red-500',
    high: 'bg-orange-500',
    medium: 'bg-yellow-500',
    low: 'bg-green-500'
  }
  return classes[healthStore.riskLevel] || 'bg-gray-500'
})

const moodDescription = computed(() => {
  if (moodLevel.value >= 8) return '非常愉悦'
  if (moodLevel.value >= 6) return '心情不错'
  if (moodLevel.value >= 4) return '情绪一般'
  if (moodLevel.value >= 2) return '情绪低落'
  return '需要关注'
})

onMounted(async () => {
  await healthStore.fetchEmotionState()
  await healthStore.fetchPhaseInfo()
  await healthStore.fetchCyclePrediction()
  await healthStore.fetchRecommendations()
})

function goToNotifications() {
  router.push('/profile/notifications')
}

function goToProfile() {
  router.push('/profile')
}

function startStateChat() {
  chatStore.endInterview()
  router.push('/chat')
}
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  background: #f9fafb;
}
</style>
