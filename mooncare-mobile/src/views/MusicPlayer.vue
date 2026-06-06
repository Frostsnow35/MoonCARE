<template>
  <div class="music-page">
    <main class="music-shell">
      <header class="page-header">
        <div>
          <p class="eyebrow">音乐疗愈</p>
          <h1>陪伴播放</h1>
        </div>
        <button type="button" class="icon-button" :disabled="isLoading" aria-label="刷新音乐列表" @click="loadMusic">
          刷新
        </button>
      </header>

      <section class="upload-panel">
        <input
          ref="fileInput"
          type="file"
          class="hidden-input"
          accept="audio/*,.mp3,.wav,.ogg,.m4a,.aac,.flac"
          @change="handleFileChange"
        />
        <button type="button" class="upload-button" :disabled="uploading" @click="openFilePicker">
          导入本地音乐
        </button>
        <p class="upload-hint">支持 mp3、wav、ogg、m4a、aac、flac，单个文件不超过 30MB。</p>
        <p v-if="uploadMessage" class="upload-message">{{ uploadMessage }}</p>
      </section>

      <section v-if="isLoading" class="state-panel">
        <p>正在加载音乐列表...</p>
      </section>

      <section v-else-if="error" class="state-panel">
        <p>{{ error }}</p>
        <button type="button" class="plain-button" @click="loadMusic">重新加载</button>
      </section>

      <template v-else>
        <section class="player-panel">
          <MusicPlayer
            :songs="songs"
            :selected-index="currentIndex"
            :auto-play="false"
            @song-change="handleSongChange"
            @play-state-change="handlePlayStateChange"
            @playback-error="handlePlaybackError"
            @playback-started="handlePlaybackStarted"
          />

          <div v-if="currentSong" class="feedback-row">
            <button type="button" :disabled="feedbackPending" @click="likeCurrentSong">
              喜欢
            </button>
            <button type="button" :disabled="feedbackPending" @click="dislikeCurrentSong">
              不合适
            </button>
          </div>

          <p v-if="feedbackMessage" class="feedback-message">{{ feedbackMessage }}</p>
          <p v-if="playbackError" class="error-text">{{ playbackError }}</p>
        </section>

        <section v-if="likedSongs.length" class="list-panel liked-panel">
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
              <span class="song-index">心</span>
              <span class="song-copy">
                <strong>{{ song.title }}</strong>
                <small>{{ song.artist || '示例音乐' }}</small>
              </span>
              <span class="song-state">播放</span>
            </button>
          </div>
        </section>

        <section class="list-panel">
          <div class="section-title">
            <h2>可播放列表</h2>
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
                <small>{{ song.artist || '示例音乐' }}</small>
              </span>
              <span class="song-state">
                {{ currentIndex === index && isPlaying ? '播放中' : '播放' }}
              </span>
            </button>
          </div>

          <div v-else class="empty-list">
            <p>当前还没有可播放的音乐。</p>
            <p class="empty-hint">你可以先导入本地音频，或确认服务器上的示例音乐目录已经同步。</p>
          </div>
        </section>
      </template>
    </main>

    <BottomNav />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { musicAPI } from '../api'
import { getUserScopedKey } from '../services/userScopedStorage'
import MusicPlayer from '../components/MusicPlayer.vue'
import BottomNav from '../components/BottomNav.vue'

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
const playedFeedbackKeys = ref(new Set())
const likedSongsStorageKey = getUserScopedKey('mooncare_liked_music')

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
      ? '请先登录后再使用音乐功能。'
      : '音乐列表加载失败，请稍后重试。'
  } finally {
    isLoading.value = false
  }
}

function loadLikedSongs() {
  try {
    likedSongs.value = JSON.parse(localStorage.getItem(likedSongsStorageKey) || '[]')
  } catch (err) {
    console.warn('Failed to read liked music:', err)
    likedSongs.value = []
  }
}

function saveLikedSongs() {
  localStorage.setItem(likedSongsStorageKey, JSON.stringify(likedSongs.value.slice(0, 50)))
}

function openFilePicker() {
  uploadMessage.value = ''
  fileInput.value?.click()
}

