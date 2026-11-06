<template>
  <AppLayout>
    <div class="page-head">
      <div>
        <h2>拍照识题</h2>
        <p>上传题目图片，OCR 识别后结合知识库分步讲解；识别不准时可直接修改文字再讲解。</p>
      </div>
      <el-button @click="resetAll">重新开始</el-button>
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :lg="10">
        <el-card shadow="hover">
          <template #header><span>题目图片</span></template>
          <div
            class="drop-zone"
            @click="triggerFile"
            @dragover.prevent
            @drop.prevent="onDrop"
          >
            <img v-if="previewUrl" :src="previewUrl" class="preview" alt="题目预览" />
            <template v-else>
              <el-icon :size="40" color="#409eff"><Camera /></el-icon>
              <p>点击拍照或选择图片</p>
              <span>支持 JPG、PNG，建议光线充足、题目完整</span>
            </template>
            <input ref="fileRef" type="file" accept="image/*" capture="environment" style="display:none" @change="onFileSelected" />
          </div>
          <div class="upload-actions">
            <el-button type="primary" :loading="solving" :disabled="!file" @click="solveImage">
              识别并讲解
            </el-button>
            <el-button :disabled="!file || solving" @click="removeImage">移除图片</el-button>
          </div>
          <el-alert
            v-if="error"
            :title="error"
            type="error"
            show-icon
            :closable="false"
            style="margin-top: 12px"
          />
        </el-card>

        <el-card shadow="hover" style="margin-top: 16px">
          <template #header>
            <span>识别到的题目</span>
            <el-tag v-if="ocrUsed" size="small" type="success" style="float: right">OCR 识别</el-tag>
          </template>
          <el-input
            v-model="questionText"
            type="textarea"
            :rows="6"
            placeholder="识别结果会显示在这里；也可以直接手动输入题目"
          />
          <el-button
            type="primary"
            plain
            style="width: 100%; margin-top: 10px"
            :loading="solving"
            :disabled="!questionText.trim()"
            @click="solveText"
          >
            用这段文字重新讲解
          </el-button>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="14">
        <el-card shadow="hover" class="answer-card">
          <template #header>
            <span>分步讲解</span>
            <div v-if="answer" class="answer-actions">
              <el-button text size="small" @click="readAnswer">朗读</el-button>
              <el-button text size="small" @click="stopReading">停止</el-button>
            </div>
          </template>
          <div v-if="solving" class="solving">
            <el-icon class="is-loading" :size="30"><Loading /></el-icon>
            <p>正在识别题目并生成分步讲解...</p>
          </div>
          <div v-else-if="answer" ref="answerRef">
            <div class="markdown" v-html="answerHtml"></div>
          </div>
          <el-empty v-else description="上传图片或输入题目后，这里会显示分步讲解" />
        </el-card>

        <el-card v-if="sources.length" shadow="hover" style="margin-top: 16px">
          <template #header><span>引用来源</span></template>
          <div v-for="(source, index) in sources" :key="index" class="source">
            <div class="source-head">
              <span class="source-no">[{{ index + 1 }}]</span>
              <span class="source-name">{{ source.filename || '知识库片段' }}</span>
              <span class="source-score">相关度 {{ Math.round((source.score || 0) * 100) }}%</span>
            </div>
            <div class="source-content">{{ source.content }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </AppLayout>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import renderMathInElement from 'katex/contrib/auto-render'
import 'katex/dist/katex.min.css'
import AppLayout from '../components/AppLayout.vue'
import { photoSolve } from '../api/quiz'
import { cancelSpeech, speak } from '../composables/useVoice'

marked.setOptions({ breaks: true, gfm: true })

const fileRef = ref(null)
const file = ref(null)
const previewUrl = ref('')
const questionText = ref('')
const answer = ref('')
const answerHtml = ref('')
const answerRef = ref(null)
const sources = ref([])
const ocrUsed = ref(false)
const solving = ref(false)
const error = ref('')

function triggerFile() {
  fileRef.value?.click()
}

function setFile(selected) {
  if (!selected) return
  if (!selected.type?.startsWith('image/')) {
    ElMessage.warning('请选择图片文件')
    return
  }
  removePreview()
  file.value = selected
  previewUrl.value = URL.createObjectURL(selected)
  error.value = ''
}

function onFileSelected(event) {
  setFile(event.target.files?.[0])
  event.target.value = ''
}

function onDrop(event) {
  setFile(event.dataTransfer?.files?.[0])
}

function removePreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
}

