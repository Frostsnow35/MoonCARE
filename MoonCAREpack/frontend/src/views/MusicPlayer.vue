<template>
  <div class="music-page">
    <!-- Background Animation - inside music-page but constrained width -->
    <div v-if="isPlaying" class="bg-animation-container">
      <div class="bg-animation">
        <!-- Floating Bubbles -->
        <div v-for="i in 8" :key="i" class="bubble" :class="`bubble-${i}`"></div>

        <!-- Pulsing Gradient Orbs -->
        <div class="orb orb-1"></div>
        <div class="orb orb-2"></div>
        <div class="orb orb-3"></div>

        <!-- Sound Wave Lines -->
        <div class="wave-container">
          <div v-for="i in 20" :key="i" class="wave-bar" :style="`animation-delay: ${i * 0.05}s`"></div>
        </div>
      </div>
    </div>

    <div class="max-w-lg mx-auto pb-16 px-4 relative z-10">
      <!-- Header -->
      <div class="text-center pt-4 pb-3">
        <h1 class="text-lg font-bold text-gray-800 mb-0.5">🎵 音乐疗愈</h1>
        <p class="text-xs text-gray-500">{{ emotionMessage }}</p>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="flex flex-col items-center justify-center py-16">
        <div class="w-16 h-16 rounded-full bg-pink-100 flex items-center justify-center mb-3">
          <span class="text-3xl">🎧</span>
        </div>
        <p class="text-gray-500 text-sm">正在为您匹配音乐...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="flex flex-col items-center justify-center py-16">
        <div class="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mb-3">
          <span class="text-3xl">😢</span>
        </div>
        <p class="text-gray-600 mb-3 text-sm">{{ error }}</p>
        <button
          @click="loadMusic"
          class="px-5 py-2 bg-pink-400 text-white rounded-full hover:bg-pink-500 transition-colors text-sm"
        >
          重试
        </button>
      </div>

      <!-- Music Player -->
      <div v-else class="mt-4">
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <!-- Current Emotion Badge -->
          <div class="flex items-center justify-center mb-4">
            <span
              class="px-3 py-1 rounded-full text-xs font-medium"
              :class="emotionBadgeClass"
            >
              {{ emotionLabel }}
            </span>
          </div>

          <!-- Music Player Component -->
          <MusicPlayer
            :songs="songs"
            :auto-play="true"
            @song-change="handleSongChange"
            @play-state-change="handlePlayStateChange"
          />
        </div>

        <!-- Song Queue -->
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mt-3">
          <h3 class="font-medium text-gray-800 mb-2 flex items-center gap-1 text-sm">
            <span>📋</span>
            <span>播放列表</span>
          </h3>

          <div class="space-y-1.5">
            <button
              v-for="(song, index) in songs"
              :key="song.id"
              @click="playSong(index)"
              class="w-full flex items-center gap-2.5 p-2.5 rounded-lg hover:bg-pink-50 transition-colors text-left"
              :class="{ 'bg-pink-50': currentIndex === index }"
            >
              <span class="text-lg">{{ getSongEmoji(song.emotion_category) }}</span>
              <div class="flex-1 min-w-0">
                <div class="font-medium text-gray-800 text-sm truncate">{{ song.title }}</div>
                <div class="text-xs text-gray-500">{{ song.artist || '未知艺术家' }}</div>
              </div>
              <span v-if="currentIndex === index && isPlaying" class="text-pink-400 text-sm">
                🔊
              </span>
            </button>
          </div>

          <div v-if="songs.length === 0" class="text-center py-6 text-gray-400">
            <span class="text-3xl mb-1 block">🎶</span>
            <p class="text-sm">暂无音乐，请稍后再试</p>
          </div>
        </div>

        <!-- Mood Tips -->
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mt-3">
          <h3 class="font-medium text-gray-800 mb-1.5 flex items-center gap-1 text-sm">
            <span>💡</span>
            <span>疗愈小贴士</span>
          </h3>
          <p class="text-gray-600 text-xs leading-relaxed">
            {{ moodTip }}
          </p>
        </div>
      </div>
    </div>

    <!-- Bottom Nav -->
    <BottomNav />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { musicAPI, emotionAPI } from '../api'
