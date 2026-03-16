import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AdminInfo } from '@/types'
import { adminApi, getStoredToken, setStoredToken, removeStoredToken } from '@/api'

export const useAdminStore = defineStore('admin', () => {
  // State
  const isAuthenticated = ref(false)
  const adminInfo = ref<AdminInfo | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const username = computed(() => adminInfo.value?.username || '')
  const role = computed(() => adminInfo.value?.role || null)
  
  const isSuperAdmin = computed(() => role.value === 'super_admin')
  const isAdmin = computed(() => role.value === 'admin' || role.value === 'super_admin')
  const canEdit = computed(() => isAdmin.value)
  const canDelete = computed(() => isSuperAdmin.value)

  // Actions
  async function login(username: string, password: string): Promise<boolean> {
    isLoading.value = true
    error.value = null
    
    try {
      const response = await adminApi.login({ username, password })
      setStoredToken(response.access_token)
      
      // Verify token and get admin info
      const info = await adminApi.verifyToken()
      adminInfo.value = info
      isAuthenticated.value = true
      
      return true
    } catch (err: any) {
      error.value = err.response?.data?.detail || '登录失败，请检查用户名和密码'
      isAuthenticated.value = false
      adminInfo.value = null
      removeStoredToken()
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function logout(): Promise<void> {
    try {
      await adminApi.logout()
    } catch {
      // Ignore logout errors
    } finally {
      isAuthenticated.value = false
      adminInfo.value = null
      removeStoredToken()
    }
  }

  async function checkAuth(): Promise<boolean> {
    const token = getStoredToken()
    if (!token) {
      isAuthenticated.value = false
      adminInfo.value = null
      return false
    }

    try {
      const info = await adminApi.verifyToken()
      adminInfo.value = info
      isAuthenticated.value = true
      return true
    } catch {
      isAuthenticated.value = false
      adminInfo.value = null
      removeStoredToken()
      return false
    }
  }

  function clearError(): void {
    error.value = null
  }

  return {
    // State
    isAuthenticated,
    adminInfo,
    isLoading,
    error,
    // Computed
    username,
    role,
    isSuperAdmin,
    isAdmin,
    canEdit,
    canDelete,
    // Actions
    login,
    logout,
    checkAuth,
    clearError
  }
})
