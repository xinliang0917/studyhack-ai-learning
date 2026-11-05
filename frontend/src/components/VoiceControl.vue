<template>
  <div style="display: flex; align-items: center; gap: 6px">
    <el-switch :model-value="isActive" size="small" @change="toggleVoice" style="margin-right: 2px" />
    <el-tooltip :content="isActive ? '语音识别已开启' : '语音识别已关闭'" placement="bottom">
      <el-icon
        :style="{ color: isActive ? (isListening ? '#67c23a' : '#409eff') : '#999', cursor: 'pointer' }"
        :size="18"
        @click="toggleVoice"
        class="voice-icon"
        :class="{ 'is-listening': isActive && isListening }"
      >
        <Microphone />
      </el-icon>
    </el-tooltip>
    <span v-if="transcript" style="font-size: 11px; color: #909399; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ transcript }}</span>
    <el-tooltip :content="muted ? '已静音' : '语音播报'" placement="bottom">
      <el-icon :style="{ color: muted ? '#bbb' : '#e6a23c', cursor: 'pointer' }" :size="16" @click="toggleSpeaker">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3A4.5 4.5 0 0 0 14 8.5v5a4.47 4.47 0 0 0 2.5-1.5zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>
      </el-icon>
    </el-tooltip>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { speak, cancelSpeech, toggleMute, isMuted as getMuted } from '../composables/useVoice'

const route = useRoute()
const router = useRouter()
const muted = ref(getMuted())
const isActive = ref(false)
const isListening = ref(false)
const transcript = ref('')
const wakeWord = '助手'
let recognition = null

const commandMap = {
  // Navigation
  '首页': '/dashboard',
  '打开首页': '/dashboard',
  '知识库': '/knowledge',
  '打开知识库': '/knowledge',
  'AI问答': '/rag',
  '智能问答': '/rag',
  '打开问答': '/rag',
  '课程大纲': '/course',
  '打开课程': '/course',
  '开始测验': '/quiz',
  '在线测验': '/quiz',
  '错题本': '/wrong-questions',
  '查看错题': '/wrong-questions',
  '设置': '/settings',
  '打开设置': '/settings',
  // Progress
  '查看进度': '/dashboard',
  '学习进度': '/dashboard',
  '我的进度': '/dashboard',
  // Page actions
  '上一页': 'prev',
  '下一页': 'next',
  '返回': 'back',
  '刷新': 'reload',
}

function toggleVoice() {
  isActive.value = !isActive.value
  if (isActive.value) {
    startListening()
  } else {
    stopListening()
    cancelSpeech()
  }
}

