<template>
  <div class="diary-detail-page">
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
      <div class="flex items-center gap-4 pt-4 pb-3">
        <button
          type="button"
          @click="goBack"
          class="w-8 h-8 flex items-center justify-center rounded-full bg-gray-100 hover:bg-gray-200 transition-colors"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M15 18l-6-6 6-6"/>
          </svg>
        </button>
        <h1 class="text-lg font-bold text-gray-800">日记详情</h1>
      </div>

      <div v-if="isLoading" class="bg-white rounded-xl p-8 animate-pulse">
        <div class="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div class="h-3 bg-gray-100 rounded w-full mb-2"></div>
        <div class="h-3 bg-gray-100 rounded w-3/4 mb-2"></div>
        <div class="h-3 bg-gray-100 rounded w-1/2 mb-4"></div>
        <div class="flex gap-2">
          <div class="h-6 bg-gray-100 rounded-full px-4"></div>
          <div class="h-6 bg-gray-100 rounded-full px-4"></div>
        </div>
      </div>

      <div v-else-if="diary" class="space-y-4">
        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div class="p-6">
            <div class="flex justify-between items-start mb-4">
              <div>
                <span class="text-xs text-gray-500">{{ formatDateTime(diary.date) }}</span>
                <div v-if="diary.mood_level" class="mt-2 flex items-center gap-2">
                  <span class="text-xs text-gray-500">心情评分</span>
                  <div class="flex gap-0.5">
                    <span
                      v-for="i in 10"
                      :key="i"
                      class="w-3 h-3 rounded-full transition-colors"
                      :class="i <= Math.round(diary.mood_level) ? 'bg-pink-400' : 'bg-gray-200'"
                    ></span>
                  </div>
                  <span class="text-sm font-medium text-pink-600">{{ Number(diary.mood_level).toFixed(1) }}/10</span>
                </div>
              </div>
              <div class="flex gap-2">
                <button
                  type="button"
                  @click="startEdit"
                  :disabled="isEditing"
                  class="px-3 py-1.5 rounded-full text-sm text-pink-600 bg-pink-50 hover:bg-pink-100 transition-colors disabled:opacity-50"
                >
                  编辑
                </button>
                <button
                  type="button"
                  @click="showDeleteConfirm = true"
                  :disabled="isEditing"
                  class="px-3 py-1.5 rounded-full text-sm text-red-600 bg-red-50 hover:bg-red-100 transition-colors disabled:opacity-50"
                >
                  删除
                </button>
              </div>
            </div>

            <div v-if="!isEditing" class="space-y-4">
              <p class="text-gray-700 leading-relaxed">{{ diary.original_text || diary.processed_text }}</p>
              
              <div v-if="(diary.emotion_tags || []).length > 0">
                <div class="text-xs text-gray-500 mb-2">情绪标签</div>
                <div class="flex flex-wrap gap-2">
                  <span
                    v-for="tag in diary.emotion_tags"
                    :key="tag"
                    class="px-3 py-1 bg-gradient-to-r from-pink-50 to-rose-50 text-pink-600 text-xs rounded-full border border-pink-100"
                  >
                    {{ tag }}
                  </span>
                </div>
              </div>

              <div v-if="(diary.keywords || []).length > 0" class="pt-4 border-t border-gray-100">
                <div class="text-xs text-gray-500 mb-2">关键词</div>
                <div class="flex flex-wrap gap-2">
                  <span
                    v-for="keyword in diary.keywords"
                    :key="keyword"
                    class="px-2 py-0.5 bg-gray-50 text-gray-600 text-xs rounded"
                  >
                    {{ keyword }}
                  </span>
                </div>
              </div>
            </div>

            <div v-else class="space-y-4">
              <textarea
                v-model="editText"
                rows="5"
                class="w-full p-4 border border-gray-200 rounded-xl focus:ring-2 focus:ring-pink-200 focus:border-pink-400 outline-none transition-all resize-none"
                placeholder="写下你的心情..."
              ></textarea>

              <div>
                <div class="text-xs text-gray-500 mb-2">情绪标签（可多选）</div>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="tag in emotionTags"
                    :key="tag"
                    type="button"
                    @click="toggleTag(tag)"
                    class="px-3 py-1 rounded-full text-xs transition-colors"
                    :class="editTags.includes(tag)
                      ? 'bg-pink-100 text-pink-700 border border-pink-300'
                      : 'bg-gray-50 text-gray-600 border border-gray-200 hover:bg-gray-100'"
                  >
                    {{ tag }}
                  </button>
                </div>
              </div>

              <div>
                <label class="block text-xs text-gray-500 mb-1">心情评分</label>
                <div class="flex items-center gap-3">
                  <input
                    v-model.number="editMoodLevel"
                    type="range"
                    min="1"
                    max="10"
                    step="0.5"
                    class="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-pink-500"
                  />
                  <span class="text-sm font-medium text-pink-600 w-12 text-right">{{ editMoodLevel.toFixed(1) }}/10</span>
                </div>
              </div>

              <div class="flex gap-3 pt-4">
                <button
                  type="button"
                  @click="cancelEdit"
                  class="flex-1 py-2.5 rounded-xl text-gray-600 bg-gray-100 font-medium text-sm hover:bg-gray-200 transition-colors"
                >
                  取消
                </button>
                <button
                  type="button"
                  :disabled="!editText.trim() || isSaving"
                  @click="saveEdit"
                  class="flex-1 py-2.5 rounded-xl font-medium text-white text-sm disabled:bg-gray-300 bg-pink-500 hover:bg-pink-600 transition-colors"
                >
                  {{ isSaving ? '保存中...' : '保存修改' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="text-center py-16 text-gray-500">
        <p class="text-sm">日记不存在</p>
        <button
          type="button"
          @click="goBack"
          class="mt-4 px-4 py-2 text-pink-600 hover:text-pink-700"
        >
          返回列表
        </button>
      </div>
    </div>

    <BottomNav />

    <Transition name="modal">
      <div v-if="showDeleteConfirm" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click.self="showDeleteConfirm = false">
        <div class="bg-white rounded-2xl p-6 w-full max-w-sm transform">
          <h3 class="text-lg font-semibold text-gray-800 mb-2">确认删除</h3>
          <p class="text-sm text-gray-600 mb-6">确定要删除这篇日记吗？删除后无法恢复。</p>
          <div class="flex gap-3">
            <button
              type="button"
              @click="showDeleteConfirm = false"
              class="flex-1 py-2.5 rounded-xl text-gray-600 bg-gray-100 font-medium text-sm"
            >
              取消
            </button>
            <button
              type="button"
              @click="confirmDelete"
              class="flex-1 py-2.5 rounded-xl font-medium text-white text-sm bg-red-500 hover:bg-red-600"
            >
              确认删除
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDiaryStore } from '../stores/diary'
import BottomNav from '../components/BottomNav.vue'

const route = useRoute()
const router = useRouter()
const diaryStore = useDiaryStore()

const diary = ref(null)
const isLoading = ref(true)
const toastMessage = ref('')
const toastType = ref('success')
const isEditing = ref(false)
const editText = ref('')
const editTags = ref([])
const editMoodLevel = ref(5)
const editOriginalText = ref('')
const isSaving = ref(false)
const showDeleteConfirm = ref(false)

const emotionTags = ['平静', '开心', '焦虑', '低落', '烦躁', '疲惫', '压力大', '失眠']

function showToast(message, type = 'success') {
  toastMessage.value = message
  toastType.value = type
  window.setTimeout(() => {
    if (toastMessage.value === message) toastMessage.value = ''
  }, 2200)
}

function formatDateTime(dateStr) {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function goBack() {
  router.push('/diary')
}

async function loadDiary() {
  const diaryId = parseInt(route.params.id)
  if (!diaryId) {
    isLoading.value = false
    return
  }

  try {
    const result = await diaryStore.getDiary(diaryId)
    diary.value = result
  } catch (error) {
    console.error('Failed to load diary:', error)
    showToast('加载日记失败', 'error')
  } finally {
    isLoading.value = false
  }
}

function startEdit() {
  if (!diary.value) return
  isEditing.value = true
  editText.value = diary.value.original_text || diary.value.processed_text || ''
  editOriginalText.value = editText.value
  editTags.value = [...(diary.value.emotion_tags || [])]
  editMoodLevel.value = diary.value.mood_level || 5
}

function cancelEdit() {
  isEditing.value = false
  editText.value = ''
  editTags.value = []
  editMoodLevel.value = 5
}

function toggleTag(tagName) {
  const index = editTags.value.indexOf(tagName)
  if (index === -1) editTags.value.push(tagName)
  else editTags.value.splice(index, 1)
}

async function saveEdit() {
  if (!diary.value || !editText.value.trim() || isSaving.value) return

  isSaving.value = true
  try {
    const textChanged = editText.value !== editOriginalText.value
    const options = textChanged ? {} : { skip_nlp: true }
    
    await diaryStore.updateDiary(diary.value.id, {
      original_text: editText.value,
      emotion_tags: editTags.value,
      mood_level: editMoodLevel.value
    }, options)
    
    await loadDiary()
    cancelEdit()
    showToast('日记已更新')
  } catch (error) {
    console.error('Failed to update diary:', error)
    showToast('更新失败，请稍后重试', 'error')
  } finally {
    isSaving.value = false
  }
}

async function confirmDelete() {
  if (!diary.value) return

  showDeleteConfirm.value = false
  try {
    await diaryStore.deleteDiary(diary.value.id)
    showToast('日记已删除')
    setTimeout(() => {
      router.push('/diary')
    }, 1000)
  } catch (error) {
    console.error('Failed to delete diary:', error)
    showToast('删除失败，请稍后重试', 'error')
  }
}

onMounted(() => {
  loadDiary()
})
</script>

<script>
import { useDiaryStore } from '../stores/diary'

export default {
  mounted() {
    const diaryStore = useDiaryStore()
    if (!diaryStore.getDiary) {
      diaryStore.getDiary = async function(id) {
        const { diaryAPI } = await import('../api')
        return diaryAPI.get(id)
      }
    }
  }
}
</script>

<style scoped>
.diary-detail-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #fef7f8 0%, #f9fafb 100%);
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

.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from > div,
.modal-leave-to > div {
  transform: scale(0.9);
}

input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ec4899;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(236, 72, 153, 0.3);
}

input[type="range"]::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ec4899;
  cursor: pointer;
  border: none;
  box-shadow: 0 2px 6px rgba(236, 72, 153, 0.3);
}
</style>