<template>
  <AppLayout>
    <div class="rag-page">
      <div class="rag-header">
        <div>
          <h2>知识库 AI 问答</h2>
          <p>基于已上传课程资料的 RAG 检索增强问答，支持流式回答与引用溯源。</p>
        </div>
        <div class="rag-actions">
          <el-select
            v-model="sessionId"
            clearable
            placeholder="选择会话"
            style="width: 180px"
            :loading="sessionLoading"
            @change="onSessionChange"
            @clear="newChat"
          >
            <el-option
              v-for="item in sessions"
              :key="item.id"
              :label="`${item.title} (${item.message_count})`"
              :value="item.id"
            />
          </el-select>
          <el-button @click="newChat">新对话</el-button>
          <el-button v-if="sessionId" type="danger" plain @click="removeSession">删除</el-button>
          <el-button @click="openEval">评估</el-button>
          <el-button :disabled="!messages.length || loading" @click="clearChat">清空</el-button>
        </div>
      </div>

      <el-card shadow="hover" class="chat-card">
        <el-scrollbar ref="scrollRef" class="chat-scroll">
          <div ref="chatBodyRef" class="chat-body">
            <div v-if="!messages.length" class="welcome">
              <el-icon :size="42" color="#409eff"><ChatDotRound /></el-icon>
              <h3>向你的课程资料提问</h3>
              <p>系统会先检索知识库，再让大模型基于检索片段作答，并标注引用来源。</p>
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
                <div v-if="m.role === 'assistant' && m.streaming && !m.content" class="bubble typing">
                  正在检索知识库并生成回答...
                </div>
                <div
                  v-else-if="m.role === 'assistant' && m.html"
                  class="bubble markdown"
                  v-html="m.html"
                ></div>
                <div v-else :class="['bubble', { error: m.error }]">{{ m.content }}</div>

                <div v-if="m.sources && m.sources.length" class="sources">
                  <div class="sources-title">引用来源（点击查看原文）</div>
                  <div
                    v-for="(s, si) in m.sources"
                    :key="si"
                    class="source"
                    @click="openSource(s)"
                  >
                    <div class="source-head">
                      <span class="source-no">[{{ si + 1 }}]</span>
                      <span class="source-name">{{ s.filename || '知识库片段' }}</span>
                      <span class="source-score">相关度 {{ Math.round((s.score || 0) * 100) }}%</span>
                    </div>
                    <div class="source-content">{{ s.content }}</div>
                  </div>
                </div>
              </div>
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
            :disabled="loading || sessionLoading"
            @keydown="onKeydown"
          />
          <el-button type="primary" :loading="loading" :disabled="!input.trim()" @click="send()">发送</el-button>
        </div>
      </el-card>
    </div>

    <el-dialog v-model="sourceDialog" :title="sourceDoc.filename || '引用来源'" width="62%" top="6vh">
      <div class="source-dialog-meta">
        <span v-if="sourceDoc.chunk_index !== undefined">片段 #{{ sourceDoc.chunk_index }}</span>
        <el-button
          v-if="!sourceFull && sourceDoc.doc_id"
          text
          type="primary"
          size="small"
          :loading="sourceLoading"
          @click="loadFullDoc"
        >查看全文</el-button>
      </div>
      <el-scrollbar max-height="58vh">
        <div class="source-dialog-content">{{ sourceDoc.content }}</div>
      </el-scrollbar>
      <template #footer>
        <el-button @click="sourceDialog = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="evalDialog" title="RAG 检索评估" width="720px" top="6vh">
      <p class="eval-tip">每行一条，格式：问题 | 关键词1,关键词2</p>
      <el-input
        v-model="evalInput"
        type="textarea"
        :rows="7"
        placeholder="牛顿第二定律是什么 | F=ma,加速度&#10;光合作用的场所 | 叶绿体"
      />
      <div v-if="evalResult" class="eval-result">
        <el-row :gutter="12">
          <el-col :span="8">
            <el-card shadow="never"><div class="eval-metric">
              <div class="eval-value">{{ (evalResult.summary.hit_rate * 100).toFixed(1) }}%</div>
              <div class="eval-label">Hit@{{ evalResult.summary.k }}</div>
            </div></el-card>
          </el-col>
          <el-col :span="8">
            <el-card shadow="never"><div class="eval-metric">
              <div class="eval-value">{{ evalResult.summary.mrr.toFixed(3) }}</div>
              <div class="eval-label">MRR</div>
            </div></el-card>
          </el-col>
          <el-col :span="8">
            <el-card shadow="never"><div class="eval-metric">
              <div class="eval-value">{{ evalResult.summary.hits }}/{{ evalResult.summary.cases }}</div>
              <div class="eval-label">命中用例</div>
            </div></el-card>
          </el-col>
        </el-row>
        <el-table :data="evalResult.results" size="small" style="margin-top: 12px">
          <el-table-column prop="question" label="问题" min-width="180" />
          <el-table-column label="命中" width="80">
            <template #default="{ row }">
              <el-tag :type="row.hit ? 'success' : 'danger'" size="small">{{ row.hit ? '是' : '否' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="rank" label="排名" width="70" />
          <el-table-column label="Top 来源" min-width="220">
            <template #default="{ row }">
              {{ row.top_sources && row.top_sources[0] ? row.top_sources[0].snippet : '-' }}
            </template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <el-button @click="evalDialog = false">关闭</el-button>
        <el-button type="primary" :loading="evalLoading" @click="runEval">开始评估</el-button>
      </template>
    </el-dialog>
  </AppLayout>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import renderMathInElement from 'katex/contrib/auto-render'
import 'katex/dist/katex.min.css'
import AppLayout from '../components/AppLayout.vue'
import {
  chatRag,
  createSession,
  deleteSession,
  evaluateRag,
  getSession,
  listSessions,
} from '../api/rag'
import { getDocumentContent } from '../api/knowledge'

marked.setOptions({ breaks: true, gfm: true })

const messages = ref([])
const input = ref('')
const loading = ref(false)
const scrollRef = ref(null)
const chatBodyRef = ref(null)
const sourceDialog = ref(false)
const sourceLoading = ref(false)
const sourceFull = ref(false)
const sourceDoc = ref({})
const sessions = ref([])
const sessionId = ref(null)
const sessionLoading = ref(false)
const evalDialog = ref(false)
const evalInput = ref('')
const evalLoading = ref(false)
const evalResult = ref(null)

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

function renderMarkdown(text) {
  return DOMPurify.sanitize(marked.parse(text || ''))
}

async function renderMath() {
  await nextTick()
  if (!chatBodyRef.value) return
  try {
    renderMathInElement(chatBodyRef.value, {
      delimiters: [
        { left: '$$', right: '$$', display: true },
        { left: '\\[', right: '\\]', display: true },
        { left: '$', right: '$', display: false },
        { left: '\\(', right: '\\)', display: false },
      ],
      throwOnError: false,
    })
  } catch (e) {
    // ignore malformed formulas
  }
}

function onKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    if (event.isComposing) return
    event.preventDefault()
    send()
  }
}

