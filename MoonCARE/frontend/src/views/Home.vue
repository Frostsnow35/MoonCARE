<template>
  <div class="app-page">
    <div class="page-content page-stack">
      <section class="page-card-soft overflow-hidden p-5">
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <div class="inline-flex items-center gap-2 rounded-full bg-white/85 px-3 py-1 text-xs font-medium text-rose-600">
              <span>MoonCARE</span>
              <span class="h-1 w-1 rounded-full bg-rose-300"></span>
              <span>{{ currentDate }}</span>
            </div>
            <h1 class="mt-4 text-[1.6rem] font-bold leading-tight text-slate-800">
              {{ greetingTitle }}
            </h1>
            <p class="page-subtitle max-w-[26rem]">
              {{ greetingSubtitle }}
            </p>
          </div>

          <button type="button" class="icon-button shrink-0" aria-label="打开个人中心" @click="goToProfile">
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </button>
        </div>

        <div class="mt-6 rounded-[1.4rem] bg-white/95 p-4 shadow-[0_20px_45px_rgba(236,72,153,0.14)]">
          <div class="flex items-start gap-4">
            <div class="grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-rose-400 to-pink-500 text-2xl text-white shadow-[0_16px_30px_rgba(236,72,153,0.22)]">
              💗
            </div>
            <div class="min-w-0 flex-1">
              <p class="text-sm font-semibold text-slate-800">{{ chatCtaTitle }}</p>
              <p class="mt-1 text-sm leading-6 text-slate-500">
                聊天会继续承接你的情绪、身体感受和周期变化，也会在需要时给出轻量照护建议，仅供参考。
              </p>
            </div>
          </div>

          <div class="mt-4 flex flex-col gap-2 sm:flex-row">
            <button type="button" class="primary-button flex-1" @click="openChat">
              {{ chatCtaLabel }}
            </button>
            <router-link to="/diary" class="secondary-button flex flex-1 items-center justify-center">
              先写一则日记
            </router-link>
          </div>
        </div>
      </section>

      <section class="page-card p-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="section-label">周期摘要</p>
            <h2 class="mt-2 text-base font-semibold text-slate-800">
              {{ phaseEmoji }} {{ phaseName }}
            </h2>
            <p class="mt-1 text-sm leading-6 text-slate-500">
              {{ cycleSummaryText }}
            </p>
          </div>
          <span class="rounded-full px-3 py-1 text-xs font-semibold" :class="riskClass">
            {{ riskLabel }}
          </span>
        </div>

        <div class="mt-4 grid grid-cols-2 gap-3">
          <div class="rounded-2xl bg-rose-50 px-3 py-3">
            <div class="text-xs text-slate-500">经前关注度</div>
            <div class="mt-2 text-lg font-semibold text-rose-600">
              {{ Math.round(pmsRisk * 100) }}%
            </div>
            <div class="mt-1 text-xs text-slate-500">{{ riskHintText }}</div>
          </div>
          <div class="rounded-2xl bg-slate-50 px-3 py-3">
            <div class="text-xs text-slate-500">下一次月经</div>
            <div class="mt-2 text-sm font-semibold text-slate-800">
              {{ phasePredictionText || '还需要更多记录' }}
            </div>
            <div class="mt-1 text-xs text-slate-500">记录越完整，预测越稳定。</div>
          </div>
        </div>
      </section>

      <section class="page-card p-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="section-label">今日状态</p>
            <h2 class="mt-2 text-base font-semibold text-slate-800">
              情绪 {{ moodLevel.toFixed(1) }} / 10
            </h2>
            <p class="mt-1 text-sm leading-6 text-slate-500">
              {{ moodDescription }}
            </p>
          </div>
          <div class="rounded-2xl bg-amber-50 px-3 py-2 text-right">
            <div class="text-xs text-slate-500">陪伴提示</div>
            <div class="mt-1 text-sm font-medium text-amber-700">{{ supportFocusText }}</div>
          </div>
        </div>

        <div class="mt-4 rounded-2xl bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-600">
          {{ statusSummaryText }}
        </div>
      </section>

      <section class="page-card p-4">
        <div class="flex items-end justify-between gap-3">
          <div>
            <p class="section-label">照护工具</p>
            <h2 class="mt-2 text-base font-semibold text-slate-800">辅助功能仍然可见</h2>
            <p class="mt-1 text-sm leading-6 text-slate-500">
              音乐、呼吸和波形监测从一级导航下移，但不会消失。
            </p>
          </div>
        </div>

        <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <router-link
            v-for="tool in toolEntries"
            :key="tool.path"
            :to="tool.path"
            class="rounded-[1.25rem] border border-rose-100 bg-rose-50/70 p-4 transition-transform active:scale-[0.98]"
          >
            <div class="text-2xl">{{ tool.icon }}</div>
            <div class="mt-3 text-sm font-semibold text-slate-800">{{ tool.label }}</div>
            <div class="mt-1 text-xs leading-5 text-slate-500">{{ tool.helper }}</div>
          </router-link>
        </div>
      </section>

      <section class="page-card-soft p-4">
        <p class="section-label">今日提醒</p>
        <div class="mt-3 grid gap-3">
          <div class="rounded-2xl bg-white/90 px-4 py-3">
            <div class="text-sm font-medium text-slate-800">关于经前状态</div>
            <div class="mt-1 text-sm leading-6 text-slate-500">
              经前状态了解会继续并入正常聊天，不会变成显性筛查入口；如果你愿意，直接从聊天开始即可。
            </div>
          </div>
          <div class="rounded-2xl bg-white/90 px-4 py-3">
            <div class="text-sm font-medium text-slate-800">关于数据完整度</div>
            <div class="mt-1 text-sm leading-6 text-slate-500">
              周期预测、今日情绪和后续小结都依赖你留下的记录。缺失数据时，MoonCARE 会尽量诚实地提示“不足以判断”。
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useHealthStore } from '../stores/health'
import { useChatStore } from '../stores/chat'

