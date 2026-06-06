<template>
  <div class="min-h-screen">
    <div v-if="showAppChrome" class="shell-layout">
      <aside class="shell-sidebar hidden lg:flex">
        <div class="shell-brand">
          <div class="shell-brand-badge">她语</div>
          <div>
            <p class="shell-brand-title">MoonCARE</p>
            <p class="shell-brand-copy">经前情绪陪伴与周期照护</p>
          </div>
        </div>

        <nav class="shell-nav" aria-label="主导航">
          <router-link
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="shell-nav-item"
            :class="{ active: activeNavId === item.id }"
          >
            <span class="shell-nav-icon">{{ item.icon }}</span>
            <span>{{ item.label }}</span>
          </router-link>
        </nav>

        <div class="shell-side-card">
          <p class="section-label">辅助工具</p>
          <p class="shell-side-copy">音乐、呼吸和波形监测仍保留在前台，作为情绪照护的二级能力。</p>
          <div class="mt-3 grid gap-2">
            <router-link
              v-for="tool in toolLinks"
              :key="tool.path"
              :to="tool.path"
              class="shell-tool-link"
            >
              <span>{{ tool.icon }}</span>
              <span>{{ tool.label }}</span>
            </router-link>
          </div>
        </div>

        <div class="shell-user-card">
          <p class="shell-user-name">{{ authStore.user?.nickname || 'MoonCARE 用户' }}</p>
          <p class="shell-user-email">{{ authStore.user?.email || '已登录' }}</p>
          <p class="shell-user-note">登录后会继续保存你的聊天、周期和日记状态。</p>
        </div>
      </aside>

      <main class="shell-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>

      <BottomNav />
    </div>

    <router-view v-else v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>

    <transition name="fade">
      <div
        v-if="appUpdateStore.promptVisible"
        class="fixed inset-0 z-[70] flex items-end justify-center bg-slate-900/55 p-4 backdrop-blur-sm sm:items-center"
      >
        <div class="w-full max-w-md overflow-hidden rounded-3xl border border-rose-100 bg-white shadow-2xl">
          <div class="bg-gradient-to-r from-rose-500 to-orange-400 px-5 py-4 text-white">
            <div class="text-sm font-medium">
              {{ appUpdateStore.isForceUpdate ? '更新后才能继续使用' : '发现新版本 MoonCARE' }}
            </div>
            <div class="mt-1 text-xs text-white/85">
              当前 {{ appUpdateStore.currentVersionLabel }} / 最新 {{ appUpdateStore.latestVersionLabel }}
            </div>
          </div>

          <div class="space-y-4 px-5 py-4">
            <div class="text-sm leading-6 text-gray-700">
              {{ appUpdateStore.statusLabel }}
            </div>

            <div
              v-if="appUpdateStore.latestRelease?.published_at"
              class="rounded-2xl border border-rose-100 bg-white px-4 py-3 text-xs text-gray-500"
            >
              发布时间：{{ appUpdateStore.latestPublishedAtLabel }}
            </div>

            <div
              v-if="appUpdateStore.releaseNotes.length"
              class="rounded-2xl border border-rose-100 bg-rose-50 px-4 py-3"
            >
              <div class="mb-2 text-xs font-medium text-rose-700">更新内容</div>
              <ul class="space-y-1 text-sm text-gray-600">
                <li v-for="note in appUpdateStore.releaseNotes" :key="note">• {{ note }}</li>
              </ul>
            </div>

            <div
              v-if="appUpdateStore.errorMessage"
              class="rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3 text-sm text-amber-700"
            >
              {{ appUpdateStore.errorMessage }}
            </div>

            <div class="flex flex-col gap-2">
              <button
                type="button"
                class="w-full rounded-2xl bg-rose-500 py-3 text-sm font-medium text-white disabled:opacity-60"
                :disabled="appUpdateStore.isUpdating"
                @click="appUpdateStore.startUpdate"
              >
                {{ appUpdateStore.isUpdating ? '正在准备更新包…' : '立即更新' }}
              </button>

              <button
                v-if="appUpdateStore.needsInstallPermission"
                type="button"
                class="w-full rounded-2xl border border-rose-200 py-3 text-sm font-medium text-rose-600"
                @click="appUpdateStore.openInstallerSettings"
              >
                去开启安装权限
              </button>

              <button
                v-if="appUpdateStore.hasUpdateAvailable && !appUpdateStore.supportsSelfUpdate"
                type="button"
                class="w-full rounded-2xl border border-rose-200 py-3 text-sm font-medium text-rose-600"
                @click="appUpdateStore.openDownloadPage"
              >
                打开下载链接
              </button>

              <button
                v-if="appUpdateStore.canDismissPrompt"
                type="button"
                class="w-full rounded-2xl border border-gray-200 py-3 text-sm font-medium text-gray-600"
                @click="appUpdateStore.dismissPrompt"
              >
                稍后再说
              </button>

              <button
                v-else
                type="button"
                class="w-full rounded-2xl border border-gray-200 py-3 text-sm font-medium text-gray-600"
                @click="appUpdateStore.exitForUpdate"
              >
                退出应用
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import BottomNav from './components/BottomNav.vue'
import { useAppUpdateStore } from './stores/appUpdate'
import { useAuthStore } from './stores/auth'

