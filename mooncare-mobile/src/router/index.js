import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/home',
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('../views/Home.vue'),
    meta: { requiresAuth: true, navGroup: 'home' },
  },
  {
    path: '/home-old',
    name: 'HomeOld',
    component: () => import('../views/HomeOld.vue'),
    meta: { requiresAuth: true, navGroup: 'home' },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { guestOnly: true, hideChrome: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { guestOnly: true, hideChrome: true },
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('../views/ForgotPassword.vue'),
    meta: { guestOnly: true, hideChrome: true },
  },
  {
    path: '/diary',
    name: 'Diary',
    component: () => import('../views/Diary.vue'),
    meta: { requiresAuth: true, navGroup: 'diary' },
  },
  {
    path: '/diary/:id',
    name: 'DiaryDetail',
    component: () => import('../views/DiaryDetail.vue'),
    meta: { requiresAuth: true, navGroup: 'diary' },
  },
  {
    path: '/cycle',
    name: 'Cycle',
    component: () => import('../views/Cycle.vue'),
    meta: { requiresAuth: true, navGroup: 'cycle' },
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('../views/Chat.vue'),
    meta: { requiresAuth: true, navGroup: 'chat', hideChrome: true },
  },
  {
    path: '/breathing',
    name: 'Breathing',
    component: () => import('../views/Breathing.vue'),
    meta: { requiresAuth: true, navGroup: 'tools' },
  },
  {
    path: '/music',
    name: 'Music',
    component: () => import('../views/MusicPlayer.vue'),
    meta: { requiresAuth: true, navGroup: 'tools' },
  },
  {
    path: '/wave',
    name: 'WaveMonitor',
    component: () => import('../views/WaveMonitor.vue'),
    meta: { requiresAuth: true, navGroup: 'tools' },
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../views/Profile.vue'),
    meta: { requiresAuth: true, navGroup: 'profile' },
  },
  {
    path: '/ble',
    name: 'BleMonitor',
    component: () => import('../views/BleMonitor.vue'),
    meta: { requiresAuth: true, navGroup: 'tools' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings.vue'),
    meta: { requiresAuth: true, navGroup: 'profile' },
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  const isAuthenticated = Boolean(token)
  // #region debug-point B:router-before-each
  window.__MC_DBG?.('B', 'src/router/index.js:beforeEach', '[DEBUG] router beforeEach', {
    to: to.fullPath,
    from: from.fullPath,
    requiresAuth: Boolean(to.meta.requiresAuth),
    guestOnly: Boolean(to.meta.guestOnly),
    isAuthenticated,
  })
  // #endregion

  if (to.meta.requiresAuth && !isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.meta.guestOnly && isAuthenticated) {
    next({ name: 'Home' })
  } else {
    next()
  }
})

router.afterEach((to, from) => {
  // #region debug-point B:router-after-each
  window.__MC_DBG?.('B', 'src/router/index.js:afterEach', '[DEBUG] router afterEach', {
    to: to.fullPath,
    from: from.fullPath,
    name: String(to.name || ''),
  })
  // #endregion
})

export default router
