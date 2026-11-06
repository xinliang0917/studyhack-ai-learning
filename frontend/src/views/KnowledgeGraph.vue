<template>
  <AppLayout>
    <div class="page-head">
      <div>
        <h2>知识图谱</h2>
        <p>章节关系与答题掌握度，红色表示薄弱，绿色表示掌握较好。</p>
      </div>
      <div class="head-actions">
        <el-select
          v-model="outlineId"
          placeholder="选择课程大纲"
          style="width: 220px"
          @change="loadGraph"
        >
          <el-option v-for="o in outlines" :key="o.id" :label="o.title" :value="o.id" />
        </el-select>
        <el-button :loading="loading" @click="loadGraph">刷新</el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover"><div class="stat">
          <div class="num blue">{{ summary.overall_mastery || 0 }}%</div>
          <div class="label">整体掌握度</div>
        </div></el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover"><div class="stat">
          <div class="num green">{{ summary.attempts || 0 }}</div>
          <div class="label">累计答题</div>
        </div></el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover"><div class="stat">
          <div class="num orange">{{ summary.correct || 0 }}</div>
          <div class="label">累计答对</div>
        </div></el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover"><div class="stat">
          <div class="num">{{ summary.chapter_count || 0 }}</div>
          <div class="label">章节/小节数</div>
        </div></el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :xs="24" :lg="14">
        <el-card shadow="hover">
          <template #header><span>章节关系图</span></template>
          <div ref="graphRef" class="chart"></div>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="10">
        <el-card shadow="hover">
          <template #header><span>章节掌握度</span></template>
          <div ref="radarRef" class="chart"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="hover" style="margin-top: 16px">
      <template #header><span>章节明细</span></template>
      <el-table :data="detailRows" stripe v-if="detailRows.length">
        <el-table-column prop="title" label="章节" min-width="220" />
        <el-table-column label="层级" width="80">
          <template #default="{ row }">{{ row.level === 0 ? '章节' : '小节' }}</template>
        </el-table-column>
        <el-table-column prop="attempts" label="答题数" width="90" />
        <el-table-column prop="correct" label="答对数" width="90" />
        <el-table-column label="掌握度" min-width="180">
          <template #default="{ row }">
            <el-progress :percentage="row.mastery" :color="masteryColor" />
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无章节数据，请先生成课程大纲并完成测验" />
    </el-card>
  </AppLayout>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import AppLayout from '../components/AppLayout.vue'
import { getKnowledgeGraph, getOutlines } from '../api/course'

const outlines = ref([])
const outlineId = ref(null)
const loading = ref(false)
const graphRef = ref(null)
const radarRef = ref(null)
const nodes = ref([])
const edges = ref([])
const summary = ref({})
let graphChart = null
let radarChart = null

const detailRows = computed(() =>
  nodes.value
    .filter(node => node.level >= 0)
    .slice()
    .sort((a, b) => a.id - b.id)
)

function masteryColor(value) {
  if (value >= 80) return '#67c23a'
  if (value >= 50) return '#e6a23c'
  return '#f56c6c'
}

async function loadOutlines() {
  try {
    const res = await getOutlines()
    outlines.value = res.data || []
    if (!outlineId.value && outlines.value.length) {
      outlineId.value = outlines.value[0].id
      await loadGraph()
    }
  } catch (e) {
    ElMessage.error('加载课程大纲失败')
  }
}

async function loadGraph() {
  if (!outlineId.value) return
  loading.value = true
  try {
    const res = await getKnowledgeGraph(outlineId.value)
    nodes.value = res.data.nodes || []
    edges.value = res.data.edges || []
    summary.value = res.data.summary || {}
    await nextTick()
    renderCharts()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载知识图谱失败')
  } finally {
    loading.value = false
  }
}

function renderCharts() {
  if (graphRef.value && !graphChart) {
    graphChart = echarts.init(graphRef.value)
  }
  if (radarRef.value && !radarChart) {
    radarChart = echarts.init(radarRef.value)
  }
  const labelColor = document.documentElement.classList.contains('dark')
    ? '#e5eaf3'
    : '#303133'
  if (graphChart) {
    graphChart.setOption({
      tooltip: {
        formatter: params => {
          if (params.dataType !== 'node') return ''
          const data = params.data
          return `${data.name}<br/>掌握度：${data.mastery}%<br/>答题：${data.attempts}`
        },
      },
      series: [{
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        label: { show: true, fontSize: 11, color: labelColor },
        force: { repulsion: 240, edgeLength: [60, 140], gravity: 0.1 },
        lineStyle: { color: '#c0c4cc', curveness: 0.1 },
        emphasis: { focus: 'adjacency' },
        categories: [{ name: '大纲' }, { name: '章节' }, { name: '小节' }],
        data: nodes.value.map(node => ({
          id: String(node.id),
          name: node.title,
          category: node.level === -1 ? 0 : node.level === 0 ? 1 : 2,
          symbolSize: node.level === -1 ? 48 : node.level === 0 ? 34 : 22,
          mastery: node.mastery,
          attempts: node.attempts,
          itemStyle: { color: masteryColor(node.mastery) },
        })),
        links: edges.value.map(edge => ({
          source: String(edge.source),
          target: String(edge.target),
        })),
      }],
    }, true)
  }
  if (radarChart) {
    const top = summary.value.top_chapters || []
    if (!top.length) {
      radarChart.clear()
      radarChart.setOption({
        title: {
          text: '暂无章节数据',
          left: 'center',
          top: 'center',
          textStyle: { color: '#909399', fontSize: 14, fontWeight: 'normal' },
        },
      })
      return
    }
    radarChart.setOption({
      tooltip: {},
      radar: {
        indicator: top.map(chapter => ({ name: chapter.title, max: 100 })),
        radius: '62%',
        axisName: { color: labelColor },
      },
      series: [{
        type: 'radar',
        data: [{
          value: top.map(chapter => chapter.mastery),
          name: '掌握度',
          areaStyle: { opacity: 0.25 },
          lineStyle: { color: '#409eff' },
          itemStyle: { color: '#409eff' },
        }],
      }],
    }, true)
  }
}

function handleResize() {
  graphChart?.resize()
  radarChart?.resize()
}

onMounted(async () => {
  await loadOutlines()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  graphChart?.dispose()
  radarChart?.dispose()
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
  color: #303133;
}
.page-head p {
  margin: 4px 0 0;
  color: #909399;
  font-size: 13px;
}
.head-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}
.stat {
  text-align: center;
}
.stat .num {
  font-size: 30px;
  font-weight: bold;
  color: #409eff;
}
.stat .num.green { color: #67c23a; }
.stat .num.orange { color: #e6a23c; }
.stat .label {
  margin-top: 4px;
  color: #909399;
}
.chart {
  width: 100%;
  height: 420px;
}
@media (max-width: 768px) {
  .page-head {
    flex-direction: column;
    gap: 10px;
  }
  .head-actions {
    width: 100%;
    flex-wrap: wrap;
  }
  .chart {
    height: 320px;
  }
}
</style>
