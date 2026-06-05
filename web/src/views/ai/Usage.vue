<template>
  <div class="usage-container">
    <!-- 标题栏 + 时间筛选 -->
    <div class="usage-header">
      <div class="usage-title">{{ t('usageStatistics') }}</div>
      <div class="usage-controls">
        <a-button size="small" type="primary" @click="handleReset" :loading="resetting">{{ t('reset') }}</a-button> 
        <a-select v-model="timeRange" @change="loadData" style="width: 140px;" size="small"> 
          <a-option value="today">{{ t('today') }}</a-option>
          <a-option value="week">{{ t('thisWeek') }}</a-option>
          <a-option value="month">{{ t('thisMonth') }}</a-option>
          <a-option value="all">{{ t('all') }}</a-option>
        </a-select>
        <a-button size="small" @click="loadData" :loading="loading">{{ t('refresh') }}</a-button>
      </div>
    </div>

    <!-- ============ 1. 汇总卡片 ============ -->
    <div class="metrics-grid">
      <div class="content-row">
        <div class="card-item card-25">
          <div class="card-content">
            <div class="stat-item">
              <span class="stat-label">{{ t('usageTotalRequests') }}</span>
              <span class="stat-value">{{ summary.total_requests }}</span>
            </div>
          </div>
        </div>
        <div class="card-item card-25">
          <div class="card-content">
            <div class="stat-item">
              <span class="stat-label">{{ t('usageTotalInputTokens') }}</span>
              <span class="stat-value">{{ formatNum(summary.total_input_tokens) }}</span>
            </div>
          </div>
        </div>
        <div class="card-item card-25">
          <div class="card-content">
            <div class="stat-item">
              <span class="stat-label">{{ t('usageTotalOutputTokens') }}</span>
              <span class="stat-value">{{ formatNum(summary.total_output_tokens) }}</span>
            </div>
          </div>
        </div>
        <div class="card-item card-25">
          <div class="card-content">
            <div class="stat-item highlight">
              <span class="stat-label">{{ t('usageTotalTokens') }}</span>
              <span class="stat-value">{{ formatNum(summary.total_tokens) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ============ 2. 按模型统计（表格） ============ -->
    <a-card class="section-card">
      <template #title>
        <div class="section-title">{{ t('usageByModel') }}</div>
      </template>
      <a-table
        :columns="modelColumns"
        :data="byModel"
        :loading="loading"
        :pagination="false"
        :scroll="{ x: 700 }"
        size="small"
      >
        <template #provider="{ record }">
          <a-tag>{{ record.provider }}</a-tag>
        </template>
      </a-table>
    </a-card>

    <!-- ============ 3. 每日趋势 ============ -->
    <div class="chart-section">
      <a-card class="section-card chart-card">
        <template #title>
          <div class="section-title">{{ t('usageDailyTrend') }}</div>
        </template>
        <div ref="trendChart" class="chart-container"></div>
      </a-card>
      <a-card class="section-card stats-card">
        <template #title>
          <div class="section-title">{{ t('usageRequestAndTokens') }}</div>
        </template>
        <div class="daily-mini-cards">
          <div v-for="(day, idx) in dailyStats.slice(0, 7)" :key="idx" class="mini-card">
            <span class="mini-date">{{ day.date }}</span>
            <span class="mini-val">{{ formatNum(day.total_tokens) }}</span>
            <div class="mini-bar-wrap">
              <div class="mini-bar" :style="{ width: barWidth(day.total_tokens) + '%' }"></div>
            </div>
            <span class="mini-sub">{{ day.request_count }}{{ t('usageRequests') }}</span>
          </div>
          <div v-if="dailyStats.length === 0" class="mini-empty">{{ t('noData') }}</div>
        </div>
      </a-card>
    </div>

    <!-- ============ 4. 最近记录 ============ -->
    <a-card class="section-card">
      <template #title>
        <div class="section-title">{{ t('usageRecentLogs') }}</div>
      </template>
      <template #extra>
        <a-space>
          <a-button size="small" type="outline" @click="handleExport" :loading="exporting">{{ t('export') }}</a-button>
        </a-space>
      </template>
      <a-table
        :columns="logColumns"
        :data="recentLogs"
        :loading="loading"
        :pagination="{ current: logPage, pageSize: 15, total: recentLogs.length, showTotal: true }"
        @page-change="logPage = $event"
        :scroll="{ x: 800 }"
        size="small"
      >
        <template #total_tokens="{ record }">
          <span class="token-num">{{ formatNum(record.total_tokens) }}</span>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { t } from '../../utils/locale'
import { getAiUsage, exportAiUsage, resetAiUsage } from '../../api/ai'
import { Message } from '@arco-design/web-vue'
import * as echarts from 'echarts5'

// ============ 状态 ============
const timeRange = ref('week')
const loading = ref(false)
const exporting = ref(false)
const resetting = ref(false)
const logPage = ref(1)

const summary = reactive({
  total_requests: 0,
  total_input_tokens: 0,
  total_output_tokens: 0,
  total_tokens: 0,
})
const byModel = ref([])
const dailyStats = ref([])
const recentLogs = ref([])

// 图表
const trendChart = ref(null)
let trendChartInstance = null

// ============ 表格列定义 ============
const modelColumns = [
  { title: t.value('modelName'), dataIndex: 'model_name', width: 160 },
  { title: t.value('provider'), slotName: 'provider', width: 100 },
  { title: t.value('requestCount'), dataIndex: 'request_count', width: 100 },
  { title: t.value('usageInputTokens'), dataIndex: 'input_tokens', width: 120 },
  { title: t.value('usageOutputTokens'), dataIndex: 'output_tokens', width: 120 },
  { title: t.value('usageTotalTokens'), dataIndex: 'total_tokens', width: 120, sortable: true },
]

const logColumns = [
  { title: t.value('usageTime'), dataIndex: 'created_at', width: 160 },
  { title: t.value('modelName'), dataIndex: 'model_name', width: 140 },
  { title: t.value('provider'), dataIndex: 'provider', width: 90 },
  { title: t.value('usageInputTokens'), dataIndex: 'prompt_tokens', width: 100 },
  { title: t.value('usageOutputTokens'), dataIndex: 'completion_tokens', width: 100 },
  { title: t.value('usageTotalTokens'), slotName: 'total_tokens', width: 100 },
  { title: t.value('usageConversation'), dataIndex: 'conversation_title', ellipsis: true, width: 200 },
]

// ============ 工具 ============
function formatNum(value) {
  if (value === undefined || value === null) return '0'
  if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M'
  if (value >= 1000) return (value / 1000).toFixed(1) + 'k'
  return String(value)
}

const maxToken = computed(() => {
  if (dailyStats.value.length === 0) return 1
  return Math.max(...dailyStats.value.map(d => d.total_tokens), 1)
})

function barWidth(tokens) {
  const m = maxToken.value
  if (m <= 0) return 0
  return Math.max((tokens / m) * 100, 2)
}

// ============ 数据加载 ============
async function loadData() {
  loading.value = true
  try {
    const res = await getAiUsage({ time_range: timeRange.value })
    summary.total_requests = res.summary?.total_requests ?? 0
    summary.total_input_tokens = res.summary?.total_input_tokens ?? 0
    summary.total_output_tokens = res.summary?.total_output_tokens ?? 0
    summary.total_tokens = res.summary?.total_tokens ?? 0
    byModel.value = res.by_model || []
    dailyStats.value = res.daily_stats || []
    recentLogs.value = res.recent_logs || []

    nextTick(() => {
      renderChart()
    })
  } catch {
    Message.error(t.value('usageLoadFailed'))
  } finally {
    loading.value = false
  }
}

// ============ 图表渲染 ============
function renderChart() {
  if (!trendChart.value) return
  const data = dailyStats.value
  if (data.length === 0) {
    if (trendChartInstance) {
      trendChartInstance.clear()
    }
    return
  }

  if (!trendChartInstance) {
    if (trendChart.value.clientWidth === 0 || trendChart.value.clientHeight === 0) {
      setTimeout(() => renderChart(), 100)
      return
    }
    trendChartInstance = echarts.init(trendChart.value)
  }

  const dates = data.map(d => d.date)
  const totalTokens = data.map(d => d.total_tokens)
  const requestCounts = data.map(d => d.request_count)
  const inputTokens = data.map(d => d.input_tokens)
  const outputTokens = data.map(d => d.output_tokens)

  trendChartInstance.setOption({
    tooltip: {
      trigger: 'axis',
    },
    legend: {
      data: [t.value('usageTotalTokens'), t.value('usageInputTokens'), t.value('usageOutputTokens'), t.value('requestCount')],
      top: 0,
      textStyle: { fontSize: 11 },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '8%',
      top: '16%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { fontSize: 10, rotate: 30 },
    },
    yAxis: [
      {
        type: 'value',
        name: 'Token',
        position: 'left',
        axisLabel: { fontSize: 10 },
      },
      {
        type: 'value',
        name: t.value('requestCount'),
        position: 'right',
        axisLabel: { fontSize: 10 },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: t.value('usageTotalTokens'),
        type: 'line',
        smooth: true,
        data: totalTokens,
        itemStyle: { color: '#722ed1' },
        areaStyle: { opacity: 0.1, color: '#722ed1' },
      },
      {
        name: t.value('usageInputTokens'),
        type: 'line',
        smooth: true,
        data: inputTokens,
        itemStyle: { color: '#40a9ff' },
        lineStyle: { type: 'dashed' },
      },
      {
        name: t.value('usageOutputTokens'),
        type: 'line',
        smooth: true,
        data: outputTokens,
        itemStyle: { color: '#52c41a' },
        lineStyle: { type: 'dashed' },
      },
      {
        name: t.value('requestCount'),
        type: 'bar',
        yAxisIndex: 1,
        data: requestCounts,
        itemStyle: { color: 'rgba(114, 46, 209, 0.3)' },
        barWidth: '40%',
      },
    ],
  })
}

// ============ 导出 / 重置 ============
async function handleExport() {
  exporting.value = true
  try {
    const res = await exportAiUsage({ time_range: timeRange.value })
    const data = res.data || []
    // 导出为 CSV
    const headers = [t.value('usageTime'), t.value('modelName'), t.value('provider'), t.value('usageInputTokens'), t.value('usageOutputTokens'), t.value('usageTotalTokens'), 'Cost']
    const rows = data.map(item => [
      item.date,
      item.model,
      item.provider,
      item.input_tokens,
      item.output_tokens,
      item.total_tokens,
      item.cost ?? 0,
    ])
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ai-usage-${timeRange.value}-${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
    Message.success(t.value('usageExportSuccess'))
  } catch {
    Message.error(t.value('usageExportFailed'))
  } finally {
    exporting.value = false
  }
}

async function handleReset() {
  try {
    const res = await resetAiUsage()
    Message.success(t.value('usageResetSuccess'))
    await loadData()
  } catch {
    Message.error(t.value('usageResetFailed'))
  }
}

// ============ 窗口自适应 ============
function handleResize() {
  trendChartInstance?.resize()
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendChartInstance?.dispose()
  trendChartInstance = null
})
</script>

<style scoped>
.usage-container {
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.usage-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.usage-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-1);
}

.usage-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* ===== 汇总卡片 ===== */
.metrics-grid {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 20px;
}

.content-row {
  display: flex;
  gap: 15px;
}

.card-item {
  background: var(--color-bg-1);
  padding: 12px;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.card-25 {
  flex: 1;
  min-width: 0;
}

.card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 12px 8px;
  background: var(--color-bg-2);
  border-radius: 6px;
  border: 1px solid var(--color-neutral-3);
}

.stat-item.highlight {
  border-color: rgb(var(--primary-6));
  background: var(--color-primary-light-1);
}

.stat-label {
  font-size: 12px;
  color: var(--color-text-3);
  margin-bottom: 4px;
}

.stat-value {
  font-size: clamp(20px, 2vw, 28px);
  font-weight: 700;
  color: var(--color-text-1);
}

.stat-item.highlight .stat-value {
  color: rgb(var(--primary-6));
}

/* ===== 通用卡片 ===== */
.section-card {
  margin-bottom: 20px;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

:deep(.section-card .arco-card-header) {
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border-2);
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-1);
}

