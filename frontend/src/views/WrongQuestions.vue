<template>
  <AppLayout>
    <h2 style="margin-bottom: 20px">错题本</h2>

    <!-- Filter Card -->
    <el-card shadow="hover" style="margin-bottom: 16px">
      <el-form :inline="true">
        <el-form-item label="按章节">
          <el-select v-model="filterChapterId" clearable placeholder="全部章节" style="width: 180px">
            <el-option v-for="ch in allChapters" :key="ch.id" :label="ch.title" :value="ch.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="难度">
          <el-select v-model="filterDifficulty" clearable placeholder="全部" style="width: 100px">
            <el-option label="简单" value="easy" />
            <el-option label="中等" value="medium" />
            <el-option label="困难" value="hard" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="loadWrongQuestions">刷新</el-button>
          <el-button type="primary" @click="togglePracticeMode">
            {{ practiceMode ? '退出重练' : '错题重练' }}
          </el-button>
        </el-form-item>
      </el-form>
      <el-tag type="danger" style="margin-bottom: 12px">
        共 {{ wrongList.length }} 道错题
      </el-tag>
    </el-card>

    <!-- Stats Card -->
    <el-card v-if="!practiceMode && stats" shadow="hover" style="margin-bottom: 16px">
      <template #header><span>统计概况</span></template>
      <el-row :gutter="20">
        <el-col :span="8">
          <div class="stat-item">
            <p class="stat-value">{{ stats.total_wrong }}</p>
            <p class="stat-label">总错题数</p>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="stat-item">
            <p class="stat-value">{{ stats.per_chapter?.length || 0 }}</p>
            <p class="stat-label">涉及章节</p>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="stat-item">
            <p class="stat-value">{{ stats.score_trend?.length || 0 }}</p>
            <p class="stat-label">考试记录</p>
          </div>
        </el-col>
      </el-row>

      <!-- Score trend -->
      <el-divider v-if="stats.score_trend?.length">成绩趋势</el-divider>
      <div v-if="stats.score_trend?.length" class="trend-chart">
        <div v-for="(s, i) in stats.score_trend" :key="s.exam_id" class="trend-bar-wrapper">
          <div class="trend-bar" :style="{ height: s.score + '%', background: s.score >= 60 ? '#67c23a' : '#f56c6c' }">
            <span class="trend-label">{{ s.score }}</span>
          </div>
          <span class="trend-date">{{ formatShortDate(s.created_at) }}</span>
        </div>

      <!-- Wrong question correct rate trend -->
      <el-divider v-if="stats.wrong_trend?.length">错题正确率势趋势</el-divider>
      <div v-if="stats.wrong_trend?.length" class="trend-chart">
        <div v-for="(w, i) in stats.wrong_trend" :key="w.exam_id" class="trend-bar-wrapper">
          <div class="trend-bar" :style="{ height: (w.correct_rate || 0) + '%', background: (w.correct_rate || 0) >= 60 ? '#67c23a' : (w.correct_rate || 0) >= 30 ? '#e6a23c' : '#f56c6c' }">
            <span class="trend-label">{{ w.corrected }}/{{ w.previously_wrong }}</span>
          </div>
          <span class="trend-date">{{ formatShortDate(w.created_at) }}</span>
        </div>
      </div>
      </div>

      <!-- Per-chapter breakdown -->
      <el-divider v-if="stats.per_chapter?.length">各章节错题分布</el-divider>
      <div v-if="stats.per_chapter?.length" class="chapter-bars">
        <div v-for="ch in stats.per_chapter" :key="ch.chapter_id" class="chapter-bar-row">
          <span class="chapter-bar-label" :title="ch.chapter_title">{{ ch.chapter_title }}</span>
          <div class="chapter-bar-track">
            <div class="chapter-bar-fill" :style="{ width: (ch.wrong_count / stats.total_wrong * 100) + '%' }"></div>
          </div>
          <span class="chapter-bar-count">{{ ch.wrong_count }}</span>
        </div>
      </div>


    </el-card>

    <!-- Wrong questions list / practice mode -->
    <el-card shadow="hover">
      <div v-if="!wrongList.length">
        <el-empty description="暂无错题，继续加油！" />
      </div>

      <template v-else>
        <!-- Practice mode header -->
        <div v-if="practiceMode" style="margin-bottom: 16px">
          <el-alert
            :title="'错题重练模式 — 共 ' + wrongList.length + ' 题'"
            type="warning"
            :closable="false"
            show-icon
          />
        </div>

        <div v-for="(w, i) in wrongList" :key="w.id"
             style="margin-bottom: 16px; padding: 16px; background: #fafafa; border-radius: 8px;
                    border-left: 4px solid #f56c6c">
          <p>
            <strong>{{ i+1 }}. {{ w.question_text }}</strong>
            <el-tag size="small" style="margin-left: 8px" type="info">
              {{ w.difficulty === 'easy' ? '简单' : w.difficulty === 'hard' ? '困难' : '中等' }}
            </el-tag>
            <el-tag v-if="w.chapter_title" size="small" style="margin-left: 4px" type="warning">
              {{ w.chapter_title }}
            </el-tag>
          </p>

          <!-- Options in non-practice mode -->
          <div v-if="!practiceMode && w.options && Object.keys(w.options).length > 0" style="margin: 8px 0 8px 20px; font-size: 14px">
            <p v-for="(optText, optKey) in w.options" :key="optKey"
               :style="{ color: optKey === w.correct_answer ? '#67c23a' : (optKey === w.user_answer ? '#f56c6c' : 'inherit') }">
              {{ optKey }}. {{ optText }}
              <el-tag v-if="optKey === w.correct_answer" size="small" type="success" style="margin-left: 4px">正确答案</el-tag>
              <el-tag v-if="optKey === w.user_answer && optKey !== w.correct_answer" size="small" type="danger" style="margin-left: 4px">你的选择</el-tag>
            </p>
          </div>

          <div v-if="practiceMode" style="margin: 12px 0">
            <el-radio-group v-if="w.type !== 'true_false'" v-model="practiceAnswers[String(w.question_id)]"
                            style="display: flex; flex-direction: column; gap: 8px">
              <el-radio v-for="(opt, key) in w.options" :key="key" :value="key" border>
                <span class="option-text">{{ key }}. {{ opt }}</span>
              </el-radio>
            </el-radio-group>
            <el-radio-group v-else v-model="practiceAnswers[String(w.question_id)]"
                            style="display: flex; flex-direction: column; gap: 8px; margin-top: 8px">
              <el-radio value="A" border>正确</el-radio>
              <el-radio value="B" border>错误</el-radio>
            </el-radio-group>
          </div>

          <p v-if="!practiceMode || showAnswer[w.question_id]" style="color: #f56c6c; margin: 4px 0">
            你的答案: {{ practiceMode ? (practiceAnswers[String(w.question_id)] || '未作答') : w.user_answer }}
          </p>
          <p v-if="!practiceMode || showAnswer[w.question_id]" style="color: #67c23a; margin: 4px 0">
            正确答案: {{ w.correct_answer }}
          </p>
          <p v-if="!practiceMode || showAnswer[w.question_id]" style="color: #909399; font-size: 13px; margin-top: 4px;
                padding: 8px; background: #fff; border-radius: 4px">
            解析: {{ w.explanation || '暂无解析' }}
          </p>
          <el-button v-if="!practiceMode" text size="small" type="primary" @click="speak(w.question_text + ' 正确答案' + w.correct_answer)" style="margin-top: 4px">
            <el-icon><svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3A4.5 4.5 0 0 0 14 8.5v5a4.47 4.47 0 0 0 2.5-1.5zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg></el-icon> 朗读
          </el-button>

          <el-button v-if="practiceMode && practiceAnswers[String(w.question_id)] && !showAnswer[w.question_id]"
                     type="primary" size="small" style="margin-top: 8px"
                     @click="checkPracticeAnswer(w)">
            检查答案
          </el-button>
        </div>

        <!-- Submit practice -->
        <div v-if="practiceMode && wrongList.length" style="text-align: center; margin-top: 20px">
          <el-button type="primary" @click="checkAllPractice" :disabled="!hasAnyPracticeAnswer">
            检查全部
          </el-button>
        </div>
      </template>
    </el-card>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import { getWrongQuestions, getWrongStats } from '../api/quiz'
