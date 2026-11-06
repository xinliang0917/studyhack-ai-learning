<template>
  <AppLayout>
    <h2 style="margin-bottom: 20px; color: #303133">学习概览</h2>
    <el-row :gutter="20">
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover"><div style="text-align: center">
          <div style="font-size: 36px; color: #409eff; font-weight: bold">{{ stats.total || 0 }}</div>
          <div style="color: #909399; margin-top: 4px">总章节</div>
        </div></el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover"><div style="text-align: center">
          <div style="font-size: 36px; color: #67c23a; font-weight: bold">{{ stats.completed || 0 }}</div>
          <div style="color: #909399; margin-top: 4px">已完成</div>
        </div></el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover"><div style="text-align: center">
          <div style="font-size: 36px; color: #e6a23c; font-weight: bold">{{ stats.learning || 0 }}</div>
          <div style="color: #909399; margin-top: 4px">学习中</div>
        </div></el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover"><div style="text-align: center">
          <div style="font-size: 36px; color: #f56c6c; font-weight: bold">{{ stats.completion_rate || 0 }}%</div>
          <div style="color: #909399; margin-top: 4px">完成率</div>
        </div></el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 20px" shadow="hover">
      <template #header><span>学习进度</span></template>
      <el-progress :percentage="stats.completion_rate || 0" :stroke-width="20" :text-inside="true" striped style="margin: 16px 0" />
      <div v-if="progressByCourse.length">
        <el-collapse v-model="activeCourse" accordion>
          <el-collapse-item v-for="course in progressByCourse" :key="course.title" :title="course.title + ' (' + course.chapters.filter(c => c.status === 'completed').length + '/' + course.chapters.length + ')'" :name="course.title">
            <div v-for="row in course.chapters" :key="row.chapter_id" style="display: flex; align-items: center; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f0f0f0">
              <a style="color: #409eff; cursor: pointer; font-size: 14px" @click="goToChapter(row)">{{ row.chapter_title }}</a>
              <span>
                <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'learning' ? 'warning' : 'info'" size="small">{{ row.status === 'completed' ? '已完成' : row.status === 'learning' ? '学习中' : '未开始' }}</el-tag>
                <el-button size="small" @click="markComplete(row.chapter_id)" v-if="row.status !== 'completed'" style="margin-left: 8px">标记完成</el-button>
              </span>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
      <el-empty v-else description="暂无学习进度，请先上传知识库并生成课程大纲" />
    </el-card>

    <el-card style="margin-top: 20px" shadow="hover">
      <template #header>
        <span>近 7 天待办</span>
        <el-button size="small" style="float: right" @click="router.push('/schedule')">学习计划</el-button>
      </template>
      <div v-if="upcomingTasks.length">
        <div v-for="task in upcomingTasks" :key="task.id" class="task-row">
          <div class="task-main">
            <span :class="['dot', task.priority]"></span>
            <span class="task-name">{{ task.title }}</span>
            <el-tag size="small" effect="plain" style="margin-left: 8px">{{ TYPE_LABELS[task.item_type] || task.item_type }}</el-tag>
            <span v-if="task.course" class="task-course">{{ task.course }}</span>
          </div>
          <span class="task-due">{{ formatDue(task.due_at) }}</span>
        </div>
      </div>
      <el-empty v-else description="近 7 天没有待办任务" :image-size="60" />
    </el-card>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AppLayout from '../components/AppLayout.vue'
import { getProgress, updateProgress } from '../api/course'
import { getLearningStats } from '../api/quiz'
import { getScheduleStats } from '../api/schedule'

const TYPE_LABELS = { course: '课程', homework: '作业', exam: '考试', other: '其他' }

const router = useRouter()
const stats = ref({})
const progressList = ref([])
const activeCourse = ref("")
const upcomingTasks = ref([])

const progressByCourse = computed(() => {
  const map = {}
  for (const item of progressList.value) {
    const key = item.course_title || "未分组"
    if (!map[key]) {
      map[key] = { title: key, chapters: [] }
    }
    map[key].chapters.push(item)
  }
  return Object.values(map)
})

function goToChapter(row) {
  if (row.outline_id && row.chapter_id) {
    router.push("/course/" + row.outline_id + "/chapter/" + row.chapter_id)
  }
}

onMounted(async () => {
  try {
    const [s, p] = await Promise.all([
      getLearningStats(),
      getProgress()
    ])
    stats.value = s.data
    progressList.value = p.data
  } catch (e) { /* ignore */ }
  try {
    const sch = await getScheduleStats()
    upcomingTasks.value = sch.data.upcoming || []
  } catch (e) { /* ignore */ }
})

function formatDue(value) {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function markComplete(chapterId) {
  try {
    await updateProgress(chapterId, 'completed')
    ElMessage.success('已标记完成')
    const p = await getProgress()
    progressList.value = p.data
    const s = await getLearningStats()
    stats.value = s.data
  } catch (e) { ElMessage.error('操作失败') }
}
</script>

<style scoped>
.task-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
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
  color: #303133;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.task-course {
  margin-left: 8px;
  color: #909399;
  font-size: 12px;
}
.task-due {
  color: #e6a23c;
  font-size: 13px;
  flex-shrink: 0;
  margin-left: 12px;
}
</style>