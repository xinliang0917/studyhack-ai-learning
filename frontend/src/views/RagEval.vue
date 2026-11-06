<template>
  <AppLayout>
    <div class="page-head">
      <div>
        <h2>RAG 检索评估</h2>
        <p>用 Hit@k 与 MRR 对比 BM25、混合检索和向量检索，定位检索质量。</p>
      </div>
      <div class="head-actions">
        <el-button @click="loadExample">载入示例</el-button>
        <el-button type="primary" :loading="loading" @click="runEval">开始评估</el-button>
      </div>
    </div>

    <el-card shadow="hover" class="config-card">
      <el-form label-width="82px">
        <el-form-item label="评估用例">
          <el-input
            v-model="casesText"
            type="textarea"
            :rows="6"
            placeholder="每行一条，格式：问题 | 关键词1,关键词2"
          />
        </el-form-item>
        <el-form-item label="检索模式">
          <el-checkbox-group v-model="modes">
            <el-checkbox-button value="bm25">BM25</el-checkbox-button>
            <el-checkbox-button value="hybrid">混合检索</el-checkbox-button>
            <el-checkbox-button value="vector">向量检索</el-checkbox-button>
          </el-checkbox-group>
          <span class="hint">向量检索需要启用 Embedding；未启用时会标注为不可用。</span>
        </el-form-item>
        <el-form-item label="Top K">
          <el-input-number v-model="k" :min="1" :max="10" />
        </el-form-item>
      </el-form>
    </el-card>

    <template v-if="result">
      <el-row :gutter="16" style="margin-top: 16px">
        <el-col v-for="mode in result.modes" :key="mode.mode" :xs="24" :sm="12" :lg="8">
          <el-card shadow="hover" class="mode-card">
            <div class="mode-head">
              <span class="mode-name">{{ mode.label || mode.mode }}</span>
              <el-tag v-if="mode.available === false" type="info" size="small">未启用</el-tag>
              <el-tag v-else type="success" size="small">可用</el-tag>
            </div>
            <div class="metric-row">
              <div class="metric">
                <div class="metric-value">{{ ((mode.summary?.hit_rate || 0) * 100).toFixed(1) }}%</div>
                <div class="metric-label">Hit@{{ mode.summary?.k || k }}</div>
              </div>
              <div class="metric">
                <div class="metric-value">{{ (mode.summary?.mrr || 0).toFixed(3) }}</div>
                <div class="metric-label">MRR</div>
              </div>
              <div class="metric">
                <div class="metric-value">{{ mode.summary?.hits || 0 }}/{{ mode.summary?.cases || 0 }}</div>
                <div class="metric-label">命中用例</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-card shadow="hover" style="margin-top: 16px">
        <template #header>
          <span>模式对比</span>
          <el-button size="small" style="float: right" @click="exportCsv">导出 CSV</el-button>
        </template>
        <div ref="chartRef" class="chart"></div>
      </el-card>

      <el-card shadow="hover" style="margin-top: 16px">
        <template #header>
          <span>逐条结果</span>
          <el-select v-model="selectedMode" size="small" style="width: 160px; float: right">
            <el-option v-for="mode in result.modes" :key="mode.mode" :label="mode.label" :value="mode.mode" />
          </el-select>
        </template>
        <el-table :data="activeResults" size="small" stripe>
          <el-table-column prop="question" label="问题" min-width="220" />
          <el-table-column label="命中" width="80">
            <template #default="{ row }">
              <el-tag :type="row.hit ? 'success' : 'danger'" size="small">{{ row.hit ? '是' : '否' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="rank" label="排名" width="70">
            <template #default="{ row }">{{ row.rank || '-' }}</template>
          </el-table-column>
          <el-table-column label="期望关键词" min-width="180">
            <template #default="{ row }">
              <el-tag v-for="kw in row.expected_keywords" :key="kw" size="small" effect="plain" style="margin: 1px">{{ kw }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="Top 来源" min-width="280">
            <template #default="{ row }">
              <div v-if="row.top_sources?.[0]" class="top-source">
                <span class="source-name">{{ row.top_sources[0].filename || '知识库片段' }}</span>
                <span class="source-snippet">{{ row.top_sources[0].snippet }}</span>
              </div>
              <span v-else class="muted">无结果</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <el-empty v-else description="填写评估用例后点击「开始评估」" />
  </AppLayout>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import AppLayout from '../components/AppLayout.vue'
import { evaluateRag } from '../api/rag'

const DEFAULT_CASES = [
  '栈和队列有什么区别 | 后进先出,先进先出',
  '二分查找对数据有什么要求 | 有序,O(log n)',
  '二叉搜索树的左右子树有什么特点 | 左子树,右子树',
].join('\n')

const casesText = ref(DEFAULT_CASES)
const modes = ref(['bm25', 'hybrid'])
const k = ref(5)
const loading = ref(false)
const result = ref(null)
const selectedMode = ref('')
const chartRef = ref(null)
let chart = null

const activeResults = computed(() => {
  const mode = result.value?.modes?.find(item => item.mode === selectedMode.value)
  return mode?.results || []
})

function loadExample() {
  casesText.value = DEFAULT_CASES
}

function parseCases() {
  return casesText.value
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)
    .map(line => {
      const parts = line.split('|')
      return {
        question: (parts[0] || '').trim(),
        expected_keywords: (parts[1] || '')
          .split(/[,，]/)
          .map(item => item.trim())
          .filter(Boolean),
      }
    })
    .filter(item => item.question && item.expected_keywords.length)
}

async function runEval() {
  const cases = parseCases()
  if (!cases.length) {
    ElMessage.warning('请按“问题 | 关键词1,关键词2”格式填写')
    return
  }
  if (!modes.value.length) {
    ElMessage.warning('请至少选择一种检索模式')
    return
  }
  loading.value = true
  try {
    const res = await evaluateRag(cases, k.value, modes.value)
    result.value = res.data
    selectedMode.value = res.data.modes?.[0]?.mode || ''
    await nextTick()
    renderChart()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '评估失败')
  } finally {
    loading.value = false
  }
}

function renderChart() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const current = result.value?.modes || []
  const dark = document.documentElement.classList.contains('dark')
  const labelColor = dark ? '#e5eaf3' : '#606266'
  const splitColor = dark ? '#3a3a3a' : '#ebeef5'
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { textStyle: { color: labelColor } },
    grid: { left: 44, right: 24, top: 42, bottom: 30 },
    xAxis: {
      type: 'category',
      data: current.map(item => item.label),
      axisLabel: { color: labelColor },
      axisLine: { lineStyle: { color: splitColor } },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { color: labelColor, formatter: '{value}%' },
      splitLine: { lineStyle: { color: splitColor } },
    },
    series: [
      {
        name: 'Hit@K',
        type: 'bar',
        barMaxWidth: 34,
        data: current.map(item => Number(((item.summary?.hit_rate || 0) * 100).toFixed(1))),
        itemStyle: { color: '#409eff', borderRadius: [6, 6, 0, 0] },
      },
      {
        name: 'MRR × 100',
        type: 'bar',
        barMaxWidth: 34,
        data: current.map(item => Number(((item.summary?.mrr || 0) * 100).toFixed(1))),
        itemStyle: { color: '#67c23a', borderRadius: [6, 6, 0, 0] },
      },
    ],
  }, true)
}

