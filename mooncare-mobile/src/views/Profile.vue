<template>
  <div class="profile-page">
    <div class="max-w-lg mx-auto pb-20">
      <div class="bg-gradient-to-br from-pink-50 to-rose-100 px-4 pt-4 pb-3">
        <h1 class="text-lg font-bold text-gray-800">我的</h1>
      </div>

      <div class="px-4 -mt-2">
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <div class="flex items-center gap-3">
            <div class="w-12 h-12 rounded-full bg-gradient-to-br from-pink-100 to-pink-200 flex items-center justify-center">
              <svg class="w-6 h-6 text-pink-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <div class="flex-1">
              <div class="font-medium text-gray-800">{{ authStore.user?.nickname || '用户' }}</div>
              <div class="text-xs text-gray-500">{{ authStore.user?.email || '' }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="px-4 mt-4">
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <router-link to="/cycle" class="item-row">
            <div class="row-copy">
              <span class="row-icon">📅</span>
              <div>
                <div class="row-title">周期记录</div>
                <div class="row-subtitle">查看和管理月经周期数据</div>
              </div>
            </div>
            <span class="row-arrow">›</span>
          </router-link>

          <div class="divider"></div>

          <div v-if="cyclePrediction" class="p-4">
            <div class="flex items-center gap-2 mb-2">
              <span class="text-xl">🔭</span>
              <span class="text-sm font-medium text-gray-700">周期摘要</span>
            </div>
            <div class="space-y-1 text-xs text-gray-600 pl-7">
              <div v-if="cyclePrediction.predicted_start">下次月经：{{ formatDate(cyclePrediction.predicted_start) }}</div>
              <div>
                {{ getPhaseName(cyclePrediction.current_phase) }}
                <span v-if="cyclePrediction.phase_days_remaining !== null && cyclePrediction.phase_days_remaining !== undefined">
                  ，{{ cyclePrediction.phase_days_remaining }} 天后进入下一阶段
                </span>
              </div>
            </div>
          </div>

          <div class="divider"></div>

          <router-link to="/wave" class="item-row">
            <div class="row-copy">
              <span class="row-icon">📳</span>
              <div>
                <div class="row-title">波形监测</div>
                <div class="row-subtitle">查看设备与生理数据状态</div>
              </div>
            </div>
            <span class="row-arrow">›</span>
          </router-link>
        </div>
      </div>

      <div class="px-4 mt-4">
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <router-link to="/settings" class="item-row">
            <div class="row-copy">
              <span class="row-icon">⚙️</span>
              <div>
                <div class="row-title">设置</div>
                <div class="row-subtitle">昵称、通知、缓存和版本信息</div>
              </div>
            </div>
            <span class="row-arrow">›</span>
          </router-link>

          <div class="divider"></div>

          <button type="button" class="item-row text-left w-full" @click="handleLogout">
            <div class="row-copy">
              <span class="row-icon text-red-500">↩</span>
              <div>
                <div class="row-title text-red-500">退出登录</div>
                <div class="row-subtitle">切换账号或退出当前登录状态</div>
              </div>
            </div>
            <span class="row-arrow">›</span>
          </button>
        </div>
      </div>

      <div class="px-4 mt-6 text-center">
        <div class="text-xs text-gray-400">她语 MoonCARE v1.0.1-api-hotfix</div>
      </div>
    </div>

    <BottomNav />
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import BottomNav from '../components/BottomNav.vue'
import { useHealthStore } from '../stores/health'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const healthStore = useHealthStore()
const authStore = useAuthStore()

const cyclePrediction = computed(() => healthStore.cyclePrediction)

function getPhaseName(phase) {
  const names = {
    follicular: '卵泡期',
    ovulation: '排卵期',
    luteal: '黄体期',
    menstrual: '经期',
    unknown: '状态未知',
  }
  return names[phase] || '状态未知'
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' })
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

onMounted(async () => {
  await healthStore.fetchCyclePrediction()
})
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  background: #f9fafb;
}

.item-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
}

.row-copy {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.row-icon {
  font-size: 1.25rem;
}

.row-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #1f2937;
}

.row-subtitle {
  font-size: 0.75rem;
  color: #6b7280;
}

.row-arrow {
  color: #9ca3af;
  font-size: 1rem;
}

.divider {
  height: 1px;
  background: #f3f4f6;
}
</style>
