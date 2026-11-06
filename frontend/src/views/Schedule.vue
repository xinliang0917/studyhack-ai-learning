<template>
  <AppLayout>
    <div class="page-head">
      <div>
        <h2>学习计划</h2>
        <p>管理课程、作业与考试截止时间，掌握本周学习节奏。</p>
      </div>
      <div style="display: flex; gap: 10px">
        <el-button @click="openPlanDialog">从大纲生成</el-button>
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>
          新建任务
        </el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover"><div class="stat">
          <div class="num blue">{{ stats.todo || 0 }}</div>
          <div class="label">待完成</div>
        </div></el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover"><div class="stat">
          <div class="num orange">{{ stats.doing || 0 }}</div>
          <div class="label">进行中</div>
        </div></el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover"><div class="stat">
          <div class="num green">{{ stats.done || 0 }}</div>
          <div class="label">已完成</div>
        </div></el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover"><div class="stat">
          <div class="num red">{{ stats.overdue || 0 }}</div>
          <div class="label">已逾期</div>
        </div></el-card>
      </el-col>
    </el-row>

    <el-card shadow="hover" style="margin-top: 16px">
      <div class="filters">
        <el-select v-model="filters.status" clearable placeholder="全部状态" style="width: 130px" @change="load">
          <el-option label="待完成" value="todo" />
          <el-option label="进行中" value="doing" />
          <el-option label="已完成" value="done" />
        </el-select>
        <el-select v-model="filters.item_type" clearable placeholder="全部类型" style="width: 130px" @change="load">
          <el-option v-for="(label, value) in TYPE_LABELS" :key="value" :label="label" :value="value" />
        </el-select>
        <el-input v-model="keyword" clearable placeholder="搜索标题或课程" style="width: 220px" />
        <span class="count">共 {{ filtered.length }} 项</span>
      </div>

      <el-table v-if="filtered.length" :data="filtered" stripe>
        <el-table-column width="56">
          <template #default="{ row }">
            <el-checkbox :model-value="row.status === 'done'" @change="toggle(row)" />
          </template>
        </el-table-column>
        <el-table-column label="任务" min-width="220">
          <template #default="{ row }">
            <div :class="['task-title', { done: row.status === 'done' }]">{{ row.title }}</div>
            <div v-if="row.course" class="task-meta">{{ row.course }}</div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="typeTag(row.item_type)">{{ TYPE_LABELS[row.item_type] || row.item_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="截止时间" width="180">
          <template #default="{ row }">
            <span v-if="row.due_at" :class="{ overdue: isOverdue(row) }">{{ formatDate(row.due_at) }}</span>
            <span v-else class="muted">未设置</span>
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="priorityTag(row.priority)" effect="plain">{{ PRIORITY_LABELS[row.priority] || row.priority }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="statusTag(row.status)">{{ STATUS_LABELS[row.status] || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button text size="small" @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无任务，点击右上角新建" />
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑任务' : '新建任务'" width="520px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" maxlength="200" placeholder="如：完成数据结构第三章作业" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.item_type" style="width: 100%">
            <el-option v-for="(label, value) in TYPE_LABELS" :key="value" :label="label" :value="value" />
          </el-select>
        </el-form-item>
        <el-form-item label="课程">
          <el-input v-model="form.course" placeholder="可选，如：数据结构" />
        </el-form-item>
        <el-form-item label="截止时间">
          <el-date-picker
            v-model="form.due_at"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="选择日期时间"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="优先级">
          <el-radio-group v-model="form.priority">
            <el-radio-button value="low">低</el-radio-button>
            <el-radio-button value="normal">中</el-radio-button>
            <el-radio-button value="high">高</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="待完成" value="todo" />
            <el-option label="进行中" value="doing" />
            <el-option label="已完成" value="done" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="planDialog" title="从课程大纲生成学习计划" width="480px">
      <el-form label-width="90px">
        <el-form-item label="课程大纲" required>
          <el-select v-model="planForm.outline_id" placeholder="选择大纲" style="width: 100%">
            <el-option v-for="o in outlines" :key="o.id" :label="o.title" :value="o.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="周期(天)">
          <el-input-number v-model="planForm.days" :min="1" :max="60" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="planForm.start_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="默认今天"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="planDialog = false">取消</el-button>
        <el-button type="primary" :loading="planSaving" @click="savePlan">生成</el-button>
      </template>
    </el-dialog>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import AppLayout from '../components/AppLayout.vue'
import {
  autoPlan,
  createSchedule,
  deleteSchedule,
  getScheduleStats,
  listSchedule,
  toggleSchedule,
  updateSchedule,
} from '../api/schedule'
import { getOutlines } from '../api/course'

const TYPE_LABELS = { course: '课程', homework: '作业', exam: '考试', other: '其他', review: '复习' }
const STATUS_LABELS = { todo: '待完成', doing: '进行中', done: '已完成' }
const PRIORITY_LABELS = { low: '低', normal: '中', high: '高' }

const items = ref([])
const stats = ref({ todo: 0, doing: 0, done: 0, overdue: 0 })
const filters = reactive({ status: '', item_type: '' })
const keyword = ref('')
const dialogVisible = ref(false)
const saving = ref(false)
const editingId = ref(null)

const emptyForm = () => ({
  title: '',
  item_type: 'homework',
  course: '',
  due_at: '',
  priority: 'normal',
  status: 'todo',
  notes: '',
})
const form = reactive(emptyForm())
const planDialog = ref(false)
const planSaving = ref(false)
const outlines = ref([])
const planForm = reactive({ outline_id: null, days: 7, start_date: '' })

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return items.value
  return items.value.filter(item =>
    (item.title || '').toLowerCase().includes(kw) ||
    (item.course || '').toLowerCase().includes(kw)
  )
})

async function load() {
  try {
    const params = {}
    if (filters.status) params.status = filters.status
    if (filters.item_type) params.item_type = filters.item_type
    const [listRes, statsRes] = await Promise.all([listSchedule(params), getScheduleStats()])
    items.value = listRes.data
    stats.value = statsRes.data
  } catch (e) {
    if (e.response?.status !== 401) ElMessage.error('加载学习计划失败')
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, emptyForm())
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  Object.assign(form, emptyForm(), {
    title: row.title,
    item_type: row.item_type,
    course: row.course || '',
    due_at: row.due_at ? String(row.due_at).slice(0, 19) : '',
    priority: row.priority,
    status: row.status,
    notes: row.notes || '',
  })
  dialogVisible.value = true
}

async function save() {
  const title = form.title.trim()
  if (!title) {
    ElMessage.warning('请输入任务标题')
    return
  }
  const payload = {
    title,
    item_type: form.item_type,
    course: form.course.trim() || null,
    due_at: form.due_at || null,
    priority: form.priority,
    status: form.status,
    notes: form.notes.trim() || null,
  }
  saving.value = true
  try {
    if (editingId.value) {
      await updateSchedule(editingId.value, payload)
    } else {
      await createSchedule(payload)
    }
    ElMessage.success('已保存')
    dialogVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function toggle(row) {
  try {
    await toggleSchedule(row.id)
    await load()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.title}」吗？`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch (e) {
    return
  }
  try {
    await deleteSchedule(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

function formatDate(value) {
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function isOverdue(row) {
  return row.status !== 'done' && row.due_at && new Date(row.due_at) < new Date()
}

function typeTag(type) {
  return { course: '', homework: 'success', exam: 'danger', other: 'info', review: 'warning' }[type] || 'info'
}

function priorityTag(priority) {
  return { low: 'info', normal: '', high: 'danger' }[priority] || ''
}

function statusTag(status) {
  return { todo: 'info', doing: 'warning', done: 'success' }[status] || 'info'
}

async function openPlanDialog() {
  planForm.outline_id = null
  planForm.days = 7
  planForm.start_date = ''
  planDialog.value = true
  try {
    const res = await getOutlines()
    outlines.value = res.data || []
  } catch (e) {
    ElMessage.error('加载课程大纲失败')
  }
}

async function savePlan() {
  if (!planForm.outline_id) {
    ElMessage.warning('请选择课程大纲')
    return
  }
  planSaving.value = true
  try {
    const res = await autoPlan(planForm.outline_id, planForm.days, planForm.start_date || null)
    ElMessage.success(`已生成 ${res.data.created} 个任务`)
    planDialog.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '生成失败')
  } finally {
    planSaving.value = false
  }
}

onMounted(load)
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
  color: #303133;
}
.page-head p {
  margin: 4px 0 0;
  color: #909399;
  font-size: 13px;
}
.stat {
  text-align: center;
}
.stat .num {
  font-size: 34px;
  font-weight: bold;
}
.stat .num.blue { color: #409eff; }
.stat .num.orange { color: #e6a23c; }
.stat .num.green { color: #67c23a; }
.stat .num.red { color: #f56c6c; }
.stat .label {
  margin-top: 4px;
  color: #909399;
}
.filters {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}
.filters .count {
  margin-left: auto;
  color: #909399;
  font-size: 13px;
}
.task-title {
  color: #303133;
}
.task-title.done {
  color: #c0c4cc;
  text-decoration: line-through;
}
.task-meta {
  margin-top: 2px;
  color: #909399;
  font-size: 12px;
}
.overdue {
  color: #f56c6c;
  font-weight: 600;
}
.muted {
  color: #c0c4cc;
}
</style>