import { speak } from '../composables/useVoice'

const wrongList = ref([])
const filterChapterId = ref(null)
const filterDifficulty = ref('')
const practiceMode = ref(false)
const practiceAnswers = ref({})
const showAnswer = ref({})
const allChapters = ref([])
const stats = ref(null)

const hasAnyPracticeAnswer = computed(() => {
  return Object.keys(practiceAnswers.value).length > 0
})

function formatShortDate(dateStr) {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    return `${d.getMonth()+1}/${d.getDate()}`
  } catch { return '' }
}

async function loadWrongQuestions() {
  try {
    const qRes = await getWrongQuestions(filterChapterId.value, filterDifficulty.value)
    wrongList.value = qRes.data || []

    // Populate chapter filter from wrong questions data
    const chapterMap = {}
    for (const w of wrongList.value) {
      if (w.chapter_id && !chapterMap[w.chapter_id]) {
        chapterMap[w.chapter_id] = { id: w.chapter_id, title: w.chapter_title || '??' + w.chapter_id }
      } else if (!w.chapter_id && w.chapter_title && !chapterMap[w.chapter_title]) {
        chapterMap[w.chapter_title] = { id: w.question_id, title: w.chapter_title }
      }
    }
    allChapters.value = Object.values(chapterMap)
  } catch (e) { console.error('loadWrongQuestions error:', e) }
}

