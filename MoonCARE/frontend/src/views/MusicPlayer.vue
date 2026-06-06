<template>
  <div class="app-page">
    <main class="music-shell">
      <header class="page-card-soft p-5">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="section-label">音乐</p>
            <h1 class="page-title mt-3">舒缓播放</h1>
            <p class="page-subtitle">
              这里保留为二级工具，适合在聊天或日记之后切过来听一会儿，让情绪有个落点。
            </p>
          </div>
          <button type="button" class="icon-button shadow-none" :disabled="isLoading" aria-label="刷新" @click="loadMusic">
            ↻
          </button>
        </div>
      </header>

      <section class="page-card p-4">
        <input
          ref="fileInput"
          type="file"
          class="hidden-input"
          accept="audio/*,.mp3,.wav,.ogg,.m4a,.aac,.flac"
          @change="handleFileChange"
        />
        <button type="button" class="primary-button w-full" :disabled="uploading" @click="openFilePicker">
          上传本地音乐
        </button>
        <p v-if="uploadMessage" class="upload-message">{{ uploadMessage }}</p>
      </section>

      <section v-if="isLoading" class="page-card p-8 text-center text-sm text-slate-500">
        正在加载音乐...
      </section>

      <section v-else-if="error" class="page-card p-8 text-center">
        <p class="text-sm leading-6 text-slate-500">{{ error }}</p>
        <button type="button" class="secondary-button mt-4 w-full" @click="loadMusic">重试</button>
      </section>

      <template v-else>
        <section class="page-card p-4">
          <MusicPlayer
            :songs="songs"
            :selected-index="currentIndex"
            :auto-play="false"
            @song-change="handleSongChange"
            @play-state-change="handlePlayStateChange"
            @playback-error="handlePlaybackError"
          />

          <div v-if="currentSong" class="mt-4 grid grid-cols-2 gap-3">
            <button type="button" class="secondary-button border-blue-200 text-blue-700" :disabled="feedbackPending" @click="likeCurrentSong">
              喜欢
            </button>
            <button type="button" class="ghost-button border border-gray-200 text-slate-600" :disabled="feedbackPending" @click="dislikeCurrentSong">
              不合适
            </button>
          </div>

          <p v-if="feedbackMessage" class="feedback-message">{{ feedbackMessage }}</p>
          <p v-if="playbackError" class="error-text">{{ playbackError }}</p>
        </section>

        <section v-if="likedSongs.length" class="page-card border-pink-100 p-4">
          <div class="section-title">
            <h2>我喜欢的音乐</h2>
            <span>{{ likedSongs.length }} 首</span>
          </div>

          <div class="song-list">
            <button
              v-for="song in likedSongs"
              :key="`liked-${song.id}-${song.url}`"
              type="button"
              class="song-item"
              @click="playLikedSong(song)"
            >
              <span class="song-index">♥</span>
              <span class="song-copy">
                <strong>{{ song.title }}</strong>
                <small>{{ song.artist || '本地音乐' }}</small>
              </span>
              <span class="song-state">播放</span>
            </button>
          </div>
        </section>

        <section class="page-card p-4">
          <div class="section-title">
            <h2>本地音乐</h2>
            <span>{{ songs.length }} 首</span>
          </div>

          <div v-if="songs.length" class="song-list">
            <button
              v-for="(song, index) in songs"
              :key="`${song.id}-${song.url}`"
              type="button"
              class="song-item"
              :class="{ active: currentIndex === index }"
              @click="playSong(index)"
            >
              <span class="song-index">{{ index + 1 }}</span>
              <span class="song-copy">
                <strong>{{ song.title }}</strong>
                <small>{{ song.artist || '本地音乐' }}</small>
              </span>
              <span class="song-state">{{ currentIndex === index && isPlaying ? '播放中' : '播放' }}</span>
            </button>
          </div>

          <div v-else class="empty-list">
            <p>还没有音乐，先上传一首吧。</p>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { musicAPI } from '../api'
import MusicPlayer from '../components/MusicPlayer.vue'

const songs = ref([])
const currentIndex = ref(0)
const isPlaying = ref(false)
const isLoading = ref(true)
const error = ref(null)
const playbackError = ref('')
const uploading = ref(false)
const uploadMessage = ref('')
const feedbackPending = ref(false)
const feedbackMessage = ref('')
const likedSongs = ref([])
const fileInput = ref(null)

const currentSong = computed(() => songs.value[currentIndex.value] || null)

async function loadMusic() {
  isLoading.value = true
  error.value = null
  playbackError.value = ''

  try {
    const result = await musicAPI.list(null, 100)
    songs.value = result.music_list || []
    if (currentIndex.value >= songs.value.length) {
      currentIndex.value = 0
    }
  } catch (err) {
    console.error('Failed to load music:', err)
    error.value = err?.response?.status === 401
      ? '请先登录后再使用音乐播放。'
      : '音乐加载失败，请稍后重试。'
  } finally {
    isLoading.value = false
  }
}

