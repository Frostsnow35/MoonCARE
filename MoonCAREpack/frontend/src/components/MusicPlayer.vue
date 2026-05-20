<template>
  <div class="music-player">
    <!-- Current Song Info with Spinning Disc -->
    <div v-if="currentSong" class="current-song mb-4">
      <div class="flex items-center gap-3">
        <!-- Spinning Disc -->
        <div class="relative">
          <div
            class="w-14 h-14 rounded-full bg-gradient-to-br from-pink-400 to-purple-500 flex items-center justify-center shadow-lg"
            :class="{ 'animate-spin-slow': isPlaying }"
          >
            <div class="w-11 h-11 rounded-full bg-white/30 flex items-center justify-center">
              <span class="text-xl">{{ getSongEmoji(currentSong.emotion_category) }}</span>
            </div>
          </div>
          <!-- Center dot when not playing -->
          <div v-if="!isPlaying" class="absolute inset-0 flex items-center justify-center">
            <div class="w-3 h-3 rounded-full bg-white/80 shadow"></div>
          </div>
        </div>
        <div class="flex-1 min-w-0">
          <div class="font-semibold text-gray-800 truncate">{{ currentSong.title }}</div>
          <div class="text-sm text-gray-500">{{ currentSong.artist || '未知艺术家' }}</div>
        </div>
      </div>
    </div>

    <!-- Progress Bar -->
    <div v-if="currentSong" class="progress-section mb-4">
      <div class="h-1.5 bg-white/50 rounded-full overflow-hidden backdrop-blur-sm">
        <div
          class="h-full bg-gradient-to-r from-pink-400 to-purple-400 rounded-full transition-all duration-300"
          :style="{ width: `${progress}%` }"
        ></div>
      </div>
      <div class="flex justify-between text-xs text-gray-500/70 mt-1">
        <span>{{ formatTime(currentTime) }}</span>
        <span>{{ formatTime(duration) }}</span>
      </div>
    </div>

    <!-- Controls -->
    <div class="flex items-center justify-center gap-8">
      <button
        @click="playPrevious"
        class="w-11 h-11 rounded-full bg-gradient-to-br from-pink-100 to-purple-100 hover:from-pink-200 hover:to-purple-200 flex items-center justify-center transition-all shadow-md hover:shadow-lg active:scale-95"
      >
        <svg class="w-5 h-5 text-pink-500" viewBox="0 0 24 24" fill="currentColor">
          <path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/>
        </svg>
      </button>

      <!-- Main Play Button -->
      <button
        @click="togglePlay"
        class="w-16 h-16 rounded-full bg-gradient-to-br from-pink-400 to-purple-500 hover:from-pink-500 hover:to-purple-600 flex items-center justify-center transition-all shadow-xl hover:shadow-2xl active:scale-95"
      >
        <svg v-if="isPlaying" class="w-7 h-7 text-white ml-0.5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
        </svg>
        <svg v-else class="w-7 h-7 text-white ml-1" viewBox="0 0 24 24" fill="currentColor">
          <path d="M8 5v14l11-7z"/>
        </svg>
      </button>

      <button
        @click="playNext"
        class="w-11 h-11 rounded-full bg-gradient-to-br from-pink-100 to-purple-100 hover:from-pink-200 hover:to-purple-200 flex items-center justify-center transition-all shadow-md hover:shadow-lg active:scale-95"
      >
        <svg class="w-5 h-5 text-pink-500" viewBox="0 0 24 24" fill="currentColor">
          <path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z"/>
        </svg>
      </button>
    </div>

    <!-- Volume Control -->
    <div class="flex items-center gap-3 mt-4">
      <svg class="w-4 h-4 text-pink-400 opacity-70" viewBox="0 0 24 24" fill="currentColor">
        <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
      </svg>
      <input
        type="range"
        min="0"
        max="100"
        v-model="volume"
        @input="updateVolume"
        class="flex-1 h-1.5 bg-gradient-to-r from-pink-200 to-purple-200 rounded-full appearance-none cursor-pointer"
      />
      <svg class="w-4 h-4 text-pink-400 opacity-70" viewBox="0 0 24 24" fill="currentColor">
        <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
      </svg>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  songs: {
    type: Array,
    default: () => []
  },
  autoPlay: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['songChange', 'playStateChange'])

// Create audio element immediately
const audio = ref(new Audio())
const currentIndex = ref(0)
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const volume = ref(70)

// Set initial volume
audio.value.volume = volume.value / 100

const currentSong = computed(() => {
  return props.songs[currentIndex.value] || null
})

const progress = computed(() => {
  if (duration.value === 0) return 0
  return (currentTime.value / duration.value) * 100
})

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

function formatTime(seconds) {
  if (isNaN(seconds)) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function togglePlay() {
  if (!currentSong.value) return

  if (isPlaying.value) {
    audio.value.pause()
    isPlaying.value = false
  } else {
    audio.value.src = currentSong.value.url
    audio.value.play().then(() => {
      isPlaying.value = true
    }).catch(err => {
      console.error('Play failed:', err)
    })
  }
  emit('playStateChange', isPlaying.value)
}

function playNext() {
  if (currentIndex.value < props.songs.length - 1) {
    currentIndex.value++
    loadAndPlay()
  }
}

function playPrevious() {
  if (currentIndex.value > 0) {
    currentIndex.value--
    loadAndPlay()
  }
}

function loadAndPlay() {
  if (!currentSong.value) return

  audio.value.src = currentSong.value.url
  audio.value.load()
  if (props.autoPlay) {
    const playPromise = audio.value.play()
    if (playPromise !== undefined) {
      playPromise.then(() => {
        isPlaying.value = true
      }).catch(err => {
        console.error('Auto-play failed:', err)
        isPlaying.value = false
      })
    }
  }
  emit('songChange', currentSong.value)
}

function updateVolume() {
  if (audio.value) {
    audio.value.volume = volume.value / 100
  }
}

function handleTimeUpdate() {
  if (audio.value) {
    currentTime.value = audio.value.currentTime
  }
}

function handleLoadedMetadata() {
  if (audio.value) {
    duration.value = audio.value.duration
  }
}

function handleEnded() {
  // Auto play next song
  playNext()
}

watch(() => props.songs, (newSongs) => {
  if (newSongs.length > 0 && !currentSong.value) {
    currentIndex.value = 0
    loadAndPlay()
  }
}, { immediate: true })

onMounted(() => {
  // Audio already created in setup, just add listeners
  audio.value.addEventListener('timeupdate', handleTimeUpdate)
  audio.value.addEventListener('loadedmetadata', handleLoadedMetadata)
  audio.value.addEventListener('ended', handleEnded)
})

onUnmounted(() => {
  if (audio.value) {
    audio.value.pause()
    audio.value.removeEventListener('timeupdate', handleTimeUpdate)
    audio.value.removeEventListener('loadedmetadata', handleLoadedMetadata)
    audio.value.removeEventListener('ended', handleEnded)
  }
})
</script>

<style scoped>
input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 12px;
  height: 12px;
  background: linear-gradient(to right, #fb7185, #a855f7);
  border-radius: 50%;
  cursor: pointer;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.animate-spin-slow {
  animation: spin 8s linear infinite;
}
</style>