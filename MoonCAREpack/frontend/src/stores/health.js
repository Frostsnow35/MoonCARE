import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { emotionAPI, menstrualAPI, biometricAPI } from '../api'

export const useHealthStore = defineStore('health', () => {
  // State
  const currentPhase = ref('unknown')
  const pmsRisk = ref(0.5)
  const moodLevel = ref(5.0)
  const phaseInfo = ref(null)
  const isLoading = ref(false)
  const lastUpdated = ref(null)

  // Biometric data
  const latestBiometric = ref(null)

  // Predictions
  const cyclePrediction = ref(null)
  const recommendations = ref([])

  // Computed
  const riskLevel = computed(() => {
    if (pmsRisk.value >= 0.8) return 'critical'
    if (pmsRisk.value >= 0.7) return 'high'
    if (pmsRisk.value >= 0.4) return 'medium'
    return 'low'
  })

  const phaseName = computed(() => {
    const names = {
      follicular: '卵泡期',
      ovulation: '排卵期',
      luteal: '黄体期',
      menstrual: '经期',
      unknown: '未知'
    }
    return names[currentPhase.value] || '未知'
  })

  const phaseEmoji = computed(() => {
    const emojis = {
      follicular: '🌱',
      ovulation: '🌸',
      luteal: '🌷',
      menstrual: '🌺',
      unknown: '❓'
    }
    return emojis[currentPhase.value] || '❓'
  })

  // Actions
  async function fetchEmotionState(userId = 1) {
    isLoading.value = true
    try {
      const result = await emotionAPI.predict(userId)
      currentPhase.value = result.phase
      pmsRisk.value = result.pms_risk
      moodLevel.value = result.mood_level
      lastUpdated.value = result.updated_at
    } catch (error) {
      console.error('Failed to fetch emotion state:', error)
    } finally {
      isLoading.value = false
    }
  }

  async function fetchPhaseInfo(userId = 1) {
    try {
      const result = await emotionAPI.getPhase(userId)
      phaseInfo.value = result
      currentPhase.value = result.phase
    } catch (error) {
      console.error('Failed to fetch phase info:', error)
    }
  }

  async function fetchCyclePrediction(userId = 1) {
    try {
      cyclePrediction.value = await menstrualAPI.predict(userId)
    } catch (error) {
      console.error('Failed to fetch cycle prediction:', error)
      cyclePrediction.value = null
    }
  }

  async function fetchRecommendations(userId = 1, context = 'mood_low') {
    try {
      const result = await emotionAPI.recommend(userId, context)
      recommendations.value = result.recommendations
    } catch (error) {
      console.error('Failed to fetch recommendations:', error)
      recommendations.value = []
    }
  }

  async function fetchLatestBiometric(userId = 1) {
    try {
      latestBiometric.value = await biometricAPI.getLatest(userId)
    } catch (error) {
      console.error('Failed to fetch latest biometric:', error)
      latestBiometric.value = null
    }
  }

  return {
    // State
    currentPhase,
    pmsRisk,
    moodLevel,
    phaseInfo,
    isLoading,
    lastUpdated,
    latestBiometric,
    cyclePrediction,
    recommendations,
    // Computed
    riskLevel,
    phaseName,
    phaseEmoji,
    // Actions
    fetchEmotionState,
    fetchPhaseInfo,
    fetchCyclePrediction,
    fetchRecommendations,
    fetchLatestBiometric
  }
})
