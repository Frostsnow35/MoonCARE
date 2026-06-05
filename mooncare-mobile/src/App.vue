<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from './stores/auth'

const auth_store = useAuthStore()

onMounted(() => {
  auth_store.initialize_auth()
})
</script>

<template>
  <div class="app">
    <header class="topbar">
      <div class="topbar-title">MoonCARE</div>
      <div class="topbar-actions">
        <router-link class="topbar-link" to="/settings">设置</router-link>
      </div>
    </header>

    <main class="content">
      <router-view />
    </main>

    <nav class="tabbar">
      <router-link class="tabbar-item" to="/">蓝牙</router-link>
      <router-link class="tabbar-item" to="/login">登录</router-link>
    </nav>
  </div>
</template>