const route = useRoute()
const appUpdateStore = useAppUpdateStore()
const authStore = useAuthStore()

const showAppChrome = computed(() => !route.meta.hideChrome)
const activeNavId = computed(() => route.meta.navGroup || 'home')

const navItems = [
  { id: 'home', label: '首页', path: '/home', icon: '🏠' },
  { id: 'chat', label: '聊天', path: '/chat', icon: '💬' },
  { id: 'diary', label: '日记', path: '/diary', icon: '📝' },
  { id: 'cycle', label: '周期', path: '/cycle', icon: '🗓️' },
  { id: 'profile', label: '我的', path: '/profile', icon: '👤' }
]

const toolLinks = [
  { path: '/music', label: '音乐陪伴', icon: '🎵' },
  { path: '/breathing', label: '呼吸练习', icon: '🍃' },
  { path: '/wave', label: '波形监测', icon: '📈' }
]
</script>

<style scoped>
.shell-layout {
  min-height: 100vh;
}

.shell-main {
  min-height: 100vh;
}

.shell-sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  width: 18rem;
  padding: 2rem 1.25rem;
  flex-direction: column;
  gap: 1.5rem;
  background: rgba(255, 250, 252, 0.88);
  backdrop-filter: blur(18px);
  border-right: 1px solid rgba(244, 114, 182, 0.14);
}

.shell-brand {
  display: flex;
  align-items: center;
  gap: 0.9rem;
}

.shell-brand-badge {
  width: 3rem;
  height: 3rem;
  border-radius: 1rem;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #fb7185 0%, #ec4899 100%);
  color: #fff;
  font-weight: 700;
  box-shadow: 0 16px 30px rgba(236, 72, 153, 0.2);
}

.shell-brand-title {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 700;
  color: #1f2937;
}

.shell-brand-copy {
  margin: 0.28rem 0 0;
  font-size: 0.82rem;
  line-height: 1.5;
  color: #6b7280;
}

.shell-nav {
  display: grid;
  gap: 0.45rem;
}

.shell-nav-item,
.shell-tool-link {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  min-height: 3rem;
  padding: 0 0.95rem;
  border-radius: 1rem;
  color: #6b7280;
  transition: background 0.18s ease, color 0.18s ease, transform 0.18s ease;
}

.shell-nav-item.active {
  background: rgba(251, 207, 232, 0.5);
  color: #be185d;
  font-weight: 600;
}

.shell-nav-icon {
  width: 1.5rem;
  text-align: center;
}

.shell-side-card,
.shell-user-card {
  padding: 1rem;
  border-radius: 1.25rem;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(244, 114, 182, 0.14);
  box-shadow: 0 18px 36px rgba(190, 24, 93, 0.06);
}

.shell-side-copy {
  margin: 0.45rem 0 0;
  font-size: 0.82rem;
  line-height: 1.55;
  color: #6b7280;
}

.shell-tool-link {
  min-height: 2.75rem;
  background: #fff8fb;
  color: #374151;
}

.shell-user-name {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: #1f2937;
}

.shell-user-email {
  margin: 0.35rem 0 0;
  font-size: 0.78rem;
  color: #6b7280;
  word-break: break-all;
}

.shell-user-note {
  margin: 0.55rem 0 0;
  font-size: 0.78rem;
  line-height: 1.5;
  color: #9ca3af;
}

@media (min-width: 1024px) {
  .shell-main {
    margin-left: 18rem;
  }
}
</style>