function historyPayload() {
  return messages.value
    .filter(m => !m.error && !m.streaming && (m.role === 'user' || m.role === 'assistant') && m.content)
    .map(m => ({ role: m.role, content: m.content }))
}

function handleEvent(raw, assistant, state) {
  let event = 'message'
  let data = ''
  for (const line of raw.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) data += line.slice(5).trim()
  }
  if (!data) return
  let payload = null
  try {
    payload = JSON.parse(data)
  } catch (e) {
    return
  }
  if (event === 'sources') {
    assistant.sources = payload.sources || []
  } else if (event === 'delta') {
    assistant.content += payload.content || ''
    state.gotDelta = true
  } else if (event === 'error') {
    assistant.content = payload.message || '生成失败，请稍后重试'
    assistant.error = true
    assistant.streaming = false
  } else if (event === 'done') {
    assistant.streaming = false
  }
}

async function send(text) {
  const question = (typeof text === 'string' ? text : input.value).trim()
  if (!question || loading.value) return

  const history = historyPayload()
  messages.value.push({ role: 'user', content: question })
  messages.value.push({ role: 'assistant', content: '', sources: [], streaming: true })
  const assistant = messages.value[messages.value.length - 1]
  input.value = ''
  loading.value = true
  scrollToBottom()

  let activeSessionId = sessionId.value
  if (!activeSessionId) {
    try {
      activeSessionId = await ensureSession(question)
    } catch (e) {
      activeSessionId = null
    }
  }

  let streamed = false
  try {
    const token = localStorage.getItem('token')
    const resp = await fetch('/api/rag/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ question, history, k: 5, session_id: activeSessionId }),
    })
    if (!resp.ok || !resp.body) {
      throw new Error(`HTTP ${resp.status}`)
    }
    streamed = true
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    const state = { gotDelta: false }
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''
      for (const part of parts) handleEvent(part, assistant, state)
      scrollToBottom()
    }
    if (buffer.trim()) handleEvent(buffer, assistant, state)
    assistant.streaming = false
    if (assistant.error) {
      loading.value = false
      return
    }
    if (!assistant.content) {
      assistant.content = '没有生成内容，请稍后重试。'
      assistant.error = true
    } else {
      assistant.html = renderMarkdown(assistant.content)
      await renderMath()
    }
  } catch (e) {
    if (!streamed) {
      try {
        const res = await chatRag({ question, history, k: 5, session_id: activeSessionId })
        assistant.content = res.data.answer
        assistant.sources = res.data.sources || []
        assistant.html = renderMarkdown(assistant.content)
        await renderMath()
      } catch (err) {
        assistant.content = err.response?.data?.detail || '问答失败，请稍后重试'
        assistant.error = true
      }
    } else if (!assistant.content) {
      assistant.content = '流式输出中断，请重试。'
      assistant.error = true
    }
  } finally {
    assistant.streaming = false
    loading.value = false
    if (activeSessionId) {
      await loadSessions()
    }
    scrollToBottom()
  }
}

