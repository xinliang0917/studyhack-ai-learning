<template>
  <AppLayout>
    <el-button text @click="router.back()" style="margin-bottom: 16px"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
    <el-card shadow="hover">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <h3 style="margin: 0">{{ chapter.title }}</h3>
          <span v-if="allChapters.length" style="font-size: 13px; color: #909399">{{ currentIndex + 1 }} / {{ allChapters.length }}</span>
        </div>
      </template>
      <div v-if="generating" style="text-align: center; padding: 40px">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <p style="margin-top: 12px; color: #909399">正在生成学习内容...</p>
      </div>
      <div v-else-if="chapter.content" style="line-height: 1.8; font-size: 15px" v-html="chapter.content"></div>
      <el-empty v-else description="尚未生成学习内容" />
      <div style="margin-top: 16px; display: flex; align-items: center; justify-content: space-between" v-if="chapter.title">
        <div>
          <el-button :disabled="currentIndex <= 0" @click="goToPrev" size="small">
            <el-icon><ArrowLeft /></el-icon> 上一节
          </el-button>
          <el-button :disabled="currentIndex >= allChapters.length - 1" @click="goToNext" size="small">
            下一节 <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
        <div style="display: flex; gap: 8px">
          <el-button @click="markStatus('learning')">标记学习中</el-button>
          <el-button type="success" @click="markStatus('completed')">标记已完成</el-button>
          <el-button type="primary" @click="readContent" :disabled="!chapter.content">
            <el-icon><svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3A4.5 4.5 0 0 0 14 8.5v5a4.47 4.47 0 0 0 2.5-1.5zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg></el-icon> 朗读
          </el-button>
        </div>
      </div>
    </el-card>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { speak, toggleMute, isMuted } from '../composables/useVoice'
import AppLayout from '../components/AppLayout.vue'
import { getChapter, getChapters, generateChapterContent, updateProgress } from '../api/course'

const route = useRoute()
const router = useRouter()
const chapter = ref({})
const generating = ref(false)
const allChapters = ref([])
const currentIndex = ref(-1)

async function loadChapter(chapterId) {
  try {
    const [res, chaptersRes] = await Promise.all([
      getChapter(chapterId),
      route.params.outlineId ? getChapters(route.params.outlineId) : Promise.resolve({ data: [] })
    ])
    chapter.value = res.data
    allChapters.value = chaptersRes.data || []
    currentIndex.value = allChapters.value.findIndex(c => c.id == chapterId)
    if (!chapter.value.content) {
      await generateContent()
    }
  } catch (e) { /* ignore */ }
}

onMounted(() => {
  loadChapter(route.params.chapterId)
})

watch(() => route.params.chapterId, (newId) => {
  if (newId) {
    generating.value = false
    loadChapter(newId)
  }
})

async function generateContent() {
  generating.value = true
  try {
    const res = await generateChapterContent(route.params.chapterId)
    chapter.value.content = res.data.content
    ElMessage.success('学习内容已生成')
  } catch (e) {
    ElMessage.error('生成失败')
  }
  generating.value = false
}


function readAloud() {
  if (!chapter.value.content) return
  const text = (chapter.value.title || "") + "。" + chapter.value.content.replace(/<[^>]+>/g, "").replace(/\s+/g, " ")
  speak(text)
}

function goToPrev() {
  if (currentIndex.value > 0) {
    const prev = allChapters.value[currentIndex.value - 1]
    router.push(`/course/${route.params.outlineId}/chapter/${prev.id}`)
  }
}

function goToNext() {
  if (currentIndex.value < allChapters.value.length - 1) {
    const next = allChapters.value[currentIndex.value + 1]
    router.push(`/course/${route.params.outlineId}/chapter/${next.id}`)
  }
}

async function markStatus(status) {
  try {
    await updateProgress(route.params.chapterId, status)
    ElMessage.success(status === 'completed' ? '已标记完成' : '已标记')
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

function readContent() {
  if (!chapter.value.content) return
  const div = document.createElement('div')
  div.innerHTML = chapter.value.content
  const text = div.textContent || div.innerText || ''
  const title = chapter.value.title || ''
  if (isMuted()) toggleMute()
  speak(title + '：' + text.substring(0, 500))
}

</script>
