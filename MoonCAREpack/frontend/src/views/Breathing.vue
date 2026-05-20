<template>
  <div class="breathing-page">
    <div class="max-w-lg mx-auto pb-16 px-4">
      <!-- Header -->
      <div class="text-center pt-4 pb-3">
        <h1 class="text-lg font-bold text-gray-800 mb-1">呼吸引导</h1>
        <p class="text-xs text-gray-500">跟随节奏练习，恢复平静</p>
      </div>

      <!-- Breathing Circle -->
      <div class="flex flex-col items-center justify-center py-6">
        <div class="relative">
          <!-- Glow Effect -->
          <div
            v-if="isActive"
            class="absolute inset-0 w-56 h-56 rounded-full bg-blue-400 opacity-20 blur-xl animate-pulse"
          ></div>

          <!-- Outer Ring -->
          <div
            class="w-56 h-56 rounded-full border-4 flex items-center justify-center transition-all duration-1000"
            :class="[breathingPhaseClass, { 'scale-100': !isActive, 'scale-110': isActive && phase === 'inhale', 'scale-100': isActive && phase === 'hold', 'scale-90': isActive && phase === 'exhale' }]"
          >
            <!-- Inner Circle -->
            <div
              class="w-40 h-40 rounded-full flex flex-col items-center justify-center transition-colors duration-500"
              :class="isActive ? 'bg-blue-100' : 'bg-gray-50'"
            >
              <span class="text-3xl mb-1">{{ phaseEmoji }}</span>
              <span class="text-base font-semibold transition-colors duration-300" :class="isActive ? 'text-blue-700' : 'text-gray-600'">
                {{ phaseText }}
              </span>
              <span v-if="isActive" class="text-xs text-blue-500 mt-1">
                {{ countdown }}秒
              </span>
            </div>
          </div>

          <!-- Phase Indicator -->
          <div class="absolute -bottom-6 left-1/2 -translate-x-1/2 flex gap-2">
            <div
              v-for="i in 3"
              :key="i"
              class="w-2 h-2 rounded-full transition-all duration-300"
              :class="phaseIndex >= i ? 'bg-blue-500 scale-110' : 'bg-gray-300'"
            ></div>
          </div>
        </div>
      </div>

      <!-- Duration Selection -->
      <div v-if="!isActive" class="bg-white rounded-xl p-4 border border-gray-100">
        <h3 class="font-medium text-gray-800 mb-3 text-center text-sm">选择训练时长</h3>
        <div class="grid grid-cols-3 gap-2">
          <button
            v-for="duration in durationOptions"
            :key="duration.minutes"
            @click="selectedDuration = duration"
            class="p-3 rounded-xl border-2 text-center transition-colors"
            :class="selectedDuration.minutes === duration.minutes
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-100 hover:border-gray-200'"
          >
            <div class="text-xl mb-0.5">{{ duration.emoji }}</div>
            <div class="font-medium text-gray-800 text-sm">{{ duration.minutes }}分钟</div>
            <div class="text-xs text-gray-500">{{ duration.description }}</div>
          </button>
        </div>
      </div>

      <!-- Controls -->
      <div class="flex justify-center gap-3 mt-4">
        <button
          v-if="!isActive"
          @click="startBreathing"
          class="px-6 py-3 bg-blue-500 text-white font-medium rounded-full hover:bg-blue-600 transition-colors shadow-lg shadow-blue-200 text-sm"
        >
          开始练习
        </button>
        <button
          v-else
          @click="stopBreathing"
          class="px-6 py-3 bg-red-100 text-red-600 font-medium rounded-full hover:bg-red-200 transition-colors text-sm"
        >
          停止
        </button>
      </div>

      <!-- Progress -->
      <div v-if="isActive" class="text-center text-xs text-gray-500 mt-3">
        <p>已完成 {{ completedCycles }} 个循环</p>
        <p>剩余时间: {{ remainingTime }}秒</p>
      </div>

      <!-- Tips -->
      <div v-if="!isActive" class="bg-blue-50 rounded-xl p-4 border border-blue-100 mt-4">
        <h3 class="font-medium text-gray-800 mb-2 flex items-center gap-1 text-sm">
          <span>💡</span>
          <span>呼吸引导小贴士</span>
        </h3>
        <ul class="text-xs text-gray-600 space-y-1">
          <li>• 选择一个舒适的姿势坐着或躺下</li>
          <li>• 用鼻子吸气，嘴巴呼气</li>
          <li>• 保持呼吸节奏平稳自然</li>
          <li>• 专注于呼吸的感觉，不要分心</li>
          <li>• 如果感到头晕，暂停并正常呼吸</li>
        </ul>
      </div>

      <!-- Intervention Card (from Agent) -->
      <div v-if="showIntervention" class="fixed bottom-20 left-4 right-4 max-w-lg mx-auto">
        <div class="bg-white rounded-xl shadow-lg border border-blue-100 p-4 animate-fadeIn">
          <div class="flex items-start gap-3">
            <span class="text-xl">🌬️</span>
            <div class="flex-1">
              <div class="font-medium text-gray-800 mb-1 text-sm">呼吸引导建议</div>
              <p class="text-xs text-gray-600 mb-2">
                检测到您可能有些紧张，建议进行一次呼吸引导练习来放松身心。
              </p>
              <button
                @click="startBreathing"
                class="px-3 py-1.5 bg-blue-500 text-white text-xs font-medium rounded-full"
              >
                开始练习
              </button>
            </div>
            <button @click="showIntervention = false" class="text-gray-400 hover:text-gray-600 text-sm">
              ✕
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom Nav -->
    <BottomNav />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import BottomNav from '../components/BottomNav.vue'

