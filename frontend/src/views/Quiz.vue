<template>
  <AppLayout>
    <h2 style="margin-bottom: 20px">在线测验</h2>

    <el-card shadow="hover" style="margin-bottom: 16px">
      <template #header><span>生成新测验</span></template>
      <el-form :inline="true" label-width="70px">
        <el-form-item label="课程">
          <el-select v-model="selectedOutlineId" placeholder="选择课程" style="width: 200px" @change="onOutlineChange">
            <el-option v-for="o in outlines" :key="o.id" :label="o.title" :value="o.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="出题方式">
          <el-radio-group v-model="mode">
            <el-radio value="course">整门课程</el-radio>
            <el-radio value="chapter">按章节抽取</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="mode === 'chapter'" label="选择章节">
          <el-select v-model="selectedChapterIds" multiple placeholder="选择章节" style="width: 280px">
            <el-option v-for="ch in chapters" :key="ch.id" :label="ch.title" :value="ch.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="难度">
          <el-select v-model="difficulty" style="width: 100px">
            <el-option label="简单" value="easy" />
            <el-option label="中等" value="medium" />
            <el-option label="困难" value="hard" />
          </el-select>
        </el-form-item>
        <el-form-item label="题数">
          <el-input-number v-model="count" :min="3" :max="30" />
        </el-form-item>
        <el-form-item label="时限(分)">
          <el-input-number v-model="timeLimit" :min="5" :max="120" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="startQuiz" :loading="loading" :disabled="loading">
            {{ loading ? '正在生成题目...' : '开始测验' }}
          </el-button>
        </el-form-item>
      </el-form>
      <el-empty v-if="!outlines.length" description="请先上传知识库并生成课程大纲" />
    </el-card>

    <!-- Exam History -->
    <el-card shadow="hover" v-if="examHistory.length">
      <template #header><span>历史记录</span></template>
      <el-table :data="examHistory" stripe>
        <el-table-column prop="course_title" label="课程/章节" min-width="200">
          <template #default="{row}">
            <div>{{ row.course_title || '未知课程' }}</div>
            <div v-if="row.chapter_titles?.length" style="font-size: 12px; color: #909399; margin-top: 2px">
              {{ row.chapter_titles.join('、') }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="score" label="分数" width="80">
          <template #default="{row}">
            <el-tag :type="row.score >= 60 ? 'success' : 'danger'" size="small">{{ row.score }}分</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total" label="题数" width="60" />
        <el-table-column label="用时" width="120">
          <template #default="{row}">
            {{ Math.floor(row.time_spent / 60) }}分{{ row.time_spent % 60 }}秒
          </template>
        </el-table-column>
        <el-table-column label="时间" width="170">
          <template #default="{row}">{{ formatCST(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{row}">
            <div style="display:flex;gap:2px;white-space:nowrap;align-items:center">
              <el-button text type="primary" size="small" @click="router.push('/exam/' + row.id)">查看</el-button>
              <el-popconfirm title="确定删除此记录？" @confirm="handleDelete(row.id)">
                <template #reference>
                  <el-button text type="danger" size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AppLayout from '../components/AppLayout.vue'
import { generateQuizByCourse, generateQuiz, getExamHistory, deleteExam } from '../api/quiz'
import { getOutlines, getChapters } from '../api/course'
import { speakQuizGenerated } from '../composables/useVoice'

const router = useRouter()
const mode = ref('course')
const difficulty = ref('medium')
const count = ref(5)
const timeLimit = ref(30)
const loading = ref(false)
const outlines = ref([])
const selectedOutlineId = ref(null)
const chapters = ref([])
const selectedChapterIds = ref([])
const examHistory = ref([])

onMounted(async () => {
  try {
    const [o, h] = await Promise.all([getOutlines(), getExamHistory()])
    outlines.value = o.data
    examHistory.value = h.data
    if (o.data.length) {
      selectedOutlineId.value = o.data[0].id
      const c = await getChapters(o.data[0].id)
      chapters.value = c.data
    }
  } catch (e) { /* ignore */ }
})

watch(selectedOutlineId, async (newId) => {
  if (!newId) return
  try {
    const c = await getChapters(newId)
    chapters.value = c.data
    selectedChapterIds.value = []
  } catch (e) {}
})

function onOutlineChange() {}

async function startQuiz() {
  if (!selectedOutlineId.value) {
    ElMessage.warning("请选择课程")
    return
  }
  if (mode.value === 'chapter' && !selectedChapterIds.value.length) {
    ElMessage.warning("请选择至少一个章节")
    return
  }
  if (mode.value === 'chapter' && selectedChapterIds.value.length > 0) {
    const parentChapters = chapters.value.filter(ch => ch.parent_id === 0)
    const validIds = selectedChapterIds.value.filter(id => parentChapters.some(pc => pc.id === id))
    if (!validIds.length) {
      ElMessage.warning("请选择有效的主章节")
      return
    }
  }

  loading.value = true
  try {
    let res
    if (mode.value === 'course') {
      res = await generateQuizByCourse(selectedOutlineId.value, count.value, difficulty.value, timeLimit.value * 60)
    } else {
      res = await generateQuiz(selectedChapterIds.value, count.value, difficulty.value, timeLimit.value * 60)
    }

    if (res.data && res.data.exam_id) {
      sessionStorage.setItem("exam_" + res.data.exam_id, JSON.stringify(res.data))
      ElMessage.success("测验已生成，共" + res.data.total + "道题")
      router.push("/exam/" + res.data.exam_id)
    } else {
      ElMessage.error("生成失败：未返回有效数据")
    }
  } catch (e) {
    const detail = e.response?.data?.detail
    if (detail) {
      ElMessage.error(detail)
    } else if (e.code === 'ERR_NETWORK') {
      ElMessage.error("网络连接失败，请检查后端服务是否运行")
    } else {
      ElMessage.error("生成失败：" + (e.message || "未知错误"))
    }
  }
  loading.value = false
}

async function handleDelete(examId) {
  try {
    await deleteExam(examId)
    examHistory.value = examHistory.value.filter(e => e.id !== examId)
    ElMessage.success("已删除")
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "删除失败")
  }
}

function formatCST(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
}

</script>
