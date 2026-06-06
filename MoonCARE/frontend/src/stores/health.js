import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { biometricAPI, emotionAPI, menstrualAPI } from '../api'

export const useHealthStore = defineStore('health', () => {
  const currentPhase = ref('unknown')
  const pmsRisk = ref(0.5)
  const moodLevel = ref(5)
  const phaseInfo = ref(null)
  const isLoading = ref(false)
  const lastUpdated = ref(null)
  const latestBiometric = ref(null)
  const cyclePrediction = ref(null)
  const recommendations = ref([])

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
      unknown: '待判断'
    }
    return names[currentPhase.value] || '待判断'
  })

  const phaseEmoji = computed(() => {
    const emojis = {
      follicular: '🌱',
      ovulation: '🌼',
      luteal: '🌙',
      menstrual: '🩸',
      unknown: '·'
    }
    return emojis[currentPhase.value] || '·'
  })

  async function fetchEmotionState(days = 7) {
    isLoading.value = true
    try {
      const result = await emotionAPI.predict(days)
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

  async function fetchPhaseInfo() {
    try {
      const result = await emotionAPI.getPhase()
      phaseInfo.value = result
      currentPhase.value = result.phase
    } catch (error) {
      console.error('Failed to fetch phase info:', error)
    }
  }

  async function fetchCyclePrediction() {
    try {
      cyclePrediction.value = await menstrualAPI.predict()
    } catch (error) {
      console.error('Failed to fetch cycle prediction:', error)
      cyclePrediction.value = null
    }
  }

  async function fetchRecommendations(context = 'mood_low') {
    try {
      const result = await emotionAPI.recommend(context)
      recommendations.value = result.recommendations
    } catch (error) {
      console.error('Failed to fetch recommendations:', error)
      recommendations.value = []
    }
  }

  async function fetchLatestBiometric() {
    try {
      latestBiometric.value = await biometricAPI.getLatest()
    } catch (error) {
      console.error('Failed to fetch latest biometric:', error)
      latestBiometric.value = null
    }
  }

  return {
    currentPhase,
    pmsRisk,
    moodLevel,
    phaseInfo,
    isLoading,
    lastUpdated,
    latestBiometric,
    cyclePrediction,
    recommendations,
    riskLevel,
    phaseName,
    phaseEmoji,
    fetchEmotionState,
    fetchPhaseInfo,
    fetchCyclePrediction,
    fetchRecommendations,
    fetchLatestBiometric
  }
})
