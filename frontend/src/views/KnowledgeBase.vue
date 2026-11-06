<template>
  <AppLayout>
    <h2 style="margin-bottom: 20px">知识库管理</h2>
    <el-card shadow="hover" style="margin-bottom: 16px">
      <div style="text-align: center; padding: 40px 20px; border: 2px dashed #dcdfe6; border-radius: 8px; cursor: pointer" @click="triggerUpload" @dragover.prevent @drop.prevent="handleDrop">
        <el-icon v-if="!uploading" :size="40" color="#409eff"><UploadFilled /></el-icon>
        <div v-if="!uploading" style="margin-top: 8px; color: #606266">点击选择文件，或拖拽文件到此处</div>
        <div v-if="!uploading" style="font-size: 12px; color: #909399; margin-top: 4px">支持 PDF、DOCX、TXT、MD、PPTX 格式</div>
        <input ref="fileInputRef" type="file" accept=".pdf,.docx,.txt,.md,.pptx" style="display:none" @change="onFileSelected" />
        <div v-if="uploading" style="margin-top: 12px">
          <el-icon class="is-loading" :size="28" color="#409eff">
            <Loading />
          </el-icon>
          <p style="color: #909399; font-size: 13px; margin-top: 8px">正在解析并索引文件...</p>
        </div>
      </div>
      <el-alert v-if="uploadError" :title="uploadError" type="error" show-icon :closable="true" @close="uploadError = ''" style="margin-top: 12px" />
      <div class="audio-row">
        <el-button :loading="transcribing" @click="triggerAudioUpload">音频转写入库</el-button>
        <span class="audio-hint">支持 wav/mp3/m4a/flac/ogg，需要后端启用 FunASR</span>
        <input
          ref="audioInputRef"
          type="file"
          accept=".wav,.mp3,.m4a,.flac,.ogg,.webm"
          style="display: none"
          @change="onAudioSelected"
        />
      </div>
      <el-alert v-if="audioError" :title="audioError" type="error" show-icon :closable="true" @close="audioError = ''" style="margin-top: 8px" />
    </el-card>
    <el-card shadow="hover">
      <template #header>
        <span>已上传文档({{ docs.length }})</span>
        <el-button size="small" style="float: right" @click="refreshIndexHandler">刷新索引</el-button>
      </template>
      <el-table :data="docs" stripe v-if="docs.length">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div style="padding: 12px">文件类型: {{ row.file_type }} | 大小: {{ (row.file_size / 1024).toFixed(1) }} KB | 分块: {{ row.chunk_count }} | 上传: {{ new Date(row.upload_time).toLocaleString() }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="filename" label="文件名" min-width="200" />
        <el-table-column prop="file_type" label="格式" width="80" />
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" @click="viewDoc(row.id)">查看</el-button>
            <el-button size="small" type="danger" @click="removeDoc(row.id)" :loading="deletingId === row.id" :disabled="deletingId !== null">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无文档，请上传课程资料" />
    </el-card>
  </AppLayout>
  <el-dialog v-model="viewDialogVisible" :title="viewingDoc.filename" width="60%" top="5vh">
    <div style="font-size: 13px; color: #909399; margin-bottom: 12px">
      类型: {{ viewingDoc.file_type }} | 大小: {{ (viewingDoc.file_size / 1024).toFixed(1) }} KB | 分块: {{ viewingDoc.chunk_count }}
    </div>
    <el-scrollbar max-height="55vh">
      <div style="white-space: pre-wrap; line-height: 1.8; font-size: 14px">{{ viewingDoc.content }}</div>
    </el-scrollbar>
    <template #footer>
      <el-button @click="viewDialogVisible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { ElMessage } from "element-plus"
import AppLayout from "../components/AppLayout.vue"
import {
  uploadDocument,
  listDocuments,
  deleteDocument,
  refreshIndex,
  getDocumentContent,
  transcribeAudio,
} from "../api/knowledge"

const docs = ref([])
const fileInputRef = ref(null)
const audioInputRef = ref(null)
const uploading = ref(false)
const uploadError = ref("")
const transcribing = ref(false)
const audioError = ref("")
const viewDialogVisible = ref(false)
const viewingDoc = ref({ content: "" })
const deletingId = ref(null)

onMounted(async () => {
  try {
    const res = await listDocuments()
    docs.value = res.data
  } catch (e) {
    if (e.response?.status !== 401) console.warn("加载知识库列表失败", e)
  }
})

function triggerUpload() {
  fileInputRef.value?.click()
}

function handleDrop(e) {
  const files = e.dataTransfer?.files
  if (files?.length) {
    uploadFile(files[0])
  }
}

function onFileSelected(e) {
  const files = e.target.files
  if (files?.length) {
    uploadFile(files[0])
  }
  e.target.value = ""
}

async function uploadFile(file) {
  uploading.value = true
  uploadError.value = ""
  try {
    const res = await uploadDocument(file)
    ElMessage.success(res.data.message || "上传成功")
    try {
      const r = await listDocuments()
      docs.value = r.data
    } catch (listErr) {
      // 列表刷新失败不影响上传成功
    }
  } catch (e) {
    const msg = e.response?.data?.detail || "上传失败，请重试"
    uploadError.value = msg
    ElMessage.error(msg)
  }
  uploading.value = false
}

function triggerAudioUpload() {
  audioInputRef.value?.click()
}

function onAudioSelected(e) {
  const files = e.target.files
  if (files?.length) {
    transcribeFile(files[0])
  }
  e.target.value = ""
}

async function transcribeFile(file) {
  transcribing.value = true
  audioError.value = ""
  try {
    const res = await transcribeAudio(file)
    ElMessage.success(res.data.message || "音频转写完成")
    const r = await listDocuments()
    docs.value = r.data
  } catch (e) {
    audioError.value = e.response?.data?.detail || "音频转写失败"
    ElMessage.error(audioError.value)
  } finally {
    transcribing.value = false
  }
}

async function viewDoc(id) {
  try {
    const res = await getDocumentContent(id)
    viewingDoc.value = res.data
    viewDialogVisible.value = true
  } catch (e) {
    ElMessage.error("加载文档内容失败")
  }
}

async function removeDoc(id) {
  deletingId.value = id
  try {
    await deleteDocument(id)
    ElMessage.success("已删除")
    docs.value = docs.value.filter(d => d.id !== id)
  } catch (e) {
    ElMessage.error("删除失败")
  }
  deletingId.value = null
}

async function refreshIndexHandler() {
  try {
    await refreshIndex()
    ElMessage.success("索引已刷新")
  } catch (e) {
    ElMessage.error("刷新失败")
  }
}
</script>

<style scoped>
.audio-row {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.audio-hint {
  color: #909399;
  font-size: 12px;
}
</style>
