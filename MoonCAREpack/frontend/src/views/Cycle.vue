<template>
  <div class="cycle-page">
    <div class="max-w-lg mx-auto pb-16 px-4">
      <!-- Header -->
      <div class="flex items-center justify-between pt-4 pb-3">
        <h1 class="text-lg font-bold text-gray-800">月经周期</h1>
        <button
          @click="showRecordModal = true"
          class="px-3 py-1.5 bg-pink-500 text-white text-xs font-medium rounded-full hover:bg-pink-600 transition-colors"
        >
          + 记录
        </button>
      </div>

      <!-- Current Cycle Status -->
      <div class="bg-gradient-to-br from-pink-100 to-purple-100 rounded-xl p-4 border border-pink-200">
        <div class="text-center mb-3">
          <div class="text-4xl mb-1">{{ currentPhaseEmoji }}</div>
          <div class="text-base font-semibold text-gray-800">{{ currentPhaseName }}</div>
          <div class="text-xs text-gray-600">{{ currentPhaseDescription }}</div>
        </div>

        <div v-if="prediction" class="space-y-1.5 bg-white/50 rounded-lg p-3">
          <div class="flex justify-between items-center">
            <span class="text-gray-600 text-xs">下次月经预计</span>
            <span class="font-medium text-purple-700 text-sm">{{ formatDate(prediction.predicted_start) }}</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-gray-600 text-xs">距离现在</span>
            <span class="text-xs font-medium text-pink-600">
              {{ daysUntilNextPeriod }} 天
            </span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-gray-600 text-xs">预测置信度</span>
            <span class="text-xs font-medium text-purple-600">
              {{ (prediction.confidence * 100).toFixed(0) }}%
            </span>
          </div>
        </div>
      </div>

      <!-- Tabs -->
      <div class="mt-3 bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div class="flex border-b border-gray-100">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            class="flex-1 py-2.5 text-sm font-medium transition-colors relative"
            :class="activeTab === tab.id ? 'text-pink-500' : 'text-gray-400 hover:text-gray-600'"
          >
            {{ tab.name }}
            <span
              v-if="activeTab === tab.id"
              class="absolute bottom-0 left-1/2 -translate-x-1/2 w-8 h-0.5 bg-pink-500 rounded-full"
            ></span>
          </button>
        </div>

        <!-- Tab Content -->
        <div class="p-3">
          <!-- Calendar Tab -->
          <div v-if="activeTab === 'calendar'">
            <div class="flex items-center justify-between mb-2">
              <button @click="prevMonth" class="p-1 rounded-full hover:bg-gray-100">
                <span class="text-gray-600 text-sm">←</span>
              </button>
              <span class="font-medium text-gray-800 text-sm">{{ currentMonthName }}</span>
              <button @click="nextMonth" class="p-1 rounded-full hover:bg-gray-100">
                <span class="text-gray-600 text-sm">→</span>
              </button>
            </div>

            <!-- Weekday Headers -->
            <div class="grid grid-cols-7 gap-0.5 mb-1">
              <div
                v-for="day in ['日', '一', '二', '三', '四', '五', '六']"
                :key="day"
                class="text-center text-xs text-gray-500 py-1"
              >
                {{ day }}
              </div>
            </div>

            <!-- Calendar Days -->
            <div class="grid grid-cols-7 gap-0.5">
              <div
                v-for="(day, index) in calendarDays"
                :key="index"
                class="aspect-square flex flex-col items-center justify-center rounded-lg text-xs relative"
                :class="getDayClass(day)"
              >
                <span>{{ day > 0 ? day : '' }}</span>
                <span
                  v-if="day > 0 && isPeriodDay(day)"
                  class="absolute bottom-0.5 w-1 h-1 rounded-full bg-red-400"
                ></span>
                <span
                  v-if="day > 0 && isPredictedPeriod(day)"
                  class="absolute bottom-0.5 w-1 h-1 rounded-full bg-pink-300"
                ></span>
              </div>
            </div>

            <!-- Legend -->
            <div class="flex items-center justify-center gap-4 mt-3 text-xs text-gray-500">
              <div class="flex items-center gap-1">
                <span class="w-1.5 h-1.5 rounded-full bg-red-400"></span>
                <span>月经期</span>
              </div>
              <div class="flex items-center gap-1">
                <span class="w-1.5 h-1.5 rounded-full bg-pink-300"></span>
                <span>预测经期</span>
              </div>
            </div>
          </div>

          <!-- Prediction Tab -->
          <div v-if="activeTab === 'prediction'">
            <div class="text-center py-4" v-if="prediction">
              <div class="text-5xl mb-2">{{ currentPhaseEmoji }}</div>
              <div class="text-lg font-semibold text-gray-800 mb-1">{{ currentPhaseName }}</div>
              <div class="text-sm text-gray-600 mb-4">{{ currentPhaseDescription }}</div>

              <div class="bg-pink-50 rounded-xl p-4">
                <div class="text-xs text-gray-500 mb-1">下次月经预计</div>
                <div class="text-lg font-bold text-pink-600">{{ formatDate(prediction.predicted_start) }}</div>
                <div class="text-sm text-pink-500 mt-1">{{ daysUntilNextPeriod }} 天后</div>
              </div>

              <div class="mt-3 flex items-center justify-center gap-2">
                <span class="text-xs text-gray-500">预测置信度</span>
                <span class="text-sm font-medium text-purple-600">{{ (prediction.confidence * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </div>

          <!-- Records Tab -->
          <div v-if="activeTab === 'records'">
            <div v-if="records.length === 0" class="text-center py-6">
              <span class="text-3xl mb-1 block">📅</span>
              <p class="text-sm text-gray-500">还没有周期记录</p>
              <button
                @click="showRecordModal = true"
                class="mt-2 px-3 py-1.5 bg-pink-50 text-pink-600 text-xs font-medium rounded-full"
              >
                添加第一条记录
              </button>
            </div>

            <div v-else class="space-y-2">
              <div
                v-for="record in records"
                :key="record.id"
                class="bg-gray-50 rounded-xl p-3"
              >
                <div class="flex justify-between items-start">
                  <div>
                    <div class="font-medium text-gray-800 text-sm">
                      {{ formatDate(record.start_date) }}
                      <span v-if="record.end_date" class="text-gray-400 font-normal">
                        ~ {{ formatDate(record.end_date) }}
                      </span>
                    </div>
                    <div v-if="record.duration" class="text-xs text-gray-500">
                      持续 {{ record.duration }} 天
                    </div>
                  </div>
                  <div class="flex items-center gap-0.5">
                    <span
                      v-for="i in (record.flow_intensity || 3)"
                      :key="i"
                      class="text-red-400 text-xs"
                    >
                      ●
                    </span>
                  </div>
                </div>

                <div v-if="record.symptoms && record.symptoms.length > 0" class="mt-1.5 flex flex-wrap gap-1">
                  <span
                    v-for="symptom in record.symptoms"
                    :key="symptom"
                    class="px-1.5 py-0.5 bg-orange-50 text-orange-600 text-xs rounded-full"
                  >
                    {{ symptom }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Record Modal -->
      <div
        v-if="showRecordModal"
        class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
        @click.self="showRecordModal = false"
      >
        <div class="bg-white rounded-xl w-full max-w-sm p-5 animate-fadeIn">
          <h3 class="text-base font-semibold text-gray-800 mb-3">记录月经</h3>

          <div class="space-y-3">
            <div>
              <label class="block text-xs text-gray-600 mb-1">开始日期</label>
              <input
                type="date"
                v-model="newRecord.start_date"
                class="w-full p-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-pink-200 focus:border-pink-400 outline-none text-sm"
              />
            </div>

            <div>
              <label class="block text-xs text-gray-600 mb-1">结束日期（选填）</label>
              <input
                type="date"
                v-model="newRecord.end_date"
                class="w-full p-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-pink-200 focus:border-pink-400 outline-none text-sm"
              />
            </div>

            <div>
              <label class="block text-xs text-gray-600 mb-1.5">经量</label>
              <div class="flex gap-1.5">
                <button
                  v-for="level in [1, 2, 3, 4, 5]"
                  :key="level"
                  @click="newRecord.flow_intensity = level"
                  class="flex-1 py-1.5 rounded-lg text-xs transition-colors"
                  :class="newRecord.flow_intensity === level
                    ? 'bg-red-100 text-red-600 border border-red-300'
                    : 'bg-gray-50 text-gray-600 border border-gray-200'"
                >
                  {{ level === 1 ? '少' : level === 3 ? '中' : level === 5 ? '多' : '' }}
                </button>
              </div>
            </div>

            <div>
              <label class="block text-xs text-gray-600 mb-1.5">症状（可多选）</label>
              <div class="flex flex-wrap gap-1">
                <button
                  v-for="symptom in symptomOptions"
                  :key="symptom"
                  @click="toggleSymptom(symptom)"
                  :class="newRecord.symptoms.includes(symptom)
                    ? 'bg-orange-100 text-orange-600 border border-orange-300'
                    : 'bg-gray-50 text-gray-600 border border-gray-200'"
                  class="px-2 py-1 rounded-full text-xs"
                >
                  {{ symptom }}
                </button>
              </div>
            </div>
          </div>

          <div class="flex gap-2 mt-4">
            <button
              @click="showRecordModal = false"
              class="flex-1 py-2 rounded-lg text-gray-600 bg-gray-100 text-sm"
            >
              取消
            </button>
            <button
              @click="submitRecord"
              :disabled="!newRecord.start_date || isSubmitting"
              class="flex-1 py-2 rounded-lg text-white font-medium text-sm"
              :class="newRecord.start_date
                ? 'bg-pink-500 hover:bg-pink-600'
                : 'bg-gray-300 cursor-not-allowed'"
            >
              {{ isSubmitting ? '保存中...' : '保存' }}
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
import { ref, computed, onMounted } from 'vue'
import { menstrualAPI } from '../api'
import BottomNav from '../components/BottomNav.vue'

const records = ref([])
const prediction = ref(null)
const showRecordModal = ref(false)
const isSubmitting = ref(false)
const activeTab = ref('calendar')

const tabs = [
  { id: 'calendar', name: '日历' },
  { id: 'prediction', name: '预测' },
  { id: 'records', name: '记录' }
]

const currentMonth = ref(new Date())
const newRecord = ref({
  start_date: '',
  end_date: '',
  flow_intensity: 3,
  symptoms: []
})

const symptomOptions = ['头痛', '疲劳', '易怒', '腹胀', '乳房胀痛', '长痘', '失眠', '焦虑']

const currentMonthName = computed(() => {
  return currentMonth.value.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long'
  })
})

const currentPhaseEmoji = computed(() => {
  if (!prediction.value) return '📅'
  const emojis = {
    follicular: '🌱',
    ovulation: '🌸',
    luteal: '🌷',
    menstrual: '🌺'
  }
  return emojis[prediction.value.current_phase] || '📅'
})

const currentPhaseName = computed(() => {
  if (!prediction.value) return '加载中...'
  const names = {
    follicular: '卵泡期',
    ovulation: '排卵期',
    luteal: '黄体期',
    menstrual: '经期'
  }
  return names[prediction.value.current_phase] || '未知'
})

const currentPhaseDescription = computed(() => {
  if (!prediction.value) return ''
  const descs = {
    follicular: '身体状态恢复中',
    ovulation: '情绪和精力较好',
    luteal: '留意经前不适',
    menstrual: '注意休息保暖'
  }
  return descs[prediction.value.current_phase] || ''
})

const daysUntilNextPeriod = computed(() => {
  if (!prediction.value) return 0
  const predicted = new Date(prediction.value.predicted_start)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const diff = predicted - today
  return Math.ceil(diff / (1000 * 60 * 60 * 24))
})

const calendarDays = computed(() => {
  const year = currentMonth.value.getFullYear()
  const month = currentMonth.value.getMonth()
  const firstDay = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()

  const days = []
  // Add empty cells for days before the first day of month
  for (let i = 0; i < firstDay; i++) {
    days.push(0)
  }
  // Add days of month
  for (let i = 1; i <= daysInMonth; i++) {
    days.push(i)
  }
  return days
})

function getDayClass(day) {
  if (day <= 0) return ''

  const date = new Date(currentMonth.value.getFullYear(), currentMonth.value.getMonth(), day)
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  if (date.getTime() === today.getTime()) {
    return 'bg-blue-100 text-blue-700 font-semibold'
  }

  if (isPeriodDay(day)) {
    return 'bg-red-50 text-red-600'
  }

  return 'text-gray-700 hover:bg-gray-50'
}

function isPeriodDay(day) {
  const date = new Date(currentMonth.value.getFullYear(), currentMonth.value.getMonth(), day)

  return records.value.some(record => {
    const start = new Date(record.start_date)
    const end = record.end_date ? new Date(record.end_date) : start
    return date >= start && date <= end
  })
}

function isPredictedPeriod(day) {
  if (!prediction.value) return false
  const date = new Date(currentMonth.value.getFullYear(), currentMonth.value.getMonth(), day)
  const predicted = new Date(prediction.value.predicted_start)

  // Show prediction for 5 days around the predicted date
  const diff = Math.abs((date - predicted) / (1000 * 60 * 60 * 24))
  return diff <= 2
}

function prevMonth() {
  currentMonth.value = new Date(
    currentMonth.value.getFullYear(),
    currentMonth.value.getMonth() - 1
  )
}

function nextMonth() {
  currentMonth.value = new Date(
    currentMonth.value.getFullYear(),
    currentMonth.value.getMonth() + 1
  )
}

function toggleSymptom(symptom) {
  const index = newRecord.value.symptoms.indexOf(symptom)
  if (index === -1) {
    newRecord.value.symptoms.push(symptom)
  } else {
    newRecord.value.symptoms.splice(index, 1)
  }
}

async function submitRecord() {
  if (!newRecord.value.start_date || isSubmitting.value) return

  isSubmitting.value = true
  try {
    const data = {
      start_date: newRecord.value.start_date,
      end_date: newRecord.value.end_date || null,
      flow_intensity: newRecord.value.flow_intensity,
      symptoms: newRecord.value.symptoms
    }

    await menstrualAPI.createRecord(data)
    await fetchData()
    showRecordModal.value = false

    // Reset form
    newRecord.value = {
      start_date: '',
      end_date: '',
      flow_intensity: 3,
      symptoms: []
    }
  } catch (error) {
    console.error('Failed to save record:', error)
  } finally {
    isSubmitting.value = false
  }
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    month: 'long',
    day: 'numeric'
  })
}

async function fetchData() {
  try {
    const recordsRes = await menstrualAPI.getRecords()
    records.value = recordsRes

    prediction.value = await menstrualAPI.predict()
  } catch (error) {
    console.error('Failed to fetch data:', error)
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.cycle-page {
  min-height: 100vh;
  background: #f9fafb;
}
</style>