const isActive = ref(false)
const phase = ref('idle') // idle, inhale, hold, exhale
const phaseIndex = ref(0)
const countdown = ref(4)
const completedCycles = ref(0)
const totalDuration = ref(180) // seconds
const remainingTime = ref(180)
const showIntervention = ref(false)

let timer = null
let phaseTimer = null

const selectedDuration = ref({
  minutes: 3,
  seconds: 180,
  emoji: '🌱',
  description: '轻度紧张'
})

const durationOptions = [
  { minutes: 3, seconds: 180, emoji: '🌱', description: '轻度紧张' },
  { minutes: 6, seconds: 360, emoji: '🌿', description: '中度焦虑' },
  { minutes: 9, seconds: 540, emoji: '🌳', description: '高度压力' }
]

const phaseEmoji = computed(() => {
  const emojis = {
    idle: '🧘',
    inhale: '吸气',
    hold: '屏息',
    exhale: '呼气'
  }
  return emojis[phase.value] || '🧘'
})

const phaseText = computed(() => {
  const texts = {
    idle: '准备开始',
    inhale: '吸气...',
    hold: '保持...',
    exhale: '呼气...'
  }
  return texts[phase.value] || '准备开始'
})

const breathingPhaseClass = computed(() => {
  if (!isActive.value) return 'bg-blue-50'

  if (phase.value === 'inhale') {
    return 'bg-blue-200 border-blue-400'
  } else if (phase.value === 'hold') {
    return 'bg-blue-100 border-blue-300'
  } else if (phase.value === 'exhale') {
    return 'bg-blue-50 border-blue-200'
  }
  return 'bg-blue-50'
})

function startBreathing() {
  isActive.value = true
  showIntervention.value = false
  totalDuration.value = selectedDuration.value.seconds
  remainingTime.value = totalDuration.value
  completedCycles.value = 0

  startTimer()
  runBreathingCycle()
}

function stopBreathing() {
  isActive.value = false
  phase.value = 'idle'
  phaseIndex.value = 0

  if (timer) clearInterval(timer)
  if (phaseTimer) clearTimeout(phaseTimer)
}

function startTimer() {
  timer = setInterval(() => {
    remainingTime.value--

    if (remainingTime.value <= 0) {
      stopBreathing()
    }
  }, 1000)
}

function runBreathingCycle() {
  if (!isActive.value) return

  // Inhale - 4 seconds
  phase.value = 'inhale'
  phaseIndex.value = 1
  countdown.value = 4

  phaseTimer = setTimeout(() => {
    if (!isActive.value) return

    // Hold - 4 seconds
    phase.value = 'hold'
    phaseIndex.value = 2
    countdown.value = 4

    phaseTimer = setTimeout(() => {
      if (!isActive.value) return

      // Exhale - 4 seconds
      phase.value = 'exhale'
      phaseIndex.value = 3
      countdown.value = 4

      phaseTimer = setTimeout(() => {
        if (!isActive.value) return

        completedCycles.value++
        phaseIndex.value = 0

        // Continue cycle
        runBreathingCycle()
      }, 4000)
    }, 4000)
  }, 4000)
}

onMounted(() => {
  // Check if coming from intervention
  const urlParams = new URLSearchParams(window.location.search)
  if (urlParams.get('intervention') === 'true') {
    showIntervention.value = true
  }
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (phaseTimer) clearTimeout(phaseTimer)
})
</script>

<style scoped>
.breathing-page {
  min-height: 100vh;
  background: #f9fafb;
}
</style>
