<template>
  <el-container style="height: 100vh">
    <el-aside v-if="!isMobile" :width="collapsed ? '64px' : '220px'" class="app-aside">
      <div class="logo">
        <span v-if="!collapsed">AI 学习助手</span>
        <el-icon v-else :size="24"><Monitor /></el-icon>
      </div>
      <el-menu
        :default-active="route.path"
        :collapse="collapsed"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
        router
        style="border-right: none"
      >
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <span v-if="!collapsed">{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="app-header">
        <div class="header-left">
          <el-icon v-if="isMobile" style="cursor: pointer" @click="drawer = true"><Menu /></el-icon>
          <el-icon v-else style="cursor: pointer" @click="collapsed = !collapsed"><Fold /></el-icon>
        </div>
        <div class="header-right">
          <VoiceControl />
          <el-tooltip :content="dark ? '切换浅色' : '切换暗色'" placement="bottom">
            <el-icon class="theme-toggle" @click="toggleDark">
              <Sunny v-if="dark" />
              <Moon v-else />
            </el-icon>
          </el-tooltip>
          <el-dropdown trigger="click">
            <span style="cursor: pointer; display: flex; align-items: center; gap: 4px;">
              <el-icon><User /></el-icon> {{ store.user.username || '用户' }}
            </span>
            <template #dropdown>
              <el-dropdown-item @click="logout">退出登录</el-dropdown-item>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="app-main">
        <slot />
      </el-main>
    </el-container>

    <el-drawer v-model="drawer" direction="ltr" size="220px" :with-header="false">
      <div class="drawer-logo">AI 学习助手</div>
      <el-menu
        :default-active="route.path"
        router
        background-color="transparent"
        @select="drawer = false"
      >
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
    </el-drawer>
  </el-container>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '../store'
import VoiceControl from './VoiceControl.vue'

const route = useRoute()
const router = useRouter()
const store = useAppStore()
const collapsed = ref(false)
const drawer = ref(false)
const isMobile = ref(typeof window !== 'undefined' && window.innerWidth < 768)
const dark = ref(localStorage.getItem('theme') === 'dark')

const menuItems = [
  { path: '/dashboard', label: '首页', icon: 'DataBoard' },
  { path: '/knowledge', label: '知识库', icon: 'Folder' },
  { path: '/rag', label: 'AI 问答', icon: 'ChatDotRound' },
  { path: '/schedule', label: '学习计划', icon: 'Calendar' },
  { path: '/course', label: '课程大纲', icon: 'Reading' },
  { path: '/knowledge-graph', label: '知识图谱', icon: 'Share' },
  { path: '/quiz', label: '在线测验', icon: 'Edit' },
  { path: '/wrong-questions', label: '错题本', icon: 'Warning' },
  { path: '/settings', label: '设置', icon: 'Setting' },
]

watchEffect(() => {
  document.documentElement.classList.toggle('dark', dark.value)
  localStorage.setItem('theme', dark.value ? 'dark' : 'light')
})

function toggleDark() {
  dark.value = !dark.value
}

function onResize() {
  isMobile.value = window.innerWidth < 768
  if (!isMobile.value) drawer.value = false
}

onMounted(() => window.addEventListener('resize', onResize))
onBeforeUnmount(() => window.removeEventListener('resize', onResize))

function logout() {
  store.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-aside {
  transition: width 0.3s;
  background: #304156;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.app-header {
  height: 50px;
  background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}
.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.theme-toggle {
  cursor: pointer;
  font-size: 18px;
  color: var(--el-text-color-regular);
}
.app-main {
  background: var(--el-bg-color-page);
  padding: 20px;
  overflow-y: auto;
}
.drawer-logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid var(--el-border-color-light);
}
@media (max-width: 768px) {
  .app-header {
    padding: 0 12px;
  }
  .app-main {
    padding: 12px;
  }
}
</style>