/* ===== 图表区域 ===== */
.chart-section {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
}

.chart-card {
  flex: 1;
  min-width: 0;
}

.chart-card .chart-container {
  width: 100%;
  height: 280px;
}

.stats-card {
  width: 340px;
  min-width: 280px;
  flex-shrink: 0;
}

.daily-mini-cards {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 280px;
  overflow-y: auto;
}

.mini-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: var(--color-bg-2);
  border-radius: 4px;
  font-size: 12px;
}

.mini-date {
  width: 80px;
  flex-shrink: 0;
  color: var(--color-text-2);
  font-size: 11px;
}

.mini-val {
  width: 70px;
  text-align: right;
  font-weight: 600;
  color: var(--color-text-1);
  flex-shrink: 0;
}

.mini-bar-wrap {
  flex: 1;
  height: 8px;
  background: var(--color-fill-2);
  border-radius: 4px;
  overflow: hidden;
}

.mini-bar {
  height: 100%;
  background: linear-gradient(90deg, #722ed1, #40a9ff);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.mini-sub {
  width: 70px;
  text-align: right;
  color: var(--color-text-4);
  font-size: 11px;
  flex-shrink: 0;
}

.mini-empty {
  text-align: center;
  padding: 24px;
  color: var(--color-text-3);
}

/* ===== Token 数字高亮 ===== */
.token-num {
  font-weight: 600;
  color: rgb(var(--primary-6));
}

/* ===== 响应式 ===== */
@media (max-width: 900px) {
  .chart-section {
    flex-direction: column;
  }
  .stats-card {
    width: 100%;
    min-width: 0;
  }
  .content-row {
    flex-wrap: wrap;
  }
  .card-25 {
    min-width: calc(50% - 8px);
    flex: 1 1 calc(50% - 8px);
  }
}
</style>
