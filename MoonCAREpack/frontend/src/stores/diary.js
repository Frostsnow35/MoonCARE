import { defineStore } from 'pinia'
import { ref } from 'vue'
import { diaryAPI } from '../api'

export const useDiaryStore = defineStore('diary', () => {
  // State
  const diaries = ref([])
  const currentDiary = ref(null)
  const isLoading = ref(false)
  const total = ref(0)

  // Voice recording state
  const isRecording = ref(false)
  const recordingTranscript = ref('')

  // Actions
  async function fetchDiaries(params = { limit: 30, offset: 0 }) {
    isLoading.value = true
    try {
      const result = await diaryAPI.list(params)
      diaries.value = result.diaries
      total.value = result.total
    } catch (error) {
      console.error('Failed to fetch diaries:', error)
    } finally {
      isLoading.value = false
    }
  }

  async function createDiary(data) {
    try {
      const result = await diaryAPI.create(data)
      // Convert to plain object for proper Vue reactivity
      const plainDiary = JSON.parse(JSON.stringify(result))
      diaries.value.unshift(plainDiary)
      total.value++
      return plainDiary
    } catch (error) {
      console.error('Failed to create diary:', error)
      throw error
    }
  }

  async function updateDiary(id, data) {
    try {
      const result = await diaryAPI.update(id, data)
      const index = diaries.value.findIndex(d => d.id === id)
      if (index !== -1) {
        diaries.value[index] = result
      }
      return result
    } catch (error) {
      console.error('Failed to update diary:', error)
      throw error
    }
  }

  async function deleteDiary(id) {
    try {
      await diaryAPI.delete(id)
      diaries.value = diaries.value.filter(d => d.id !== id)
      total.value--
    } catch (error) {
      console.error('Failed to delete diary:', error)
      throw error
    }
  }

  function setRecording(value) {
    isRecording.value = value
    if (!value) {
      recordingTranscript.value = ''
    }
  }

  function setTranscript(text) {
    recordingTranscript.value = text
  }

  return {
    // State
    diaries,
    currentDiary,
    isLoading,
    total,
    isRecording,
    recordingTranscript,
    // Actions
    fetchDiaries,
    createDiary,
    updateDiary,
    deleteDiary,
    setRecording,
    setTranscript
  }
})
