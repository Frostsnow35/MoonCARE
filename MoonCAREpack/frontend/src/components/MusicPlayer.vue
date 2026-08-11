<template>
  <div class="music-player">
    <div v-if="currentSong" class="current-song">
      <div class="disc" :class="{ spinning: isPlaying }">
        <span>{{ getSongEmoji(currentSong.emotion_category) }}</span>
      </div>
      <div class="song-meta">
        <div class="song-title">{{ currentSong.title }}</div>
        <div class="song-artist">{{ currentSong.artist || '未知艺术家' }}</div>
      </div>
    </div>

    <div v-if="currentSong" class="progress-section">
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: `${progress}%` }"></div>
      </div>
      <div class="time-row">
        <span>{{ formatTime(currentTime) }}</span>
        <span>{{ formatTime(duration) }}</span>
      </div>
    </div>

    <div class="controls" aria-label="音乐播放控制">
      <button type="button" class="control-button" aria-label="上一首" @click="playPrevious">
        <span>⏮</span>
      </button>

      <button type="button" class="play-button" :aria-label="isPlaying ? '暂停' : '播放'" @click="togglePlay">
        <span>{{ isPlaying ? '⏸' : '▶' }}</span>
      </button>

      <button type="button" class="control-button" aria-label="下一首" @click="playNext">
        <span>⏭</span>
      </button>
    </div>

    <div class="volume-row">
      <span class="volume-icon">🔉</span>
      <input
        v-model="volume"
        type="range"
        min="0"
        max="100"
        class="volume-slider"
        aria-label="音量"
        @input="updateVolume"
      />
      <span class="volume-icon">🔊</span>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { resolveMediaUrl } from '../config/runtime'

const props = defineProps({
  songs: {
    type: Array,
    default: () => []
  },
  selectedIndex: {
    type: Number,
    default: 0
  },
  autoPlay: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['songChange', 'playStateChange', 'playbackError', 'playbackStarted'])

const audio = ref(new Audio())
const currentIndex = ref(0)
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const volume = ref(70)

audio.value.volume = volume.value / 100

const currentSong = computed(() => props.songs[currentIndex.value] || null)

const progress = computed(() => {
  if (!duration.value) return 0
  return Math.min(100, Math.max(0, (currentTime.value / duration.value) * 100))
})

function getSongEmoji(category) {
  const emojis = {
    joy: '😊',
    normal: '🌿',
    anxiety: '🫧',
    sadness: '🌙',
    calm: '☁️'
  }
  return emojis[category] || '🎵'
}

function formatTime(seconds) {
  if (!Number.isFinite(seconds)) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function emitPlaybackState(playing) {
  isPlaying.value = playing
  emit('playStateChange', playing)
}

function reportPlaybackError(error) {
  emitPlaybackState(false)
  emit('playbackError', {
    song: currentSong.value,
    message: error?.message || '音频暂时无法播放'
  })
}

function resolveSongUrl(url) {
  return resolveMediaUrl(url)
}

async function startPlayback() {
  if (!currentSong.value) return

  try {
    const resolved = resolveSongUrl(currentSong.value.url)
    if (audio.value.src !== resolved) {
      audio.value.src = resolved
      audio.value.load()
    }
    await audio.value.play()
    emitPlaybackState(true)
    emit('playbackStarted', currentSong.value)
  } catch (error) {
    reportPlaybackError(error)
  }
}

function pausePlayback() {
  audio.value.pause()
  emitPlaybackState(false)
}

function togglePlay() {
  if (!currentSong.value) return
  if (isPlaying.value) {
    pausePlayback()
  } else {
    startPlayback()
  }
}

function setIndex(index, shouldPlay = false) {
  if (index < 0 || index >= props.songs.length) return
  currentIndex.value = index
  currentTime.value = 0
  duration.value = 0
  audio.value.src = resolveSongUrl(currentSong.value.url)
  audio.value.load()
  emit('songChange', currentSong.value)
  if (shouldPlay || props.autoPlay) {
    startPlayback()
  } else {
    emitPlaybackState(false)
  }
}

function playNext() {
  const nextIndex = currentIndex.value < props.songs.length - 1 ? currentIndex.value + 1 : 0
  setIndex(nextIndex, isPlaying.value)
}

function playPrevious() {
  const previousIndex = currentIndex.value > 0 ? currentIndex.value - 1 : props.songs.length - 1
  setIndex(previousIndex, isPlaying.value)
}

function updateVolume() {
  audio.value.volume = volume.value / 100
}

function handleTimeUpdate() {
  currentTime.value = audio.value.currentTime
}

function handleLoadedMetadata() {
  duration.value = Number.isFinite(audio.value.duration) ? audio.value.duration : 0
}

function handleEnded() {
  emitPlaybackState(false)
  playNext()
}

watch(() => props.songs, (newSongs) => {
  if (!newSongs.length) {
    pausePlayback()
    currentIndex.value = 0
    return
  }
  const nextIndex = Math.min(props.selectedIndex, newSongs.length - 1)
  setIndex(nextIndex, false)
}, { immediate: true })

watch(() => props.selectedIndex, (index, previousIndex) => {
  if (index === previousIndex || !props.songs.length) return
  setIndex(index, true)
})

onMounted(() => {
  audio.value.addEventListener('timeupdate', handleTimeUpdate)
  audio.value.addEventListener('loadedmetadata', handleLoadedMetadata)
  audio.value.addEventListener('ended', handleEnded)
  audio.value.addEventListener('error', reportPlaybackError)
})

onUnmounted(() => {
  audio.value.pause()
  audio.value.removeEventListener('timeupdate', handleTimeUpdate)
  audio.value.removeEventListener('loadedmetadata', handleLoadedMetadata)
  audio.value.removeEventListener('ended', handleEnded)
  audio.value.removeEventListener('error', reportPlaybackError)
})
</script>

<style scoped>
.music-player {
  display: grid;
  gap: 16px;
}

.current-song {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr);
  gap: 14px;
  align-items: center;
}

.disc {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #f472b6 0%, #60a5fa 100%);
  box-shadow: 0 14px 26px rgba(244, 114, 182, 0.26);
  color: #ffffff;
  font-size: 26px;
}

.spinning {
  animation: spin 9s linear infinite;
}

.song-meta {
  min-width: 0;
}

.song-title {
  font-size: 16px;
  font-weight: 700;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.song-artist {
  margin-top: 4px;
  font-size: 13px;
  color: #64748b;
}

.progress-track {
  width: 100%;
  height: 8px;
  border-radius: 999px;
  overflow: hidden;
  background: #e5e7eb;
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #ec4899 0%, #38bdf8 100%);
  transition: width 180ms ease;
}

.time-row {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
}

.controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 18px;
}

.control-button,
.play-button {
  border: 0;
  cursor: pointer;
  display: grid;
  place-items: center;
  color: #ffffff;
  transition: transform 160ms ease, box-shadow 160ms ease;
}

.control-button {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: #dbeafe;
  color: #2563eb;
  font-size: 18px;
}

.play-button {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ec4899 0%, #2563eb 100%);
  box-shadow: 0 16px 28px rgba(37, 99, 235, 0.2);
  font-size: 24px;
}

.control-button:active,
.play-button:active {
  transform: scale(0.96);
}

.volume-row {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) 24px;
  gap: 10px;
  align-items: center;
}

.volume-icon {
  text-align: center;
  color: #64748b;
  font-size: 15px;
}

.volume-slider {
  width: 100%;
  accent-color: #ec4899;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
