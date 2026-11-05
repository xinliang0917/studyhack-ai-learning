<template>
  <el-container style="height: 100vh">
    <el-aside :width="collapsed ? '64px' : '220px'" style="transition: width 0.3s; background: #304156">
      <div style="height: 60px; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 18px; font-weight: bold; border-bottom: 1px solid rgba(255,255,255,0.1)">
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
        <el-menu-item index="/dashboard"><el-icon><DataBoard /></el-icon><span>首页</span></el-menu-item>
        <el-menu-item index="/knowledge"><el-icon><Folder /></el-icon><span>知识库</span></el-menu-item>
        <el-menu-item index="/rag"><el-icon><ChatDotRound /></el-icon><span>AI 问答</span></el-menu-item>
        <el-menu-item index="/course"><el-icon><Reading /></el-icon><span>课程大纲</span></el-menu-item>
        <el-menu-item index="/quiz"><el-icon><Edit /></el-icon><span>在线测验</span></el-menu-item>
        <el-menu-item index="/wrong-questions"><el-icon><Warning /></el-icon><span>错题本</span></el-menu-item>
        <el-menu-item index="/settings"><el-icon><Setting /></el-icon><span>设置</span></el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header style="height: 50px; background: #fff; border-bottom: 1px solid #e6e6e6; display: flex; align-items: center; justify-content: space-between; padding: 0 20px">
        <el-icon style="cursor: pointer" @click="collapsed = !collapsed"><Fold /></el-icon>
        <div style="display: flex; align-items: center; gap: 12px">
          <VoiceControl />
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
      <el-main style="background: #f0f2f5; padding: 20px; overflow-y: auto">
        <slot />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '../store'
import VoiceControl from './VoiceControl.vue'

const route = useRoute()
const router = useRouter()
const store = useAppStore()
const collapsed = ref(false)

function logout() {
  store.logout()
  router.push('/login')
}
</script>
