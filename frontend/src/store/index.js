import { defineStore } from 'pinia'
import { ref } from 'vue'
import { clearToken } from '../utils/token'

export const useAppStore = defineStore('app', () => {
  const user = ref(JSON.parse(localStorage.getItem('user') || '{}'))
  const voiceEnabled = ref(true)
  const sidebarCollapsed = ref(false)

  function setUser(u) {
    user.value = u
    localStorage.setItem('user', JSON.stringify(u))
  }

  function logout() {
    user.value = {}
    clearToken()
    localStorage.removeItem('user')
  }

  return { user, voiceEnabled, sidebarCollapsed, setUser, logout }
})
