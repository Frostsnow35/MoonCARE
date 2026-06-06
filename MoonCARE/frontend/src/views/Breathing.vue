<template>
  <div class="app-page">
    <div class="page-content page-stack">
      <header class="page-card-soft p-5 text-center">
        <p class="section-label">呼吸练习</p>
        <h1 class="page-title mt-3">跟着节奏慢慢呼吸</h1>
        <p class="page-subtitle">
          这是一个轻量干预工具，适合在紧张、烦躁或需要把注意力拉回身体时使用。
        </p>
      </header>

      <section class="page-card p-5">
        <div class="flex flex-col items-center justify-center py-4">
          <div class="relative">
            <div
              v-if="isActive"
              class="absolute inset-0 h-56 w-56 rounded-full bg-sky-300 opacity-20 blur-xl animate-pulse"
            ></div>

            <div
              class="flex h-56 w-56 items-center justify-center rounded-full border-4 transition-all duration-1000"
              :class="breathingPhaseClass"
            >
              <div
                class="flex h-40 w-40 flex-col items-center justify-center rounded-full transition-colors duration-500"
                :class="isActive ? 'bg-sky-50' : 'bg-gray-50'"
              >
                <span class="text-3xl">{{ phaseEmoji }}</span>
                <span class="mt-2 text-base font-semibold" :class="isActive ? 'text-sky-700' : 'text-gray-600'">
                  {{ phaseText }}
                </span>
                <span v-if="isActive" class="mt-1 text-xs text-sky-500">
                  {{ countdown }} 秒
                </span>
              </div>
            </div>

            <div class="absolute -bottom-6 left-1/2 flex -translate-x-1/2 gap-2">
              <div
                v-for="i in 3"
                :key="i"
                class="h-2 w-2 rounded-full transition-all duration-300"
                :class="phaseIndex >= i ? 'scale-110 bg-sky-500' : 'bg-gray-300'"
              ></div>
            </div>
          </div>
        </div>

        <div v-if="isActive" class="mt-6 text-center text-sm text-slate-500">
          <p>已完成 {{ completedCycles }} 个循环</p>
          <p class="mt-1">剩余时间：{{ remainingTime }} 秒</p>
        </div>
      </section>

      <section v-if="!isActive" class="page-card p-5">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h2 class="text-base font-semibold text-slate-800">选择练习时长</h2>
            <p class="mt-1 text-sm text-slate-500">先从一个轻量时长开始，完成后再决定要不要继续。</p>
          </div>
        </div>

        <div class="mt-4 grid grid-cols-3 gap-3">
          <button
            v-for="duration in durationOptions"
            :key="duration.minutes"
            type="button"
            class="rounded-2xl border-2 p-3 text-center transition-colors"
            :class="selectedDuration.minutes === duration.minutes ? 'border-sky-500 bg-sky-50' : 'border-gray-100 hover:border-gray-200'"
            @click="selectedDuration = duration"
          >
            <div class="text-2xl">{{ duration.emoji }}</div>
            <div class="mt-2 text-sm font-semibold text-slate-800">{{ duration.minutes }} 分钟</div>
            <div class="mt-1 text-xs text-slate-500">{{ duration.description }}</div>
          </button>
        </div>
      </section>

      <section class="page-card p-5">
        <div class="flex justify-center gap-3">
          <button
            v-if="!isActive"
            type="button"
            class="primary-button min-w-[10rem]"
            @click="startBreathing"
          >
            开始练习
          </button>
          <button
            v-else
            type="button"
            class="secondary-button min-w-[10rem] border-red-200 text-red-600"
            @click="stopBreathing"
          >
            停止
          </button>
        </div>
      </section>

      <section class="page-card p-5">
        <h2 class="text-base font-semibold text-slate-800">练习提示</h2>
        <ul class="mt-3 space-y-2 text-sm leading-6 text-slate-500">
          <li>找一个舒服的姿势坐着或躺着。</li>
          <li>用鼻子吸气，用嘴巴慢慢呼气。</li>
          <li>如果感到头晕或胸闷，先暂停，恢复自然呼吸。</li>
          <li>它可以帮助你缓一缓，但不替代专业帮助。</li>
        </ul>
      </section>

      <section
        v-if="showIntervention"
        class="page-card border border-sky-100 p-5 shadow-lg"
      >
        <div class="flex items-start gap-3">
          <span class="text-2xl">🌿</span>
          <div class="min-w-0 flex-1">
            <h2 class="text-base font-semibold text-slate-800">呼吸练习建议</h2>
            <p class="mt-2 text-sm leading-6 text-slate-500">
              如果你现在有些紧绷，可以先做一轮 3 分钟练习，让身体慢慢把节奏拉回来。
            </p>
            <button type="button" class="primary-button mt-4" @click="startBreathing">
              立刻开始
            </button>
          </div>
          <button type="button" class="icon-button shadow-none" @click="showIntervention = false">
            ×
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

const isActive = ref(false)
const phase = ref('idle')
const phaseIndex = ref(0)
const countdown = ref(4)
const completedCycles = ref(0)
const totalDuration = ref(180)
const remainingTime = ref(180)
const showIntervention = ref(false)

let timer = null
let phaseTimer = null

const selectedDuration = ref({
  minutes: 3,
  seconds: 180,
  emoji: '🌤️',
  description: '轻度紧绷'
})

const durationOptions = [
  { minutes: 3, seconds: 180, emoji: '🌤️', description: '轻度紧绷' },
  { minutes: 6, seconds: 360, emoji: '🌥️', description: '中度焦虑' },
  { minutes: 9, seconds: 540, emoji: '🌙', description: '高压时段' }
]

const phaseEmoji = computed(() => ({
  idle: '🫁',
  inhale: '吸气',
  hold: '停留',
  exhale: '呼气'
}[phase.value] || '🫁'))

const phaseText = computed(() => ({
  idle: '准备开始',
  inhale: '慢慢吸气',
  hold: '停留一下',
  exhale: '慢慢呼气'
}[phase.value] || '准备开始'))

const breathingPhaseClass = computed(() => {
  if (!isActive.value) return 'border-sky-100 bg-sky-50'
  if (phase.value === 'inhale') return 'scale-110 border-sky-400 bg-sky-200'
  if (phase.value === 'hold') return 'border-sky-300 bg-sky-100'
  if (phase.value === 'exhale') return 'scale-90 border-sky-200 bg-sky-50'
  return 'border-sky-100 bg-sky-50'
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
    remainingTime.value -= 1
    if (remainingTime.value <= 0) {
      stopBreathing()
    }
  }, 1000)
}

function runBreathingCycle() {
  if (!isActive.value) return

  phase.value = 'inhale'
  phaseIndex.value = 1
  countdown.value = 4

  phaseTimer = setTimeout(() => {
    if (!isActive.value) return

    phase.value = 'hold'
    phaseIndex.value = 2
    countdown.value = 4

    phaseTimer = setTimeout(() => {
      if (!isActive.value) return

      phase.value = 'exhale'
      phaseIndex.value = 3
      countdown.value = 4

      phaseTimer = setTimeout(() => {
        if (!isActive.value) return
        completedCycles.value += 1
        phaseIndex.value = 0
        runBreathingCycle()
      }, 4000)
    }, 4000)
  }, 4000)
}

onMounted(() => {
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
