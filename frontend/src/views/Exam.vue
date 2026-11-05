<template>
  <AppLayout>
    <el-button text @click="router.push('/quiz')" style="margin-bottom: 12px">
      <el-icon><ArrowLeft /></el-icon> 返回
    </el-button>

    <el-card shadow="hover">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>在线考试</span>
          <div style="display: flex; gap: 12px; align-items: center">
            <el-tag v-if="!submitted && timeLimit > 0" :type="timeLeft <= 60 ? 'danger' : 'info'">
              ⏱ {{ formatTime(timeLeft) }}
            </el-tag>
            <el-tag :type="submitted ? 'success' : 'warning'">
              {{ submitted ? '已提交' : '作答中' }}
            </el-tag>
          </div>
        </div>
      </template>

      <!-- Loading state -->
      <div v-if="pageLoading" style="text-align: center; padding: 60px">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <p style="margin-top: 12px; color: #909399">加载题目...</p>
      </div>

      <!-- Results -->
      <div v-else-if="submitted">
        <el-result :title="'得分: ' + result.score + '分'" :sub-title="'正确: ' + result.correct + '/' + result.total">
          <template #icon>
            <el-icon :size="60" :color="result.score >= 60 ? '#67c23a' : '#f56c6c'">
              <SuccessFilled v-if="result.score >= 60" />
              <CircleCloseFilled v-else />
            </el-icon>
          </template>
        </el-result>

        <el-progress
          :percentage="Math.round(result.score)"
          :color="result.score >= 60 ? '#67c23a' : '#f56c6c'"
          :stroke-width="16"
          style="margin-bottom: 20px; max-width: 400px; margin-left: auto; margin-right: auto"
        />

        <el-divider>题目详情</el-divider>

        <div v-for="(d, i) in result.details" :key="i"
             style="margin-bottom: 16px; padding: 16px; background: #fafafa; border-radius: 8px;
                    border-left: 4px solid #f56c6c"
             :style="{ borderLeftColor: d.is_correct ? '#67c23a' : '#f56c6c' }">
          <p>
            <strong>{{ i+1 }}. {{ d.question_text }}</strong>
            <el-tag :type="d.is_correct ? 'success' : 'danger'" size="small" style="margin-left: 8px">
              {{ d.is_correct ? '✓ 正确' : '✗ 错误' }}
            </el-tag>
          </p>
          <div v-if="d.options && Object.keys(d.options).length > 0" style="margin: 8px 0 8px 20px; font-size: 14px">
            <p v-for="(optText, optKey) in d.options" :key="optKey"
               :style="{ color: optKey === d.correct_answer ? '#67c23a' : (optKey === d.user_answer ? '#f56c6c' : 'inherit') }">
              {{ optKey }}. {{ optText }}
              <el-tag v-if="optKey === d.correct_answer" size="small" type="success" style="margin-left: 4px">正确答案</el-tag>
              <el-tag v-if="optKey === d.user_answer && optKey !== d.correct_answer" size="small" type="danger" style="margin-left: 4px">你的选择</el-tag>
            </p>
          </div>
          <p :style="{ color: d.is_correct ? '#67c23a' : '#f56c6c', margin: '4px 0' }">
            你的答案: {{ d.user_answer || '未作答' }}
          </p>
          <p v-if="!d.is_correct" style="color: #67c23a; margin: '4px 0'">
            正确答案: {{ d.correct_answer }}
          </p>
          <p style="color: #909399; font-size: 13px; margin-top: 8px; padding: 8px; background: #fff; border-radius: 4px">
            解析: {{ d.explanation || '暂无解析' }}
          </p>
          <el-button text size="small" type="primary" @click="speakQuestion(d, i, result.details.length)" style="margin-top: 4px">
            <el-icon><svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3A4.5 4.5 0 0 0 14 8.5v5a4.47 4.47 0 0 0 2.5-1.5zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg></el-icon> 朗读
          </el-button>
        </div>

        <el-button @click="router.push('/quiz')">返回测验</el-button>
      </div>

      <!-- Questions -->
      <div v-else>
        <p style="margin-bottom: 16px; color: #909399">
          共 {{ questions.length }} 道题，请认真作答：
        </p>

        <!-- Question progress -->
        <div style="margin-bottom: 16px">
          <el-progress
            :percentage="answeredCount"
            :format="() => answeredCount + '% 已作答'"
            :stroke-width="12"
            color="#409eff"
          />
        </div>

        <div v-for="(q, i) in questions" :key="q.id"
             style="margin-bottom: 20px; padding: 20px; background: #f8f9fa; border-radius: 8px;
                    border: 1px solid #ebeef5"
             :class="{ 'question-answered': answers[String(q.id)] }">
          <p>
            <strong>{{ i+1 }}. {{ q.question }}</strong>
            <el-tag size="small" style="margin-left: 8px" type="info">
              {{ q.type === 'true_false' ? '判断题' : '选择题' }}
            </el-tag>
          </p>

          <el-radio-group
            v-if="q.type !== 'true_false'"
            v-model="answers[String(q.id)]"
            style="margin-top: 12px; display: flex; flex-direction: column; gap: 8px"
          >
            <el-radio v-for="(opt, key) in q.options" :key="key" :value="key" border style="margin-right: 0">
              <span class="option-text">{{ key }}. {{ opt }}</span>
            </el-radio>
          </el-radio-group>

          <el-radio-group
            v-else
            v-model="answers[String(q.id)]"
            style="margin-top: 12px; display: flex; flex-direction: column; gap: 8px"
          >
            <el-radio value="A" border>正确</el-radio>
            <el-radio value="B" border>错误</el-radio>
          </el-radio-group>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 20px">
          <span style="color: #909399; font-size: 13px">
            已答 {{ Object.keys(answers).length }} / {{ questions.length }} 题
          </span>
          <div style="display: flex; gap: 12px">
            <el-button @click="confirmExit">退出</el-button>
            <el-button type="primary" @click="submitAnswers" :loading="submitting">
              提交答案
            </el-button>
          </div>
        </div>
      </div>
    </el-card>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Loading, SuccessFilled, CircleCloseFilled, Promotion } from '@element-plus/icons-vue'
