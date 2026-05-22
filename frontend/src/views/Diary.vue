<template>
  <div class="diary-page">
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
        <h1 class="text-lg font-bold text-gray-800">情绪日记</h1>
        <span class="text-xs text-gray-500">{{ diaryStore.total }} 篇</span>
      </div>

      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
        <h3 class="font-medium text-gray-800 mb-3">记录今天的感受</h3>

        <div class="mb-4">
          <div class="text-xs text-gray-500 mb-2">今天心情如何？</div>
          <div class="grid grid-cols-5 gap-1">
            <button
              v-for="mood in quickMoods"
              :key="mood.id"
              type="button"
              @click="selectQuickMood(mood)"
              class="flex flex-col items-center gap-0.5 p-2 rounded-xl transition-all active:scale-95"
              :class="selectedMood?.id === mood.id
                ? 'bg-pink-100 border-2 border-pink-400'
                : 'bg-gray-50 border-2 border-transparent hover:bg-pink-50'"
            >
              <span class="text-xs font-medium text-gray-700">{{ mood.label }}</span>
              <span class="text-[11px] text-gray-500">{{ mood.moodLevel }}/10</span>
            </button>
          </div>
        </div>

        <div class="mb-4">
          <textarea
            v-model="newDiaryText"
            class="w-full p-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-pink-200 focus:border-pink-400 outline-none transition-all resize-none text-sm"
            rows="3"
            placeholder="写下今天让你有这种感受的事情，或身体和周期相关的变化..."
          ></textarea>
        </div>

        <div class="flex items-center gap-3 mb-4">
          <button
            type="button"
            @click="toggleVoiceRecording"
            class="flex items-center gap-2 px-3 py-1.5 rounded-full transition-colors text-sm"
            :class="isRecording ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
          >
            <span class="font-medium">{{ isRecording ? '停止录音' : '语音输入' }}</span>
          </button>
          <span v-if="isRecording" class="text-xs text-red-500 animate-pulse">录音中...</span>
        </div>

        <div class="mb-4">
          <div class="text-xs text-gray-600 mb-2">情绪标签（可多选）</div>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="tag in emotionTags"
              :key="tag"
              type="button"
              @click="toggleTag(tag)"
              class="px-3 py-1 rounded-full text-xs transition-colors"
              :class="selectedTags.includes(tag)
                ? 'bg-pink-100 text-pink-700 border border-pink-300'
                : 'bg-gray-50 text-gray-600 border border-gray-200 hover:bg-gray-100'"
            >
              {{ tag }}
            </button>
          </div>
        </div>

        <button
          type="button"
          @click="submitDiary"
          :disabled="!newDiaryText.trim() || isSubmitting"
          class="w-full py-2.5 rounded-xl font-medium text-white text-sm transition-all disabled:bg-gray-300 disabled:cursor-not-allowed bg-pink-500 hover:bg-pink-600 active:scale-[0.98]"
        >
          {{ isSubmitting ? '保存中...' : '保存日记' }}
        </button>
      </div>

      <div class="mt-4">
        <h2 class="font-medium text-gray-800 mb-3 text-sm">最近日记</h2>

        <div v-if="diaryStore.isLoading" class="space-y-3">
          <div v-for="i in 3" :key="i" class="bg-white rounded-xl p-4 animate-pulse">
            <div class="h-3 bg-gray-200 rounded w-1/4 mb-2"></div>
            <div class="h-3 bg-gray-100 rounded w-full mb-1"></div>
            <div class="h-3 bg-gray-100 rounded w-2/3"></div>
          </div>
        </div>

        <div v-else-if="diaryStore.diaries.length === 0" class="text-center py-10 text-gray-500">
          <p class="text-sm">还没有日记，先写下一篇吧</p>
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="diary in diaryStore.diaries"
            :key="diary.id"
            class="bg-white rounded-xl p-4 border border-gray-100"
          >
            <div class="flex justify-between items-start gap-3 mb-2">
              <div>
                <span class="text-xs text-gray-500">{{ formatDateTime(diary.date) }}</span>
                <div v-if="editingDiaryId !== diary.id" class="flex gap-2 mt-1">
                  <button type="button" class="text-xs text-pink-500" @click="startEditDiary(diary)">编辑</button>
                  <button
                    type="button"
                    class="text-xs text-red-500 disabled:text-gray-300"
                    :disabled="deletingDiaryId === diary.id"
                    @click="deleteDiary(diary)"
                  >
                    {{ deletingDiaryId === diary.id ? '删除中' : '删除' }}
                  </button>
                </div>
              </div>

              <div v-if="editingDiaryId !== diary.id" class="flex flex-wrap gap-1 justify-end">
                <span
                  v-for="tag in diary.emotion_tags || []"
                  :key="tag"
                  class="px-2 py-0.5 bg-pink-50 text-pink-600 text-xs rounded-full"
                >
                  {{ tag }}
                </span>
              </div>
            </div>

            <div v-if="editingDiaryId === diary.id" class="space-y-3">
              <textarea
                v-model="editDiaryText"
                rows="3"
                class="w-full p-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-pink-200 focus:border-pink-400 outline-none transition-all resize-none text-sm"
              ></textarea>

              <div class="flex flex-wrap gap-2">
                <button
                  v-for="tag in emotionTags"
                  :key="tag"
                  type="button"
                  @click="toggleEditTag(tag)"
                  class="px-3 py-1 rounded-full text-xs transition-colors"
                  :class="editDiaryTags.includes(tag)
                    ? 'bg-pink-100 text-pink-700 border border-pink-300'
                    : 'bg-gray-50 text-gray-600 border border-gray-200'"
                >
                  {{ tag }}
                </button>
              </div>

              <label class="block text-xs text-gray-500">
                心情评分
                <input
                  v-model.number="editDiaryMoodLevel"
                  type="number"
                  min="1"
                  max="10"
                  step="0.5"
                  class="mt-1 w-full p-2 border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-pink-200"
                />
              </label>

              <div class="flex gap-2">
                <button type="button" class="flex-1 py-2 rounded-lg text-gray-600 bg-gray-100 text-sm" @click="cancelEditDiary">
                  取消
                </button>
                <button
                  type="button"
                  :disabled="!editDiaryText.trim() || isEditingSubmitting"
                  class="flex-1 py-2 rounded-lg text-white font-medium text-sm disabled:bg-gray-300 bg-pink-500"
                  @click="saveDiaryEdit"
                >
                  {{ isEditingSubmitting ? '保存中' : '保存修改' }}
                </button>
              </div>
            </div>

            <div v-else>
              <p class="text-gray-700 text-sm leading-relaxed">{{ diary.original_text || diary.processed_text }}</p>
              <div v-if="diary.mood_level" class="mt-2 text-xs text-gray-400">
                情绪评分: {{ Number(diary.mood_level).toFixed(1) }}/10
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <BottomNav />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useDiaryStore } from '../stores/diary'
import BottomNav from '../components/BottomNav.vue'