const router = useRouter()
const healthStore = useHealthStore()
const chatStore = useChatStore()

const toolEntries = [
  { path: '/music', label: '音乐陪伴', helper: '先让情绪慢一点，再决定要不要继续聊。', icon: '🎵' },
  { path: '/breathing', label: '呼吸练习', helper: '适合先稳定呼吸节奏，给自己一点缓冲。', icon: '🍃' },
  { path: '/wave', label: '波形监测', helper: '查看设备侧生理波动，区分真实数据和演示状态。', icon: '📈' }
]

const currentDate = computed(() => {
  return new Date().toLocaleDateString('zh-CN', {
    month: 'long',
    day: 'numeric',
    weekday: 'long'
  })
})

const phaseEmoji = computed(() => healthStore.phaseEmoji)
const phaseName = computed(() => healthStore.phaseName)
const pmsRisk = computed(() => healthStore.pmsRisk)
const moodLevel = computed(() => healthStore.moodLevel)
const cyclePrediction = computed(() => healthStore.cyclePrediction)

const greetingTitle = computed(() => {
  if (healthStore.riskLevel === 'high' || healthStore.riskLevel === 'critical') {
    return '今天如果有点难熬，我们就先从陪伴开始。'
  }
  if (moodLevel.value >= 7.5) {
    return '状态不错的时候，也值得被轻轻接住。'
  }
  if (cyclePrediction.value?.current_phase === 'luteal') {
    return '黄体期里更敏感一点，也很正常。'
  }
  return '先看看今天的状态，再决定怎么照顾自己。'
})

const greetingSubtitle = computed(() => {
  if (chatStore.sessionId) {
    return '你可以继续上次的聊天，也可以从今天的情绪、身体感受或周期变化重新开始。'
  }
  return '首页先给你一个简洁入口：聊天主链路在前，周期和日记作为补充，不再让导航分散注意力。'
})

const chatCtaTitle = computed(() => chatStore.sessionId ? '上次的对话还在，可以继续聊。' : '今天先从一段对话开始。')
const chatCtaLabel = computed(() => chatStore.sessionId ? '继续聊聊' : '开始聊聊')

