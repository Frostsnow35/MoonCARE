<template>
  <div class="app-page">
    <div class="page-content page-stack">
      <section class="page-card-soft p-5">
        <div class="flex items-start gap-4">
          <div class="grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-rose-100 to-pink-200 text-rose-600">
            <svg class="h-7 w-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <div class="min-w-0 flex-1">
            <p class="section-label">账户</p>
            <h1 class="mt-2 text-lg font-semibold text-slate-800">{{ authStore.user?.nickname || 'MoonCARE 用户' }}</h1>
            <p class="mt-1 break-all text-sm text-slate-500">{{ authStore.user?.email || '尚未同步邮箱信息' }}</p>
            <p class="mt-3 text-sm leading-6 text-slate-500">
              这里保留账户、工具入口、更新状态和设置占位，不再让版本更新区域盖过个人信息本身。
            </p>
          </div>
        </div>

        <div class="mt-4 grid grid-cols-2 gap-3">
          <div class="rounded-2xl bg-white/90 px-4 py-3">
            <div class="text-xs text-slate-500">下一次月经</div>
            <div class="mt-2 text-sm font-semibold text-slate-800">{{ nextPeriodLabel }}</div>
          </div>
          <div class="rounded-2xl bg-white/90 px-4 py-3">
            <div class="text-xs text-slate-500">当前阶段</div>
            <div class="mt-2 text-sm font-semibold text-slate-800">{{ currentPhaseLabel }}</div>
          </div>
        </div>
      </section>

      <section class="page-card p-4">
        <div>
          <p class="section-label">照护工具</p>
          <h2 class="mt-2 text-base font-semibold text-slate-800">辅助能力统一收口</h2>
          <p class="mt-1 text-sm leading-6 text-slate-500">
            音乐、呼吸和波形监测不再占一级导航，但在个人中心和首页都能直接到达。
          </p>
        </div>

        <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <router-link
            v-for="tool in toolLinks"
            :key="tool.path"
            :to="tool.path"
            class="rounded-[1.25rem] border border-rose-100 bg-rose-50/70 p-4 transition-transform active:scale-[0.98]"
          >
            <div class="flex items-center gap-3">
              <div class="grid h-11 w-11 place-items-center rounded-2xl bg-white text-xl shadow-sm">
                {{ tool.icon }}
              </div>
              <div class="min-w-0">
                <div class="text-sm font-semibold text-slate-800">{{ tool.label }}</div>
                <div class="mt-1 text-xs leading-5 text-slate-500">{{ tool.helper }}</div>
              </div>
            </div>
          </router-link>
        </div>
      </section>

      <section class="page-card p-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="section-label">版本更新</p>
            <h2 class="mt-2 text-base font-semibold text-slate-800">保留，但降级到账户区之后</h2>
            <p class="mt-1 text-sm leading-6 text-slate-500">
              当前内测包仍支持查看版本状态。若环境允许，还可以继续走应用内更新。
            </p>
          </div>
          <span
            class="rounded-full px-3 py-1 text-[11px] font-semibold"
            :class="appUpdateStore.hasUpdateAvailable ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-500'"
          >
            {{ appUpdateStore.appInfo.updateChannel || 'beta' }}
          </span>
        </div>

        <div class="mt-4 rounded-[1.25rem] bg-rose-50/80 p-4">
          <div class="grid gap-2 text-xs text-slate-500">
            <div class="flex items-center justify-between gap-4">
              <span>当前版本</span>
              <span class="text-right">{{ appUpdateStore.currentVersionLabel }}</span>
            </div>
            <div class="flex items-center justify-between gap-4">
              <span>最近检查</span>
              <span class="text-right">{{ formatLastChecked(appUpdateStore.lastCheckedAt) }}</span>
            </div>
            <div class="flex items-center justify-between gap-4">
              <span>更新状态</span>
              <span class="max-w-[11rem] text-right">{{ appUpdateStore.statusLabel }}</span>
            </div>
            <div class="flex items-center justify-between gap-4">
              <span>最新版本</span>
              <span class="text-right">{{ appUpdateStore.latestVersionLabel }}</span>
            </div>
            <div class="flex items-center justify-between gap-4">
              <span>发布时间</span>
              <span class="text-right">{{ appUpdateStore.latestPublishedAtLabel }}</span>
            </div>
          </div>
        </div>

        <div
          v-if="appUpdateStore.errorMessage"
          class="mt-3 rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3 text-xs leading-6 text-amber-700"
        >
          {{ appUpdateStore.errorMessage }}
        </div>

        <div
          v-if="!appUpdateStore.supportsSelfUpdate"
          class="mt-3 rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3 text-xs leading-6 text-slate-500"
        >
          当前环境不是 Android 内测包，这里会继续显示版本状态，但不会直接触发安装。
        </div>

        <div class="mt-4 flex flex-col gap-2 sm:flex-row">
          <button
            type="button"
            class="secondary-button flex-1"
            :disabled="appUpdateStore.isChecking"
            @click="checkForUpdates"
          >
            {{ appUpdateStore.isChecking ? '检查中…' : '检查更新' }}
          </button>
          <button
            type="button"
            class="primary-button flex-1 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="!appUpdateStore.supportsSelfUpdate || !appUpdateStore.hasUpdateAvailable || appUpdateStore.isUpdating"
            @click="startUpdate"
          >
            {{ appUpdateStore.isUpdating ? '准备中…' : '立即更新' }}
          </button>
        </div>

        <button
          v-if="appUpdateStore.hasUpdateAvailable && !appUpdateStore.supportsSelfUpdate"
          type="button"
          class="ghost-button mt-3 w-full"
          @click="appUpdateStore.openDownloadPage"
        >
          打开下载链接
        </button>
      </section>

      <section class="page-card p-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="section-label">设置</p>
            <h2 class="mt-2 text-base font-semibold text-slate-800">仍在前台，但诚实标记为计划中</h2>
            <p class="mt-1 text-sm leading-6 text-slate-500">
              通知、隐私和数据管理入口后续会补齐，当前先明确它还没有完成，而不是伪装成可用功能。
            </p>
          </div>
          <span class="rounded-full bg-amber-100 px-3 py-1 text-[11px] font-semibold text-amber-700">计划中</span>
        </div>

        <div class="mt-4 rounded-[1.25rem] border border-dashed border-amber-200 bg-amber-50/70 px-4 py-3 text-sm leading-6 text-amber-800">
          这一组设置后续会承接通知、隐私说明、数据导出/删除等真实能力。现在先保留入口，不制造“已经可用”的错觉。
        </div>
      </section>

      <section class="page-card p-4">
        <button
          type="button"
          class="flex w-full items-center gap-3 rounded-[1.25rem] bg-rose-50 px-4 py-4 text-left transition-colors hover:bg-rose-100"
          @click="handleLogout"
        >
          <div class="grid h-11 w-11 place-items-center rounded-2xl bg-white text-rose-500 shadow-sm">
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </div>
          <div class="min-w-0 flex-1">
            <div class="text-sm font-semibold text-rose-600">退出登录</div>
            <div class="mt-1 text-xs leading-5 text-slate-500">切换账户或退出当前账户。</div>
          </div>
        </button>

        <div class="mt-4 text-center text-xs text-slate-400">
          她语 MoonCARE v{{ appUpdateStore.appInfo.versionName }}
          <div class="mt-1">Build {{ appUpdateStore.appInfo.versionCode }} · {{ appUpdateStore.appInfo.flavor }}</div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useHealthStore } from '../stores/health'
