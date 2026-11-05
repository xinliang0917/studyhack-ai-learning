<template>
  <AppLayout>
    <h2 style="margin-bottom: 20px">课程大纲</h2>
    <el-card shadow="hover" style="margin-bottom: 16px">
      <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap">
        <el-input v-model="title" placeholder="课程名称" style="width: 260px" />
        <el-button type="primary" @click="generate" :loading="generating">生成大纲</el-button>
      </div>
      <!-- File selection -->
      <el-divider />
      <div v-if="files.length > 0">
        <el-checkbox
          :indeterminate="isIndeterminate"
          :model-value="checkAll"
          @change="handleCheckAllChange"
        >全选（已选{{ selectedIds.length }}/{{ files.length }} 个文件）</el-checkbox>
        <div style="margin-top: 8px; display: flex; flex-wrap: wrap; gap: 4px 16px">
          <el-checkbox
            v-for="f in files"
            :key="f.id"
            :label="f.id"
            v-model="selectedIds"
          >{{ f.filename }}</el-checkbox>
        </div>
      </div>
      <el-empty v-else-if="!files.length" description="暂无知识库文件，请先上传" :image-size="60" style="padding: 8px 0" />
    </el-card>
    <el-card shadow="hover" v-if="outline" style="margin-bottom: 16px">
      <div v-if="allOutlines.length > 1" style="display: flex; align-items: center; gap: 8px">
        <span style="font-size: 14px; color: #606266">切换大纲：</span>
        <el-select v-model="selectedOutlineId" placeholder="选择大纲" style="width: 260px" @change="(v) => {}">
          <el-option v-for="o in allOutlines" :key="o.id" :label="o.title" :value="o.id" />
        </el-select>
      </div>
    </el-card>
    <el-card shadow="hover" v-if="outline">
      <template #header>
        <span style="display: flex; justify-content: space-between; align-items: center">
          <span>{{ outline.title }}</span>
          <el-button size="small" type="danger" @click="handleDeleteOutline" :disabled="generating">删除</el-button>
        </span>
      </template>
      <el-tree :data="treeData" :props="{ children: 'children', label: 'title' }" node-key="id" default-expand-all highlight-current @node-click="handleNodeClick">
        <template #default="{ node, data }">
          <span style="display: flex; align-items: center; gap: 8px">
            <span>{{ data.title }}</span>
          </span>
        </template>
      </el-tree>
    </el-card>
    <el-empty v-else description="还没有课程大纲，请输入课程名称并选择文件，然后点击「生成大纲」" />
  </AppLayout>
</template>

<script setup>
import { ref, onMounted, computed, watch } from "vue"
import { useRouter } from "vue-router"
import { ElMessage, ElMessageBox } from "element-plus"
import AppLayout from "../components/AppLayout.vue"
import { generateOutline, getOutlines, getChapters, deleteOutline } from "../api/course"
import { getProgress } from "../api/course"
import { listDocuments } from "../api/knowledge"

const router = useRouter()
const title = ref("")
const generating = ref(false)
const outline = ref(null)
const allChapters = ref([])
const progressMap = ref({})

// File selection
const files = ref([])
const allOutlines = ref([])
const selectedOutlineId = ref(null)
const selectedIds = ref([])
const checkAll = ref(false)
const isIndeterminate = ref(false)

watch(selectedIds, (val) => {
  if (val.length === 0) {
    checkAll.value = false
    isIndeterminate.value = false
  } else if (val.length === files.value.length) {
    checkAll.value = true
    isIndeterminate.value = false
  } else {
    isIndeterminate.value = true
    checkAll.value = false
  }
})

function handleCheckAllChange(val) {
  selectedIds.value = val ? files.value.map(f => f.id) : []
  isIndeterminate.value = false
}

onMounted(async () => {
  try {
    const outlines = await getOutlines()
    allOutlines.value = outlines.data
    if (outlines.data.length) {
      selectedOutlineId.value = outlines.data[0].id
      outline.value = outlines.data[0]
      await loadChapters(outline.value.id)
    }
    const p = await getProgress()
    for (const item of p.data) {
      progressMap.value[item.chapter_id] = item.status
    }
  } catch (e) { /* ignore */ }
  // Fetch KB files for selection
  try {
    const res = await listDocuments()
    files.value = res.data
    if (files.value.length) {
      selectedIds.value = files.value.map(f => f.id)
      checkAll.value = true
    }
  } catch (e) {}
})

async function loadChapters(outlineId) {
  const res = await getChapters(outlineId)
  allChapters.value = res.data
}

const treeData = computed(() => {
  if (!allChapters.value.length) return []
  const result = []
  for (const root of allChapters.value) {
    if (root.parent_id !== 0) continue
    const children = []
    for (const c of allChapters.value) {
      if (c.parent_id === root.id) {
        children.push({
          id: c.id,
          title: c.title,
          status: progressMap.value[c.id],
        })
      }
    }
    result.push({
      id: root.id,
      title: root.title,
      status: progressMap.value[root.id],
      children: children,
    })
  }
  return result
})

watch(selectedOutlineId, async (newId) => {
  if (!newId) return
  const found = allOutlines.value.find(o => o.id === newId)
  if (found) {
    outline.value = found
    await loadChapters(found.id)
  }
})

async function generate() {
  if (!title.value) { ElMessage.warning("请输入课程名称"); return }
  if (!selectedIds.value.length) { ElMessage.warning("请选择至少一个知识库文件"); return }
  generating.value = true
  try {
    const res = await generateOutline(title.value, [...selectedIds.value])
    const newOutline = res.data
    // Add to outline list so the switch card appears immediately
    allOutlines.value.unshift(newOutline)
    // selectedOutlineId watch handles outline.value + loadChapters
    selectedOutlineId.value = newOutline.id
    ElMessage.success("大纲生成成功")
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "生成失败")
  }
  generating.value = false
}

async function handleDeleteOutline() {
  try {
    await ElMessageBox.confirm("确定要删除这个课程大纲吗？相关的章节和进度记录也会删除。", "确认删除", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
    })
    await deleteOutline(outline.value.id)
    ElMessage.success("大纲已删除")
    allOutlines.value = allOutlines.value.filter(o => o.id !== outline.value.id)
    outline.value = null
    allChapters.value = []
    selectedOutlineId.value = allOutlines.value.length ? allOutlines.value[0].id : null
    if (selectedOutlineId.value) {
      const found = allOutlines.value.find(o => o.id === selectedOutlineId.value)
      if (found) {
        outline.value = found
        await loadChapters(found.id)
      }
    }
  } catch (e) {
    if (e !== "cancel") ElMessage.error("删除澶辫触")
  }
}

function handleNodeClick(data) {
  if (data.id && outline.value) {
    router.push(`/course/${outline.value.id}/chapter/${data.id}`)
  }
}
</script>