const diaryStore = useDiaryStore()

const newDiaryText = ref('')
const selectedTags = ref([])
const isSubmitting = ref(false)
const selectedMood = ref(null)
const toastMessage = ref('')
const toastType = ref('success')
const editingDiaryId = ref(null)
const editDiaryText = ref('')
const editDiaryTags = ref([])
const editDiaryMoodLevel = ref(5)
const isEditingSubmitting = ref(false)
const deletingDiaryId = ref(null)

const quickMoods = [
  { id: 'great', label: '很好', text: '今天心情很好。', moodLevel: 9 },
  { id: 'good', label: '不错', text: '今天感觉还不错。', moodLevel: 7 },
  { id: 'normal', label: '一般', text: '今天心情一般。', moodLevel: 5 },
  { id: 'low', label: '低落', text: '今天心情有点低落。', moodLevel: 3 },
  { id: 'hard', label: '难过', text: '今天很难过。', moodLevel: 2 }
]

const emotionTags = ['平静', '开心', '焦虑', '低落', '烦躁', '疲惫', '压力大', '失眠']
const isRecording = computed(() => diaryStore.isRecording)

function showToast(message, type = 'success') {
  toastMessage.value = message
  toastType.value = type
  window.setTimeout(() => {
    if (toastMessage.value === message) toastMessage.value = ''
  }, 2200)
}

