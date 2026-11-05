<template>
  <div class="login-container">
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>

    <el-card class="login-card" shadow="never">
      <div class="card-header">
        <h2 class="card-title">AI 学习助手</h2>
        <p class="card-subtitle">用户登录</p>
      </div>

      <el-tabs v-model="activeTab" class="login-tabs">
        <el-tab-pane label="密码登录" name="password">
          <el-form ref="formRef" :model="form" :rules="rules" label-width="0">
            <el-form-item prop="username">
              <el-input v-model="form.username" placeholder="用户名" prefix-icon="User" />
            </el-form-item>
            <el-form-item prop="password">
              <el-input v-model="form.password" type="password" placeholder="密码" prefix-icon="Lock" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" style="width: 100%" @click="handleLogin" :loading="loading">登录</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="人脸登录" name="face">
          <FaceCamera @captured="handleFaceCapture" />
          <el-input v-model="faceUsername" placeholder="用户名" style="margin-top: 8px" prefix-icon="User" />
          <el-button type="primary" style="width: 100%; margin-top: 8px" @click="startFaceLogin" :loading="faceLoading">人脸登录</el-button>
        </el-tab-pane>
      </el-tabs>
      <div style="text-align: center; margin-top: 16px">
        <span style="color: #909399; font-size: 14px">还没有账号？</span>
        <el-button text type="primary" @click="router.push('/register')">去注册</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from "vue"
import { useRouter } from "vue-router"
import { ElMessage } from "element-plus"
import { login, loginFace } from "../api/auth"
import { useAppStore } from "../store"
import FaceCamera from "../components/FaceCamera.vue"

const router = useRouter()
const store = useAppStore()
const activeTab = ref("password")
const loading = ref(false)
const faceLoading = ref(false)
const faceUsername = ref("")
let faceBase64 = ""
const form = reactive({ username: "", password: "" })
const rules = { username: [{ required: true, message: "请输入用户名" }], password: [{ required: true, message: "请输入密码" }] }

async function handleLogin() {
  loading.value = true
  try {
    const res = await login(form.username, form.password)
    localStorage.setItem("token", res.data.access_token)
    store.setUser({ username: res.data.username })
    ElMessage.success("登录成功")
    router.push("/dashboard")
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "登录失败")
  }
  loading.value = false
}

function handleFaceCapture(base64) {
  faceBase64 = base64
  ElMessage.success("人脸采集成功")
}

async function startFaceLogin() {
  if (!faceUsername.value) { ElMessage.warning("请输入用户名"); return }
  if (!faceBase64) { ElMessage.warning("请先采集人脸"); return }
  faceLoading.value = true
  try {
    const res = await loginFace(faceUsername.value, faceBase64)
    localStorage.setItem("token", res.data.access_token)
    store.setUser({ username: res.data.username })
    ElMessage.success("人脸登录成功")
    router.push("/dashboard")
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "人脸识别失败")
  }
  faceLoading.value = false
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
  position: relative;
  overflow: hidden;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.4;
  pointer-events: none;
}

.orb-1 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, #00d2ff 0%, #3a7bd5 100%);
  top: -200px;
  right: -200px;
  animation: float 18s ease-in-out infinite;
}

.orb-2 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, #a18cd1 0%, #fbc2eb 100%);
  bottom: -200px;
  left: -150px;
  animation: float 22s ease-in-out infinite;
  animation-delay: -6s;
}

.orb-3 {
  width: 350px;
  height: 350px;
  background: radial-gradient(circle, #4facfe 0%, #667eea 100%);
  top: 40%;
  left: 60%;
  animation: float 15s ease-in-out infinite;
  animation-delay: -12s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(60px, -40px) scale(1.1); }
  50% { transform: translate(-40px, 30px) scale(0.9); }
  75% { transform: translate(30px, 50px) scale(1.05); }
}

.login-card {
  width: 420px;
  padding: 10px;
  border-radius: 16px !important;
  border: none !important;
  position: relative;
  z-index: 1;
}

.card-header {
  text-align: center;
  margin-bottom: 8px;
}

.card-title {
  font-size: 26px;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0 0 4px 0;
  letter-spacing: 1px;
}

.card-subtitle {
  color: #909399;
  font-size: 15px;
  margin: 0 0 16px 0;
  font-weight: 400;
}

.login-tabs :deep(.el-tabs__item) {
  font-size: 14px;
  padding: 0 16px;
}

.login-tabs :deep(.el-tabs__item.is-active) {
  font-weight: 600;
}

:deep(.el-card__body) {
  padding: 24px;
}
</style>
