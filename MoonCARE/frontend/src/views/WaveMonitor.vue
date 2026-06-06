<template>
  <div class="app-page">
    <div class="page-content page-stack">
      <header class="page-card-soft p-5">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="section-label">波形与生理数据</p>
            <h1 class="page-title mt-3">实时状态监测</h1>
            <p class="page-subtitle">
              这里用于承接设备上传的波形和生理指标。在没有真实数据前，会明确标出空状态或演示状态。
            </p>
          </div>
          <div class="flex items-center gap-2">
            <span class="rounded-full bg-white/80 px-3 py-1 text-xs text-slate-500 shadow-sm">{{ dataPoints }} 点</span>
            <button
              type="button"
              class="secondary-button min-h-10 px-3 text-xs"
              :class="isPaused ? 'border-green-200 text-green-700' : 'border-amber-200 text-amber-700'"
              @click="togglePause"
            >
              {{ isPaused ? '继续' : '暂停' }}
            </button>
            <button type="button" class="ghost-button min-h-10 px-3 text-xs" @click="clearData">
              清空
            </button>
          </div>
        </div>
      </header>

      <section
        v-if="statusBannerText"
        class="rounded-2xl border px-4 py-4"
        :class="waveStatus === 'error' ? 'border-amber-100 bg-amber-50 text-amber-700' : 'border-gray-100 bg-gray-50 text-gray-600'"
      >
        <div class="text-sm font-semibold">{{ statusBannerTitle }}</div>
        <div class="mt-1 text-sm leading-6">{{ statusBannerText }}</div>
      </section>

      <section class="page-card p-4">
        <div class="mb-3 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-xl">💙</span>
            <span class="text-sm font-semibold text-slate-700">HRV 心率变异性</span>
          </div>
          <div class="text-right">
            <span class="text-2xl font-bold text-blue-600">{{ currentHrv.toFixed(1) }}</span>
            <span class="ml-1 text-xs text-slate-400">ms</span>
          </div>
        </div>
        <canvas ref="hrvCanvas" class="w-full" height="100"></canvas>
        <div class="mt-1 flex justify-between text-xs text-slate-400">
          <span>时间 →</span>
          <span>最新 {{ formatTime(lastUpdate) }}</span>
        </div>
      </section>

      <section class="page-card p-4">
        <div class="mb-3 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-xl">🌡️</span>
            <span class="text-sm font-semibold text-slate-700">皮肤温度</span>
          </div>
          <div class="text-right">
            <span class="text-2xl font-bold text-pink-600">{{ currentTemp.toFixed(1) }}</span>
            <span class="ml-1 text-xs text-slate-400">°C</span>
          </div>
        </div>
        <canvas ref="tempCanvas" class="w-full" height="100"></canvas>
        <div class="mt-1 flex justify-between text-xs text-slate-400">
          <span>时间 →</span>
          <span>最新 {{ formatTime(lastUpdate) }}</span>
        </div>
      </section>

      <section class="page-card p-4">
        <div class="mb-3 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-xl">🧠</span>
            <span class="text-sm font-semibold text-slate-700">脑血流量</span>
          </div>
          <div class="text-right">
            <span class="text-2xl font-bold text-purple-600">{{ currentCbf.toFixed(1) }}</span>
            <span class="ml-1 text-xs text-slate-400">mL/100g/min</span>
          </div>
        </div>
        <canvas ref="cbfCanvas" class="w-full" height="100"></canvas>
        <div class="mt-1 flex justify-between text-xs text-slate-400">
          <span>时间 →</span>
          <span>最新 {{ formatTime(lastUpdate) }}</span>
        </div>
      </section>

      <section class="page-card p-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-xl">🏃</span>
            <span class="text-sm font-semibold text-slate-700">运动状态</span>
          </div>
          <span class="rounded-full px-3 py-1 text-xs font-semibold" :class="motionClass">
            {{ motion }}
          </span>
        </div>
      </section>

      <section class="page-card p-4">
        <div class="mb-4 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-xl">{{ emotionEmoji }}</span>
            <span class="text-sm font-semibold text-slate-700">情绪状态</span>
          </div>
          <span class="rounded-full px-3 py-1 text-xs font-semibold" :class="dominantEmotionClass">
            {{ dominantEmotion }}
          </span>
        </div>

        <div class="space-y-3">
          <div class="flex items-center gap-2">
            <span class="w-12 text-xs text-slate-500">低落</span>
            <div class="h-2 flex-1 overflow-hidden rounded-full bg-gray-100">
              <div class="h-full rounded-full bg-purple-400 transition-all duration-300" :style="{ width: `${emotionData.depression}%` }"></div>
            </div>
            <span class="w-8 text-right text-xs text-slate-500">{{ emotionData.depression.toFixed(0) }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-12 text-xs text-slate-500">焦虑</span>
            <div class="h-2 flex-1 overflow-hidden rounded-full bg-gray-100">
              <div class="h-full rounded-full bg-orange-400 transition-all duration-300" :style="{ width: `${emotionData.anxiety}%` }"></div>
            </div>
            <span class="w-8 text-right text-xs text-slate-500">{{ emotionData.anxiety.toFixed(0) }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-12 text-xs text-slate-500">烦躁</span>
            <div class="h-2 flex-1 overflow-hidden rounded-full bg-gray-100">
              <div class="h-full rounded-full bg-red-400 transition-all duration-300" :style="{ width: `${emotionData.anger}%` }"></div>
            </div>
            <span class="w-8 text-right text-xs text-slate-500">{{ emotionData.anger.toFixed(0) }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-12 text-xs text-slate-500">平静</span>
            <div class="h-2 flex-1 overflow-hidden rounded-full bg-gray-100">
              <div class="h-full rounded-full bg-green-400 transition-all duration-300" :style="{ width: `${emotionData.calm}%` }"></div>
            </div>
            <span class="w-8 text-right text-xs text-slate-500">{{ emotionData.calm.toFixed(0) }}</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { biometricAPI, emotionAPI } from '../api'

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
    低落: 'bg-purple-100 text-purple-700',
    焦虑: 'bg-orange-100 text-orange-700',
    烦躁: 'bg-red-100 text-red-700',
    平静: 'bg-green-100 text-green-700',
    未知: 'bg-gray-100 text-gray-700'
  }
  return classes[dominantEmotion.value] || 'bg-gray-100 text-gray-700'
})

const emotionEmoji = computed(() => {
  const emojis = {
    低落: '😔',
    焦虑: '😣',
    烦躁: '😤',
    平静: '😌',
    未知: '❔'
  }
  return emojis[dominantEmotion.value] || '❔'
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
    return '请检查后端服务、网络连接或设备上传链路。未拿到真实数据前，这里不会再生成随机波形。'
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
  for (let i = 0; i < 5; i += 1) {
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
  for (let i = 0; i < data.length; i += 1) {
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
  for (let i = 0; i < data.length; i += 1) {
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
  if (hrvCanvas.value) hrvCanvas.value.width = hrvCanvas.value.offsetWidth
  if (tempCanvas.value) tempCanvas.value.width = tempCanvas.value.offsetWidth
  if (cbfCanvas.value) cbfCanvas.value.width = cbfCanvas.value.offsetWidth
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
  if (pollInterval) clearInterval(pollInterval)
  if (animationFrame) cancelAnimationFrame(animationFrame)
})
</script>
