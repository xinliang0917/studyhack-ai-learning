<template>
  <AppLayout>
    <h2 style="margin-bottom: 20px">系统设置</h2>
    <el-card shadow="hover" style="margin-bottom: 16px">
      <template #header><span>账户信息</span></template>
      <p>用户名: <strong>{{ store.user.username }}</strong></p>
      <div style="margin-top: 12px">
        <el-button type="primary" @click="showFaceDialog = true">管理人脸识别</el-button>
        <el-button type="danger" @click="handleLogout">退出登录</el-button>
      </div>
    </el-card>

    <el-card shadow="hover" style="margin-bottom: 16px">
      <template #header><span>语音设置</span></template>
      <el-form>
        <el-form-item label="启用语音交互">
          <el-switch v-model="store.voiceEnabled" />
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="hover">
      <template #header><span>关于</span></template>
      <p>AI 学习助手 v1.0</p>
      <p style="color: #909399; font-size: 13px; margin-top: 4px">基于 LangChain + Vue3 + FastAPI 构建</p>
    </el-card>

    <el-dialog v-model="showFaceDialog" title="人脸识别管理" width="400px">
      <FaceCamera @captured="handleFaceCapture" />
      <el-input v-model="faceUsername" placeholder="用户名" style="margin-top: 8px" />
    </el-dialog>
  </AppLayout>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AppLayout from '../components/AppLayout.vue'
import FaceCamera from '../components/FaceCamera.vue'
import { useAppStore } from '../store'
import { registerFace } from '../api/auth'

const router = useRouter()
const store = useAppStore()
const showFaceDialog = ref(false)
const faceUsername = ref(store.user.username)

function handleLogout() {
  store.logout()
  router.push('/login')
}

async function handleFaceCapture(base64) {
  try {
    await registerFace(faceUsername.value, base64)
    ElMessage.success('人脸注册成功')
    showFaceDialog.value = false
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '注册失败')
  }
}
</script>
