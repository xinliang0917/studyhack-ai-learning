<template>
  <div class="register-container">
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>

    <el-card class="register-card" shadow="never">
      <div class="card-header">
        <h2 class="card-title">AI 学习助手</h2>
        <p class="card-subtitle">用户注册</p>
      </div>

      <el-steps :active="step" simple style="margin-bottom: 20px">
        <el-step title="创建账号" icon="User" />
        <el-step title="注册人脸（可选）" icon="Picture" />
      </el-steps>

      <div v-if="step === 0">
        <el-form ref="formRef" :model="form" :rules="rules" label-width="0">
          <el-form-item prop="username">
            <el-input v-model="form.username" placeholder="请输入用户名" prefix-icon="User" />
          </el-form-item>
          <el-form-item prop="password">
            <el-input v-model="form.password" type="password" placeholder="请输入密码" prefix-icon="Lock" show-password />
          </el-form-item>
          <el-form-item prop="confirmPassword">
            <el-input v-model="form.confirmPassword" type="password" placeholder="请再次输入密码" prefix-icon="Lock" show-password />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" style="width: 100%" @click="handleRegister" :loading="loading">注册</el-button>
          </el-form-item>
        </el-form>
      </div>

      <div v-if="step === 1">
        <el-alert title="账号创建成功！现在可以注册人脸，以后就能用人脸登录了" type="success" :closable="false" show-icon style="margin-bottom: 16px" />
        <div style="text-align: center; margin-bottom: 12px">
          <el-tag type="success">当前用户：{{ registeredUsername }}</el-tag>
        </div>
        <FaceCamera @captured="handleFaceCapture" />
        <el-button type="primary" style="width: 100%; margin-top: 12px" @click="startFaceRegister" :loading="faceLoading" :disabled="!faceCaptured">
          {{ faceCaptured ? "注册人脸" : "请先采集人脸" }}
        </el-button>
        <div style="margin-top: 12px; display: flex; gap: 8px; justify-content: center">
          <el-button @click="skipFace">跳过，去首页</el-button>
        </div>
      </div>

      <div style="text-align: center; margin-top: 16px">
        <span style="color: #909399; font-size: 14px">已有账号？</span>
        <el-button text type="primary" @click="router.push('/login')">去登录</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from "vue"
import { useRouter } from "vue-router"
import { ElMessage } from "element-plus"
import { register, registerFace } from "../api/auth"
import { useAppStore } from "../store"
import FaceCamera from "../components/FaceCamera.vue"

const router = useRouter()
const store = useAppStore()
const formRef = ref(null)
const step = ref(0)
const loading = ref(false)
const faceLoading = ref(false)
const registeredUsername = ref("")
const faceCaptured = ref(false)
let faceBase64 = ""

const form = reactive({ username: "", password: "", confirmPassword: "" })

const validatePass2 = (rule, value, callback) => {
  if (value !== form.password) {
    callback(new Error("两次密码输入不一致"))
  } else {
    callback()
  }
}

const rules = {
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    { min: 4, message: "密码至少4位", trigger: "blur" },
  ],
  confirmPassword: [
    { required: true, message: "请再次输入密码", trigger: "blur" },
    { validator: validatePass2, trigger: "blur" },
  ],
}

async function handleRegister() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    const res = await register(form.username, form.password)
    localStorage.setItem("token", res.data.access_token)
    store.setUser({ username: res.data.username })
    registeredUsername.value = form.username
    ElMessage.success("账号创建成功！")
    step.value = 1
  } catch (e) {
    const msg = e.response?.data?.detail
    if (msg === "Username already exists") {
      ElMessage.error("该用户名已被注册，请换一个")
    } else if (e.response?.status === 400) {
      ElMessage.error(msg || "请求参数有误")
    } else if (e.code === "ERR_NETWORK") {
      ElMessage.error("无法连接服务器，请确认后端服务是否启动")
    } else {
      ElMessage.error(msg || "注册失败，请重试")
    }
  }
  loading.value = false
}

function handleFaceCapture(base64) {
  faceBase64 = base64
  faceCaptured.value = true
  ElMessage.success("人脸采集成功，点击「注册人脸」完成注册")
}

async function startFaceRegister() {
  if (!faceBase64) { ElMessage.warning("请先采集人脸"); return }
  faceLoading.value = true
  try {
    const res = await registerFace(registeredUsername.value, faceBase64)
    ElMessage.success(res.data?.message || "人脸注册成功")
    router.push("/dashboard")
  } catch (e) {
    const errMsg = e.response?.data?.detail || "人脸注册失败，请确保光线充足且正对摄像头"
    ElMessage.error(errMsg)
    faceCaptured.value = false
    faceBase64 = ""
  }
  faceLoading.value = false
}

function skipFace() {
  ElMessage.success("欢迎使用 AI 学习助手！")
  router.push("/dashboard")
}
</script>

<style scoped>
.register-container {
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

.register-card {
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

.register-tabs :deep(.el-tabs__item) {
  font-size: 14px;
  padding: 0 16px;
}

.register-tabs :deep(.el-tabs__item.is-active) {
  font-weight: 600;
}

:deep(.el-card__body) {
  padding: 24px;
}
</style>
