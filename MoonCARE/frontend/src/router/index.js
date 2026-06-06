import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Welcome',
    component: () => import('../views/Welcome.vue'),
    meta: { guestOnly: true, hideChrome: true }
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('../views/Home.vue'),
    meta: { requiresAuth: true, navGroup: 'home' }
  },
  {
    path: '/home-old',
    redirect: '/home'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { guestOnly: true, hideChrome: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { guestOnly: true, hideChrome: true }
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('../views/ForgotPassword.vue'),
    meta: { guestOnly: true, hideChrome: true }
  },
  {
    path: '/diary',
    name: 'Diary',
    component: () => import('../views/Diary.vue'),
    meta: { requiresAuth: true, navGroup: 'diary' }
  },
  {
    path: '/diary/:id',
    name: 'DiaryDetail',
    component: () => import('../views/DiaryDetail.vue'),
    meta: { requiresAuth: true, navGroup: 'diary' }
  },
  {
    path: '/cycle',
    name: 'Cycle',
    component: () => import('../views/Cycle.vue'),
    meta: { requiresAuth: true, navGroup: 'cycle' }
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('../views/Chat.vue'),
    meta: { requiresAuth: true, navGroup: 'chat' }
  },
  {
    path: '/breathing',
    name: 'Breathing',
    component: () => import('../views/Breathing.vue'),
    meta: { requiresAuth: true, navGroup: 'profile' }
  },
  {
    path: '/music',
    name: 'Music',
    component: () => import('../views/MusicPlayer.vue'),
    meta: { requiresAuth: true, navGroup: 'profile' }
  },
  {
    path: '/wave',
    name: 'WaveMonitor',
    component: () => import('../views/WaveMonitor.vue'),
    meta: { requiresAuth: true, navGroup: 'profile' }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../views/Profile.vue'),
    meta: { requiresAuth: true, navGroup: 'profile' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  const isAuthenticated = !!token

  if (to.meta.requiresAuth && !isAuthenticated) {
    next({ name: 'Welcome', query: { redirect: to.fullPath } })
  } else if (to.meta.guestOnly && isAuthenticated) {
    next({ name: 'Home' })
  } else {
    next()
  }
})

export default router
