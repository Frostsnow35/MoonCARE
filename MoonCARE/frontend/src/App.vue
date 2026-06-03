<template>
  <div class="min-h-screen bg-gradient-to-b from-rose-50 via-white to-orange-50">
    <div v-if="showAppChrome">
      <header class="sticky top-0 z-50 bg-white/90 backdrop-blur-sm border-b border-rose-100">
        <div class="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-2xl">&#x1F338;</span>
            <span class="font-semibold text-gray-800">MoonCARE</span>
          </div>
          <nav class="flex items-center gap-4">
            <router-link
              v-for="item in navItems"
              :key="item.path"
              :to="item.path"
              class="text-sm px-3 py-1.5 rounded-full transition-colors"
              :class="[
                $route.path === item.path
                  ? 'bg-rose-100 text-rose-600 font-medium'
                  : 'text-gray-600 hover:bg-rose-50'
              ]"
            >
              {{ item.name }}
            </router-link>
          </nav>
        </div>
      </header>

      <main class="max-w-4xl mx-auto px-4 py-6">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>

      <nav class="fixed bottom-0 left-0 right-0 bg-white border-t border-rose-100 md:hidden">
        <div class="flex justify-around py-2">
          <router-link
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="flex flex-col items-center gap-0.5 p-2 rounded-lg transition-colors"
            :class="[
              $route.path === item.path
                ? 'text-rose-600'
                : 'text-gray-400'
            ]"
          >
            <span class="text-xl">{{ item.icon }}</span>
            <span class="text-xs">{{ item.name }}</span>
          </router-link>
        </div>
      </nav>
    </div>

    <router-view v-else v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>

    <transition name="fade">
      <div
        v-if="appUpdateStore.promptVisible"
        class="fixed inset-0 z-[70] bg-slate-900/55 backdrop-blur-sm flex items-end sm:items-center justify-center p-4"
      >
        <div class="w-full max-w-md rounded-3xl bg-white shadow-2xl border border-rose-100 overflow-hidden">
          <div class="bg-gradient-to-r from-rose-500 to-orange-400 px-5 py-4 text-white">
            <div class="text-sm font-medium">
              {{ appUpdateStore.isForceUpdate ? '需要更新后继续使用' : '发现新的 MoonCARE 版本' }}
            </div>
            <div class="text-xs text-white/85 mt-1">
              当前 {{ appUpdateStore.currentVersionLabel }} / 最新 {{ appUpdateStore.latestVersionLabel }}
            </div>
          </div>

          <div class="px-5 py-4 space-y-4">
            <div class="text-sm text-gray-700 leading-6">
              {{ appUpdateStore.statusLabel }}
            </div>

            <div
              v-if="appUpdateStore.latestRelease?.published_at"
              class="rounded-2xl bg-white border border-rose-100 px-4 py-3 text-xs text-gray-500"
            >
              发布时间：{{ appUpdateStore.latestPublishedAtLabel }}
            </div>

            <div v-if="appUpdateStore.releaseNotes.length" class="rounded-2xl bg-rose-50 border border-rose-100 px-4 py-3">
              <div class="text-xs font-medium text-rose-700 mb-2">更新内容</div>
              <ul class="space-y-1 text-sm text-gray-600">
                <li v-for="note in appUpdateStore.releaseNotes" :key="note">• {{ note }}</li>
              </ul>
            </div>

            <div v-if="appUpdateStore.errorMessage" class="rounded-2xl bg-amber-50 border border-amber-100 px-4 py-3 text-sm text-amber-700">
              {{ appUpdateStore.errorMessage }}
            </div>

            <div class="flex flex-col gap-2">
              <button
                type="button"
                class="w-full rounded-2xl bg-rose-500 text-white py-3 text-sm font-medium disabled:opacity-60"
                :disabled="appUpdateStore.isUpdating"
                @click="appUpdateStore.startUpdate"
              >
                {{ appUpdateStore.isUpdating ? '正在准备更新包...' : '立即更新' }}
              </button>

              <button
                v-if="appUpdateStore.needsInstallPermission"
                type="button"
                class="w-full rounded-2xl border border-rose-200 text-rose-600 py-3 text-sm font-medium"
                @click="appUpdateStore.openInstallerSettings"
              >
                去开启安装权限
              </button>

              <button
                v-if="appUpdateStore.hasUpdateAvailable && !appUpdateStore.supportsSelfUpdate"
                type="button"
                class="w-full rounded-2xl border border-rose-200 text-rose-600 py-3 text-sm font-medium"
                @click="appUpdateStore.openDownloadPage"
              >
                打开下载链接
              </button>

              <button
                v-if="appUpdateStore.canDismissPrompt"
                type="button"
                class="w-full rounded-2xl border border-gray-200 text-gray-600 py-3 text-sm font-medium"
                @click="appUpdateStore.dismissPrompt"
              >
                稍后再说
              </button>

              <button
                v-else
                type="button"
                class="w-full rounded-2xl border border-gray-200 text-gray-600 py-3 text-sm font-medium"
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
import { useAppUpdateStore } from './stores/appUpdate'

const route = useRoute()
const appUpdateStore = useAppUpdateStore()
const showAppChrome = computed(() => !route.meta.hideChrome)

const navItems = [
  { name: '\u9996\u9875', path: '/home', icon: '\u{1F3E0}' },
  { name: '\u65E5\u8BB0', path: '/diary', icon: '\u{1F4DD}' },
  { name: '\u5468\u671F', path: '/cycle', icon: '\u{1F4C5}' },
  { name: '\u804A\u804A', path: '/chat', icon: '\u{1F4AC}' },
  { name: '\u547C\u5438', path: '/breathing', icon: '\u{1F343}' }
]
</script>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
