<template>
  <div class="wave-page">
    <div class="max-w-lg mx-auto pb-16 px-4">
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

      <div
        v-if="statusBannerText"
        class="mb-3 rounded-xl border px-3 py-3"
        :class="waveStatus === 'error' ? 'bg-amber-50 border-amber-100 text-amber-700' : 'bg-gray-50 border-gray-100 text-gray-600'"
      >
        <div class="text-sm font-medium">{{ statusBannerTitle }}</div>
        <div class="mt-1 text-xs leading-relaxed">{{ statusBannerText }}</div>
      </div>

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

        <div class="space-y-1.5">
          <div class="flex items-center gap-1.5">
            <span class="text-xs text-gray-600 w-10">😢</span>
            <div class="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                class="h-full bg-purple-400 rounded-full transition-all duration-300"
                :style="{ width: `${emotionData.depression}%` }"
              ></div>
            </div>
            <span class="text-xs text-gray-500 w-8 text-right">{{ emotionData.depression.toFixed(0) }}</span>
          </div>
          <div class="flex items-center gap-1.5">
            <span class="text-xs text-gray-600 w-10">😰</span>
            <div class="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                class="h-full bg-orange-400 rounded-full transition-all duration-300"
                :style="{ width: `${emotionData.anxiety}%` }"
              ></div>
            </div>
            <span class="text-xs text-gray-500 w-8 text-right">{{ emotionData.anxiety.toFixed(0) }}</span>
          </div>
          <div class="flex items-center gap-1.5">
            <span class="text-xs text-gray-600 w-10">😠</span>
            <div class="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                class="h-full bg-red-400 rounded-full transition-all duration-300"
                :style="{ width: `${emotionData.anger}%` }"
              ></div>
            </div>
            <span class="text-xs text-gray-500 w-8 text-right">{{ emotionData.anger.toFixed(0) }}</span>
          </div>
          <div class="flex items-center gap-1.5">
            <span class="text-xs text-gray-600 w-10">😌</span>
            <div class="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                class="h-full bg-green-400 rounded-full transition-all duration-300"
                :style="{ width: `${emotionData.calm}%` }"
              ></div>
            </div>
            <span class="text-xs text-gray-500 w-8 text-right">{{ emotionData.calm.toFixed(0) }}</span>
          </div>
        </div>
      </div>
    </div>

    <BottomNav />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { biometricAPI, emotionAPI } from '../api'
import BottomNav from '../components/BottomNav.vue'

const MAX_POINTS = 100
const biometricDemoEnabled = import.meta.env.VITE_ENABLE_BIOMETRIC_DEMO === 'true'

const hrvCanvas = ref(null)
const tempCanvas = ref(null)
const cbfCanvas = ref(null)
const isPaused = ref(false)
const dataPoints = ref(0)
const lastUpdate = ref(new Date())
const waveStatus = ref('loading')

const hrvData = ref([])
const tempData = ref([])
const cbfData = ref([])
const currentHrv = ref(0)
const currentTemp = ref(0)
const currentCbf = ref(0)
const motion = ref('LOW')

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
    抑郁: 'bg-purple-100 text-purple-700',
    焦虑: 'bg-orange-100 text-orange-700',
    愤怒: 'bg-red-100 text-red-700',
    平静: 'bg-green-100 text-green-700',
    未知: 'bg-gray-100 text-gray-700'
  }
  return classes[dominantEmotion.value] || 'bg-gray-100 text-gray-700'
})
const emotionEmoji = computed(() => {
  const emojis = {
    抑郁: '😢',
    焦虑: '😰',
    愤怒: '😠',
    平静: '😌',
    未知: '❓'
  }
  return emojis[dominantEmotion.value] || '❓'
})

const motionClass = computed(() => {
  const classes = {
    LOW: 'bg-green-100 text-green-700',
    MEDIUM: 'bg-yellow-100 text-yellow-700',
    HIGH: 'bg-red-100 text-red-700'
  }
  return classes[motion.value] || 'bg-gray-100 text-gray-700'
})

const statusBannerTitle = computed(() => {
  if (waveStatus.value === 'demo') return '演示数据已开启'
  if (waveStatus.value === 'error') return '暂时无法获取设备数据'
  if (waveStatus.value === 'empty') return '暂无设备数据'
  return ''
})

const statusBannerText = computed(() => {
  if (waveStatus.value === 'demo') {
    return '当前显示的是演示波形，仅用于界面联调，不代表真实硬件采集。'
  }
  if (waveStatus.value === 'error') {
    return '请检查后端服务、网络连接或设备上传链路。未拿到真实数据前，这里不会生成随机波形。'
  }
  if (waveStatus.value === 'empty') {
    return '设备尚未连接或还没有上传生理数据。接入真实数据后，这里会开始显示波形。'
  }
  return ''
})

let pollInterval = null
let animationFrame = null
let lastBiometricTimestamp = null