import AppLayout from '../components/AppLayout.vue'
import { speakExamResult, speakQuestion } from '../composables/useVoice'

const route = useRoute()
const router = useRouter()
const pageLoading = ref(true)
const submitted = ref(false)
const submitting = ref(false)
const questions = ref([])
const answers = ref({})
const result = ref({})
const timeLimit = ref(0)
const timeLeft = ref(0)
let timerInterval = null

const answeredCount = computed(() => {
  if (!questions.value.length) return 0
  return Math.round((Object.keys(answers.value).length / questions.value.length) * 100)
})

function formatTime(seconds) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

function startTimer(limit) {
  timeLimit.value = limit
  timeLeft.value = limit
  if (timerInterval) clearInterval(timerInterval)
  timerInterval = setInterval(() => {
    timeLeft.value--
    if (timeLeft.value <= 0) {
      clearInterval(timerInterval)
      timerInterval = null
      ElMessage.warning('时间到！自动交卷')
      submitAnswers()
    }
  }, 1000)
}

onMounted(async () => {
  try {
    const stored = sessionStorage.getItem('exam_' + route.params.examId)
    if (stored) {
      const data = JSON.parse(stored)
      questions.value = data.questions || []
      timeLimit.value = data.time_limit || 0
      if (timeLimit.value > 0) {
        startTimer(timeLimit.value)
      }
    } else {
      // Try to fetch from backend
      try {
        const { getExamQuestions } = await import('../api/quiz')
        const qRes = await getExamQuestions(route.params.examId)
        if (qRes.data && qRes.data.questions && qRes.data.questions.length) {
          questions.value = qRes.data.questions
          timeLimit.value = 0
          if (qRes.data.exam && qRes.data.exam.submitted) {
            // Show submitted result
            if (qRes.data.exam.result && qRes.data.exam.result.details) {
              submitted.value = true
              result.value = qRes.data.exam.result
            }
          } else {
            ElMessage.info('已从服务器加载题目')
          }
        } else {
          ElMessage.warning('考试信息已过期，请重新生成')
        }
      } catch (e2) {
        ElMessage.warning('考试信息已过期，请重新生成')
      }
    }
  } catch (e) {
    ElMessage.error('加载试题失败')
  }
  pageLoading.value = false
})

onBeforeUnmount(() => {
  if (timerInterval) clearInterval(timerInterval)
})

function confirmExit() {
  ElMessageBox.confirm('确定退出当前考试？未提交的答案将丢失。', '提示', {
    confirmButtonText: '退出',
    cancelButtonText: '继续作答',
    type: 'warning',
  }).then(() => {
    router.push('/quiz')
  }).catch(() => {})
}

async function submitAnswers() {
  const unanswered = questions.value.filter(q => !answers.value[String(q.id)])
  if (unanswered.length > 0) {
    try {
      await ElMessageBox.confirm(
        `还有 ${unanswered.length} 题未作答，确定提交吗？`,
        '确认提交',
        { confirmButtonText: '提交', cancelButtonText: '继续作答', type: 'warning' }
      )
    } catch {
      return
    }
  }

  submitting.value = true
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }

  try {
    const { submitExam } = await import('../api/quiz')
  const { getExamQuestions } = await import('../api/quiz')
    const res = await submitExam(route.params.examId, answers.value)
    result.value = res.data
    submitted.value = true
    speakExamResult(res.data)
    ElMessage.success('提交成功！得分: ' + res.data.score + '分')
    sessionStorage.removeItem('exam_' + route.params.examId)
  } catch (e) {
    const detail = e.response?.data?.detail
    ElMessage.error(detail || '提交失败，请重试')
    if (timerInterval === null && timeLimit.value > 0 && !submitted.value) {
      startTimer(timeLeft.value)
    }
  }
  submitting.value = false
}
</script>

<style scoped>
.question-answered {
  border-color: #409eff !important;
}

:deep(.el-radio) {
  width: 100%;
}
:deep(.el-radio__label) {
  text-align: left;
  flex: 1;
}
</style>
