<template>
  <AppLayout>
    <div class="page-head">
      <div>
        <h2>学习概览</h2>
        <p>掌握度、学习节奏、薄弱点和今日复习任务一屏掌握。</p>
      </div>
      <div class="head-actions">
        <el-button @click="router.push('/knowledge-graph')">知识图谱</el-button>
        <el-button type="primary" @click="router.push('/wrong-questions')">去复习</el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :xs="12" :sm="8" :lg="4">
        <el-card shadow="hover"><div class="stat">
          <div class="num blue">{{ dashboard.mastery || 0 }}%</div>
          <div class="label">整体掌握度</div>
        </div></el-card>
      </el-col>
      <el-col :xs="12" :sm="8" :lg="4">
        <el-card shadow="hover"><div class="stat">
          <div class="num green">{{ dashboard.completion_rate || 0 }}%</div>
          <div class="label">课程完成率</div>
        </div></el-card>
      </el-col>
      <el-col :xs="12" :sm="8" :lg="4">
        <el-card shadow="hover"><div class="stat">
          <div class="num red">{{ dashboard.due_review || 0 }}</div>
          <div class="label">今日待复习</div>
        </div></el-card>
      </el-col>
      <el-col :xs="12" :sm="8" :lg="4">
        <el-card shadow="hover"><div class="stat">
          <div class="num orange">{{ dashboard.today_tasks_done || 0 }}/{{ dashboard.today_tasks || 0 }}</div>
          <div class="label">今日任务</div>
        </div></el-card>
      </el-col>
      <el-col :xs="12" :sm="8" :lg="4">
        <el-card shadow="hover"><div class="stat">
          <div class="num purple">{{ dashboard.streak_days || 0 }}</div>
          <div class="label">连续学习天数</div>
        </div></el-card>
      </el-col>
      <el-col :xs="12" :sm="8" :lg="4">
        <el-card shadow="hover"><div class="stat">
          <div class="num">{{ dashboard.study_minutes || 0 }}</div>
          <div class="label">累计学习分钟</div>
        </div></el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :xs="24" :lg="14">
        <el-card shadow="hover">
          <template #header><span>近 7 天学习活跃度</span></template>
          <div ref="activityRef" class="chart"></div>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="10">
        <el-card shadow="hover">
          <template #header><span>最近考试成绩</span></template>
          <div ref="scoreRef" class="chart"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :xs="24" :lg="14">
        <el-card shadow="hover">
          <template #header><span>薄弱章节</span></template>
          <div v-if="dashboard.weak_chapters?.length" class="weak-list">
            <div v-for="item in dashboard.weak_chapters" :key="item.chapter_id" class="weak-row">
              <div class="weak-main">
                <div class="weak-title">{{ item.title }}</div>
                <div class="weak-meta">错题 {{ item.wrong_count }} 道 · {{ statusLabel(item.status) }}</div>
              </div>
              <el-progress
                :percentage="item.mastery"
                :color="masteryColor"
                :stroke-width="10"
                style="width: 160px"
              />
              <el-button text type="primary" size="small" @click="goWeak(item)">去学习</el-button>
            </div>
          </div>
          <el-empty v-else description="暂无薄弱章节，继续保持" :image-size="70" />
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="10">
        <el-card shadow="hover">
          <template #header>
            <span>今日复习</span>
            <el-button
              size="small"
              type="warning"
              plain
              :loading="reviewPlanLoading"
              style="float: right"
              @click="generateReviewPlan"
            >加入今日任务</el-button>
          </template>
          <div v-if="dashboard.next_review?.length" class="review-list">
            <div v-for="item in dashboard.next_review" :key="item.question_id" class="review-row">
              <div class="review-question">{{ item.question_text }}</div>
              <div class="review-meta">
                <el-tag v-if="item.chapter_title" size="small" type="warning">{{ item.chapter_title }}</el-tag>
                <span>间隔 {{ item.interval_days }} 天</span>
              </div>
            </div>
            <el-button type="primary" plain style="width: 100%; margin-top: 8px" @click="router.push('/wrong-questions')">
              开始复习
            </el-button>
          </div>
          <el-empty v-else description="今天没有到期错题" :image-size="70" />
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="hover" style="margin-top: 16px">
      <template #header><span>今日任务</span></template>
      <div v-if="dashboard.today_items?.length">
        <div v-for="task in dashboard.today_items" :key="task.id" class="task-row">
          <div class="task-main">
            <el-checkbox :model-value="task.status === 'done'" @change="toggleTask(task)" />
            <span :class="['dot', task.priority]"></span>
            <span :class="['task-name', { done: task.status === 'done' }]">{{ task.title }}</span>
            <el-tag size="small" effect="plain" style="margin-left: 8px">{{ typeLabel(task.item_type) }}</el-tag>
          </div>
          <span class="task-due">{{ formatDue(task.due_at) }}</span>
        </div>
      </div>
      <el-empty v-else description="今天没有安排任务" :image-size="60" />
    </el-card>

    <el-card shadow="hover" style="margin-top: 16px">
      <template #header>
        <span>学习进度</span>
        <el-button size="small" style="float: right" @click="router.push('/schedule')">学习计划</el-button>
      </template>
      <el-progress :percentage="dashboard.completion_rate || 0" :stroke-width="20" :text-inside="true" striped style="margin: 16px 0" />
      <div v-if="progressByCourse.length">
        <el-collapse v-model="activeCourse" accordion>
          <el-collapse-item v-for="course in progressByCourse" :key="course.title" :title="course.title + ' (' + course.chapters.filter(c => c.status === 'completed').length + '/' + course.chapters.length + ')'" :name="course.title">
            <div v-for="row in course.chapters" :key="row.chapter_id" style="display: flex; align-items: center; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f0f0f0">
              <a style="color: #409eff; cursor: pointer; font-size: 14px" @click="goToChapter(row)">{{ row.chapter_title }}</a>
              <span>
                <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'learning' ? 'warning' : 'info'" size="small">{{ statusLabel(row.status) }}</el-tag>
                <el-button size="small" @click="markComplete(row.chapter_id)" v-if="row.status !== 'completed'" style="margin-left: 8px">标记完成</el-button>
              </span>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
      <el-empty v-else description="暂无学习进度，请先上传知识库并生成课程大纲" />
    </el-card>

    <el-card shadow="hover" style="margin-top: 16px">
      <template #header>
        <span>近 7 天待办</span>
        <el-button size="small" style="float: right" @click="router.push('/schedule')">学习计划</el-button>
      </template>
      <div v-if="dashboard.upcoming?.length">
        <div v-for="task in dashboard.upcoming" :key="task.id" class="task-row">
          <div class="task-main">
            <span :class="['dot', task.priority]"></span>
            <span class="task-name">{{ task.title }}</span>
            <el-tag size="small" effect="plain" style="margin-left: 8px">{{ typeLabel(task.item_type) }}</el-tag>
          </div>
          <span class="task-due">{{ formatDue(task.due_at) }}</span>
        </div>
      </div>
      <el-empty v-else description="近 7 天没有待办任务" :image-size="60" />
    </el-card>
  </AppLayout>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import AppLayout from '../components/AppLayout.vue'
