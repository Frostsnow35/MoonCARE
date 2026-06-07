<template>
  <nav class="bottom-nav">
    <div class="nav-shell">
      <div class="active-bar" :style="activeBarStyle"></div>

      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="isActive(item.path) ? 'is-active' : ''"
      >
        <div class="icon-wrap">
          <svg
            v-if="item.icon === 'home'"
            class="nav-icon"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
            />
          </svg>
          <svg
            v-else-if="item.icon === 'chat'"
            class="nav-icon"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
            />
          </svg>
          <svg
            v-else-if="item.icon === 'diary'"
            class="nav-icon"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
            />
          </svg>
          <svg
            v-else-if="item.icon === 'cycle'"
            class="nav-icon"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <svg
            v-else
            class="nav-icon"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
            />
          </svg>
        </div>
        <span class="nav-label">{{ item.label }}</span>
      </router-link>
    </div>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  { path: '/home', label: '首页', icon: 'home' },
  { path: '/chat', label: '聊天', icon: 'chat' },
  { path: '/diary', label: '日记', icon: 'diary' },
  { path: '/cycle', label: '周期', icon: 'cycle' },
  { path: '/profile', label: '我的', icon: 'user' },
]

const activeIndex = computed(() => {
  const index = navItems.findIndex(item => route.path.startsWith(item.path))
  return index >= 0 ? index : 0
})

const activeBarStyle = computed(() => {
  const width = 100 / navItems.length
  return {
    width: `${width}%`,
    left: `${activeIndex.value * width}%`,
  }
})

function isActive(path) {
  return route.path.startsWith(path)
}
</script>

<style scoped>
.bottom-nav {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 50;
  background: #ffffff;
  box-shadow: 0 -8px 24px rgba(15, 23, 42, 0.08);
  padding-bottom: env(safe-area-inset-bottom, 0);
}

.nav-shell {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-around;
  width: min(100%, 448px);
  height: 58px;
  margin: 0 auto;
}

.active-bar {
  position: absolute;
  top: 0;
  height: 2px;
  border-radius: 999px;
  background: linear-gradient(90deg, #fb7185, #ec4899);
  transition: left 180ms ease;
}

.nav-item {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
  transition: color 180ms ease, transform 180ms ease;
}

.nav-item.is-active {
  color: #ec4899;
}

.nav-item:active {
  transform: scale(0.96);
}

.icon-wrap {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
}

.nav-icon {
  width: 20px;
  height: 20px;
}

.nav-label {
  margin-top: 4px;
  font-size: 11px;
  font-weight: 600;
}
</style>
