<template>
  <div class="welcome-page">
    <div class="welcome-shell">
      <section class="welcome-hero">
        <div class="logo-frame">
          <img :src="mooncareLogo" alt="MoonCARE logo" class="logo-image" />
        </div>
        <div class="hero-copy">
          <p class="eyebrow">她语</p>
          <h1 class="title">MoonCARE</h1>
        </div>
      </section>

      <section class="welcome-actions">
        <router-link :to="loginTarget" class="action-button action-button-primary">
          登录
        </router-link>
        <router-link :to="registerTarget" class="action-button action-button-secondary">
          注册
        </router-link>
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

<style scoped>
.welcome-page {
  min-height: 100vh;
  background:
    radial-gradient(circle at top, rgba(244, 114, 182, 0.18), transparent 40%),
    linear-gradient(180deg, #fff7fb 0%, #ffffff 58%, #fff1f7 100%);
}

.welcome-shell {
  min-height: 100vh;
  max-width: 480px;
  margin: 0 auto;
  padding: 48px 28px calc(40px + env(safe-area-inset-bottom));
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.welcome-hero {
  padding-top: 64px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}

.logo-frame {
  width: 132px;
  height: 132px;
  border-radius: 36px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 24px 60px rgba(244, 114, 182, 0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(14px);
}

.logo-image {
  width: 92px;
  height: 92px;
  object-fit: contain;
}

.hero-copy {
  text-align: center;
}

.eyebrow {
  margin: 0 0 10px;
  font-size: 14px;
  letter-spacing: 0.18em;
  color: #ec4899;
}

.title {
  margin: 0;
  font-size: 34px;
  font-weight: 700;
  color: #1f2937;
}

.welcome-actions {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.action-button {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 56px;
  border-radius: 999px;
  font-size: 17px;
  font-weight: 600;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.action-button:active {
  transform: scale(0.985);
}

.action-button-primary {
  color: #ffffff;
  background: linear-gradient(135deg, #fb7185 0%, #ec4899 100%);
  box-shadow: 0 18px 36px rgba(236, 72, 153, 0.26);
}

.action-button-secondary {
  color: #be185d;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(244, 114, 182, 0.2);
}
</style>