import { getLearningDashboard, getProgress, updateProgress } from '../api/course'
import { createReviewPlan, toggleSchedule } from '../api/schedule'

const TYPE_LABELS = { course: '课程', homework: '作业', exam: '考试', other: '其他', review: '复习' }
const STATUS_LABELS = { completed: '已完成', learning: '学习中', not_started: '未开始', todo: '待完成', doing: '进行中', done: '已完成' }

const router = useRouter()
const dashboard = ref({})
const progressList = ref([])
const activeCourse = ref('')
const reviewPlanLoading = ref(false)
const activityRef = ref(null)
const scoreRef = ref(null)
let activityChart = null
let scoreChart = null

const progressByCourse = computed(() => {
  const map = {}
  for (const item of progressList.value) {
    const key = item.course_title || '未分组'
    if (!map[key]) {
      map[key] = { title: key, chapters: [] }
    }
    map[key].chapters.push(item)
  }
  return Object.values(map)
})

function typeLabel(type) {
  return TYPE_LABELS[type] || type
}

function statusLabel(status) {
  return STATUS_LABELS[status] || status
}

function masteryColor(value) {
  if (value >= 80) return '#67c23a'
  if (value >= 50) return '#e6a23c'
  return '#f56c6c'
}

function formatDue(value) {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function goToChapter(row) {
  if (row.outline_id && row.chapter_id) {
    router.push('/course/' + row.outline_id + '/chapter/' + row.chapter_id)
  }
}

function goWeak(item) {
  if (item.outline_id) {
    router.push('/course/' + item.outline_id + '/chapter/' + item.chapter_id)
  } else {
    router.push('/knowledge-graph')
  }
}

async function loadDashboard() {
  try {
    const [dash, progress] = await Promise.all([getLearningDashboard(), getProgress()])
    dashboard.value = dash.data || {}
    progressList.value = progress.data || []
    await nextTick()
    renderCharts()
  } catch (e) {
    if (e.response?.status !== 401) ElMessage.error('加载学习概览失败')
  }
}

function renderCharts() {
  if (!activityRef.value || !scoreRef.value) return
  if (!activityChart) activityChart = echarts.init(activityRef.value)
  if (!scoreChart) scoreChart = echarts.init(scoreRef.value)
  const dark = document.documentElement.classList.contains('dark')
  const labelColor = dark ? '#e5eaf3' : '#606266'
  const splitColor = dark ? '#3a3a3a' : '#ebeef5'
  const activity = dashboard.value.activity || []
  const scores = dashboard.value.score_trend || []

  activityChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 36, right: 16, top: 24, bottom: 26 },
    xAxis: {
      type: 'category',
      data: activity.map(item => item.label),
      axisLabel: { color: labelColor },
      axisLine: { lineStyle: { color: splitColor } },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: labelColor },
      splitLine: { lineStyle: { color: splitColor } },
    },
    series: [{
      type: 'bar',
      data: activity.map(item => item.count),
      barMaxWidth: 28,
      itemStyle: { color: '#409eff', borderRadius: [6, 6, 0, 0] },
    }],
  }, true)

  if (!scores.length) {
    scoreChart.clear()
    scoreChart.setOption({
      title: {
        text: '暂无考试记录',
        left: 'center',
        top: 'center',
        textStyle: { color: '#909399', fontSize: 14, fontWeight: 'normal' },
      },
    })
    return
  }
  scoreChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 36, right: 16, top: 24, bottom: 26 },
    xAxis: {
      type: 'category',
      data: scores.map((_, index) => '第' + (index + 1) + '次'),
      axisLabel: { color: labelColor },
      axisLine: { lineStyle: { color: splitColor } },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { color: labelColor },
      splitLine: { lineStyle: { color: splitColor } },
    },
    series: [{
      type: 'line',
      smooth: true,
      symbolSize: 8,
      data: scores.map(item => item.score),
      itemStyle: { color: '#67c23a' },
      areaStyle: { color: 'rgba(103, 194, 58, 0.15)' },
    }],
  }, true)
}