import MusicPlayer from '../components/MusicPlayer.vue'
import BottomNav from '../components/BottomNav.vue'

const songs = ref([])
const currentEmotion = ref('normal')
const moodLevel = ref(5.0)
const currentIndex = ref(0)
const isPlaying = ref(false)
const isLoading = ref(true)
const error = ref(null)

const emotionLabels = {
  joy: '心情愉悦 🌟',
  normal: '心情平静 ☁️',
  anxiety: '有些焦虑 😰',
  sadness: '情绪低落 😢',
  calm: '放松状态 🧘'
}

const emotionBadgeClasses = {
  joy: 'bg-yellow-100 text-yellow-700',
  normal: 'bg-blue-100 text-blue-700',
  anxiety: 'bg-orange-100 text-orange-700',
  sadness: 'bg-purple-100 text-purple-700',
  calm: 'bg-green-100 text-green-700'
}

const moodTips = {
  joy: '愉悦的音乐能帮助您保持积极向上的心情，继续传递这份快乐吧！',
  normal: '轻柔的音乐有助于放松身心，享受这份宁静的时光。',
  anxiety: '深呼吸，让舒缓的音乐帮助您放松紧张的神经，一切都会好起来的。',
  sadness: '音乐是情感的容器，让这些温暖的旋律陪伴您，悲伤终会过去。',
  calm: '保持这个放松的状态，聆听内心的声音，感受当下的美好。'
}

const emotionMessage = computed(() => {
  const messages = {
    joy: '根据您愉悦的心情，为您推荐欢快的音乐',
    normal: '根据您平静的心情，为您推荐轻柔的音乐',
    anxiety: '根据您焦虑的心情，为您推荐舒缓的音乐',
    sadness: '根据您低落的心情，为您推荐安慰的音乐',
    calm: '根据您需要放松的心情，为您推荐放松的音乐'
  }
  return messages[currentEmotion.value] || '为您推荐疗愈音乐'
})

const emotionLabel = computed(() => emotionLabels[currentEmotion.value] || '心情平静')
const emotionBadgeClass = computed(() => emotionBadgeClasses[currentEmotion.value] || 'bg-gray-100 text-gray-700')
const moodTip = computed(() => moodTips[currentEmotion.value] || '音乐是灵魂的良药，愿这些旋律带给您平静与安慰。')

function getSongEmoji(category) {
  const emojis = {
    joy: '😊',
    normal: '😌',
    anxiety: '😰',
    sadness: '😢',
    calm: '☁️'
  }
  return emojis[category] || '🎵'
}

async function loadMusic() {
  isLoading.value = true
  error.value = null

  try {
    // Get user's current emotion state
    const emotionResult = await emotionAPI.predict(1)
    moodLevel.value = emotionResult.mood_level || 5.0

    // Determine emotion category based on mood level
    if (emotionResult.mood_level >= 7) {
      currentEmotion.value = 'joy'
    } else if (emotionResult.mood_level >= 4) {
      currentEmotion.value = 'normal'
    } else {
      currentEmotion.value = 'anxiety'
    }

    // Get recommended music
    const result = await musicAPI.recommend(1, currentEmotion.value)
    songs.value = result.recommended_songs || []
  } catch (err) {
    console.error('Failed to load music:', err)
    error.value = '加载音乐失败，请稍后再试'
  } finally {
    isLoading.value = false
  }
}

function playSong(index) {
  currentIndex.value = index
}

function handleSongChange(song) {
  const index = songs.value.findIndex(s => s.id === song.id)
  if (index !== -1) {
    currentIndex.value = index
  }
}

function handlePlayStateChange(playing) {
  isPlaying.value = playing
}

onMounted(() => {
  loadMusic()
})
</script>

<style scoped>
.music-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #fdf2f8 0%, #faf5ff 100%);
  position: relative;
}

/* Background Animation Container - constrained width wrapper */
.bg-animation-container {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 448px; /* max-w-lg equivalent */
  height: 600px;
  pointer-events: none;
  overflow: hidden;
  z-index: 15;
}

