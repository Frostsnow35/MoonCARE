<template>
  <nav class="fixed bottom-0 left-0 right-0 bg-white z-50 safe-area-pb" style="box-shadow: 0 -2px 10px rgba(0,0,0,0.05);">
    <div class="flex justify-around items-center h-14 max-w-lg mx-auto relative">
      <div
        class="absolute top-0 h-0.5 bg-gradient-to-r from-pink-400 to-pink-500 transition-all duration-300"
        :style="activeBarStyle"
      ></div>

      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-item flex flex-col items-center justify-center w-full h-full transition-all duration-200"
        :class="isActive(item.path) ? 'text-pink-500' : 'text-gray-400'"
      >
        <div class="mb-0.5 transition-transform duration-200" :class="isActive(item.path) ? 'scale-110' : ''">
          <svg v-if="item.icon === 'home'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          <svg v-else-if="item.icon === 'diary'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
          <svg v-else-if="item.icon === 'cycle'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <svg v-else-if="item.icon === 'chat'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <svg v-else-if="item.icon === 'user'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        </div>
        <span class="text-xs font-medium">{{ item.label }}</span>
      </router-link>
    </div>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  { path: '/', label: '首页', icon: 'home' },
  { path: '/diary', label: '日记', icon: 'diary' },
  { path: '/cycle', label: '周期', icon: 'cycle' },
  { path: '/chat', label: '聊聊', icon: 'chat' },
  { path: '/profile', label: '我的', icon: 'user' }
]

const activeIndex = computed(() => {
  const index = navItems.findIndex(item => {
    if (item.path === '/') {
      return route.path === '/'
    }
    return route.path.startsWith(item.path)
  })
  return index >= 0 ? index : 0
})

const activeBarStyle = computed(() => {
  const width = 100 / navItems.length
  const left = activeIndex.value * width
  return {
    width: `${width}%`,
    left: `${left}%`
  }
})

function isActive(path) {
  if (path === '/') {
    return route.path === '/'
  }
  return route.path.startsWith(path)
}
</script>

<style scoped>
.safe-area-pb {
  padding-bottom: env(safe-area-inset-bottom, 0);
}

.nav-item:active {
  opacity: 0.7;
}
</style>