function loadLikedSongs() {
  try {
    likedSongs.value = JSON.parse(localStorage.getItem('mooncare_liked_music') || '[]')
  } catch (err) {
    console.warn('Failed to read liked music:', err)
    likedSongs.value = []
  }
}

function saveLikedSongs() {
  localStorage.setItem('mooncare_liked_music', JSON.stringify(likedSongs.value.slice(0, 50)))
}

function openFilePicker() {
  uploadMessage.value = ''
  fileInput.value?.click()
}

async function handleFileChange(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)
  formData.append('title', file.name.replace(/\.[^.]+$/, ''))
  formData.append('artist', '本地上传')

  uploading.value = true
  uploadMessage.value = '正在上传...'

  try {
    await musicAPI.upload(formData)
    uploadMessage.value = '上传成功'
    await loadMusic()
  } catch (err) {
    console.error('Failed to upload music:', err)
    uploadMessage.value = err?.response?.data?.detail || '上传失败，请确认文件是音频且不超过 30MB。'
  } finally {
    uploading.value = false
  }
}

function playSong(index) {
  currentIndex.value = index
  playbackError.value = ''
  feedbackMessage.value = ''
}

function playLikedSong(song) {
  const existingIndex = songs.value.findIndex(item => item.id === song.id && item.url === song.url)
  if (existingIndex !== -1) {
    playSong(existingIndex)
    return
  }

  songs.value = [song, ...songs.value]
  playSong(0)
}

function handleSongChange(song) {
  const index = songs.value.findIndex(item => item.id === song?.id && item.url === song?.url)
  if (index !== -1) {
    currentIndex.value = index
  }
}

function handlePlayStateChange(playing) {
  isPlaying.value = playing
}

function handlePlaybackError(payload) {
  const song = payload?.song || currentSong.value
  playbackError.value = `${song?.title || '当前音乐'} 暂时无法播放。`
}

async function submitFeedback(action, song = currentSong.value) {
  if (!song || feedbackPending.value) return false
  feedbackPending.value = true

  try {
    await musicAPI.feedback({
      music_id: song.id,
      music_title: song.title,
      action,
      emotion_category: song.emotion_category || 'normal',
      source: song.source || 'local',
      note: null
    })
    return true
  } catch (err) {
    console.error('Failed to submit music feedback:', err)
    feedbackMessage.value = '反馈暂时保存失败，请稍后再试。'
    return false
  } finally {
    feedbackPending.value = false
  }
}

async function likeCurrentSong() {
  const song = currentSong.value
  if (!song) return

  const saved = await submitFeedback('liked', song)
  if (!saved) return

  const exists = likedSongs.value.some(item => item.id === song.id && item.url === song.url)
  if (!exists) {
    likedSongs.value = [song, ...likedSongs.value]
    saveLikedSongs()
  }
  feedbackMessage.value = '已加入喜欢列表。'
}

async function dislikeCurrentSong() {
  const song = currentSong.value
  if (!song) return

  await submitFeedback('disliked', song)
  feedbackMessage.value = '已跳过这首。'
  if (songs.value.length > 1) {
    currentIndex.value = currentIndex.value < songs.value.length - 1 ? currentIndex.value + 1 : 0
  }
}

onMounted(() => {
  loadLikedSongs()
  loadMusic()
})
</script>

<style scoped>
.music-shell {
  width: min(100%, 32rem);
  margin: 0 auto;
  padding: 1rem 1rem calc(6.5rem + env(safe-area-inset-bottom));
  display: grid;
  gap: 1rem;
}

.hidden-input {
  display: none;
}

.upload-message,
.error-text,
.feedback-message {
  margin: 0.75rem 0 0;
  text-align: center;
  font-size: 0.8125rem;
}

.upload-message,
.feedback-message {
  color: #db2777;
}

.error-text {
  color: #64748b;
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.875rem;
}

.section-title h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #1f2937;
}

.section-title span {
  font-size: 0.75rem;
  color: #94a3b8;
}

.song-list {
  display: grid;
  gap: 0.75rem;
}

.song-item {
  width: 100%;
  display: grid;
  grid-template-columns: 2.25rem minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.75rem;
  border: 1px solid #e5e7eb;
  border-radius: 1rem;
  background: #ffffff;
  padding: 0.875rem;
  text-align: left;
}

.song-item.active {
  border-color: #f9a8d4;
  background: #fdf2f8;
}

.song-index {
  width: 2.25rem;
  height: 2.25rem;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 0.8125rem;
  font-weight: 700;
}

.song-copy {
  min-width: 0;
  display: grid;
  gap: 0.15rem;
}

.song-copy strong,
.song-copy small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.song-copy strong {
  font-size: 0.875rem;
  color: #1f2937;
}

.song-copy small {
  font-size: 0.75rem;
  color: #64748b;
}

.song-state {
  font-size: 0.75rem;
  font-weight: 700;
  color: #db2777;
}

.empty-list {
  padding: 1.5rem;
  text-align: center;
  color: #64748b;
  font-size: 0.875rem;
}

@media (min-width: 1024px) {
  .music-shell {
    width: min(100%, 40rem);
    padding: 2rem 2rem 2.5rem;
  }
}
</style>
