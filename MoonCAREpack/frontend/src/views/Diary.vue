<template>
  <div class="diary-page">
    <!-- Success Toast -->
    <Transition name="toast">
      <div v-if="showSuccessToast" class="fixed top-20 left-1/2 -translate-x-1/2 z-50 px-4 py-2 bg-green-500 text-white rounded-full shadow-lg flex items-center gap-2 text-sm">
        <span>✨</span>
        <span>情绪存档成功</span>
      </div>
    </Transition>

    <div class="max-w-lg mx-auto pb-16 px-4">
      <!-- Header -->
      <div class="flex items-center justify-between pt-4 pb-3">
        <h1 class="text-lg font-bold text-gray-800">情绪日记</h1>
        <span class="text-xs text-gray-500">{{ diaryStore.total }}篇日记</span>
      </div>

      <!-- New Entry Card -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
        <h3 class="font-medium text-gray-800 mb-3">记录今天的情绪</h3>

        <!-- Quick Mood Selection -->
        <div class="mb-4">
          <div class="text-xs text-gray-500 mb-2">今天心情如何？</div>
          <div class="flex justify-between gap-1">
            <button
              v-for="mood in quickMoods"
              :key="mood.emoji"
              @click="selectQuickMood(mood)"
              class="flex-1 flex flex-col items-center gap-0.5 p-2 rounded-xl transition-all active:scale-95"
              :class="selectedMood?.emoji === mood.emoji
                ? 'bg-pink-100 border-2 border-pink-400'
                : 'bg-gray-50 border-2 border-transparent hover:bg-pink-50'"
            >
              <span class="text-2xl">{{ mood.emoji }}</span>
              <span class="text-xs text-gray-600">{{ mood.label }}</span>
            </button>
          </div>
        </div>

        <!-- Text Input -->
        <div class="mb-4">
          <textarea
            v-model="newDiaryText"
            class="w-full p-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-pink-200 focus:border-pink-400 outline-none transition-all resize-none text-sm"
            rows="3"
            placeholder="今天发生了什么让你有这种感觉？写下你的想法..."
          ></textarea>
        </div>

        <!-- Voice Input -->
        <div class="flex items-center gap-3 mb-4">
          <button
            @click="toggleVoiceRecording"
            class="flex items-center gap-2 px-3 py-1.5 rounded-full transition-colors text-sm"
            :class="isRecording ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
          >
            <span>{{ isRecording ? '🔴' : '🎤' }}</span>
            <span class="font-medium">{{ isRecording ? '停止录音' : '语音输入' }}</span>
          </button>
          <span v-if="isRecording" class="text-xs text-red-500 animate-pulse">
            录音中...
          </span>
        </div>

        <!-- Emotion Tags -->
        <div class="mb-4">
          <div class="text-xs text-gray-600 mb-2">选择情绪标签（可多选）</div>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="tag in emotionTags"
              :key="tag.name"
              @click="toggleTag(tag.name)"
              class="px-3 py-1 rounded-full text-xs transition-colors"
              :class="selectedTags.includes(tag.name)
                ? 'bg-pink-100 text-pink-700 border border-pink-300'
                : 'bg-gray-50 text-gray-600 border border-gray-200 hover:bg-gray-100'"
            >
              {{ tag.emoji }} {{ tag.name }}
            </button>
          </div>
        </div>

        <!-- Submit Button -->
        <button
          @click="submitDiary"
          :disabled="!newDiaryText.trim() || isSubmitting"
          class="w-full py-2.5 rounded-xl font-medium text-white text-sm transition-all"
          :class="newDiaryText.trim()
            ? 'bg-pink-500 hover:bg-pink-600 active:scale-[0.98]'
            : 'bg-gray-300 cursor-not-allowed'"
        >
          {{ isSubmitting ? '保存中...' : '保存日记' }}
        </button>
      </div>

      <!-- Recent Diaries -->
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
          <span class="text-4xl mb-2 block">📝</span>
          <p class="text-sm">还没有日记，写下你的第一篇吧</p>
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="diary in diaryStore.diaries"
            :key="diary.id"
            class="bg-white rounded-xl p-4 border border-gray-100"
          >
            <div class="flex justify-between items-start mb-2">
              <span class="text-xs text-gray-500">
                {{ formatDateTime(diary.date) }}
              </span>
              <div class="flex gap-1">
                <span
                  v-for="tag in diary.emotion_tags"
                  :key="tag"
                  class="px-2 py-0.5 bg-pink-50 text-pink-600 text-xs rounded-full"
                >
                  {{ tag }}
                </span>
              </div>
            </div>
            <p class="text-gray-700 text-sm leading-relaxed">
              {{ diary.original_text || diary.processed_text }}
            </p>
            <div v-if="diary.mood_level" class="mt-2 text-xs text-gray-400">
              情绪评分: {{ diary.mood_level.toFixed(1) }}/10
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom Nav -->
    <BottomNav />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useDiaryStore } from '../stores/diary'
