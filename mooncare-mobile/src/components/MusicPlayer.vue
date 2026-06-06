<template>
  <div class="music-player">
    <audio
      ref="audioRef"
      class="native-audio-probe"
      playsinline
      webkit-playsinline="true"
      preload="metadata"
    ></audio>

    <div v-if="currentSong" class="current-song">
      <div class="disc" :class="{ spinning: isPlaying }">
        <span>{{ getSongMark(currentSong.emotion_category) }}</span>
      </div>

      <div class="song-meta">
        <div class="song-title">{{ currentSong.title }}</div>
        <div class="song-artist">{{ currentSong.artist || '未知艺术家' }}</div>
        <p v-if="currentSong.playback_notice" class="song-notice">{{ currentSong.playback_notice }}</p>
      </div>
    </div>

    <div v-if="currentSong" class="progress-section">
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: `${progress}%` }"></div>
      </div>
      <input
        v-model="seekPercent"
        class="progress-slider"
        type="range"
        min="0"
        max="100"
        aria-label="播放进度"
        @change="handleSeek"
      />
      <div class="time-row">
        <span>{{ formatTime(currentTime) }}</span>
        <span>{{ formatTime(duration) }}</span>
      </div>
    </div>

    <div class="controls" aria-label="Music playback controls">
      <button type="button" class="control-button" aria-label="上一首" @click="playPrevious">
        <span>&lt;</span>
      </button>

      <button type="button" class="play-button" :aria-label="isPlaying ? '暂停' : '播放'" @click="togglePlay">
        <span>{{ isPlaying ? '||' : '>' }}</span>
      </button>

      <button type="button" class="control-button" aria-label="下一首" @click="playNext">
        <span>&gt;</span>
      </button>
    </div>

    <div class="volume-row">
      <span class="volume-icon">L</span>
      <input
        v-model="volume"
        type="range"
        min="0"
        max="100"
        class="volume-slider"
        aria-label="音量"
        @input="updateVolume"
      />
      <span class="volume-icon">H</span>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { Capacitor, CapacitorHttp } from '@capacitor/core'
import { getBackendOrigin } from '../services/apiConfig'

