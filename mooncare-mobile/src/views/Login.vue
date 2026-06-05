<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'

const auth_store = useAuthStore()

const email = ref('')
const password = ref('')

async function submit() {
  await auth_store.login(email.value.trim(), password.value)
}
</script>

<template>
  <section class="page">
    <div class="card">
      <div class="row">
        <div class="label">邮箱</div>
        <input class="input" v-model="email" autocomplete="email" />
      </div>
      <div class="row">
        <div class="label">密码</div>
        <input class="input" v-model="password" type="password" autocomplete="current-password" />
      </div>

      <div v-if="auth_store.error_msg" class="error">{{ auth_store.error_msg }}</div>

      <div class="actions">
        <button class="btn primary" :disabled="auth_store.status === 'loading'" @click="submit">登录</button>
        <button class="btn" :disabled="!auth_store.is_authed" @click="auth_store.logout">退出</button>
      </div>

      <div class="muted">
        <div>当前状态：{{ auth_store.is_authed ? '已登录' : '未登录' }}</div>
      </div>
    </div>
  </section>
</template>

