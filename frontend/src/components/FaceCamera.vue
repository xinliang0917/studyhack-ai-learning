<template>
  <div>
    <el-alert
      v-if="cameraError"
      :title="cameraError"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 10px"
    />
    <video
      ref="videoRef"
      autoplay
      playsinline
      muted
      style="width: 100%; max-width: 400px; border-radius: 8px; border: 2px solid #dcdfe6; background: #111"
    ></video>
    <canvas ref="canvasRef" style="display:none"></canvas>
    <div style="margin-top: 8px; display: flex; gap: 8px; justify-content: center; flex-wrap: wrap">
      <el-button type="primary" @click="capture" :disabled="!videoReady">拍摄</el-button>
      <el-button @click="toggleCamera">{{ cameraActive ? '关闭摄像头' : '打开摄像头' }}</el-button>
      <el-button @click="triggerUpload">上传照片</el-button>
      <input
        ref="fileRef"
        type="file"
        accept="image/*"
        style="display:none"
        @change="onFileSelected"
      />
    </div>
    <p class="camera-hint">
      正对镜头，让人脸占画面 1/3 以上；避免逆光、侧脸和遮挡，拍摄后再点注册。
    </p>
  </div>
</template>

<script setup>
import { onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

const emit = defineEmits(['captured'])
const videoRef = ref(null)
const canvasRef = ref(null)
const fileRef = ref(null)
const cameraActive = ref(false)
const videoReady = ref(false)
const cameraError = ref('')
let stream = null

async function toggleCamera() {
  if (cameraActive.value) {
    stopCamera()
  } else {
    await startCamera()
  }
}

async function startCamera() {
  cameraError.value = ''
  if (!navigator.mediaDevices?.getUserMedia) {
    cameraError.value = '当前浏览器不支持摄像头，请改用 Chrome / Edge，或直接上传照片。'
    return
  }
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
      audio: false,
    })
    const video = videoRef.value
    if (!video) return
    video.srcObject = stream
    await video.play()
    await waitForVideo(video)
    if (!video.videoWidth || !video.videoHeight) {
      cameraError.value = '摄像头画面未就绪，请关闭后重新打开，或上传照片。'
      stopCamera()
      return
    }
    cameraActive.value = true
    videoReady.value = true
  } catch (e) {
    stopCamera()
    if (e?.name === 'NotAllowedError') {
      cameraError.value = '摄像头权限被拒绝。请允许浏览器访问摄像头，或在独立标签页打开本页面。'
    } else if (e?.name === 'NotFoundError') {
      cameraError.value = '未检测到摄像头，请连接摄像头或直接上传照片。'
    } else {
      cameraError.value = `摄像头启动失败：${e?.message || e}`
    }
  }
}

function waitForVideo(video) {
  return new Promise(resolve => {
    if (video.videoWidth > 0) {
      resolve()
      return
    }
    const done = () => {
      video.removeEventListener('loadedmetadata', done)
      video.removeEventListener('canplay', done)
      resolve()
    }
    video.addEventListener('loadedmetadata', done, { once: true })
    video.addEventListener('canplay', done, { once: true })
    setTimeout(done, 2500)
  })
}

function stopCamera() {
  if (stream) {
    stream.getTracks().forEach(track => track.stop())
    stream = null
  }
  if (videoRef.value) {
    videoRef.value.srcObject = null
  }
  cameraActive.value = false
  videoReady.value = false
}

function frameLooksUsable(ctx, width, height) {
  const data = ctx.getImageData(0, 0, width, height).data
  let sum = 0
  let sumSq = 0
  let count = 0
  for (let i = 0; i < data.length; i += 64) {
    const lum = data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114
    sum += lum
    sumSq += lum * lum
    count += 1
  }
  if (!count) return false
  const mean = sum / count
  const variance = sumSq / count - mean * mean
  return mean > 18 && variance > 8
}

function capture() {
  const video = videoRef.value
  const canvas = canvasRef.value
  if (!video || !canvas || !videoReady.value || !video.videoWidth) {
    ElMessage.warning('摄像头画面尚未就绪，请稍等再拍')
    return
  }
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  const ctx = canvas.getContext('2d')
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
  if (!frameLooksUsable(ctx, canvas.width, canvas.height)) {
    ElMessage.error('画面过暗或未就绪，请调整光线后重拍')
    return
  }
  emit('captured', canvas.toDataURL('image/jpeg', 0.92))
}

function triggerUpload() {
  fileRef.value?.click()
}

function onFileSelected(event) {
  const selected = event.target.files?.[0]
  event.target.value = ''
  if (!selected) return
  if (!selected.type?.startsWith('image/')) {
    ElMessage.warning('请选择图片文件')
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    if (typeof reader.result === 'string') {
      emit('captured', reader.result)
    }
  }
  reader.onerror = () => ElMessage.error('读取图片失败')
  reader.readAsDataURL(selected)
}

onUnmounted(() => { stopCamera() })
</script>

<style scoped>
.camera-hint {
  margin: 8px 0 0;
  color: #909399;
  font-size: 12px;
  text-align: center;
}
</style>
