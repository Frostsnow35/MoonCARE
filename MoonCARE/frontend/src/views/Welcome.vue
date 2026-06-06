<template>
  <div class="auth-page">
    <div class="auth-shell">
      <section class="auth-card overflow-hidden p-6 text-center sm:p-8">
        <div class="auth-brand-mark">
          <img :src="mooncareLogo" alt="MoonCARE logo" class="h-14 w-14 object-contain" />
        </div>

        <p class="section-label justify-center">她语</p>
        <h1 class="auth-title mt-3">MoonCARE</h1>
        <p class="auth-copy">
          围绕周期波动、经前情绪和身体感受，给你一段轻量、自然、可继续的陪伴对话。
        </p>

        <div class="mt-8 grid gap-3">
          <router-link :to="loginTarget" class="primary-button flex min-h-[3.25rem] items-center justify-center">
            登录
          </router-link>
          <router-link :to="registerTarget" class="secondary-button flex min-h-[3.25rem] items-center justify-center">
            注册
          </router-link>
        </div>

        <div class="mt-8 rounded-2xl border border-pink-100 bg-pink-50/70 p-4 text-left">
          <p class="text-sm font-semibold text-slate-700">这不是筛查问卷。</p>
          <p class="mt-2 text-sm leading-6 text-slate-500">
            进入后可以先从聊天开始，慢慢聊最近的情绪、睡眠、疼痛和周期变化，再决定要不要继续细化。
          </p>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import mooncareLogo from '../assets/mooncare-logo.png'

const route = useRoute()

const authQuery = computed(() => (
  route.query.redirect ? { redirect: route.query.redirect } : {}
))

const loginTarget = computed(() => ({
  name: 'Login',
  query: authQuery.value
}))

const registerTarget = computed(() => ({
  name: 'Register',
  query: authQuery.value
}))
</script>