function removeImage() {
  removePreview()
  file.value = null
}

function renderAnswer(text) {
  answer.value = text || ''
  answerHtml.value = DOMPurify.sanitize(marked.parse(text || ''))
  nextTick(() => {
    if (!answerRef.value) return
    try {
      renderMathInElement(answerRef.value, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '\\[', right: '\\]', display: true },
          { left: '$', right: '$', display: false },
          { left: '\\(', right: '\\)', display: false },
        ],
        throwOnError: false,
      })
    } catch (e) { /* ignore */ }
  })
}

async function solveImage() {
  if (!file.value) return
  solving.value = true
  error.value = ''
  answer.value = ''
  sources.value = []
  try {
    const form = new FormData()
    form.append('file', file.value)
    const res = await photoSolve(form)
    questionText.value = res.data.recognized_text || ''
    ocrUsed.value = Boolean(res.data.ocr_used)
    sources.value = res.data.sources || []
    renderAnswer(res.data.answer || '')
  } catch (e) {
    error.value = e.response?.data?.detail || '识别或讲解失败，请重试或手动输入题目'
    ElMessage.error(error.value)
  } finally {
    solving.value = false
  }
}

async function solveText() {
  const text = questionText.value.trim()
  if (!text) {
    ElMessage.warning('请先输入或识别题目')
    return
  }
  solving.value = true
  error.value = ''
  answer.value = ''
  sources.value = []
  try {
    const form = new FormData()
    form.append('text', text)
    const res = await photoSolve(form)
    ocrUsed.value = Boolean(res.data.ocr_used)
    sources.value = res.data.sources || []
    renderAnswer(res.data.answer || '')
  } catch (e) {
    error.value = e.response?.data?.detail || '讲解失败，请稍后重试'
    ElMessage.error(error.value)
  } finally {
    solving.value = false
  }
}

function readAnswer() {
  if (answer.value) speak(answer.value)
}

function stopReading() {
  cancelSpeech()
}

function resetAll() {
  removeImage()
  file.value = null
  questionText.value = ''
  answer.value = ''
  answerHtml.value = ''
  sources.value = []
  ocrUsed.value = false
  error.value = ''
}

onBeforeUnmount(() => {
  removePreview()
  cancelSpeech()
})
</script>

<style scoped>
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}
.page-head h2 {
  margin: 0;
  color: var(--el-text-color-primary);
}
.page-head p {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.drop-zone {
  min-height: 240px;
  border: 2px dashed var(--el-border-color);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  overflow: hidden;
  transition: border-color 0.2s;
}
.drop-zone:hover {
  border-color: #409eff;
}
.drop-zone p {
  margin: 0;
  color: var(--el-text-color-regular);
}
.drop-zone span {
  font-size: 12px;
}
.preview {
  width: 100%;
  max-height: 360px;
  object-fit: contain;
}
.upload-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
.answer-card {
  min-height: 420px;
}
.answer-actions {
  float: right;
  display: flex;
  gap: 2px;
}
.solving {
  text-align: center;
  padding: 80px 20px;
  color: var(--el-text-color-secondary);
}
.markdown {
  line-height: 1.85;
  color: var(--el-text-color-primary);
  font-size: 14px;
}
.markdown :deep(p) {
  margin: 0 0 10px;
}
.markdown :deep(ul),
.markdown :deep(ol) {
  padding-left: 22px;
  margin: 8px 0;
}
.markdown :deep(code) {
  background: var(--el-fill-color-light);
  padding: 1px 5px;
  border-radius: 4px;
}
.markdown :deep(pre) {
  background: var(--el-fill-color-light);
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
}
.source {
  background: var(--el-fill-color-lighter);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 8px;
}
.source:last-child {
  margin-bottom: 0;
}
.source-head {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
}
.source-no {
  color: #409eff;
  font-weight: 600;
}
.source-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.source-content {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
}
@media (max-width: 768px) {
  .page-head {
    flex-direction: column;
    gap: 10px;
  }
}
</style>
