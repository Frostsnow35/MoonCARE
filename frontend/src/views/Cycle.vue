<template>
  <div class="cycle-page">
    <Transition name="toast">
      <div
        v-if="toastMessage"
        class="fixed top-20 left-1/2 -translate-x-1/2 z-50 px-4 py-2 text-white rounded-full shadow-lg flex items-center gap-2 text-sm"
        :class="toastType === 'error' ? 'bg-red-500' : 'bg-green-500'"
      >
        <span>{{ toastType === 'error' ? '!' : 'OK' }}</span>
        <span>{{ toastMessage }}</span>
      </div>
    </Transition>

    <div class="max-w-lg mx-auto pb-16 px-4">
      <div class="flex items-center justify-between pt-4 pb-3">
        <h1 class="text-lg font-bold text-gray-800">月经周期</h1>
        <button
          type="button"
          @click="openCreateRecordModal"
          class="px-3 py-1.5 bg-pink-500 text-white text-xs font-medium rounded-full hover:bg-pink-600 transition-colors"
        >
          新增记录
        </button>
      </div>

      <div class="bg-gradient-to-br from-pink-100 to-purple-100 rounded-xl p-4 border border-pink-200">
        <div class="text-center mb-3">
          <div class="text-base font-semibold text-gray-800">{{ currentPhaseName }}</div>
          <div class="text-xs text-gray-600">{{ currentPhaseDescription }}</div>
        </div>

        <div v-if="prediction?.predicted_start" class="space-y-1.5 bg-white/50 rounded-lg p-3">
          <div class="flex justify-between items-center">
            <span class="text-gray-600 text-xs">下次月经预计</span>
            <span class="font-medium text-purple-700 text-sm">{{ formatDate(prediction.predicted_start) }}</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-gray-600 text-xs">距离现在</span>
            <span class="text-xs font-medium text-pink-600">{{ daysUntilNextPeriod }} 天</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-gray-600 text-xs">预测置信度</span>
            <span class="text-xs font-medium text-purple-600">{{ ((prediction.confidence || 0) * 100).toFixed(0) }}%</span>
          </div>
        </div>

        <div v-else class="bg-white/50 rounded-lg p-3 text-xs text-gray-600 text-center">
          记录至少两个周期后，可生成仅供参考的周期预测。
        </div>
      </div>

      <div class="mt-3 bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div class="flex border-b border-gray-100">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            type="button"
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

        <div class="p-3">
          <div v-if="activeTab === 'calendar'">
            <div class="flex items-center justify-between mb-2">
              <button type="button" @click="prevMonth" class="p-1 rounded-full hover:bg-gray-100 text-gray-600 text-sm">
                上月
              </button>
              <span class="font-medium text-gray-800 text-sm">{{ currentMonthName }}</span>
              <button type="button" @click="nextMonth" class="p-1 rounded-full hover:bg-gray-100 text-gray-600 text-sm">
                下月
              </button>
            </div>

            <div class="grid grid-cols-7 gap-0.5 mb-1">
              <div
                v-for="day in ['日', '一', '二', '三', '四', '五', '六']"
                :key="day"
                class="text-center text-xs text-gray-500 py-1"
              >
                {{ day }}
              </div>
            </div>

            <div class="grid grid-cols-7 gap-0.5">
              <div
                v-for="(day, index) in calendarDays"
                :key="index"
                class="aspect-square flex flex-col items-center justify-center rounded-lg text-xs relative"
                :class="getDayClass(day)"
              >
                <span>{{ day > 0 ? day : '' }}</span>
                <span v-if="day > 0 && isPeriodDay(day)" class="absolute bottom-0.5 w-1 h-1 rounded-full bg-red-400"></span>
                <span v-if="day > 0 && isPredictedPeriod(day)" class="absolute bottom-0.5 w-1 h-1 rounded-full bg-pink-300"></span>
              </div>
            </div>

            <div class="flex items-center justify-center gap-4 mt-3 text-xs text-gray-500">
              <div class="flex items-center gap-1">
                <span class="w-1.5 h-1.5 rounded-full bg-red-400"></span>
                <span>已记录经期</span>
              </div>
              <div class="flex items-center gap-1">
                <span class="w-1.5 h-1.5 rounded-full bg-pink-300"></span>
                <span>预测经期</span>
              </div>
            </div>
          </div>

          <div v-if="activeTab === 'prediction'">
            <div class="text-center py-4">
              <div class="text-lg font-semibold text-gray-800 mb-1">{{ currentPhaseName }}</div>
              <div class="text-sm text-gray-600 mb-4">{{ currentPhaseDescription }}</div>

              <div v-if="prediction?.predicted_start" class="bg-pink-50 rounded-xl p-4">
                <div class="text-xs text-gray-500 mb-1">下次月经预计</div>
                <div class="text-lg font-bold text-pink-600">{{ formatDate(prediction.predicted_start) }}</div>
                <div class="text-sm text-pink-500 mt-1">{{ daysUntilNextPeriod }} 天后</div>
              </div>
              <div v-else class="bg-gray-50 rounded-xl p-4 text-sm text-gray-500">
                暂无足够记录，先补充历史周期。
              </div>
            </div>
          </div>

          <div v-if="activeTab === 'records'">
            <div v-if="records.length === 0" class="text-center py-6">
              <p class="text-sm text-gray-500">还没有周期记录</p>
              <button
                type="button"
                @click="openCreateRecordModal"
                class="mt-2 px-3 py-1.5 bg-pink-50 text-pink-600 text-xs font-medium rounded-full"
              >
                添加第一条记录
              </button>
            </div>

            <div v-else class="space-y-2">
              <div v-for="record in records" :key="record.id" class="bg-gray-50 rounded-xl p-3">
                <div class="flex justify-between items-start gap-3">
                  <div>
                    <div class="font-medium text-gray-800 text-sm">
                      {{ formatDate(record.start_date) }}
                      <span v-if="record.end_date" class="text-gray-400 font-normal">~ {{ formatDate(record.end_date) }}</span>
                    </div>
                    <div v-if="record.duration" class="text-xs text-gray-500">持续 {{ record.duration }} 天</div>
                    <div class="flex gap-2 mt-1">
                      <button type="button" class="text-xs text-pink-500" @click="startEditRecord(record)">编辑</button>
                      <button
                        type="button"
                        class="text-xs text-red-500 disabled:text-gray-300"
                        :disabled="deletingRecordId === record.id"
                        @click="deleteRecord(record)"
                      >
                        {{ deletingRecordId === record.id ? '删除中' : '删除' }}
                      </button>
                    </div>
                  </div>
                  <div class="flex items-center gap-0.5">
                    <span v-for="i in (record.flow_intensity || 3)" :key="i" class="text-red-400 text-xs">●</span>
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

      <div
        v-if="showRecordModal"
        class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
        @click.self="closeRecordModal"
      >
        <div class="bg-white rounded-xl w-full max-w-sm p-5 animate-fadeIn">
          <h3 class="text-base font-semibold text-gray-800 mb-3">{{ editingRecordId ? '编辑周期记录' : '记录月经' }}</h3>

          <div class="space-y-3">
            <div>
              <label class="block text-xs text-gray-600 mb-1">开始日期</label>
              <input
                type="date"
                v-model="recordForm.start_date"
                class="w-full p-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-pink-200 focus:border-pink-400 outline-none text-sm"
              />
            </div>

            <div>
              <label class="block text-xs text-gray-600 mb-1">结束日期（选填）</label>
              <input
                type="date"
                v-model="recordForm.end_date"
                class="w-full p-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-pink-200 focus:border-pink-400 outline-none text-sm"
              />
            </div>

            <div>
              <label class="block text-xs text-gray-600 mb-1.5">经量</label>
              <div class="flex gap-1.5">
                <button
                  v-for="level in [1, 2, 3, 4, 5]"
                  :key="level"
                  type="button"
                  @click="recordForm.flow_intensity = level"
                  class="flex-1 py-1.5 rounded-lg text-xs transition-colors"
                  :class="recordForm.flow_intensity === level
                    ? 'bg-red-100 text-red-600 border border-red-300'
                    : 'bg-gray-50 text-gray-600 border border-gray-200'"
                >
                  {{ level }}
                </button>
              </div>
            </div>

            <div>
              <label class="block text-xs text-gray-600 mb-1.5">症状（可多选）</label>
              <div class="flex flex-wrap gap-1">
                <button
                  v-for="symptom in symptomOptions"
                  :key="symptom"
                  type="button"
                  @click="toggleSymptom(symptom)"
                  :class="recordForm.symptoms.includes(symptom)
                    ? 'bg-orange-100 text-orange-600 border border-orange-300'
                    : 'bg-gray-50 text-gray-600 border border-gray-200'"
                  class="px-2 py-1 rounded-full text-xs"
                >
                  {{ symptom }}
                </button>
              </div>
            </div>

            <p v-if="formError" class="text-xs text-red-500">{{ formError }}</p>
          </div>

          <div class="flex gap-2 mt-4">
            <button type="button" @click="closeRecordModal" class="flex-1 py-2 rounded-lg text-gray-600 bg-gray-100 text-sm">
              取消
            </button>
            <button
              type="button"
              @click="submitRecord"
              :disabled="!recordForm.start_date || isSubmitting"
              class="flex-1 py-2 rounded-lg text-white font-medium text-sm disabled:bg-gray-300 bg-pink-500 hover:bg-pink-600"
            >
              {{ isSubmitting ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </div>

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
const deletingRecordId = ref(null)
const editingRecordId = ref(null)
const activeTab = ref('calendar')
const formError = ref('')
const toastMessage = ref('')
const toastType = ref('success')

const tabs = [
  { id: 'calendar', name: '日历' },
  { id: 'prediction', name: '预测' },
  { id: 'records', name: '记录' }
]

const currentMonth = ref(new Date())
const recordForm = ref(createEmptyRecordForm())
const symptomOptions = ['头痛', '疲惫', '易怒', '腹胀', '乳房胀痛', '长痘', '失眠', '焦虑']

const currentMonthName = computed(() => {
  return currentMonth.value.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long' })
})

const currentPhaseName = computed(() => {
  const names = {
    follicular: '卵泡期',
    ovulation: '排卵期',
    luteal: '黄体期',
    menstrual: '经期',
    unknown: '状态未知'
  }
  return names[prediction.value?.current_phase] || '状态未知'
})

const currentPhaseDescription = computed(() => {
  const descs = {
    follicular: '身体状态恢复中，适合温和恢复节奏。',
    ovulation: '精力可能较好，但仍以身体感受为准。',
    luteal: '留意经前情绪和睡眠变化，仅供参考。',
    menstrual: '注意休息、保暖和补充水分。',
    unknown: '记录更多周期后，可获得更稳定的状态提示。'
  }
  return descs[prediction.value?.current_phase] || descs.unknown
})

const daysUntilNextPeriod = computed(() => {
  if (!prediction.value?.predicted_start) return 0
  const predicted = parseLocalDate(prediction.value.predicted_start)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.ceil((predicted - today) / (1000 * 60 * 60 * 24))
})

const calendarDays = computed(() => {
  const year = currentMonth.value.getFullYear()
  const month = currentMonth.value.getMonth()
  const firstDay = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const days = []
  for (let i = 0; i < firstDay; i += 1) days.push(0)
  for (let i = 1; i <= daysInMonth; i += 1) days.push(i)
  return days
})

function createEmptyRecordForm() {
  return {
    start_date: '',
    end_date: '',
    flow_intensity: 3,
    symptoms: []
  }
}

function parseLocalDate(dateStr) {
  const [year, month, day] = String(dateStr).slice(0, 10).split('-').map(Number)
  return new Date(year, month - 1, day)
}

function toDateInput(dateStr) {
  return dateStr ? String(dateStr).slice(0, 10) : ''
}

function showToast(message, type = 'success') {
  toastMessage.value = message
  toastType.value = type
  window.setTimeout(() => {
    if (toastMessage.value === message) toastMessage.value = ''
  }, 2200)
}

function getDayClass(day) {
  if (day <= 0) return ''

  const date = new Date(currentMonth.value.getFullYear(), currentMonth.value.getMonth(), day)
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  if (date.getTime() === today.getTime()) return 'bg-blue-100 text-blue-700 font-semibold'
  if (isPeriodDay(day)) return 'bg-red-50 text-red-600'
  return 'text-gray-700 hover:bg-gray-50'
}

function isPeriodDay(day) {
  const date = new Date(currentMonth.value.getFullYear(), currentMonth.value.getMonth(), day)

  return records.value.some(record => {
    const start = parseLocalDate(record.start_date)
    const end = record.end_date ? parseLocalDate(record.end_date) : start
    return date >= start && date <= end
  })
}

function isPredictedPeriod(day) {
  if (!prediction.value?.predicted_start) return false
  const date = new Date(currentMonth.value.getFullYear(), currentMonth.value.getMonth(), day)
  const predicted = parseLocalDate(prediction.value.predicted_start)
  const diff = Math.abs((date - predicted) / (1000 * 60 * 60 * 24))
  return diff <= 2
}

function prevMonth() {
  currentMonth.value = new Date(currentMonth.value.getFullYear(), currentMonth.value.getMonth() - 1)
}

function nextMonth() {
  currentMonth.value = new Date(currentMonth.value.getFullYear(), currentMonth.value.getMonth() + 1)
}

function toggleSymptom(symptom) {
  const index = recordForm.value.symptoms.indexOf(symptom)
  if (index === -1) recordForm.value.symptoms.push(symptom)
  else recordForm.value.symptoms.splice(index, 1)
}

function openCreateRecordModal() {
  editingRecordId.value = null
  recordForm.value = createEmptyRecordForm()
  formError.value = ''
  showRecordModal.value = true
}

function startEditRecord(record) {
  editingRecordId.value = record.id
  recordForm.value = {
    start_date: toDateInput(record.start_date),
    end_date: toDateInput(record.end_date),
    flow_intensity: record.flow_intensity || 3,
    symptoms: [...(record.symptoms || [])]
  }
  formError.value = ''
  showRecordModal.value = true
}

function closeRecordModal() {
  showRecordModal.value = false
  editingRecordId.value = null
  recordForm.value = createEmptyRecordForm()
  formError.value = ''
}

async function submitRecord() {
  if (!recordForm.value.start_date || isSubmitting.value) return

  isSubmitting.value = true
  formError.value = ''
  try {
    const data = {
      start_date: recordForm.value.start_date,
      end_date: recordForm.value.end_date || null,
      flow_intensity: recordForm.value.flow_intensity,
      symptoms: recordForm.value.symptoms
    }

    if (editingRecordId.value) {
      await menstrualAPI.updateRecord(editingRecordId.value, data)
      showToast('周期记录已更新')
    } else {
      await menstrualAPI.createRecord(data)
      showToast('周期记录已保存')
    }

    await fetchData()
    closeRecordModal()
    activeTab.value = 'records'
  } catch (error) {
    console.error('Failed to save record:', error)
    formError.value = error.response?.data?.detail || '保存失败，请稍后重试'
  } finally {
    isSubmitting.value = false
  }
}

async function deleteRecord(record) {
  if (!window.confirm('确定删除这条周期记录吗？')) return

  deletingRecordId.value = record.id
  try {
    await menstrualAPI.deleteRecord(record.id)
    await fetchData()
    showToast('周期记录已删除')
  } catch (error) {
    console.error('Failed to delete record:', error)
    showToast('删除失败，请稍后重试', 'error')
  } finally {
    deletingRecordId.value = null
  }
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return parseLocalDate(dateStr).toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' })
}

async function fetchData() {
  try {
    records.value = await menstrualAPI.getRecords()
    prediction.value = await menstrualAPI.predict()
  } catch (error) {
    console.error('Failed to fetch cycle data:', error)
    showToast('周期数据加载失败，请稍后重试', 'error')
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

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translate(-50%, -10px);
}
</style>
