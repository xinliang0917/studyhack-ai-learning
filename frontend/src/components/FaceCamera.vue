<template>
  <div>
    <video ref="videoRef" autoplay playsinline style="width: 100%; max-width: 400px; border-radius: 8px; border: 2px solid #dcdfe6"></video>
    <canvas ref="canvasRef" style="display:none"></canvas>
    <div style="margin-top: 8px; display: flex; gap: 8px; justify-content: center">
      <el-button type="primary" @click="capture" :disabled="!cameraActive">拍摄</el-button>
      <el-button @click="toggleCamera">{{ cameraActive ? '关闭摄像头' : '打开摄像头' }}</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'

const emit = defineEmits(['captured'])
const videoRef = ref(null)
const canvasRef = ref(null)
const cameraActive = ref(false)
let stream = null

async function toggleCamera() {
  if (cameraActive.value) {
    stopCamera()
  } else {
    await startCamera()
  }
}

async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
    if (videoRef.value) {
      videoRef.value.srcObject = stream
      cameraActive.value = true
    }
  } catch (e) {
    console.error('Camera error:', e)
  }
}

function stopCamera() {
  if (stream) {
    stream.getTracks().forEach(t => t.stop())
    stream = null
  }
  cameraActive.value = false
}

function capture() {
  if (!videoRef.value || !canvasRef.value) return
  const video = videoRef.value
  const canvas = canvasRef.value
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  const ctx = canvas.getContext('2d')
  ctx.drawImage(video, 0, 0)
  const base64 = canvas.toDataURL('image/jpeg', 0.9)
  emit('captured', base64)
}

onUnmounted(() => { stopCamera() })
</script>
