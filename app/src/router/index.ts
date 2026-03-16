import { createRouter, createWebHashHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Welcome',
    component: () => import('@/views/WelcomePage.vue'),
    meta: { title: '欢迎' }
  },
  {
    path: '/assessment',
    name: 'Assessment',
    component: () => import('@/views/AssessmentPage.vue'),
    meta: { title: '情绪评估' }
  },
  {
    path: '/therapy',
    name: 'Therapy',
    component: () => import('@/views/TherapyPage.vue'),
    meta: { title: '疗愈进行' }
  },
  {
    path: '/report',
    name: 'Report',
    component: () => import('@/views/ReportPage.vue'),
    meta: { title: '疗愈报告' }
  },
  // Admin routes
  {
    path: '/admin',
    redirect: '/admin/login'
  },
  {
    path: '/admin/login',
    name: 'AdminLogin',
    component: () => import('@/views/admin/AdminLoginPage.vue'),
    meta: { title: '管理后台登录', isAdmin: true }
  },
  {
    path: '/admin/dashboard',
    name: 'AdminDashboard',
    component: () => import('@/views/admin/AdminDashboardPage.vue'),
    meta: { title: '管理后台', isAdmin: true, requiresAuth: true }
  },
  {
    path: '/admin/config',
    name: 'AdminConfig',
    component: () => import('@/views/admin/AdminConfigPage.vue'),
    meta: { title: '配置管理', isAdmin: true, requiresAuth: true }
  },
  {
    path: '/admin/logs',
    name: 'AdminLogs',
    component: () => import('@/views/admin/AdminLogsPage.vue'),
    meta: { title: '系统日志', isAdmin: true, requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// Navigation guard for admin routes
router.beforeEach(async (to, _from, next) => {
  if (to.meta.requiresAuth) {
    const { useAdminStore } = await import('@/stores/admin')
    const adminStore = useAdminStore()
    
    const isAuth = await adminStore.checkAuth()
    if (!isAuth) {
      next({ name: 'AdminLogin', query: { redirect: to.fullPath } })
      return
    }
  }
  next()
})

export default router
