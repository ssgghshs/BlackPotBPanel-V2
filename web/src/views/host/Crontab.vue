<template>
  <a-card class="cron-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('crontabTask') }}</span>
        <a-button type="outline" size="small" @click="openCreateDrawer" style="margin-left: auto;">
          {{ t('createCrontabTask') }}
        </a-button>
      </div>
    </template>

    <a-table
      :columns="columns"
      :data="taskData"
      :loading="loading"
      :pagination="pagination"
      @page-change="handlePageChange"
      @page-size-change="handlePageSizeChange"
      :scroll="scroll"
    >
      <template #task_type="{ record }">
        <a-tag>{{ getTypeLabel(record.task_type) }}</a-tag>
      </template>
      <template #status="{ record }">
        <a-switch
          :model-value="record.status === 1"
          @change="handleToggleStatus(record)"
          :loading="togglingId === record.id"
        />
      </template>
      <template #last_run_time="{ record }">
        {{ record.last_run_time ? formatDate(record.last_run_time) : '-' }}
      </template>
      <template #last_result="{ record }">
        <a-tag v-if="record.last_result" :color="record.last_result === '成功' || record.last_result === 'Successful' ? 'green' : 'red'">
          {{ record.last_result }}
        </a-tag>
        <span v-else>-</span>
      </template>
      <template #actions="{ record }">
        <a-space>
          <a-link @click="openEditDrawer(record)">{{ t('edit') }}</a-link>
          <a-link @click="handleRunNow(record)" :loading="runningId === record.id">{{ t('runNow') }}</a-link>
          <a-link @click="openLogDrawer(record)">{{ t('crontabLog') }}</a-link>
          <a-link status="danger" @click="confirmDeleteCrontab(record)">{{ t('delete') }}</a-link>
        </a-space>
      </template>
    </a-table>
  </a-card>

  <!-- 删除确认对话框 -->
  <a-modal
    :visible="deleteModalVisible"
    @ok="handleDelete"
    @cancel="cancelDelete"
    :ok-text="t('confirm')"
    :cancel-text="t('cancel')"
  >
    <template #title>
      {{ t('delete') }}
    </template>
    <div>
      <p>{{ t('confirmDeleteCrontab') }} {{ deleteTarget.name }}?</p>
    </div>
  </a-modal>

  <!-- 清空日志确认对话框 -->
  <a-modal
    :visible="clearLogModalVisible"
    @ok="handleClearLog"
    @cancel="cancelClearLog"
    :ok-text="t('confirm')"
    :cancel-text="t('cancel')"
  >
    <template #title>
      {{ t('clearLogs') }}
    </template>
    <div>
      <p>{{ t('confirmClearCrontabLog') }}</p>
    </div>
  </a-modal>

  <a-drawer
    :visible="formDrawerVisible"
    @cancel="closeFormDrawer"
    :width="isMobile ? '100%' : 700"
    :footer="false"
    :mask-closable="false"
  >
    <template #title>
      {{ formTask.id ? t('editCrontabTask') : t('createCrontabTask') }}
    </template>

    <a-form :model="formTask" :rules="formRules" ref="formRef" layout="vertical" @submit="handleSave">
      <a-form-item field="name" :label="t('crontabName')">
        <a-input v-model="formTask.name" :placeholder="t('enterCrontabName')" />
      </a-form-item>

      <a-form-item field="task_type" :label="t('crontabType')">
        <a-select v-model="formTask.task_type" :placeholder="t('selectCrontabType')" @change="onTypeChange">
          <a-option v-for="t in typeOptions" :key="t.type" :value="t.type" :label="t.label" />
        </a-select>
      </a-form-item>

      <a-row :gutter="16">
        <a-col :span="8" v-if="showWhere1">
          <a-form-item :label="where1Label" field="where1">
            <a-input-number v-model="formTask.where1" :min="1" :max="999" />
          </a-form-item>
        </a-col>
        <a-col :span="8" v-if="showHour">
          <a-form-item :label="t('crontabHour')" field="where_hour">
            <a-input-number v-model="formTask.where_hour" :min="0" :max="23" />
          </a-form-item>
        </a-col>
        <a-col :span="8" v-if="showMinute">
          <a-form-item :label="t('crontabMinute')" field="where_minute">
            <a-input-number v-model="formTask.where_minute" :min="0" :max="59" />
          </a-form-item>
        </a-col>
        <a-col :span="8" v-if="showWeek">
          <a-form-item :label="t('crontabWeek')" field="where_week">
            <a-select v-model="formTask.where_week">
              <a-option :value="0" :label="sundayText" />
              <a-option :value="1" :label="mondayText" />
              <a-option :value="2" :label="tuesdayText" />
              <a-option :value="3" :label="wednesdayText" />
              <a-option :value="4" :label="thursdayText" />
              <a-option :value="5" :label="fridayText" />
              <a-option :value="6" :label="saturdayText" />
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <a-form-item field="command" :label="t('crontabCommand')">
        <a-textarea
          v-model="formTask.command"
          :placeholder="t('enterCrontabCommand')"
          :auto-size="{ minRows: 4, maxRows: 12 }"
        />
        <template #extra>
          <a-alert type="warning" :bordered="false" show-icon>
            <template #icon>
              <icon-exclamation-circle />
            </template>
            {{ t('crontabDangerHint') }}
          </a-alert>
        </template>
      </a-form-item>

      <a-form-item field="description" :label="t('crontabDescription')">
        <a-input v-model="formTask.description" :placeholder="t('enterCrontabDescription')" />
      </a-form-item>

      <a-form-item>
        <a-space>
          <a-button type="primary" html-type="submit" :loading="saving">
            {{ formTask.id ? t('update') : t('create') }}
          </a-button>
          <a-button @click="closeFormDrawer">{{ t('cancel') }}</a-button>
        </a-space>
      </a-form-item>
    </a-form>
  </a-drawer>

  <a-drawer
    :visible="logDrawerVisible"
    @cancel="closeLogDrawer"
    :width="isMobile ? '100%' : '1000px'"
    :footer="false"
  >
    <template #title>
      {{ t('crontabLog') }} - {{ logTaskName }}
    </template>

    <div class="log-toolbar">
      <a-button type="outline" size="small" @click="fetchLog" :loading="logLoading">
        {{ t('refresh') }}
      </a-button>
      <a-button type="outline" size="small" status="danger" :loading="logClearing" @click="confirmClearLog">
        {{ t('clearLogs') }}
      </a-button>
      <span class="log-total" v-if="logTotalLines > 0">
        {{ t('crontabLogTotal') }}: {{ logTotalLines }}
      </span>
    </div>

    <div class="log-content-card" v-if="logContent.length > 0">
      <pre class="log-content" ref="logContentRef">
        <span v-for="(line, idx) in logContent" :key="idx">{{ line }}<br></span>
      </pre>
    </div>
    <a-empty v-else>
      <template #description>
        <span>{{ t('crontabLogEmpty') }}</span>
      </template>
    </a-empty>
  </a-drawer>