function selectQuickMood(mood) {
  if (selectedMood.value?.id === mood.id) {
    selectedMood.value = null
    newDiaryText.value = ''
    return
  }
  selectedMood.value = mood
  newDiaryText.value = mood.text
}

function toggleTag(tagName) {
  const index = selectedTags.value.indexOf(tagName)
  if (index === -1) selectedTags.value.push(tagName)
  else selectedTags.value.splice(index, 1)
}

function toggleVoiceRecording() {
  if (isRecording.value) {
    diaryStore.setRecording(false)
    return
  }

  diaryStore.setRecording(true)
  window.setTimeout(() => {
    if (isRecording.value) {
      newDiaryText.value = `（语音转写内容）${newDiaryText.value}`
      diaryStore.setRecording(false)
    }
  }, 3000)
}

async function submitDiary() {
  if (!newDiaryText.value.trim() || isSubmitting.value) return

  isSubmitting.value = true
  try {
    await diaryStore.createDiary({
      date: new Date().toISOString(),
      input_type: isRecording.value ? 'voice' : 'text',
      original_text: newDiaryText.value,
      emotion_tags: selectedTags.value,
      mood_level: selectedMood.value?.moodLevel
    })

    newDiaryText.value = ''
    selectedTags.value = []
    selectedMood.value = null
    showToast('日记保存成功')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (error) {
    console.error('Failed to save diary:', error)
    showToast('保存失败，请稍后重试', 'error')
  } finally {
    isSubmitting.value = false
  }
}

function startEditDiary(diary) {
  editingDiaryId.value = diary.id
  editDiaryText.value = diary.original_text || diary.processed_text || ''
  editDiaryTags.value = [...(diary.emotion_tags || [])]
  editDiaryMoodLevel.value = diary.mood_level || 5
}

function cancelEditDiary() {
  editingDiaryId.value = null
  editDiaryText.value = ''
  editDiaryTags.value = []
  editDiaryMoodLevel.value = 5
}

function toggleEditTag(tagName) {
  const index = editDiaryTags.value.indexOf(tagName)
  if (index === -1) editDiaryTags.value.push(tagName)
  else editDiaryTags.value.splice(index, 1)
}

async function saveDiaryEdit() {
  if (!editingDiaryId.value || !editDiaryText.value.trim() || isEditingSubmitting.value) return

  isEditingSubmitting.value = true
  try {
    await diaryStore.updateDiary(editingDiaryId.value, {
      original_text: editDiaryText.value,
      emotion_tags: editDiaryTags.value,
      mood_level: editDiaryMoodLevel.value
    })
    cancelEditDiary()
    showToast('日记已更新')
  } catch (error) {
    console.error('Failed to update diary:', error)
    showToast('更新失败，请稍后重试', 'error')
  } finally {
    isEditingSubmitting.value = false
  }
}

async function deleteDiary(diary) {
  if (!window.confirm('确定删除这篇日记吗？')) return

  deletingDiaryId.value = diary.id
  try {
    await diaryStore.deleteDiary(diary.id)
    if (editingDiaryId.value === diary.id) cancelEditDiary()
    showToast('日记已删除')
  } catch (error) {
    console.error('Failed to delete diary:', error)
    showToast('删除失败，请稍后重试', 'error')
  } finally {
    deletingDiaryId.value = null
  }
}

function formatDateTime(dateStr) {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`

  return date.toLocaleDateString('zh-CN', {
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  diaryStore.fetchDiaries()
})
</script>

<style scoped>
.diary-page {
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