function formatTime(date) {
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

function resetEmotionState() {
  emotionData.value = {
    depression: 0,
    anxiety: 0,
    anger: 0,
    calm: 0,
    dominant: '未知'
  }
}

function setWaveEmptyState(nextStatus = 'empty') {
  waveStatus.value = nextStatus
  lastBiometricTimestamp = null
  hrvData.value = []
  tempData.value = []
  cbfData.value = []
  dataPoints.value = 0
  currentHrv.value = 0
  currentTemp.value = 0
  currentCbf.value = 0
  motion.value = 'LOW'
  resetEmotionState()
}

function applyDataPoint({
  hrv = 0,
  skinTemperature = 0,
  cerebralBloodFlow = 0,
  motionLabel = 'LOW',
  timestamp = null
}) {
  currentHrv.value = hrv
  currentTemp.value = skinTemperature
  currentCbf.value = cerebralBloodFlow
  motion.value = motionLabel || 'LOW'
  lastUpdate.value = timestamp ? new Date(timestamp) : new Date()

  hrvData.value.push(hrv)
  tempData.value.push(skinTemperature)
  cbfData.value.push(cerebralBloodFlow)

  if (hrvData.value.length > MAX_POINTS) hrvData.value.shift()
  if (tempData.value.length > MAX_POINTS) tempData.value.shift()
  if (cbfData.value.length > MAX_POINTS) cbfData.value.shift()

  dataPoints.value = hrvData.value.length
}

function createDemoPoint() {
  return {
    hrv: 46,
    skinTemperature: 35.8,
    cerebralBloodFlow: 52,
    motionLabel: 'LOW',
    timestamp: new Date().toISOString()
  }
}

function drawWaveform(canvas, data, color, minVal, maxVal) {
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  const width = canvas.width
  const height = canvas.height

  ctx.fillStyle = '#f9fafb'
  ctx.fillRect(0, 0, width, height)

  if (data.length < 2) return

  ctx.strokeStyle = '#e5e7eb'
  ctx.lineWidth = 1
  for (let i = 0; i < 5; i++) {
    const y = (height / 5) * i
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(width, y)
    ctx.stroke()
  }

  const dataMin = Math.min(...data)
  const dataMax = Math.max(...data)
  const padding = (dataMax - dataMin) * 0.1 || 1
  const displayMin = Math.min(minVal, dataMin - padding)
  const displayMax = Math.max(maxVal, dataMax + padding)
  const range = displayMax - displayMin || 1

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

  const gradient = ctx.createLinearGradient(0, 0, 0, height)
  gradient.addColorStop(0, `${color}40`)
  gradient.addColorStop(1, `${color}05`)

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

async function fetchEmotion(hasBiometricData = false, useDemoData = false) {
  if (isPaused.value) return
  if (!hasBiometricData && !useDemoData) {
    resetEmotionState()
    return
  }

  try {
    const response = await emotionAPI.classify()
    if (response && response.emotion) {
      emotionData.value = response.emotion
      return
    }
  } catch (error) {
    console.error('Failed to fetch emotion data:', error)
  }

  if (useDemoData) {
    emotionData.value = {
      depression: 12,
      anxiety: 18,
      anger: 8,
      calm: 62,
      dominant: '平静'
    }
    return
  }

  resetEmotionState()
}

async function fetchData() {
  if (isPaused.value) return

  try {
    const response = await biometricAPI.query({ limit: 1 })

    if (response && response.length > 0) {
      const latest = response[0]
      const latestTimestamp = latest.timestamp || null

      if (latestTimestamp && latestTimestamp === lastBiometricTimestamp) {
        return
      }

      lastBiometricTimestamp = latestTimestamp
      waveStatus.value = 'live'
      applyDataPoint({
        hrv: latest.hrv || 0,
        skinTemperature: latest.skin_temperature || 0,
        cerebralBloodFlow: latest.cerebral_blood_flow || 0,
        motionLabel: latest.motion || 'LOW',
        timestamp: latest.timestamp
      })
      fetchEmotion(true)
      return
    }

    if (biometricDemoEnabled) {
      waveStatus.value = 'demo'
      applyDataPoint(createDemoPoint())
      fetchEmotion(false, true)
      return
    }

    setWaveEmptyState('empty')
  } catch (error) {
    console.error('Failed to fetch biometric data:', error)
    if (biometricDemoEnabled) {
      waveStatus.value = 'demo'
      applyDataPoint(createDemoPoint())
      fetchEmotion(false, true)
      return
    }
    setWaveEmptyState('error')
  }
}

function togglePause() {
  isPaused.value = !isPaused.value
  if (!isPaused.value) {
    draw()
  }
}

function clearData() {
  setWaveEmptyState(biometricDemoEnabled ? 'demo' : 'empty')
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

onMounted(() => {
  resizeCanvas()
  window.addEventListener('resize', resizeCanvas)

  fetchData()
  pollInterval = setInterval(() => {
    fetchData()
  }, 1000)

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
