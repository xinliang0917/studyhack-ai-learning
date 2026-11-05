<template>
  <AppLayout>
    <div class="rag-page">
      <div class="rag-header">
        <div>
          <h2>知识库 AI 问答</h2>
          <p>基于已上传课程资料的 RAG 检索增强问答，回答会标注引用来源。</p>
        </div>
        <el-button :disabled="!messages.length || loading" @click="clearChat">清空对话</el-button>
      </div>

      <el-card shadow="hover" class="chat-card">
        <el-scrollbar ref="scrollRef" class="chat-scroll">
          <div class="chat-body">
            <div v-if="!messages.length" class="welcome">
              <el-icon :size="42" color="#409eff"><ChatDotRound /></el-icon>
              <h3>向你的课程资料提问</h3>
              <p>系统会先检索知识库，再让 DeepSeek 基于检索片段作答。</p>
              <div class="suggestions">
                <el-button v-for="q in suggestions" :key="q" round @click="send(q)">{{ q }}</el-button>
              </div>
            </div>

            <div v-for="(m, i) in messages" :key="i" :class="['msg-row', m.role]">
              <div class="avatar">
                <el-icon v-if="m.role === 'user'"><User /></el-icon>
                <el-icon v-else><MagicStick /></el-icon>
              </div>
              <div class="bubble-wrap">
                <div :class="['bubble', { error: m.error }]">{{ m.content }}</div>
                <div v-if="m.sources && m.sources.length" class="sources">
                  <div class="sources-title">引用来源</div>
                  <div v-for="(s, si) in m.sources" :key="si" class="source">
                    <div class="source-head">
                      <span class="source-no">[{{ si + 1 }}]</span>
                      <span class="source-name">{{ s.filename || '知识库片段' }}</span>
                      <span class="source-score">距离 {{ Number(s.score).toFixed(3) }}</span>
                    </div>
                    <div class="source-content">{{ s.content }}</div>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="loading" class="msg-row assistant">
              <div class="avatar"><el-icon><MagicStick /></el-icon></div>
              <div class="bubble typing">正在检索知识库并生成回答...</div>
            </div>
          </div>
        </el-scrollbar>

        <div class="composer">
          <el-input
            v-model="input"
            type="textarea"
            :rows="2"
            resize="none"
            placeholder="输入问题，Enter 发送，Shift + Enter 换行"
            :disabled="loading"
            @keydown="onKeydown"
          />
          <el-button type="primary" :loading="loading" :disabled="!input.trim()" @click="send()">发送</el-button>
        </div>
      </el-card>
    </div>
  </AppLayout>
</template>

<script setup>
import { nextTick, ref } from 'vue'
import { ElMessage } from 'element-plus'
import AppLayout from '../components/AppLayout.vue'
import { chatRag } from '../api/rag'

const messages = ref([])
const input = ref('')
const loading = ref(false)
const scrollRef = ref(null)

const suggestions = [
  '请总结知识库的核心内容',
  '列出最重要的 5 个知识点',
  '用通俗语言解释关键概念',
]

function scrollToBottom() {
  nextTick(() => {
    scrollRef.value?.setScrollTop(999999)
  })
}

function onKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    if (event.isComposing) return
    event.preventDefault()
    send()
  }
}

async function send(text) {
  const question = (typeof text === 'string' ? text : input.value).trim()
  if (!question || loading.value) return

  const history = messages.value
    .filter(m => !m.error && (m.role === 'user' || m.role === 'assistant'))
    .map(m => ({ role: m.role, content: m.content }))

  messages.value.push({ role: 'user', content: question })
  input.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const res = await chatRag({ question, history, k: 5 })
    messages.value.push({
      role: 'assistant',
      content: res.data.answer,
      sources: res.data.sources || [],
    })
  } catch (e) {
    const msg = e.response?.data?.detail || '问答失败，请稍后重试'
    messages.value.push({ role: 'assistant', content: msg, error: true })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function clearChat() {
  messages.value = []
  ElMessage.success('已清空对话')
}
</script>

<style scoped>
.rag-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 90px);
}
.rag-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}
.rag-header h2 {
  margin: 0;
  color: #303133;
}
.rag-header p {
  margin: 4px 0 0;
  color: #909399;
  font-size: 13px;
}
.chat-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.chat-card :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0;
}
.chat-scroll {
  flex: 1;
  overflow: hidden;
}
.chat-body {
  padding: 20px 24px;
}
.welcome {
  text-align: center;
  padding: 50px 20px;
}
.welcome h3 {
  margin: 12px 0 6px;
  color: #303133;
}
.welcome p {
  margin: 0 0 18px;
  color: #909399;
  font-size: 13px;
}
.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
}
.msg-row {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
}
.msg-row.user {
  flex-direction: row-reverse;
}
.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ecf5ff;
  color: #409eff;
  flex-shrink: 0;
}
.msg-row.user .avatar {
  background: #409eff;
  color: #fff;
}
.bubble-wrap {
  max-width: calc(100% - 90px);
}
.msg-row.user .bubble-wrap {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}
.bubble {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  padding: 10px 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  color: #303133;
}
.msg-row.user .bubble {
  background: #409eff;
  color: #fff;
  border-color: #409eff;
}
.bubble.error {
  background: #fef0f0;
  color: #f56c6c;
  border-color: #fde2e2;
}
.bubble.typing {
  color: #909399;
}
.sources {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sources-title {
  font-size: 12px;
  color: #909399;
}
.source {
  background: #fafafa;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 8px 10px;
}
.source-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #606266;
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
.source-score {
  color: #c0c4cc;
}
.source-content {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.composer {
  display: flex;
  gap: 10px;
  padding: 12px 16px;
  border-top: 1px solid #ebeef5;
  background: #fff;
  align-items: flex-end;
}
.composer .el-button {
  height: 54px;
}
</style>