function resizeCharts() {
  activityChart?.resize()
  scoreChart?.resize()
}

async function markComplete(chapterId) {
  try {
    await updateProgress(chapterId, 'completed')
    ElMessage.success('已标记完成')
    await loadDashboard()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function toggleTask(task) {
  try {
    await toggleSchedule(task.id)
    await loadDashboard()
  } catch (e) {
    ElMessage.error('更新任务失败')
  }
}

async function generateReviewPlan() {
  reviewPlanLoading.value = true
  try {
    const res = await createReviewPlan()
    const count = res.data.created || 0
    ElMessage.success(count ? `已生成 ${count} 个复习任务` : '今日任务已存在或没有到期错题')
    await loadDashboard()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '生成复习任务失败')
  } finally {
    reviewPlanLoading.value = false
  }
}

onMounted(async () => {
  await loadDashboard()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  activityChart?.dispose()
  scoreChart?.dispose()
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
.head-actions {
  display: flex;
  gap: 8px;
}
.stat {
  text-align: center;
}
.stat .num {
  font-size: 30px;
  font-weight: bold;
}
.stat .num.blue { color: #409eff; }
.stat .num.green { color: #67c23a; }
.stat .num.orange { color: #e6a23c; }
.stat .num.red { color: #f56c6c; }
.stat .num.purple { color: #8e44ad; }
.stat .label {
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.chart {
  height: 240px;
  width: 100%;
}
.weak-list,
.review-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.weak-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.weak-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.weak-main {
  flex: 1;
  min-width: 0;
}
.weak-title {
  color: var(--el-text-color-primary);
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.weak-meta {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-top: 2px;
}
.review-row {
  padding: 8px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.review-row:last-child {
  border-bottom: none;
}
.review-question {
  color: var(--el-text-color-primary);
  font-size: 13px;
  line-height: 1.5;
}
.review-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-top: 4px;
}
.task-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.task-row:last-child {
  border-bottom: none;
}
.task-main {
  display: flex;
  align-items: center;
  min-width: 0;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 8px;
  flex-shrink: 0;
  background: #909399;
}
.dot.high { background: #f56c6c; }
.dot.normal { background: #409eff; }
.dot.low { background: #c0c4cc; }
.task-name {
  color: var(--el-text-color-primary);
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.task-name.done {
  color: #c0c4cc;
  text-decoration: line-through;
}
.task-due {
  color: #e6a23c;
  font-size: 13px;
  flex-shrink: 0;
  margin-left: 12px;
}
@media (max-width: 768px) {
  .page-head {
    flex-direction: column;
    gap: 10px;
  }
  .weak-row {
    flex-wrap: wrap;
  }
}
</style>
