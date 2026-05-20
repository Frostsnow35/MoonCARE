<template>
  <div class="profile-page">
    <div class="max-w-lg mx-auto pb-16">
      <!-- Header -->
      <div class="bg-gradient-to-br from-pink-50 to-purple-50 px-4 pt-4 pb-3">
        <h1 class="text-lg font-bold text-gray-800">个人中心</h1>
      </div>

      <!-- User Info Card -->
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

      <!-- Cycle Section -->
      <div class="px-4 mt-4">
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <router-link
            to="/cycle"
            class="flex items-center justify-between p-4 active:bg-gray-50"
          >
            <div class="flex items-center gap-3">
              <span class="text-xl">🌼</span>
              <div>
                <div class="font-medium text-gray-800 text-sm">周期记录</div>
                <div class="text-xs text-gray-500">查看月经周期</div>
              </div>
            </div>
            <span class="text-gray-400 text-sm">→</span>
          </router-link>

          <div class="border-t border-gray-100"></div>

          <!-- Cycle Prediction Display -->
          <div v-if="cyclePrediction" class="p-4">
            <div class="flex items-center gap-2 mb-2">
              <span class="text-xl">🔮</span>
              <span class="text-sm font-medium text-gray-700">周期预测</span>
            </div>
            <div class="space-y-1 text-xs text-gray-600 pl-7">
              <div v-if="cyclePrediction.predicted_start">
                下次月经: {{ formatDate(cyclePrediction.predicted_start) }}
              </div>
              <div>
                {{ getPhaseName(cyclePrediction.current_phase) }}
                <span v-if="cyclePrediction.current_phase === 'luteal'">
                  {{ cyclePrediction.phase_days_remaining }}天后可能来潮
                </span>
                <span v-else>
                  {{ cyclePrediction.phase_days_remaining }}天后进入下一阶段
                </span>
              </div>
            </div>
          </div>

          <div class="border-t border-gray-100"></div>

          <router-link
            to="/wave"
            class="flex items-center justify-between p-4 active:bg-gray-50"
          >
            <div class="flex items-center gap-3">
              <span class="text-xl">📊</span>
              <div>
                <div class="font-medium text-gray-800 text-sm">波形监测</div>
                <div class="text-xs text-gray-500">HRV & 温度实时数据</div>
              </div>
            </div>
            <span class="text-gray-400 text-sm">→</span>
          </router-link>
        </div>
      </div>

      <!-- Settings Section -->
      <div class="px-4 mt-4">
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div class="flex items-center justify-between p-4 active:bg-gray-50 cursor-pointer">
            <div class="flex items-center gap-3">
              <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <div>
                <div class="font-medium text-gray-800 text-sm">设置</div>
                <div class="text-xs text-gray-500">通知、隐私等</div>
              </div>
            </div>
            <span class="text-gray-400 text-sm">→</span>
          </div>

          <div class="border-t border-gray-100"></div>

          <button
            type="button"
            class="w-full flex items-center gap-3 p-4 active:bg-gray-50 text-left"
            @click="handleLogout"
          >
            <svg class="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            <div>
              <div class="font-medium text-red-500 text-sm">退出登录</div>
              <div class="text-xs text-gray-400">切换账户或退出当前账户</div>
            </div>
          </button>
        </div>
      </div>

      <!-- App Info -->
      <div class="px-4 mt-6 text-center">
        <div class="text-xs text-gray-400">她语 MoonCARE v1.0.0</div>
        <div class="text-xs text-gray-300 mt-1">智能情绪管理平台</div>
      </div>
    </div>

    <!-- Bottom Nav -->
    <BottomNav />
  </div>
</template>

<script setup>
import BottomNav from '../components/BottomNav.vue'
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useHealthStore } from '../stores/health'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const healthStore = useHealthStore()
const authStore = useAuthStore()
const userId = ref(1)

const cyclePrediction = computed(() => healthStore.cyclePrediction)

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
</style>
