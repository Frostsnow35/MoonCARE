<template>
  <div class="home-page">
    <div class="max-w-lg mx-auto pb-16">
      <!-- Header -->
      <div class="px-4 pt-4 pb-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-lg font-bold text-gray-800">情绪追踪</span>
            <span class="px-2 py-0.5 text-xs bg-pink-100 text-pink-600 rounded-full">发现</span>
          </div>
          <div class="flex items-center gap-3">
            <button class="text-gray-500">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
              </svg>
            </button>
            <button class="text-gray-500">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
            </button>
          </div>
        </div>
        <p class="text-xs text-gray-500 mt-1">{{ greetingMessage }}</p>
      </div>

      <!-- Status Cards -->
      <div class="px-4 mt-3 space-y-3">
        <!-- Phase & PMS Risk -->
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-3">
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <span class="text-xl">{{ phaseEmoji }}</span>
              <span class="font-medium text-gray-700 text-sm">{{ phaseName }}</span>
              <span v-if="phasePredictionText" class="text-xs text-pink-500">{{ phasePredictionText }}</span>
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
            <span class="text-xl">{{ moodEmoji }}</span>
            <div class="flex-1">
              <div class="text-xs text-gray-500">今日情绪</div>
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

      <!-- Healing Activities (Collapsible) -->
      <div v-if="filteredRecommendations.length > 0" class="px-4 mt-4">
        <div
          class="flex items-center justify-between mb-2"
          @click="showActivities = !showActivities"
        >
          <h3 class="text-sm font-medium text-gray-700 flex items-center gap-1">
            <span>🌊</span>
            <span>疗愈活动</span>
          </h3>
          <span class="text-gray-400 text-xs">{{ showActivities ? '收起' : '展开' }}</span>
        </div>

        <div v-if="showActivities" class="grid grid-cols-2 gap-2 pb-2">
          <button
            v-for="rec in filteredRecommendations"
            :key="rec"
            class="flex flex-col items-center gap-1 p-3 rounded-xl bg-white border border-gray-100 active:bg-gray-50"
            @click="handleRecommendation(rec)"
          >
            <span class="text-xl">{{ getRecommendationEmoji(rec) }}</span>
            <span class="text-xs text-gray-600 whitespace-nowrap">{{ getRecommendationName(rec) }}</span>
          </button>
        </div>
      </div>

      <!-- Emotion Baby Chat Entry (Prominent) -->
      <div class="px-4 mt-4">
        <router-link
          to="/chat"
          class="flex items-center gap-3 p-4 w-full bg-gradient-to-r from-pink-200 to-pink-100 rounded-2xl border border-pink-300 active:scale-[0.98] transition-transform"
        >
          <span class="text-5xl">
            <svg width="56" height="56" viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg">
              <ellipse cx="28" cy="30" rx="22" ry="18" fill="#FFD6E0"/>
              <ellipse cx="28" cy="30" rx="18" ry="14" fill="#FFB3C1"/>
              <circle cx="21" cy="27" r="3.5" fill="#5D4E60"/>
              <circle cx="35" cy="27" r="3.5" fill="#5D4E60"/>
              <circle cx="22" cy="26" r="1.4" fill="white"/>
              <circle cx="36" cy="26" r="1.4" fill="white"/>
              <ellipse cx="28" cy="33" rx="3" ry="1.8" fill="#FF6B8A"/>
              <ellipse cx="16" cy="20" rx="5" ry="3.5" fill="#FFD6E0" opacity="0.8"/>
              <ellipse cx="40" cy="20" rx="5" ry="3.5" fill="#FFD6E0" opacity="0.8"/>
            </svg>
          </span>
          <div class="flex-1">
            <div class="font-semibold text-gray-800">情绪宝宝</div>
            <div class="text-xs text-gray-500">点击和我聊聊~</div>
          </div>
          <span class="text-pink-400">→</span>
        </router-link>
      </div>

      <!-- 经前状态了解 Card -->
      <div class="px-4 mt-4">
        <div
          class="flex items-center gap-3 p-4 w-full bg-gradient-to-r from-pink-100 to-pink-50 rounded-2xl border border-pink-200 active:scale-[0.98] transition-transform cursor-pointer"
          @click="startInterview"
        >
          <span class="text-4xl">🩷</span>
          <div class="flex-1">
            <div class="font-semibold text-gray-800">经前状态聊聊</div>
            <div class="text-xs text-gray-500">了解你的情绪状态</div>
          </div>
          <span class="text-pink-400">→</span>
        </div>
      </div>

    </div>

    <!-- Bottom Navigation -->
    <BottomNav />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useHealthStore } from '../stores/health'
import { useChatStore } from '../stores/chat'
import { useRouter } from 'vue-router'
import { interviewAPI } from '../api'
import BottomNav from '../components/BottomNav.vue'

const router = useRouter()
const healthStore = useHealthStore()
const chatStore = useChatStore()

const showActivities = ref(true)

const currentDate = computed(() => {
  return new Date().toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    weekday: 'short'
  })
})

// Emotional greeting based on mood
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
const recommendations = computed(() => healthStore.recommendations)
const cyclePrediction = computed(() => healthStore.cyclePrediction)

const moodEmoji = computed(() => {
  if (moodLevel.value >= 8) return '😊'
  if (moodLevel.value >= 6) return '🙂'
  if (moodLevel.value >= 4) return '😐'
  if (moodLevel.value >= 2) return '😔'
  return '😢'
})

const filteredRecommendations = computed(() => {
  return healthStore.recommendations.filter(rec => rec !== 'hot_compress')
})

const phasePredictionText = computed(() => {
  if (!cyclePrediction.value) return ''
  if (cyclePrediction.value.current_phase === 'luteal') {
    if (cyclePrediction.value.predicted_start) {
      const date = new Date(cyclePrediction.value.predicted_start)
      return `${date.getMonth() + 1}月${date.getDate()}日可能来潮`
    }
    return `${cyclePrediction.value.phase_days_remaining}天后可能来潮`
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

function getRecommendationEmoji(rec) {
  const emojis = {
    breathing_exercise: '🌬️',
    music_therapy: '🎵',
    walking: '🚶'
  }
  return emojis[rec] || '✨'
}

function getRecommendationName(rec) {
  const names = {
    breathing_exercise: '呼吸引导',
    music_therapy: '音乐疗愈',
    walking: '散步'
  }
  return names[rec] || rec
}

function handleRecommendation(rec) {
  if (rec === 'breathing_exercise') {
    router.push('/breathing')
  } else if (rec === 'music_therapy') {
    router.push('/music')
  }
}

function getPhaseName(phase) {
  const names = {
    follicular: '卵泡期',
    ovulation: '排卵期',
    luteal: '黄体期',
    menstrual: '经期'
  }
  return names[phase] || phase
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

async function startInterview() {
  try {
    const result = await interviewAPI.start(1)
    chatStore.addAssistantMessage(result.reply, [])
    chatStore.setInterviewMode(true, result.phase)
    router.push('/chat')
  } catch (error) {
    console.error('Failed to start interview:', error)
  }
}

onMounted(async () => {
  await healthStore.fetchEmotionState()
  await healthStore.fetchPhaseInfo()
  await healthStore.fetchCyclePrediction()
  await healthStore.fetchRecommendations()
})
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  background: #f9fafb;
}
</style>