</template>

<script setup>
import { reactive, ref, computed, onMounted, nextTick, onBeforeUnmount } from 'vue'
import { t } from '../../utils/locale'
import {
  getCrontabList,
  getCrontabTypes,
  createCrontabTask,
  updateCrontabTask,
  deleteCrontabTask,
  toggleCrontabTask,
  runCrontabTaskNow,
  getCrontabTaskLog,
  clearCrontabTaskLog
} from '../../api/crontab'
import { Message } from '@arco-design/web-vue'

const taskData = ref([])
const typeOptions = ref([])
const loading = ref(false)
const saving = ref(false)
const togglingId = ref(null)
const runningId = ref(null)
const isMobile = ref(false)

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showTotal: true,
  showJumper: true,
  pageSizeOptions: [10, 20, 50, 100],
  showPageSize: true
})

const scroll = reactive({ x: 1100, y: 400 })

const columns = computed(() => [
  { title: t.value('id'), dataIndex: 'id', width: 70 },
  { title: t.value('crontabName'), dataIndex: 'name', width: 160, ellipsis: true },
  { title: t.value('crontabType'), slotName: 'task_type', width: 100 },
  { title: t.value('crontabCommand'), dataIndex: 'command', width: 240, ellipsis: true },
  { title: t.value('crontabStatus'), slotName: 'status', width: 80 },
  { title: t.value('crontabLastRun'), slotName: 'last_run_time', width: 170 },
  { title: t.value('crontabLastResult'), slotName: 'last_result', width: 120 },
  { title: t.value('actions'), slotName: 'actions', width: 220, fixed: 'right' }
])

const formDrawerVisible = ref(false)
const formRef = ref()
const formTask = reactive({
  id: undefined,
  name: '',
  task_type: 'day',
  where1: 1,
  where_hour: 0,
  where_minute: 0,
  where_week: 0,
  command: '',
  description: ''
})

const deleteModalVisible = ref(false)
const deleteTarget = reactive({ id: 0, name: '' })