/* Background Animation - full width of container */
.bg-animation {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 100%;
  z-index: 16;
}

/* Floating Bubbles */
.bubble {
  position: absolute;
  bottom: -60px;
  border-radius: 50%;
  opacity: 0;
  animation: float-up 6s infinite ease-in-out;
  box-shadow: 0 0 20px rgba(244, 114, 182, 0.3), inset -5px -5px 15px rgba(255, 255, 255, 0.5), inset 5px 5px 15px rgba(196, 181, 253, 0.5);
}

.bubble-1 { left: 8%; width: 40px; height: 40px; animation-duration: 6s; background: linear-gradient(135deg, rgba(244,114,182,0.6) 0%, rgba(196,181,253,0.6) 100%); }
.bubble-2 { left: 25%; width: 28px; height: 28px; animation-duration: 7s; animation-delay: 0.5s; background: linear-gradient(135deg, rgba(196,181,253,0.5) 0%, rgba(244,114,182,0.5) 100%); }
.bubble-3 { left: 42%; width: 36px; height: 36px; animation-duration: 5.5s; animation-delay: 1s; background: linear-gradient(135deg, rgba(244,114,182,0.55) 0%, rgba(167,139,250,0.55) 100%); }
.bubble-4 { left: 58%; width: 32px; height: 32px; animation-duration: 6.5s; animation-delay: 1.5s; background: linear-gradient(135deg, rgba(167,139,250,0.5) 0%, rgba(244,114,182,0.5) 100%); }
.bubble-5 { left: 72%; width: 44px; height: 44px; animation-duration: 7.5s; animation-delay: 2s; background: linear-gradient(135deg, rgba(244,114,182,0.6) 0%, rgba(139,92,246,0.6) 100%); }
.bubble-6 { left: 88%; width: 24px; height: 24px; animation-duration: 5s; animation-delay: 2.5s; background: linear-gradient(135deg, rgba(139,92,246,0.5) 0%, rgba(244,114,182,0.5) 100%); }
.bubble-7 { left: 15%; width: 20px; height: 20px; animation-duration: 6s; animation-delay: 3s; background: linear-gradient(135deg, rgba(196,181,253,0.6) 0%, rgba(244,114,182,0.6) 100%); }
.bubble-8 { left: 65%; width: 48px; height: 48px; animation-duration: 8s; animation-delay: 3.5s; background: linear-gradient(135deg, rgba(244,114,182,0.4) 0%, rgba(167,139,250,0.4) 100%); }

@keyframes float-up {
  0% {
    transform: translateY(0) scale(1);
    opacity: 0;
  }
  10% {
    opacity: 0.8;
  }
  50% {
    opacity: 0.6;
  }
  90% {
    opacity: 0.1;
  }
  100% {
    transform: translateY(-600px) scale(0.3);
    opacity: 0;
  }
}

/* Pulsing Orbs */
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(48px);
  opacity: 0.4;
  animation: pulse 4s infinite ease-in-out;
}

.orb-1 {
  top: 15%;
  left: 10%;
  width: 120px;
  height: 120px;
  background: #f9a8d4;
}

.orb-2 {
  top: 25%;
  right: 10%;
  width: 140px;
  height: 140px;
  background: #c4b5fd;
  animation-delay: 1s;
}

.orb-3 {
  bottom: 20%;
  left: 20%;
  width: 100px;
  height: 100px;
  background: #fbcfe8;
  animation-delay: 2s;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 0.3;
  }
  50% {
    transform: scale(1.2);
    opacity: 0.5;
  }
}

/* Sound Wave Bars */
.wave-container {
  position: absolute;
  bottom: 60px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 4px;
  height: 64px;
}

.wave-bar {
  width: 4px;
  background: linear-gradient(to top, #f9a8d4 0%, #c4b5fd 100%);
  border-radius: 2px;
  animation: wave 1.2s infinite ease-in-out;
}

@keyframes wave {
  0%, 100% {
    height: 8px;
    opacity: 0.4;
  }
  50% {
    height: 48px;
    opacity: 0.9;
  }
}
</style>