async function handleFileChange(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return

  const allowedMimePrefix = 'audio/'
  if (file.type && !file.type.startsWith(allowedMimePrefix)) {
    uploadMessage.value = '请选择音频文件后再上传。'
    return
  }

  const formData = new FormData()
  formData.append('file', file)
  formData.append('title', file.name.replace(/\.[^.]+$/, ''))
  formData.append('artist', '本地上传')

  uploading.value = true
  uploadMessage.value = '正在上传...'

  try {
    const uploadedSong = await musicAPI.upload(formData)
    uploadMessage.value = '上传成功，已加入播放列表。'

    const exists = songs.value.some(song => song.id === uploadedSong.id && song.url === uploadedSong.url)
    if (!exists) {
      songs.value = [uploadedSong, ...songs.value]
      currentIndex.value = 0
    }
    playbackError.value = ''
  } catch (err) {
    console.error('Failed to upload music:', err)
    uploadMessage.value =
      err?.response?.data?.detail ||
      err?.response?.data?.message ||
      '上传失败，请确认文件是音频格式且大小不超过 30MB。'
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

async function handlePlaybackStarted(song) {
  if (!song) return
  const feedbackKey = `${song.id}:${song.url}:played`
  if (playedFeedbackKeys.value.has(feedbackKey)) return

  playedFeedbackKeys.value.add(feedbackKey)
  await submitFeedback('played', song, false)
}

async function handlePlaybackError(payload) {
  const song = payload?.song || currentSong.value
  const reason = payload?.message || '暂时无法播放'
  playbackError.value = `${song?.title || '当前音乐'} ${reason}，请尝试切换其他曲目。`
  await submitFeedback('play_failed', song, false)
}

async function submitFeedback(action, song = currentSong.value, showError = true) {
  if (!song || feedbackPending.value) return false
  feedbackPending.value = true

  try {
    await musicAPI.feedback({
      music_id: song.id,
      music_title: song.title,
      action,
      emotion_category: song.emotion_category || 'normal',
      source: song.source || 'local',
      note: null,
    })
    return true
  } catch (err) {
    console.error('Failed to submit music feedback:', err)
    if (showError) {
      feedbackMessage.value = '反馈暂时保存失败，请稍后再试。'
    }
    return false
  } finally {
    feedbackPending.value = false
  }
}

async function likeCurrentSong() {
  const song = currentSong.value
  if (!song) return

  const saved = await submitFeedback('liked', song, true)
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

  await submitFeedback('disliked', song, true)
  feedbackMessage.value = '这首歌已跳过。'
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
.music-page {
  min-height: 100vh;
  background: #f7fbff;
  color: #111827;
}

.music-shell {
  width: min(100%, 448px);
  margin: 0 auto;
  padding: 18px 16px calc(88px + env(safe-area-inset-bottom, 0));
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.eyebrow {
  margin: 0 0 4px;
  color: #ec4899;
  font-size: 13px;
  font-weight: 700;
}

.page-header h1 {
  margin: 0;
  font-size: 28px;
  line-height: 1.2;
  font-weight: 800;
}

.icon-button {
  min-width: 64px;
  height: 40px;
  border: 0;
  border-radius: 999px;
  background: #ffffff;
  color: #2563eb;
  font-size: 13px;
  font-weight: 700;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
}

.upload-panel,
.player-panel,
.list-panel,
.state-panel {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 20px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}

.upload-panel {
  padding: 12px;
  margin-bottom: 12px;
}

.hidden-input {
  display: none;
}

.upload-button,
.plain-button {
  width: 100%;
  min-height: 42px;
  border: 0;
  border-radius: 12px;
  background: #ec4899;
  color: #ffffff;
  font-size: 15px;
  font-weight: 800;
}

.upload-button:disabled {
  opacity: 0.6;
}

.upload-hint {
  margin: 10px 0 0;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.5;
  text-align: center;
}

.upload-message,
.error-text {
  margin: 10px 0 0;
  color: #64748b;
  font-size: 13px;
  text-align: center;
}

.error-text {
  color: #dc2626;
}

.state-panel {
  padding: 36px 18px;
  text-align: center;
  color: #64748b;
}

.state-panel p {
  margin: 0 0 14px;
}

.player-panel {
  padding: 16px;
  margin-bottom: 12px;
}

.feedback-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 16px;
}

.feedback-row button {
  min-height: 40px;
  border: 1px solid #dbeafe;
  border-radius: 999px;
  background: #f8fbff;
  color: #2563eb;
  font-size: 14px;
  font-weight: 800;
}

.feedback-row button:disabled {
  opacity: 0.55;
}

.feedback-message {
  margin: 10px 0 0;
  color: #ec4899;
  font-size: 13px;
  text-align: center;
}

.section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-title h2 {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
}

.section-title span {
  color: #64748b;
  font-size: 12px;
}

.list-panel {
  padding: 14px;
  margin-bottom: 12px;
}

.liked-panel {
  border-color: #fbcfe8;
}

.song-list {
  display: grid;
  gap: 8px;
}

.song-item {
  width: 100%;
  min-height: 62px;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #ffffff;
  text-align: left;
}

.song-item.active {
  border-color: #ec4899;
  background: #fdf2f8;
}

.song-index {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #eff6ff;
  color: #2563eb;
  font-size: 13px;
  font-weight: 800;
}

.song-copy {
  min-width: 0;
  display: grid;
  gap: 3px;
}

.song-copy strong,
.song-copy small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.song-copy strong {
  color: #111827;
  font-size: 14px;
}

.song-copy small {
  color: #64748b;
  font-size: 12px;
}

.song-state {
  color: #ec4899;
  font-size: 12px;
  font-weight: 800;
}

.empty-list {
  padding: 22px;
  color: #64748b;
  text-align: center;
}

.empty-list p {
  margin: 0;
}

.empty-hint {
  margin-top: 8px !important;
  font-size: 12px;
  line-height: 1.5;
}
</style>