function exportCsv() {
  const mode = result.value?.modes?.find(item => item.mode === selectedMode.value)
  if (!mode?.results?.length) {
    ElMessage.warning('暂无可导出的结果')
    return
  }
  const rows = [
    ['问题', '是否命中', '排名', '期望关键词', 'Top来源'],
    ...mode.results.map(item => [
      item.question,
      item.hit ? '是' : '否',
      item.rank || '',
      (item.expected_keywords || []).join('、'),
      item.top_sources?.[0]?.snippet || '',
    ]),
  ]
  const csv = rows
    .map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    .join('\n')
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `rag-eval-${selectedMode.value}.csv`
  link.click()
  URL.revokeObjectURL(link.href)
}

function resizeChart() {
  chart?.resize()
}

onMounted(() => window.addEventListener('resize', resizeChart))
onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  chart?.dispose()
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
.hint {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-left: 10px;
}
.mode-card {
  height: 100%;
}
.mode-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.mode-name {
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.metric-row {
  display: flex;
  justify-content: space-between;
  gap: 6px;
}
.metric {
  text-align: center;
  flex: 1;
}
.metric-value {
  font-size: 24px;
  font-weight: bold;
  color: #409eff;
}
.metric-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-top: 2px;
}
.chart {
  height: 280px;
  width: 100%;
}
.top-source {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.source-name {
  color: #409eff;
  font-size: 12px;
}
.source-snippet {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.4;
}
.muted {
  color: #c0c4cc;
}
@media (max-width: 768px) {
  .page-head {
    flex-direction: column;
    gap: 10px;
  }
  .hint {
    display: block;
    margin: 4px 0 0;
  }
}
</style>