const props = defineProps({
  songs: {
    type: Array,
    default: () => [],
  },
  selectedIndex: {
    type: Number,
    default: 0,
  },
  autoPlay: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits([
  'songChange',
  'playStateChange',
  'playbackError',
  'playbackStarted',
])

const audioRef = ref(null)
const currentIndex = ref(0)
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const volume = ref(70)
const seekPercent = ref(0)
const generatedObjectUrls = ref(new Set())

const currentSong = computed(() => props.songs[currentIndex.value] || null)

function getAudio() {
  return audioRef.value
}

const progress = computed(() => {
  if (!duration.value) return 0
  return Math.min(100, Math.max(0, (currentTime.value / duration.value) * 100))
})

function getSongMark(category) {
  const marks = {
    joy: '悦',
    normal: '柔',
    anxiety: '缓',
    sadness: '安',
    calm: '静',
  }
  return marks[category] || '乐'
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

function describeMediaError(eventOrError) {
  const audio = getAudio()
  const mediaError = audio?.error

  if (mediaError?.code === 1) return '播放被中断'
  if (mediaError?.code === 2) return '音频下载失败'
  if (mediaError?.code === 3) return '音频解码失败'
  if (mediaError?.code === 4) return '设备暂不支持这种音频格式'

  return eventOrError?.message || '当前暂时无法播放这首音乐'
}

function reportPlaybackError(error) {
  emitPlaybackState(false)
  emit('playbackError', {
    song: currentSong.value,
    message: describeMediaError(error),
  })
}

function revokeObjectUrl() {
  generatedObjectUrls.value.forEach(url => URL.revokeObjectURL(url))
  generatedObjectUrls.value.clear()
}

function isBackendHosted(url) {
  if (!url) return false
  return url.startsWith(getBackendOrigin())
}

function inferMimeType(url) {
  const normalized = String(url || '').toLowerCase()
  if (normalized.endsWith('.mp3')) return 'audio/mpeg'
  if (normalized.endsWith('.wav')) return 'audio/wav'
  if (normalized.endsWith('.ogg')) return 'audio/ogg'
  if (normalized.endsWith('.m4a')) return 'audio/mp4'
  if (normalized.endsWith('.aac')) return 'audio/aac'
  if (normalized.endsWith('.flac')) return 'audio/flac'
  return 'audio/mpeg'
}

function base64ToBlob(base64, mimeType) {
  const cleanBase64 = String(base64 || '').replace(/^data:[^;]+;base64,/, '')
  const binary = atob(cleanBase64)
  const bytes = new Uint8Array(binary.length)

  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index)
  }

  return new Blob([bytes], { type: mimeType })
}

function registerPlayableObjectUrl(blob) {
  const objectUrl = URL.createObjectURL(blob)
  generatedObjectUrls.value.add(objectUrl)
  return objectUrl
}

async function fetchNativeAudioBlob(sourceUrl) {
  const response = await CapacitorHttp.get({
    url: sourceUrl,
    responseType: 'blob',
    readTimeout: 15000,
    connectTimeout: 10000,
    shouldEncodeUrlParams: false,
  })

  if (response.status < 200 || response.status >= 300) {
    throw new Error(`Audio request failed (${response.status})`)
  }

  const contentType =
    response.headers?.['content-type'] ||
    response.headers?.['Content-Type'] ||
    inferMimeType(sourceUrl)

  if (response.data instanceof Blob) {
    return response.data
  }

  if (typeof response.data === 'string') {
    return base64ToBlob(response.data, contentType)
  }

  throw new Error('Native audio response could not be parsed')
}

async function resolvePlayableUrl(song) {
  const sourceUrl = song?.previewUrl || song?.url || ''
  if (!sourceUrl) return ''

  if (!isBackendHosted(sourceUrl)) {
    return sourceUrl
  }

  if (song.__resolvedPlayableUrl) {
    return song.__resolvedPlayableUrl
  }

  const blob = Capacitor.isNativePlatform()
    ? await fetchNativeAudioBlob(sourceUrl)
    : await (async () => {
        const response = await fetch(sourceUrl, {
          method: 'GET',
          cache: 'no-store',
        })

        if (!response.ok) {
          throw new Error(`Audio request failed (${response.status})`)
        }

        return response.blob()
      })()

  song.__resolvedPlayableUrl = registerPlayableObjectUrl(blob)
  return song.__resolvedPlayableUrl
}

function clearLoadedSong() {
  const audio = getAudio()
  if (!audio) return
  audio.removeAttribute('src')
  audio.dataset.songUrl = ''
  audio.load()
  currentTime.value = 0
  duration.value = 0
  seekPercent.value = 0
}

function prepareSongState() {
  currentTime.value = 0
  duration.value = 0
  seekPercent.value = 0
  emit('songChange', currentSong.value)
}

async function ensureSongLoaded() {
  const audio = getAudio()
  if (!audio) return false

  if (!currentSong.value?.url && !currentSong.value?.previewUrl) {
    clearLoadedSong()
    return false
  }

  if (audio.dataset.songUrl === currentSong.value.url && audio.src) {
    return true
  }

  const playableUrl = await resolvePlayableUrl(currentSong.value)
  audio.src = playableUrl
  audio.dataset.songUrl = currentSong.value.url || currentSong.value.previewUrl || ''
  audio.load()
  return true
}

async function primeCurrentSong() {
  try {
    await ensureSongLoaded()
  } catch (error) {
    reportPlaybackError(error)
  }
}

async function startPlayback() {
  const audio = getAudio()
  if (!audio) return
  if (!currentSong.value) return

  try {
    const loaded = await ensureSongLoaded()
    if (!loaded) return
    await audio.play()
    emitPlaybackState(true)
    emit('playbackStarted', currentSong.value)
  } catch (error) {
    reportPlaybackError(error)
  }
}

async function playIndex(index) {
  if (index < 0 || index >= props.songs.length) return
  const audio = getAudio()

  if (currentIndex.value !== index) {
    currentIndex.value = index
    clearLoadedSong()
    prepareSongState()
  } else if (!audio?.src) {
    prepareSongState()
  }

  await startPlayback()
}

async function playCurrent() {
  if (!currentSong.value) return
  await startPlayback()
}

function pausePlayback() {
  const audio = getAudio()
  if (!audio) return
  audio.pause()
  emitPlaybackState(false)
}

function togglePlay() {
  if (!currentSong.value) return
  if (isPlaying.value) {
    pausePlayback()
    return
  }
  startPlayback()
}

function setIndex(index, shouldPlay = false) {
  if (index < 0 || index >= props.songs.length) return
  currentIndex.value = index
  clearLoadedSong()
  prepareSongState()

  if (shouldPlay || props.autoPlay) {
    startPlayback()
  } else {
    emitPlaybackState(false)
    primeCurrentSong()
  }
}

function playNext(forcePlay = isPlaying.value) {
  if (!props.songs.length) return
  const nextIndex = currentIndex.value < props.songs.length - 1 ? currentIndex.value + 1 : 0
  setIndex(nextIndex, forcePlay)
}

function playPrevious(forcePlay = isPlaying.value) {
  if (!props.songs.length) return
  const previousIndex = currentIndex.value > 0 ? currentIndex.value - 1 : props.songs.length - 1
  setIndex(previousIndex, forcePlay)
}

function updateVolume() {
  const audio = getAudio()
  if (!audio) return
  audio.volume = volume.value / 100
}

function handleTimeUpdate() {
  const audio = getAudio()
  if (!audio) return
  currentTime.value = audio.currentTime
  seekPercent.value = progress.value
}

function handleLoadedMetadata() {
  const audio = getAudio()
  if (!audio) return
  duration.value = Number.isFinite(audio.duration) ? audio.duration : 0
  seekPercent.value = progress.value
}

function handleEnded() {
  emitPlaybackState(false)
  playNext(true)
}

function handleSeek() {
  if (!duration.value) return
  audio.currentTime = duration.value * (Number(seekPercent.value) / 100)
}

watch(
  () => props.songs,
  (newSongs) => {
    if (!newSongs.length) {
      pausePlayback()
      currentIndex.value = 0
      clearLoadedSong()
      return
    }

    const nextIndex = Math.min(props.selectedIndex, newSongs.length - 1)
    setIndex(nextIndex, false)
  },
  { immediate: true, deep: true },
)

watch(
  () => props.selectedIndex,
  (index, previousIndex) => {
    if (index === previousIndex || !props.songs.length) return
    setIndex(index, false)
  },
)

onMounted(() => {
  const audio = getAudio()
  if (!audio) return

  audio.volume = volume.value / 100
  audio.addEventListener('timeupdate', handleTimeUpdate)
  audio.addEventListener('loadedmetadata', handleLoadedMetadata)
  audio.addEventListener('ended', handleEnded)
  audio.addEventListener('error', reportPlaybackError)
})

onUnmounted(() => {
  const audio = getAudio()
  if (!audio) return
  audio.pause()
  revokeObjectUrl()
  audio.removeEventListener('timeupdate', handleTimeUpdate)
  audio.removeEventListener('loadedmetadata', handleLoadedMetadata)
  audio.removeEventListener('ended', handleEnded)
  audio.removeEventListener('error', reportPlaybackError)
})

defineExpose({
  playCurrent,
  playIndex,
  primeCurrentSong,
  pausePlayback,
})
</script>

<style scoped>
.music-player {
  display: grid;
  gap: 16px;
}

.native-audio-probe {
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
  position: absolute;
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
  font-weight: 800;
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

.song-notice {
  margin: 6px 0 0;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.5;
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

.progress-slider {
  width: 100%;
  margin-top: 8px;
  accent-color: #ec4899;
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
  font-weight: 800;
}

.play-button {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ec4899 0%, #2563eb 100%);
  box-shadow: 0 16px 28px rgba(37, 99, 235, 0.2);
  font-size: 24px;
  font-weight: 800;
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
  font-size: 12px;
  font-weight: 700;
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
