<template>
  <AppLayout>
    <h2 style="margin-bottom: 20px; color: #303133">学习概览</h2>
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover"><div style="text-align: center">
          <div style="font-size: 36px; color: #409eff; font-weight: bold">{{ stats.total || 0 }}</div>
          <div style="color: #909399; margin-top: 4px">总章节</div>
        </div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><div style="text-align: center">
          <div style="font-size: 36px; color: #67c23a; font-weight: bold">{{ stats.completed || 0 }}</div>
          <div style="color: #909399; margin-top: 4px">已完成</div>
        </div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><div style="text-align: center">
          <div style="font-size: 36px; color: #e6a23c; font-weight: bold">{{ stats.learning || 0 }}</div>
          <div style="color: #909399; margin-top: 4px">学习中</div>
        </div></el-card>
      </el-col>
      <el-col :span="6">
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
  </AppLayout>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AppLayout from '../components/AppLayout.vue'
import { getProgress, updateProgress } from '../api/course'
import { getLearningStats } from '../api/quiz'

const router = useRouter()
const stats = ref({})
const progressList = ref([])
const activeCourse = ref("")

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
})

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