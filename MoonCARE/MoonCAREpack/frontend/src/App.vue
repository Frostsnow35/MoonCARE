<template>
  <div class="min-h-screen bg-gradient-to-b from-blue-50 to-white">
    <!-- Header -->
    <header class="sticky top-0 z-50 bg-white/90 backdrop-blur-sm border-b border-blue-100">
      <div class="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="text-2xl">🌸</span>
          <span class="font-semibold text-gray-800">HealthAI</span>
        </div>
        <nav class="flex items-center gap-4">
          <router-link
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="text-sm px-3 py-1.5 rounded-full transition-colors"
            :class="[
              $route.path === item.path
                ? 'bg-blue-100 text-blue-600 font-medium'
                : 'text-gray-600 hover:bg-gray-100'
            ]"
          >
            {{ item.name }}
          </router-link>
        </nav>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-4xl mx-auto px-4 py-6">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- Bottom Navigation (Mobile) -->
    <nav class="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 md:hidden">
      <div class="flex justify-around py-2">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="flex flex-col items-center gap-0.5 p-2 rounded-lg transition-colors"
          :class="[
            $route.path === item.path
              ? 'text-blue-600'
              : 'text-gray-400'
          ]"
        >
          <span class="text-xl">{{ item.icon }}</span>
          <span class="text-xs">{{ item.name }}</span>
        </router-link>
      </div>
    </nav>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const navItems = ref([
  { name: '首页', path: '/', icon: '🏠' },
  { name: '日记', path: '/diary', icon: '📝' },
  { name: '周期', path: '/cycle', icon: '📅' },
  { name: '聊聊', path: '/chat', icon: '💬' },
  { name: '呼吸', path: '/breathing', icon: '🌬️' },
])
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