function startListening() {
  isListening.value = true
  transcript.value = '语音识别已开启'
  setTimeout(() => { if (transcript.value === '语音识别已开启') transcript.value = '' }, 1500)

  if ('webkitSpeechRecognition' in window) {
    recognition = new webkitSpeechRecognition()
    recognition.lang = 'zh-CN'
    recognition.continuous = true
    recognition.interimResults = true

    recognition.onresult = async (event) => {
      const results = event.results
      const text = results[results.length-1][0].transcript.trim()
      transcript.value = text
      if (text.includes(wakeWord)) {
        transcript.value = '我在。' + text
        setTimeout(() => { transcript.value = '' }, 2000)
      }
      // Fuzzy command matching
      function levenshtein(a, b) {
        const m = []; let i, j
        for (i = 0; i <= b.length; i++) m[i] = [i]
        for (j = 0; j <= a.length; j++) m[0][j] = j
        for (i = 1; i <= b.length; i++)
          for (j = 1; j <= a.length; j++)
            m[i][j] = b[i-1] === a[j-1] ? m[i-1][j-1] : Math.min(m[i-1][j-1]+1, m[i][j-1]+1, m[i-1][j]+1)
        return m[b.length][a.length]
      }
      let matched = null
      let matchedTarget = null
      // 1) Exact match
      for (const [cmd, target] of Object.entries(commandMap)) {
        if (text.includes(cmd)) { matched = cmd; matchedTarget = target; break }
      }
      // 2) Fuzzy match
      if (!matched) {
        for (const [cmd, target] of Object.entries(commandMap)) {
          if (text.length >= cmd.length - 2 && levenshtein(text.slice(0, cmd.length), cmd) <= 2) {
            matched = cmd; matchedTarget = target; break
          }
        }
      }
      // 3) DeepSeek intent inference
      if (!matched) {
        try {
          const resp = await fetch("/api/voice/interpret", {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ text })
          })
          const data = await resp.json()
          if (data.command) {
            matched = data.command
            matchedTarget = commandMap[data.command]
          }
        } catch(e) {}
      }
      // Execute command
      if (matched && matchedTarget) {
        transcript.value = ''
        if (matchedTarget === 'prev') {
          const btn = document.querySelector('[class*="prev"]') || document.querySelector('.el-button:not([disabled]) .el-icon--left')
          if (btn) btn.click()
        } else if (matchedTarget === 'next') {
          const btn = document.querySelector('[class*="next"]') || document.querySelector('.el-button:not([disabled]) .el-icon--right')
          if (btn) btn.click()
        } else if (matchedTarget === 'back') { router.back() }
        else if (matchedTarget === 'reload') { location.reload() }
        else { router.push(matchedTarget) }
        speak('正在打开' + matched)
      }
    }
    recognition.onerror = () => { isListening.value = false; stopListening() }
    recognition.onend = () => {
      if (isActive.value) {
        // Auto-restart recognition
        try { recognition.start() } catch(e) {}
      }
    }
    recognition.start()
  } else {
    transcript.value = '浏览器不支持语音识别'
    setTimeout(() => { if (transcript.value === '浏览器不支持语音识别') transcript.value = '' }, 3000)
  }
}

function stopListening() {
  isListening.value = false
  if (recognition) {
    try { recognition.stop() } catch(e) {}
    recognition = null
  }
}

// Read current page content based on route
function readCurrentPage() {
  const path = route.path
  if (path.startsWith('/exam/')) {
    // Try to read exam result
    const scoreEl = document.querySelector('.el-result__title')
    if (scoreEl) {
      speak('考试结果：' + scoreEl.textContent)
      return
    }
    // Try to read first question
    const qEls = document.querySelectorAll('[class*=\"question\"] strong')
    if (qEls.length > 0) {
      let msg = '共 ' + qEls.length + ' 道题'
      speak(msg)
      return
    }
  }
  if (path === '/quiz') {
    speak('在线测验页面，点击开始测验生成题目')
    return
  }
  if (path === '/wrong-questions') {
    const tag = document.querySelector('.el-tag--danger')
    const count = tag ? tag.textContent : '暂无'
    speak('错题本，' + count)
    return
  }
  if (path === '/dashboard') {
    speak('学习仪表盘')
    return
  }
  if (path === '/course') {
    speak('课程大纲页面')
    return
  }
  if (path === '/knowledge') {
    speak('知识库页面')
    return
  }
  if (path === '/rag') {
    speak('知识库智能问答页面')
    return
  }
  // Generic fallback - try to read page title
  const title = document.querySelector('h2') || document.querySelector('h3')
  if (title) {
    speak(title.textContent)
  } else {
    speak('当前页面')
  }
}

function toggleSpeaker() {
  const wasMuted = muted.value
  toggleMute()
  muted.value = getMuted()
  if (wasMuted && !muted.value) {
    // Just unmuted → read page as feedback
    setTimeout(readCurrentPage, 400)
  }
}

function clickMicIcon() {
  isActive.value = !isActive.value
  if (isActive.value) {
    startListening()
  } else {
    stopListening()
    cancelSpeech()
  }
}

onUnmounted(() => {
  stopListening()
  cancelSpeech()
})
</script>

<style scoped>
.voice-icon {
  transition: color 0.3s, transform 0.3s;
}
.voice-icon.is-listening {
  animation: pulse 1.5s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.15); }
}
</style>