const formRules = computed(() => ({
  name: [{ required: true, message: t.value('enterCrontabName') }],
  task_type: [{ required: true, message: t.value('selectCrontabType') }],
  command: [{ required: true, message: t.value('enterCrontabCommand') }]
}))

const showWhere1 = computed(() => {
  return ['day-n', 'hour-n', 'minute-n'].includes(formTask.task_type)
})

const showHour = computed(() => {
  return ['day', 'day-n', 'week', 'month'].includes(formTask.task_type)
})

const showMinute = computed(() => {
  return !['minute-n'].includes(formTask.task_type)
})

const showWeek = computed(() => {
  return formTask.task_type === 'week'
})

const where1Label = computed(() => {
  const map = { 'day-n': t.value('crontabEveryNDays'), 'hour-n': t.value('crontabEveryNHours'), 'minute-n': t.value('crontabEveryNMinutes') }
  return map[formTask.task_type] || t.value('crontabEveryNDays')
})

const sundayText = computed(() => t.value('sunday') || 'Sunday')
const mondayText = computed(() => t.value('monday') || 'Monday')
const tuesdayText = computed(() => t.value('tuesday') || 'Tuesday')
const wednesdayText = computed(() => t.value('wednesday') || 'Wednesday')
const thursdayText = computed(() => t.value('thursday') || 'Thursday')
const fridayText = computed(() => t.value('friday') || 'Friday')
const saturdayText = computed(() => t.value('saturday') || 'Saturday')

function getTypeLabel(type) {
  const found = typeOptions.value.find(t => t.type === type)
  return found ? found.label : type
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleString()
}

function onTypeChange() {
  if (formTask.task_type === 'day') { formTask.where_hour = 0; formTask.where_minute = 0; formTask.where1 = 1 }
  else if (formTask.task_type === 'day-n') { formTask.where1 = 1; formTask.where_hour = 0; formTask.where_minute = 0 }
  else if (formTask.task_type === 'hour') { formTask.where_minute = 0 }
  else if (formTask.task_type === 'hour-n') { formTask.where1 = 1; formTask.where_minute = 0 }
  else if (formTask.task_type === 'minute-n') { formTask.where1 = 5 }
  else if (formTask.task_type === 'week') { formTask.where_week = 1; formTask.where_hour = 0; formTask.where_minute = 0 }
  else if (formTask.task_type === 'month') { formTask.where1 = 1; formTask.where_hour = 0; formTask.where_minute = 0 }
}

async function fetchTypes() {
  try {
    typeOptions.value = await getCrontabTypes()
  } catch {
    Message.error(t.value('getCrontabTypesFailed'))
  }
}

async function fetchTasks(page = 1) {
  try {
    loading.value = true
    const res = await getCrontabList({ skip: (page - 1) * pagination.pageSize, limit: pagination.pageSize })
    taskData.value = res.items || []
    pagination.total = res.total || 0
  } catch {
    Message.error(t.value('getCrontabListFailed'))
  } finally {
    loading.value = false
  }
}

function handlePageChange(page) {
  pagination.current = page
  fetchTasks(page)
}

function handlePageSizeChange(size) {
  pagination.pageSize = size
  pagination.current = 1
  fetchTasks(1)
}

function openCreateDrawer() {
  formTask.id = undefined
  formTask.name = ''
  formTask.task_type = 'day'
  formTask.where1 = 1
  formTask.where_hour = 0
  formTask.where_minute = 0
  formTask.where_week = 0
  formTask.command = ''
  formTask.description = ''
  formDrawerVisible.value = true
}

function openEditDrawer(record) {
  formTask.id = record.id
  formTask.name = record.name
  formTask.task_type = record.task_type
  formTask.where1 = record.where1 || 0
  formTask.where_hour = record.where_hour || 0
  formTask.where_minute = record.where_minute || 0
  formTask.where_week = record.where_week || 0
  formTask.command = record.command
  formTask.description = record.description || ''
  formDrawerVisible.value = true
}

function closeFormDrawer() {
  formDrawerVisible.value = false
}