async function loadStats() {
  try {
    const s = await getWrongStats()
    stats.value = s.data
    // Populate chapter filter dropdown from stats
    if (s.data?.per_chapter) {
      allChapters.value = s.data.per_chapter.map(ch => ({
        id: ch.chapter_id,
        title: ch.chapter_title,
      }))
    }
  } catch (e) { console.error("loadStats error:", e) }
}

onMounted(async () => {
  await loadWrongQuestions()
  await loadStats()
})

watch(filterChapterId, () => loadWrongQuestions())
watch(filterDifficulty, () => loadWrongQuestions())

function togglePracticeMode() {
  practiceMode.value = !practiceMode.value
  practiceAnswers.value = {}
  showAnswer.value = {}
  if (practiceMode.value) {
    loadWrongQuestions()
  } else {
    loadStats()
  }
}

function checkPracticeAnswer(w) {
  const ans = practiceAnswers.value[String(w.question_id)]
  if (!ans) return
  showAnswer.value[w.question_id] = true
}

function checkAllPractice() {
  for (const w of wrongList.value) {
    if (practiceAnswers.value[String(w.question_id)]) {
      showAnswer.value[w.question_id] = true
    }
  }
}
</script>

<style scoped>
.stat-item {
  text-align: center;
  padding: 16px;
}
.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #409eff;
  margin: 0;
}
.stat-label {
  font-size: 14px;
  color: #909399;
  margin: 4px 0 0;
}

.trend-chart {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  height: 120px;
  padding: 0 8px;
}
.trend-bar-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  justify-content: flex-end;
}
.trend-bar {
  width: 100%;
  min-height: 20px;
  border-radius: 4px 4px 0 0;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  transition: height 0.3s;
}
.trend-label {
  font-size: 11px;
  color: #fff;
  font-weight: bold;
  margin-top: 2px;
}
.trend-date {
  font-size: 10px;
  color: #909399;
  margin-top: 4px;
}

.chapter-bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.chapter-bar-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.chapter-bar-label {
  width: 100px;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
}
.chapter-bar-track {
  flex: 1;
  height: 20px;
  background: #f0f2f5;
  border-radius: 10px;
  overflow: hidden;
}
.chapter-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #f56c6c, #e6a23c);
  border-radius: 10px;
  transition: width 0.5s;
}
.chapter-bar-count {
  width: 30px;
  font-size: 13px;
  font-weight: bold;
  color: #606266;
}

:deep(.el-radio) {
  width: 100%;
  margin-left: 0 !important;
  margin-right: 0 !important;
}
:deep(.el-radio__label) {
  text-align: left;
  flex: 1;
}
:deep(.el-radio.is-bordered) {
  margin-left: 0 !important;
  margin-right: 0 !important;
}
</style>