const phasePredictionText = computed(() => {
  const prediction = cyclePrediction.value
  if (!prediction) return ''

  if (prediction.predicted_start) {
    const date = new Date(prediction.predicted_start)
    return `${date.getMonth() + 1} 月 ${date.getDate()} 日左右`
  }

  if (prediction.phase_days_remaining !== undefined) {
    const futureDate = new Date()
    futureDate.setDate(futureDate.getDate() + prediction.phase_days_remaining)
    return `${futureDate.getMonth() + 1} 月 ${futureDate.getDate()} 日左右`
  }

  return ''
})

const cycleSummaryText = computed(() => {
  if (!cyclePrediction.value) {
    return '还没有足够的周期记录。先补几次经期开始时间，后续预测才会更稳。'
  }

  if (cyclePrediction.value.current_phase === 'luteal') {
    return '当前更需要留意情绪起伏、睡眠和身体疲劳感。聊天里会继续轻量承接这些变化。'
  }

  return '这里先给你阶段摘要和预测窗口，具体感受仍然以你自己的记录和聊天反馈为准。'
})

const riskLabel = computed(() => {
  const labels = {
    critical: '需要优先关注',
    high: '偏高',
    medium: '中等',
    low: '较低'
  }
  return labels[healthStore.riskLevel] || '待判断'
})

const riskClass = computed(() => {
  const classes = {
    critical: 'bg-red-100 text-red-700',
    high: 'bg-orange-100 text-orange-700',
    medium: 'bg-amber-100 text-amber-700',
    low: 'bg-emerald-100 text-emerald-700'
  }
  return classes[healthStore.riskLevel] || 'bg-slate-100 text-slate-600'
})

const riskHintText = computed(() => {
  if (healthStore.riskLevel === 'critical' || healthStore.riskLevel === 'high') {
    return '建议优先回到聊天，先说说眼前最难受的部分。'
  }
  if (cyclePrediction.value?.current_phase === 'luteal') {
    return '黄体期里更容易出现烦躁或疲惫，仅供参考。'
  }
  return '这不是诊断，只是当前数据下的轻量提示。'
})

const moodDescription = computed(() => {
  if (moodLevel.value >= 8) return '整体偏轻松，可以继续保持自己的节奏。'
  if (moodLevel.value >= 6) return '状态还可以，如果有小波动，也适合先通过聊天整理一下。'
  if (moodLevel.value >= 4) return '今天的情绪比较普通，既可以记录，也可以直接去聊天里展开。'
  if (moodLevel.value >= 2) return '今天可能更疲惫或更敏感，先把强烈感受说出来会更有帮助。'
  return '当前状态需要更多关注，先减少额外压力，再慢慢处理眼前的问题。'
})

const supportFocusText = computed(() => {
  if (healthStore.riskLevel === 'critical' || healthStore.riskLevel === 'high') return '先陪伴，再分析'
  if (cyclePrediction.value?.current_phase === 'luteal') return '留意黄体期波动'
  return '可以按你自己的节奏来'
})

const statusSummaryText = computed(() => {
  if (chatStore.assessmentSummary?.summary_available) {
    return '聊天里已经有一部分经前状态小结可继续承接。你不需要重新开始，回到聊天页就能延续。'
  }
  if (!cyclePrediction.value) {
    return '目前的摘要更多来自当下情绪数据。补充日记和周期记录后，这里的内容会更完整。'
  }
  return '首页只保留必要摘要，避免把过多解释堆在一屏里。需要更细的感受整理时，聊天会是主入口。'
})

async function loadHomeState() {
  await Promise.allSettled([
    healthStore.fetchEmotionState(),
    healthStore.fetchPhaseInfo(),
    healthStore.fetchCyclePrediction()
  ])
}

function openChat() {
  router.push('/chat')
}

function goToProfile() {
  router.push('/profile')
}

onMounted(() => {
  loadHomeState()
})
</script>