import { useAuthStore } from '../stores/auth'
import { useAppUpdateStore } from '../stores/appUpdate'

const router = useRouter()
const healthStore = useHealthStore()
const authStore = useAuthStore()
const appUpdateStore = useAppUpdateStore()

const toolLinks = [
  { path: '/music', label: '音乐陪伴', helper: '适合在需要情绪缓冲时先切换到更轻的节奏。', icon: '🎵' },
  { path: '/breathing', label: '呼吸练习', helper: '适合在紧张、烦躁或需要先稳住身体感受时使用。', icon: '🍃' },
  { path: '/wave', label: '波形监测', helper: '查看生理波动和设备状态，区分真实数据与演示模式。', icon: '📈' },
  { path: '/cycle', label: '周期记录', helper: '补充经期记录，帮助后续预测和首页摘要更稳。', icon: '🗓️' }
]

const cyclePrediction = computed(() => healthStore.cyclePrediction)

const nextPeriodLabel = computed(() => {
  if (!cyclePrediction.value?.predicted_start) return '还需要更多记录'
  const date = new Date(cyclePrediction.value.predicted_start)
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日左右`
})

const currentPhaseLabel = computed(() => {
  const phase = cyclePrediction.value?.current_phase
  const names = {
    follicular: '卵泡期',
    ovulation: '排卵期',
    luteal: '黄体期',
    menstrual: '经期'
  }
  return names[phase] || '待判断'
})

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

function formatLastChecked(timestamp) {
  if (!timestamp) return '尚未检查'
  return new Date(timestamp).toLocaleString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

async function checkForUpdates() {
  await appUpdateStore.checkForUpdates()
}

async function startUpdate() {
  await appUpdateStore.startUpdate()
}

onMounted(async () => {
  await Promise.allSettled([
    healthStore.fetchCyclePrediction(),
    appUpdateStore.initialize()
  ])
})
</script>