async function openSource(source) {
  sourceFull.value = false
  sourceDoc.value = { ...source }
  sourceDialog.value = true
}

async function loadFullDoc() {
  if (!sourceDoc.value.doc_id) return
  sourceLoading.value = true
  try {
    const res = await getDocumentContent(sourceDoc.value.doc_id)
    sourceDoc.value = { ...sourceDoc.value, content: res.data.content }
    sourceFull.value = true
  } catch (e) {
    ElMessage.error('加载全文失败')
  } finally {
    sourceLoading.value = false
  }
}

function clearChat() {
  newChat()
  ElMessage.success('已开始新对话')
}

async function loadSessions() {
  try {
    const res = await listSessions()
    sessions.value = res.data || []
  } catch (e) { /* ignore */ }
}

async function selectSession(id) {
  if (!id) {
    newChat()
    return
  }
  sessionId.value = id
  sessionLoading.value = true
  try {
    const res = await getSession(id)
    messages.value = (res.data.messages || []).map(message => ({
      role: message.role,
      content: message.content,
      sources: message.sources || [],
      html: message.role === 'assistant' ? renderMarkdown(message.content) : undefined,
    }))
    await renderMath()
    scrollToBottom()
  } catch (e) {
    ElMessage.error('加载会话失败')
  } finally {
    sessionLoading.value = false
  }
}

function onSessionChange(id) {
  if (id) selectSession(id)
  else newChat()
}

function newChat() {
  sessionId.value = null
  messages.value = []
  input.value = ''
}

async function removeSession() {
  if (!sessionId.value) return
  try {
    await ElMessageBox.confirm('确定删除当前会话吗？', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch (e) {
    return
  }
  try {
    await deleteSession(sessionId.value)
    ElMessage.success('会话已删除')
    newChat()
    await loadSessions()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

async function ensureSession(question) {
  if (sessionId.value) return sessionId.value
  const res = await createSession(question.slice(0, 40))
  sessionId.value = res.data.id
  await loadSessions()
  return sessionId.value
}

function openEval() {
  evalDialog.value = true
}

async function runEval() {
  const cases = evalInput.value
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)
    .map(line => {
      const parts = line.split('|')
      return {
        question: (parts[0] || '').trim(),
        expected_keywords: (parts[1] || '')
          .split(/[,，]/)
          .map(item => item.trim())
          .filter(Boolean),
      }
    })
    .filter(item => item.question && item.expected_keywords.length)
  if (!cases.length) {
    ElMessage.warning('请按“问题 | 关键词1,关键词2”格式填写')
    return
  }
  evalLoading.value = true
  try {
    const res = await evaluateRag(cases, 5)
    evalResult.value = res.data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '评估失败')
  } finally {
    evalLoading.value = false
  }
}

onMounted(async () => {
  await loadSessions()
  if (sessions.value.length) {
    await selectSession(sessions.value[0].id)
  }
})
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
.rag-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
}
.eval-tip {
  color: #909399;
  font-size: 13px;
  margin: 0 0 8px;
}
.eval-result {
  margin-top: 16px;
}
.eval-metric {
  text-align: center;
}
.eval-value {
  font-size: 26px;
  font-weight: bold;
  color: #409eff;
}
.eval-label {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
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
.bubble.markdown {
  white-space: normal;
}
.bubble.markdown :deep(p) {
  margin: 0 0 8px;
}
.bubble.markdown :deep(p:last-child) {
  margin-bottom: 0;
}
.bubble.markdown :deep(ul),
.bubble.markdown :deep(ol) {
  margin: 6px 0;
  padding-left: 20px;
}
.bubble.markdown :deep(code) {
  background: #f5f7fa;
  padding: 1px 5px;
  border-radius: 4px;
  font-family: Consolas, monospace;
}
.bubble.markdown :deep(pre) {
  background: #f5f7fa;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
}
.bubble.markdown :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
}
.bubble.markdown :deep(th),
.bubble.markdown :deep(td) {
  border: 1px solid #ebeef5;
  padding: 4px 8px;
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
  cursor: pointer;
  transition: border-color 0.2s;
}
.source:hover {
  border-color: #409eff;
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
.source-dialog-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #909399;
  font-size: 13px;
  margin-bottom: 10px;
}
.source-dialog-content {
  white-space: pre-wrap;
  line-height: 1.8;
  color: #303133;
  font-size: 14px;
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
@media (max-width: 768px) {
  .rag-page {
    height: calc(100vh - 70px);
  }
  .rag-header {
    flex-direction: column;
    gap: 10px;
  }
  .rag-actions {
    width: 100%;
    justify-content: flex-start;
  }
  .rag-actions .el-select {
    width: 150px !important;
  }
  .chat-body {
    padding: 12px;
  }
  .bubble-wrap {
    max-width: calc(100% - 50px);
  }
}
</style>
