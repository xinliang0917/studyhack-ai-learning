<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getMe } from './api/auth'
import { clearToken } from './utils/token'

const router = useRouter()

onMounted(async () => {
  await router.isReady()
  const token = localStorage.getItem('token')
  const path = router.currentRoute.value.path
  const publicPaths = ['/login', '/register']
  if (!token) {
    if (!publicPaths.includes(path)) router.replace('/login')
    return
  }
  try {
    const res = await getMe()
    localStorage.setItem('user', JSON.stringify({ username: res.data.username }))
  } catch (e) {
    if (e.response?.status === 401) {
      clearToken()
      localStorage.removeItem('user')
      if (!publicPaths.includes(path)) router.replace('/login')
    }
  }
})
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app { height: 100%; width: 100%; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; }
</style>
