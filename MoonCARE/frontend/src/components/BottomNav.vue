<template>
  <nav class="bottom-nav lg:hidden" aria-label="底部主导航">
    <div class="bottom-nav-inner">
      <router-link
        v-for="item in navItems"
        :key="item.id"
        :to="item.path"
        class="bottom-nav-item"
        :class="{ active: activeNavId === item.id }"
      >
        <span class="text-[1.15rem]">{{ item.icon }}</span>
        <span>{{ item.label }}</span>
      </router-link>
    </div>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  { id: 'home', label: '首页', path: '/home', icon: '🏠' },
  { id: 'chat', label: '聊天', path: '/chat', icon: '💬' },
  { id: 'diary', label: '日记', path: '/diary', icon: '📝' },
  { id: 'cycle', label: '周期', path: '/cycle', icon: '🗓️' },
  { id: 'profile', label: '我的', path: '/profile', icon: '👤' }
]

const activeNavId = computed(() => route.meta.navGroup || 'home')
</script>

<style scoped>
.bottom-nav {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 50;
  padding: 0.5rem 0.85rem calc(0.75rem + env(safe-area-inset-bottom));
  background: linear-gradient(180deg, rgba(255, 250, 252, 0) 0%, rgba(255, 250, 252, 0.95) 24%, rgba(255, 250, 252, 0.98) 100%);
}

.bottom-nav-inner {
  width: min(100%, 32rem);
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.45rem;
  padding: 0.45rem;
  border-radius: 1.35rem;
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid rgba(244, 114, 182, 0.14);
  box-shadow: 0 18px 40px rgba(190, 24, 93, 0.14);
  backdrop-filter: blur(18px);
}

.bottom-nav-item {
  min-height: 3.2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.2rem;
  border-radius: 1rem;
  color: #9ca3af;
  font-size: 0.72rem;
  font-weight: 600;
  transition: background 0.18s ease, color 0.18s ease, transform 0.18s ease;
}

.bottom-nav-item.active {
  background: rgba(251, 207, 232, 0.44);
  color: #be185d;
}

.bottom-nav-item:active {
  transform: scale(0.97);
}
</style>
