import { defineStore } from 'pinia'
import { ref } from 'vue'

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
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  return { user, voiceEnabled, sidebarCollapsed, setUser, logout }
})