import BottomNav from '../components/BottomNav.vue'

const diaryStore = useDiaryStore()

const newDiaryText = ref('')
const selectedTags = ref([])
const isSubmitting = ref(false)
const selectedMood = ref(null)
const showSuccessToast = ref(false)

// Quick mood selection with predefined texts
const quickMoods = [
  { emoji: '😊', label: '很开心', text: '今天心情很好！', moodLevel: 9 },
  { emoji: '🙂', label: '不错', text: '今天感觉还不错', moodLevel: 7 },
  { emoji: '😐', label: '一般', text: '今天心情一般', moodLevel: 5 },
  { emoji: '😔', label: '低落', text: '今天心情有点低落', moodLevel: 3 },
  { emoji: '😢', label: '难过', text: '今天很难过', moodLevel: 2 },
]

function selectQuickMood(mood) {
  if (selectedMood.value?.emoji === mood.emoji) {
    selectedMood.value = null
    newDiaryText.value = ''
  } else {
    selectedMood.value = mood
    newDiaryText.value = mood.text
  }
}

const emotionTags = [
  { name: '平静', emoji: '😌' },
  { name: '开心', emoji: '😊' },
  { name: '焦虑', emoji: '😰' },
  { name: '低落', emoji: '😔' },
  { name: '烦躁', emoji: '😤' },
  { name: '疲惫', emoji: '😩' },
  { name: '压力大', emoji: '😣' },
  { name: '失眠', emoji: '😴' }
]

const isRecording = computed(() => diaryStore.isRecording)

function toggleTag(tagName) {
  const index = selectedTags.value.indexOf(tagName)
  if (index === -1) {
    selectedTags.value.push(tagName)
  } else {
    selectedTags.value.splice(index, 1)
  }
}

function toggleVoiceRecording() {
  if (isRecording.value) {
    // Stop recording
    diaryStore.setRecording(false)
    // In production, this would use Web Speech API
  } else {
    // Start recording
    diaryStore.setRecording(true)
    // Simulate transcription after 3 seconds
    setTimeout(() => {
      if (isRecording.value) {
        newDiaryText.value = '（语音转写内容）' + newDiaryText.value
        diaryStore.setRecording(false)
      }
    }, 3000)
  }
}

async function submitDiary() {
  if (!newDiaryText.value.trim() || isSubmitting.value) return

  isSubmitting.value = true
  try {
    const diaryData = {
      date: new Date().toISOString(),
      input_type: isRecording.value ? 'voice' : 'text',
      original_text: newDiaryText.value,
      emotion_tags: selectedTags.value
    }
    console.log('Saving diary:', diaryData)
    const result = await diaryStore.createDiary(diaryData)
    console.log('Diary saved successfully:', result)

    // Reset form
    newDiaryText.value = ''
    selectedTags.value = []
    selectedMood.value = null

    // Show success toast
    showSuccessToast.value = true
    setTimeout(() => {
      showSuccessToast.value = false
    }, 2000)

    // Scroll to top to show the new diary
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (error) {
    console.error('Failed to save diary:', error)
    alert('保存失败，请稍后重试')
  } finally {
    isSubmitting.value = false
  }
}

function formatDateTime(dateStr) {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`

  return date.toLocaleDateString('zh-CN', {
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

diaryStore.fetchDiaries()
</script>

<style scoped>
.diary-page {
  min-height: 100vh;
  background: #f9fafb;
}

/* Toast animation */
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
