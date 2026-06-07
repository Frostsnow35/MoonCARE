<template>
  <div class="app-shell">
    <template v-if="showAppChrome">
      <header class="app-header">
        <div class="header-inner">
          <router-link to="/home" class="brand-link">
            <span class="brand-badge">她语</span>
            <span class="brand-name">MoonCARE</span>
          </router-link>

          <router-link
            to="/ble"
            class="ble-indicator"
            :class="bleStatusClass"
            aria-label="蓝牙连接状态"
            title="蓝牙连接状态"
          >
            <svg class="ble-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="m6.5 6.5 11 11M6.5 17.5l11-11M12 3v18l5-5-5-4 5-4-5-5Z" />
            </svg>
          </router-link>
        </div>
      </header>

      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </template>

    <router-view v-else v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
</template>

<script setup>
import { computed, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useBleStore } from './stores/ble'

const route = useRoute()
const bleStore = useBleStore()

const showAppChrome = computed(() => !route.meta.hideChrome)
const bleStatusClass = computed(() => {
  if (bleStore.isConnected) return 'is-connected'
  if (bleStore.isConnecting) return 'is-connecting'
  return 'is-disconnected'
})

onMounted(() => {
  // #region debug-point C:app-shell-mounted
  window.__MC_DBG?.('C', 'src/App.vue:onMounted', '[DEBUG] app shell mounted', {
    route: route.fullPath,
    showAppChrome: showAppChrome.value,
  })
  nextTick(() => {
    window.__MC_DBG?.('C', 'src/App.vue:nextTick', '[DEBUG] app shell nextTick', {
      route: route.fullPath,
      appShellChildren: document.querySelector('.app-shell')?.childElementCount || 0,
    })
  })
  // #endregion
})
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  background: #fff1f5;
  color: #0f172a;
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 40;
  border-bottom: 1px solid #ffe4e6;
  background: #ffffff;
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: min(100%, 448px);
  height: 56px;
  margin: 0 auto;
  padding: 0 16px;
}

.brand-link {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-badge {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 14px;
  background: linear-gradient(135deg, #fb7185, #ec4899);
  color: #ffffff;
  font-size: 12px;
  font-weight: 700;
}

.brand-name {
  color: #1f2937;
  font-size: 16px;
  font-weight: 700;
}

.ble-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 999px;
  border: 1px solid #fbcfe8;
  background: #fff1f2;
  color: #e11d48;
  transition: transform 0.18s ease, border-color 0.18s ease, color 0.18s ease;
}

.ble-indicator:active {
  transform: scale(0.96);
}

.ble-icon {
  width: 18px;
  height: 18px;
}

.ble-indicator.is-connected {
  color: #16a34a;
  border-color: #86efac;
  background: #f0fdf4;
}

.ble-indicator.is-connecting {
  color: #d97706;
  border-color: #fcd34d;
  background: #fffbeb;
}

.ble-indicator.is-disconnected {
  color: #dc2626;
  border-color: #fda4af;
  background: #fff1f2;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