async function handleSave() {
  const valid = await formRef.value.validate()
  if (valid) return
  saving.value = true
  try {
    if (formTask.id) {
      await updateCrontabTask(formTask.id, {
        name: formTask.name,
        task_type: formTask.task_type,
        where1: formTask.where1,
        where_hour: formTask.where_hour,
        where_minute: formTask.where_minute,
        where_week: formTask.where_week,
        command: formTask.command,
        description: formTask.description
      })
      Message.success(t.value('updateCrontabSuccess'))
    } else {
      await createCrontabTask({
        name: formTask.name,
        task_type: formTask.task_type,
        where1: formTask.where1,
        where_hour: formTask.where_hour,
        where_minute: formTask.where_minute,
        where_week: formTask.where_week,
        command: formTask.command,
        description: formTask.description
      })
      Message.success(t.value('createCrontabSuccess'))
    }
    closeFormDrawer()
    await fetchTasks(pagination.current)
  } catch (e) {
    const errMsg = e?.response?.data?.detail
    if (errMsg) {
      Message.error(errMsg)
    } else {
      Message.error(formTask.id ? t.value('updateCrontabFailed') : t.value('createCrontabFailed'))
    }
  } finally {
    saving.value = false
  }
}

function confirmDeleteCrontab(record) {
  deleteTarget.id = record.id
  deleteTarget.name = record.name
  deleteModalVisible.value = true
}

function cancelDelete() {
  deleteModalVisible.value = false
}

async function handleDelete() {
  try {
    await deleteCrontabTask(deleteTarget.id)
    Message.success(t.value('deleteCrontabSuccess'))
    deleteModalVisible.value = false
    await fetchTasks(pagination.current)
  } catch {
    Message.error(t.value('deleteCrontabFailed'))
    deleteModalVisible.value = false
  }
}

async function handleToggleStatus(record) {
  togglingId.value = record.id
  try {
    await toggleCrontabTask(record.id)
    Message.success(t.value('toggleCrontabSuccess'))
    await fetchTasks(pagination.current)
  } catch {
    Message.error(t.value('toggleCrontabFailed'))
  } finally {
    togglingId.value = null
  }
}

async function handleRunNow(record) {
  runningId.value = record.id
  try {
    const res = await runCrontabTaskNow(record.id)
    Message.success(t.value('runNowSuccess'))
    await fetchTasks(pagination.current)
    await openLogDrawer(record)
  } catch (e) {
    const errMsg = e?.response?.data?.detail
    if (errMsg) {
      Message.error(errMsg)
    } else {
      Message.error(t.value('runNowFailed'))
    }
  } finally {
    runningId.value = null
  }
}

const logDrawerVisible = ref(false)
const logTaskName = ref('')
const logTaskId = ref(null)
const logContent = ref([])
const logTotalLines = ref(0)
const logLoading = ref(false)
const logClearing = ref(false)
const clearLogModalVisible = ref(false)
const logContentRef = ref(null)

async function openLogDrawer(record) {
  logTaskName.value = record.name
  logTaskId.value = record.id
  logDrawerVisible.value = true
  await fetchLog()
}

function closeLogDrawer() {
  logDrawerVisible.value = false
}

async function fetchLog() {
  if (!logTaskId.value) return
  logLoading.value = true
  try {
    const res = await getCrontabTaskLog(logTaskId.value, 200)
    logContent.value = res.content || []
    logTotalLines.value = res.total_lines || 0
    await nextTick()
    if (logContentRef.value) {
      logContentRef.value.scrollTop = logContentRef.value.scrollHeight
    }
  } catch {
    Message.error(t.value('getCrontabLogFailed'))
  } finally {
    logLoading.value = false
  }
}

async function handleClearLog() {
  if (!logTaskId.value) return
  logClearing.value = true
  try {
    await clearCrontabTaskLog(logTaskId.value)
    Message.success(t.value('clearLogsSuccess'))
    clearLogModalVisible.value = false
    await fetchLog()
  } catch {
    Message.error(t.value('clearLogsFailed'))
  } finally {
    logClearing.value = false
  }
}

function confirmClearLog() {
  clearLogModalVisible.value = true
}

function cancelClearLog() {
  clearLogModalVisible.value = false
}

onMounted(() => {
  checkIsMobile()
  window.addEventListener('resize', checkIsMobile)
  fetchTypes()
  fetchTasks()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', checkIsMobile)
})

function checkIsMobile() {
  isMobile.value = window.innerWidth < 768
}
</script>

<style scoped>
.cron-container {
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 15px;
  font-size: 1.3em;
  padding: 20px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.title {
  margin: 0;
  padding: 0;
}

.log-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.log-total {
  font-size: 12px;
  color: #888;
}

.log-content-card {
  margin-top: 4px;
}

.log-content {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.4;
  margin: 0;
  padding: 15px;
  background-color: #000000;
  color: #ffffff;
  border-radius: 4px;
  max-height: 700px;
  overflow-y: auto;
}
</style>
