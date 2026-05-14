<template>
  <div class="wave-page">
    <div class="max-w-lg mx-auto pb-16 px-4">
      <!-- Header -->
      <div class="flex items-center justify-between pt-4 pb-3">
        <h1 class="text-lg font-bold text-gray-800">实时波形监测</h1>
        <div class="flex items-center gap-1.5">
          <span class="text-xs text-gray-500">{{ dataPoints }}</span>
          <button
            @click="togglePause"
            class="px-2 py-0.5 rounded-full text-xs font-medium"
            :class="isPaused ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'"
          >
            {{ isPaused ? '继续' : '暂停' }}
          </button>
          <button
            @click="clearData"
            class="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 hover:bg-gray-200"
          >
            清空
          </button>
        </div>
      </div>

      <!-- HRV Waveform -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-3 mb-3">
        <div class="flex justify-between items-center mb-1.5">
          <div class="flex items-center gap-1.5">
            <span class="text-lg">💓</span>
            <span class="font-medium text-gray-700 text-sm">HRV 心率变异性</span>
          </div>
          <div class="text-right">
            <span class="text-xl font-bold text-blue-600">{{ currentHrv.toFixed(1) }}</span>
            <span class="text-xs text-gray-500 ml-0.5">ms</span>
          </div>
        </div>
        <canvas ref="hrvCanvas" class="w-full" height="100"></canvas>
        <div class="flex justify-between text-xs text-gray-400 mt-0.5">
          <span>时间 →</span>
          <span>最新: {{ formatTime(lastUpdate) }}</span>
        </div>
      </div>

      <!-- Temperature Waveform -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-3 mb-3">
        <div class="flex justify-between items-center mb-1.5">
          <div class="flex items-center gap-1.5">
            <span class="text-lg">🌡️</span>
            <span class="font-medium text-gray-700 text-sm">皮肤温度</span>
          </div>
          <div class="text-right">
            <span class="text-xl font-bold text-pink-600">{{ currentTemp.toFixed(1) }}</span>
            <span class="text-xs text-gray-500 ml-0.5">°C</span>
          </div>
        </div>
        <canvas ref="tempCanvas" class="w-full" height="100"></canvas>
        <div class="flex justify-between text-xs text-gray-400 mt-0.5">
          <span>时间 →</span>
          <span>最新: {{ formatTime(lastUpdate) }}</span>
        </div>
      </div>

      <!-- Cerebral Blood Flow Waveform -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-3 mb-3">
        <div class="flex justify-between items-center mb-1.5">
          <div class="flex items-center gap-1.5">
            <span class="text-lg">🧠</span>
            <span class="font-medium text-gray-700 text-sm">脑血流量</span>
          </div>
          <div class="text-right">
            <span class="text-xl font-bold text-purple-600">{{ currentCbf.toFixed(1) }}</span>
            <span class="text-xs text-gray-500 ml-0.5">mL/100g/min</span>
          </div>
        </div>
        <canvas ref="cbfCanvas" class="w-full" height="100"></canvas>
        <div class="flex justify-between text-xs text-gray-400 mt-0.5">
          <span>时间 →</span>
          <span>最新: {{ formatTime(lastUpdate) }}</span>
        </div>
      </div>

      <!-- Motion Status -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-3 mb-3">
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-1.5">
            <span class="text-lg">🏃</span>
            <span class="font-medium text-gray-700 text-sm">运动状态</span>
          </div>
          <span
            class="px-2 py-0.5 rounded-full text-xs font-medium"
            :class="motionClass"
          >
            {{ motion }}
          </span>
        </div>
      </div>

      <!-- Emotion Status -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-3">
        <div class="flex justify-between items-center mb-2">
          <div class="flex items-center gap-1.5">
            <span class="text-lg">{{ emotionEmoji }}</span>
            <span class="font-medium text-gray-700 text-sm">情绪状态</span>
          </div>
          <span
            class="px-2 py-0.5 rounded-full text-xs font-medium"
            :class="dominantEmotionClass"
          >
            {{ dominantEmotion }}
          </span>
        </div>

        <!-- Emotion Bars -->
        <div class="space-y-1.5">
          <div class="flex items-center gap-1.5">
            <span class="text-xs text-gray-600 w-10">😢</span>
            <div class="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                class="h-full bg-purple-400 rounded-full transition-all duration-300"
                :style="{ width: emotionData.depression + '%' }"
              ></div>
            </div>
            <span class="text-xs text-gray-500 w-8 text-right">{{ emotionData.depression.toFixed(0) }}</span>
          </div>
          <div class="flex items-center gap-1.5">
            <span class="text-xs text-gray-600 w-10">😰</span>
            <div class="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                class="h-full bg-orange-400 rounded-full transition-all duration-300"
                :style="{ width: emotionData.anxiety + '%' }"
              ></div>
            </div>
            <span class="text-xs text-gray-500 w-8 text-right">{{ emotionData.anxiety.toFixed(0) }}</span>
          </div>
          <div class="flex items-center gap-1.5">
            <span class="text-xs text-gray-600 w-10">😠</span>
            <div class="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                class="h-full bg-red-400 rounded-full transition-all duration-300"
                :style="{ width: emotionData.anger + '%' }"
              ></div>
            </div>
            <span class="text-xs text-gray-500 w-8 text-right">{{ emotionData.anger.toFixed(0) }}</span>
          </div>
          <div class="flex items-center gap-1.5">
            <span class="text-xs text-gray-600 w-10">😌</span>
            <div class="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                class="h-full bg-green-400 rounded-full transition-all duration-300"
                :style="{ width: emotionData.calm + '%' }"
              ></div>
            </div>
            <span class="text-xs text-gray-500 w-8 text-right">{{ emotionData.calm.toFixed(0) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom Nav -->
    <BottomNav />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { biometricAPI, emotionAPI } from '../api'
import BottomNav from '../components/BottomNav.vue'

const MAX_POINTS = 100

const hrvCanvas = ref(null)
const tempCanvas = ref(null)
const cbfCanvas = ref(null)
const isPaused = ref(false)
const dataPoints = ref(0)
const lastUpdate = ref(new Date())

// Data buffers
const hrvData = ref([])
const tempData = ref([])
const cbfData = ref([])
const currentHrv = ref(0)
const currentTemp = ref(0)
const currentCbf = ref(50)
const motion = ref('LOW')

// Emotion state
const emotionData = ref({
  depression: 0,
  anxiety: 0,
  anger: 0,
  calm: 0,
  dominant: '未知'
})
const dominantEmotion = computed(() => emotionData.value.dominant)
const dominantEmotionClass = computed(() => {
  const classes = {
    '抑郁': 'bg-purple-100 text-purple-700',
    '焦虑': 'bg-orange-100 text-orange-700',
    '愤怒': 'bg-red-100 text-red-700',
    '平静': 'bg-green-100 text-green-700',
    '未知': 'bg-gray-100 text-gray-700'
  }
  return classes[dominantEmotion.value] || 'bg-gray-100 text-gray-700'
})
const emotionEmoji = computed(() => {
  const emojis = {
    '抑郁': '😢',
    '焦虑': '😰',
    '愤怒': '😠',
    '平静': '😌',
    '未知': '❓'
  }
  return emojis[dominantEmotion.value] || '❓'
})

let pollInterval = null
let animationFrame = null
let lastBiometricTimestamp = null

const motionClass = computed(() => {
  const classes = {
    'LOW': 'bg-green-100 text-green-700',
    'MEDIUM': 'bg-yellow-100 text-yellow-700',
    'HIGH': 'bg-red-100 text-red-700'
  }
  return classes[motion.value] || 'bg-gray-100 text-gray-700'
})

function formatTime(date) {
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

function drawWaveform(canvas, data, color, minVal, maxVal) {
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  const width = canvas.width
  const height = canvas.height

  // Clear canvas
  ctx.fillStyle = '#f9fafb'
  ctx.fillRect(0, 0, width, height)

  if (data.length < 2) return

  // Draw grid
  ctx.strokeStyle = '#e5e7eb'
  ctx.lineWidth = 1
  for (let i = 0; i < 5; i++) {
    const y = (height / 5) * i
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(width, y)
    ctx.stroke()
  }

  // Calculate scales
  const dataMin = Math.min(...data)
  const dataMax = Math.max(...data)
  const padding = (dataMax - dataMin) * 0.1 || 1
  const displayMin = Math.min(minVal, dataMin - padding)
  const displayMax = Math.max(maxVal, dataMax + padding)
  const range = displayMax - displayMin || 1

  // Draw waveform
  ctx.strokeStyle = color
  ctx.lineWidth = 2
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.beginPath()

  const step = width / MAX_POINTS

  for (let i = 0; i < data.length; i++) {
    const x = i * step
    const normalized = (data[i] - displayMin) / range
    const y = height - (normalized * height)

    if (i === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  }

  ctx.stroke()

  // Draw gradient fill
  const gradient = ctx.createLinearGradient(0, 0, 0, height)
  gradient.addColorStop(0, color + '40')
  gradient.addColorStop(1, color + '05')

  ctx.fillStyle = gradient
  ctx.beginPath()

  for (let i = 0; i < data.length; i++) {
    const x = i * step
    const normalized = (data[i] - displayMin) / range
    const y = height - (normalized * height)

    if (i === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  }

  ctx.lineTo((data.length - 1) * step, height)
  ctx.lineTo(0, height)
  ctx.closePath()
  ctx.fill()

  // Draw latest value indicator
  if (data.length > 0) {
    const lastX = (data.length - 1) * step
    const lastNormalized = (data[data.length - 1] - displayMin) / range
    const lastY = height - (lastNormalized * height)

    ctx.fillStyle = color
    ctx.beginPath()
    ctx.arc(lastX, lastY, 4, 0, Math.PI * 2)
    ctx.fill()
  }
}

function draw() {
  if (hrvCanvas.value && tempCanvas.value && cbfCanvas.value) {
    drawWaveform(hrvCanvas.value, hrvData.value, '#3b82f6', 0, 200)
    drawWaveform(tempCanvas.value, tempData.value, '#ec4899', 25, 40)
    drawWaveform(cbfCanvas.value, cbfData.value, '#8b5cf6', 30, 70)
  }

  if (!isPaused.value) {
    animationFrame = requestAnimationFrame(draw)
  }
}

async function fetchData() {
  if (isPaused.value) return

  try {
    const response = await biometricAPI.query({
      user_id: 1,
      limit: 1
    })

    if (response && response.length > 0) {
      // Get the latest data point
      const latest = response[0]
      const latestTimestamp = latest.timestamp || null

      if (latestTimestamp && latestTimestamp === lastBiometricTimestamp) {
        return
      }
      lastBiometricTimestamp = latestTimestamp

      currentHrv.value = latest.hrv || 0
      currentTemp.value = latest.skin_temperature || 0
      // 从API获取脑血流量，如果没有则使用模拟数据
      currentCbf.value = latest.cerebral_blood_flow || (45 + Math.random() * 15)
      motion.value = latest.motion || 'LOW'
      lastUpdate.value = new Date(latest.timestamp)

      // Add to data buffers
      hrvData.value.push(latest.hrv || 0)
      tempData.value.push(latest.skin_temperature || 0)
      cbfData.value.push(currentCbf.value)

      // Trim to max points
      if (hrvData.value.length > MAX_POINTS) {
        hrvData.value.shift()
      }
      if (tempData.value.length > MAX_POINTS) {
        tempData.value.shift()
      }
      if (cbfData.value.length > MAX_POINTS) {
        cbfData.value.shift()
      }

      dataPoints.value = hrvData.value.length

      fetchEmotion()
    } else {
      // Generate mock data for demo
      currentHrv.value = 40 + Math.random() * 40
      currentTemp.value = 34 + Math.random() * 4
      currentCbf.value = 45 + Math.random() * 15
      motion.value = Math.random() > 0.7 ? 'MEDIUM' : 'LOW'
      lastUpdate.value = new Date()

      hrvData.value.push(currentHrv.value)
      tempData.value.push(currentTemp.value)
      cbfData.value.push(currentCbf.value)

      if (hrvData.value.length > MAX_POINTS) hrvData.value.shift()
      if (tempData.value.length > MAX_POINTS) tempData.value.shift()
      if (cbfData.value.length > MAX_POINTS) cbfData.value.shift()

      dataPoints.value = hrvData.value.length

      fetchEmotion()
    }
  } catch (error) {
    console.error('Failed to fetch biometric data:', error)
    // Fallback to mock data on error
    currentHrv.value = 40 + Math.random() * 40
    currentTemp.value = 34 + Math.random() * 4
    currentCbf.value = 45 + Math.random() * 15
    motion.value = Math.random() > 0.7 ? 'MEDIUM' : 'LOW'
    lastUpdate.value = new Date()

    hrvData.value.push(currentHrv.value)
    tempData.value.push(currentTemp.value)
    cbfData.value.push(currentCbf.value)

    if (hrvData.value.length > MAX_POINTS) hrvData.value.shift()
    if (tempData.value.length > MAX_POINTS) tempData.value.shift()
    if (cbfData.value.length > MAX_POINTS) cbfData.value.shift()

    dataPoints.value = hrvData.value.length
  }
}

async function fetchEmotion() {
  if (isPaused.value) return

  try {
    const response = await emotionAPI.classify(1)
    if (response && response.emotion) {
      emotionData.value = response.emotion
    } else {
      // Generate random emotion for demo when no biometric data
      emotionData.value = {
        depression: Math.random() * 30,
        anxiety: Math.random() * 30,
        anger: Math.random() * 20,
        calm: 50 + Math.random() * 30,
        dominant: '平静'
      }
    }
  } catch (error) {
    console.error('Failed to fetch emotion data:', error)
    // Fallback mock data
    emotionData.value = {
      depression: 20,
      anxiety: 15,
      anger: 10,
      calm: 55,
      dominant: '平静'
    }
  }
}

function togglePause() {
  isPaused.value = !isPaused.value
  if (!isPaused.value) {
    draw()
  }
}

function clearData() {
  hrvData.value = []
  tempData.value = []
  cbfData.value = []
  dataPoints.value = 0
  currentHrv.value = 0
  currentTemp.value = 0
  currentCbf.value = 50
}

function resizeCanvas() {
  if (hrvCanvas.value) {
    hrvCanvas.value.width = hrvCanvas.value.offsetWidth
  }
  if (tempCanvas.value) {
    tempCanvas.value.width = tempCanvas.value.offsetWidth
  }
  if (cbfCanvas.value) {
    cbfCanvas.value.width = cbfCanvas.value.offsetWidth
  }
}

onMounted(async () => {
  resizeCanvas()
  window.addEventListener('resize', resizeCanvas)

  // Seed mock data once on first load if no data exists
  try {
    const existingData = await biometricAPI.query({ user_id: 1, limit: 1 })
    if (!existingData || existingData.length === 0) {
      await biometricAPI.seed(50)
    }
  } catch (e) {
    console.log('Seed skipped:', e)
  }

  // Start polling
  fetchData()
  pollInterval = setInterval(() => {
    fetchData()
  }, 1000)

  // Start drawing
  draw()
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCanvas)
  if (pollInterval) {
    clearInterval(pollInterval)
  }
  if (animationFrame) {
    cancelAnimationFrame(animationFrame)
  }
})
</script>

<style scoped>
.wave-page {
  min-height: 100vh;
  background: #f9fafb;
}
</style>
