<template>
  <a-card class="logs-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('systemLogs') }}</span>
        <div class="auto-refresh">
          <a-switch 
            v-model="autoRefreshEnabled" 
            @change="toggleAutoRefresh"
            :checked-text="t('autoRefreshOn')"
            :unchecked-text="t('autoRefreshOff')"
          />
        </div>
        <div class="header-actions">
          <a-button
            v-if="selectedFile"
            type="outline"
            size="small"
            @click="handleExportLogFile(selectedFile)"
          >
            {{ t('exportLog') }}
          </a-button>
          <a-button
            v-if="isAdmin"
            type="outline"
            status="danger"
            size="small"
            @click="showClearLogsModal"
          >
            {{ t('clearLogs') }}
          </a-button>
        </div>
      </div>
    </template>

    <div class="logs-body">
      <div class="logs-sidebar">
        <div class="sidebar-header">
          <span>{{ t('logDate') }}</span>
        </div>
        <div class="sidebar-list">
          <div
            v-for="file in logFiles"
            :key="file"
            class="sidebar-item"
            :class="{ active: selectedFile === file }"
            @click="handleSelectFile(file)"
          >
            <span class="sidebar-item-label">{{ formatLogFileName(file) }}</span>
            <div class="sidebar-item-actions" @click.stop>
              <icon-download
                class="action-icon export-icon"
                @click="handleExportLogFile(file)"
                :title="t('exportLogFile')"
              />
              <icon-delete
                v-if="isAdmin && !isTodayLogFile(file)"
                class="action-icon delete-icon"
                @click="showDeleteLogFileModal(file)"
                :title="t('deleteLogFile')"
              />
            </div>
          </div>
          <div v-if="logFiles.length === 0" class="sidebar-empty">
            <span>{{ t('noData') }}</span>
          </div>
        </div>
      </div>

      <div class="logs-content">
        <a-card v-if="logContent" class="log-content-card" :bordered="false">
          <pre class="log-content" ref="logContentRef"><span v-html="formatLogContent(logContent)"></span></pre>
        </a-card>
        <a-empty v-else>
          <template #description>
            <span>{{ t('noLogContent') }}</span>
          </template>
        </a-empty>
      </div>
    </div>

    <!-- 清理日志确认对话框 -->
    <a-modal 
      v-model:visible="clearLogsModalVisible" 
      :title="t('clearLogsConfirmTitle')" 
      @ok="handleClearLogs" 
      @cancel="cancelClearLogs"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
    >
      <p>{{ t('clearLogsConfirmMessage') }}</p>
    </a-modal>
    
    <!-- 删除指定日志文件确认对话框 -->
    <a-modal 
      v-model:visible="deleteLogFileModalVisible" 
      :title="t('deleteLogFileConfirmTitle')" 
      @ok="handleDeleteLogFile" 
      @cancel="cancelDeleteLogFile"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
    >
      <p>{{ t('deleteLogFileConfirmMessage', { filename: formatLogFileName(selectedLogFile) }) }}</p>
    </a-modal>
  </a-card>
</template>

<script setup>
import { onMounted, onUnmounted, ref, nextTick } from 'vue'
import { t } from '../../utils/locale'
import { Message, Modal } from '@arco-design/web-vue'
import { getLogFiles, getLogContent, clearLogs as clearLogsApi, clearLogFile as clearLogFileApi, exportLogFile } from '../../api/log'
import { isAdmin } from '../../stores/user'
import { IconDelete, IconDownload } from '@arco-design/web-vue/es/icon'

// 移动端检测
const isMobile = ref(window.innerWidth <= 768);

const checkIsMobile = () => {
  isMobile.value = window.innerWidth <= 768;
};

// 监听窗口大小变化
onMounted(() => {
  window.addEventListener('resize', checkIsMobile);
});

onUnmounted(() => {
  window.removeEventListener('resize', checkIsMobile);
});

const selectedFile = ref('')

const handleSelectFile = (file) => {
  selectedFile.value = file
  loadLogContent(file)
}

const logFiles = ref([])
const logContent = ref('')
const logContentRef = ref(null)
const autoRefreshEnabled = ref(true) // 默认开启自动刷新
const refreshInterval = ref(null)
const clearLogsModalVisible = ref(false) // 清理日志确认对话框可见性
const deleteLogFileModalVisible = ref(false) // 删除指定日志文件确认对话框可见性
const selectedLogFile = ref('') // 要删除的日志文件名
const pageVisibilityHandler = ref(null) // 页面可见性处理器

// ANSI 颜色代码映射
const ansiColorMap = {
  '30': '#000000', // 黑色
  '31': '#FF0000', // 红色
  '32': '#00FF00', // 绿色
  '33': '#FFFF00', // 黄色
  '34': '#0000FF', // 蓝色
  '35': '#FF00FF', // 紫色
  '36': '#00FFFF', // 青色
  '37': '#FFFFFF', // 白色
  '90': '#808080', // 灰色
  '91': '#FF8080', // 浅红色
  '92': '#80FF80', // 浅绿色
  '93': '#FFFF80', // 浅黄色
  '94': '#8080FF', // 浅蓝色
  '95': '#FF80FF', // 浅紫色
  '96': '#80FFFF', // 浅青色
  '97': '#FFFFFF'  // 亮白色
};

// 格式化日志内容，解析 ANSI 颜色代码
const formatLogContent = (content) => {
  if (!content) return '';
  
  // 限制日志内容长度，防止渲染过大的内容导致卡顿
  const maxLength = 50000; // 限制为50000个字符
  let processedContent = content;
  if (content.length > maxLength) {
    processedContent = content.substring(content.length - maxLength);
  }
  
  // 替换 ANSI 颜色代码为 HTML 标签
  let formattedContent = processedContent;
  
  // 匹配 ANSI 颜色代码模式 (优化正则表达式性能)
  formattedContent = formattedContent.replace(/\u001b\[(\d+)m(.*?)\u001b\[0m/g, (match, colorCode, text) => {
    const color = ansiColorMap[colorCode];
    if (color) {
      return `<span style="color: ${color};">${text}</span>`;
    }
    return text;
  });
  
  // 处理粗体文本
  formattedContent = formattedContent.replace(/\u001b\[1m(.*?)\u001b\[0m/g, '<strong>$1</strong>');
  
  // 如果原始内容被截断，添加提示信息
  if (content.length > maxLength) {
    return `<span style="color: #FFA500;">[log content truncated, only showing latest part]</span>\n${formattedContent}`;
  }
  
  return formattedContent;
};

// 格式化日志文件名，只显示日期部分
const formatLogFileName = (filename) => {
  // 假设文件名格式为 app_YYYY-MM-DD.log
  const dateMatch = filename.match(/app_(\d{4}-\d{2}-\d{2})\.log/);
  if (dateMatch && dateMatch[1]) {
    return dateMatch[1]; // 只返回日期部分 YYYY-MM-DD
  }
  // 如果不匹配格式，返回原文件名
  return filename;
};

// 获取今天的日期，用于识别当日日志文件
const getTodayLogFileName = () => {
  const today = new Date().toISOString().split('T')[0];
  return `app_${today}.log`;
};

// 判断是否为当日日志文件
const isTodayLogFile = (filename) => {
  return filename === getTodayLogFileName();
};

// 获取日志文件列表
const fetchLogFiles = async () => {
  try {
    const files = await getLogFiles()
    logFiles.value = files
    
    // 默认选择最新的日志文件
    if (files.length > 0) {
      selectedFile.value = files[0]
      await loadLogContent(files[0])
    }
  } catch (error) {
    console.error(t.value('getLogFilesFailed'), error)
    Message.error(`${t.value('getLogFilesFailed')}: ${error.message || t.value('unknownError')}`)
  }
}

// 加载日志内容并滚动到底部
const loadLogContent = async (filename) => {
  try {
    if (!filename) return
    
    const response = await getLogContent(filename)
    logContent.value = response.content
    
    // 在DOM更新后滚动到底部
    await nextTick()
    scrollToBottom()
  } catch (error) {
    console.error(t.value('getLogContentFailed'), error)
    Message.error(`${t.value('getLogContentFailed')}: ${error.message || t.value('unknownError')}`)
    logContent.value = ''
  }
}

// 滚动到底部
const scrollToBottom = () => {
  if (logContentRef.value) {
    logContentRef.value.scrollTop = logContentRef.value.scrollHeight
  }
}

// 页面可见性处理函数
const handleVisibilityChange = () => {
  if (document.hidden) {
    // 页面隐藏时，停止自动刷新
    if (refreshInterval.value) {
      clearInterval(refreshInterval.value)
      refreshInterval.value = null
    }
  } else {
    // 页面显示时，如果启用了自动刷新则重新启动
    if (autoRefreshEnabled.value && !refreshInterval.value) {
      toggleAutoRefresh()
    }
  }
}

// 切换自动刷新
const toggleAutoRefresh = () => {
  // 清除现有的定时器
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
    refreshInterval.value = null
  }
  
  if (autoRefreshEnabled.value) {
    // 启动自动刷新，每5秒刷新一次
    refreshInterval.value = setInterval(() => {
      if (selectedFile.value && !document.hidden) {
        loadLogContent(selectedFile.value)
      }
    }, 5000)
  }
}

// 显示清理日志确认对话框
const showClearLogsModal = () => {
  clearLogsModalVisible.value = true
}

// 取消清理日志
const cancelClearLogs = () => {
  clearLogsModalVisible.value = false
}

// 清理日志
const handleClearLogs = async () => {
  try {
    const response = await clearLogsApi()
    // 使用后端返回的消息，因为它包含了更详细的信息（包括当日日志未被清理的提示）
    Message.success(response.message || t.value('clearLogsSuccess'))
    
    // 关闭对话框
    clearLogsModalVisible.value = false
    
    // 重新获取日志文件列表
    await fetchLogFiles()
    
    // 清空当前日志内容
    logContent.value = ''
  } catch (error) {
    console.error(t.value('clearLogsFailed'), error)
    Message.error(`${t.value('clearLogsFailed')}: ${error.message || t.value('unknownError')}`)
    
    // 关闭对话框
    clearLogsModalVisible.value = false
  }
}

// 显示删除指定日志文件确认对话框
const showDeleteLogFileModal = (filename) => {
  selectedLogFile.value = filename
  deleteLogFileModalVisible.value = true
}

// 取消删除指定日志文件
const cancelDeleteLogFile = () => {
  deleteLogFileModalVisible.value = false
  selectedLogFile.value = ''
}

// 删除指定日志文件
const handleDeleteLogFile = async () => {
  try {
    const response = await clearLogFileApi(selectedLogFile.value)
    Message.success(response.message || t.value('deleteLogFileSuccess'))
    
    // 关闭对话框
    deleteLogFileModalVisible.value = false
    selectedLogFile.value = ''
    
    // 重新获取日志文件列表
    await fetchLogFiles()
    
    // 如果删除的是当前选中的文件，清空日志内容
    if (selectedFile.value === selectedLogFile.value) {
      logContent.value = ''
      selectedFile.value = ''
    }
  } catch (error) {
    console.error(t.value('deleteLogFileFailed'), error)
    Message.error(`${t.value('deleteLogFileFailed')}: ${error.message || t.value('unknownError')}`)
    
    // 关闭对话框
    deleteLogFileModalVisible.value = false
    selectedLogFile.value = ''
  }
}

// 导出日志文件
const handleExportLogFile = async (filename) => {
  try {
    if (!filename) {
      Message.warning(t.value('pleaseSelectLogFile'))
      return
    }

    // 禁止导出当日日志文件
    if (isTodayLogFile(filename)) {
      Message.warning(t.value('cannotExportTodayFile'))
      return
    }

    // 显示加载提示
    const loading = Message.loading(t.value('exportingLogFile'))

    const response = await exportLogFile(filename)

    // 创建下载链接
    const blob = new Blob([response], { type: 'application/octet-stream' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()

    // 清理
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    // 关闭加载提示并显示成功消息
    loading.close()
    Message.success(t.value('exportLogFileSuccess'))

  } catch (error) {
    console.error(t.value('exportLogFileFailed'), error)
    Message.error(`${t.value('exportLogFileFailed')}: ${error.message || t.value('unknownError')}`)
  }
}

// 组件挂载时获取日志文件列表并启动自动刷新
onMounted(() => {
  fetchLogFiles().then(() => {
    // 默认启动自动刷新
    toggleAutoRefresh()
  })
  
  // 添加页面可见性监听器
  pageVisibilityHandler.value = handleVisibilityChange
  document.addEventListener('visibilitychange', pageVisibilityHandler.value)
})

// 组件卸载时清理定时器和事件监听器
onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
  
  // 移除页面可见性监听器
  if (pageVisibilityHandler.value) {
    document.removeEventListener('visibilitychange', pageVisibilityHandler.value)
  }
})
</script>

<style scoped>
.logs-container {
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 15px;
  font-size: 1.3em;
  padding: 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.title {
  margin: 0;
  padding: 0;
  white-space: nowrap;
}

.auto-refresh {
  display: flex;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

/* ===== log body ===== */
.logs-body {
  display: flex;
  height: calc(100vh - 200px);
  min-height: 400px;
}

/* ===== sidebar ===== */
.logs-sidebar {
  width: 220px;
  min-width: 220px;
  border-right: 1px solid var(--color-border-2, #e5e5e5);
  display: flex;
  flex-direction: column;
  background: var(--color-bg-2, #fff);
}

.sidebar-header {
  padding: 12px 16px;
  font-weight: 600;
  font-size: 14px;
  border-bottom: 1px solid var(--color-border-2, #e5e5e5);
  color: var(--color-text-1, #333);
}

.sidebar-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.sidebar-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.2s;
  border-bottom: 1px solid var(--color-border-1, #f0f0f0);
}

.sidebar-item:hover {
  background: var(--color-fill-2, #f5f5f5);
}

.sidebar-item.active {
  background: var(--color-primary-light-1, #e8f3ff);
  color: var(--color-primary-6, #165DFF);
  font-weight: 500;
}

.sidebar-item-label {
  font-size: 14px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-item-actions {
  display: none;
  align-items: center;
  gap: 4px;
  margin-left: 8px;
  flex-shrink: 0;
}

.sidebar-item:hover .sidebar-item-actions {
  display: flex;
}

.sidebar-item.active .sidebar-item-actions {
  display: flex;
}

.action-icon {
  font-size: 14px;
  cursor: pointer;
  padding: 2px;
}

.action-icon.export-icon {
  color: var(--color-primary-6, #165DFF);
}

.action-icon.export-icon:hover {
  color: var(--color-primary-7, #0e42d2);
}

.action-icon.delete-icon {
  color: var(--color-danger-6, #f53f3f);
}

.action-icon.delete-icon:hover {
  color: var(--color-danger-7, #cb2727);
}

.sidebar-empty {
  padding: 24px 16px;
  text-align: center;
  color: var(--color-text-3, #999);
  font-size: 13px;
}

/* ===== content ===== */
.logs-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.log-content-card {
  flex: 1;
  margin: 0;
  border-radius: 0;
}

.log-content {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 16px;
  line-height: 1.4;
  margin: 0;
  padding: 15px;
  background-color: #000000;
  color: #ffffff;
  border-radius: 0;
  max-height: calc(100vh - 240px);
  overflow-y: auto;
}

/* ===== responsive ===== */
@media (max-width: 768px) {
  .logs-container {
    padding: 0;
  }

  .logs-body {
    flex-direction: column;
    height: auto;
    min-height: auto;
  }

  .logs-sidebar {
    width: 100%;
    min-width: unset;
    max-height: 200px;
    border-right: none;
    border-bottom: 1px solid var(--color-border-2, #e5e5e5);
  }

  .sidebar-list {
    display: flex;
    flex-wrap: nowrap;
    overflow-x: auto;
    overflow-y: hidden;
    padding: 4px 8px;
    gap: 4px;
  }

  .sidebar-item {
    flex-direction: column;
    align-items: flex-start;
    padding: 8px 12px;
    border-bottom: none;
    border-radius: 4px;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .sidebar-item-actions {
    display: flex;
    margin-left: 0;
    margin-top: 4px;
  }

  .log-content {
    font-size: 15px;
    padding: 10px;
    max-height: 400px;
  }

  .header-actions {
    margin-left: 0;
    width: 100%;
  }
}

@media (max-width: 480px) {
  .card-header {
    padding: 12px;
    gap: 8px;
  }

  .title {
    font-size: 1.1em;
  }

  .log-content {
    font-size: 14px;
    padding: 8px;
    max-height: 300px;
  }
}
</style>

<!-- 使用非scoped样式确保在所有主题下保持一致 -->
<style>
.logs-container :deep(.arco-card) {
  background: #ffffff !important;
  border: 1px solid #ebebeb !important;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
}

.logs-container :deep(.arco-card-body) {
  padding: 0 !important;
}

.logs-container :deep(.arco-card-header) {
  border-bottom: 1px solid #ebebeb !important;
  padding: 0 !important;
}

@media (max-width: 768px) {
  .logs-container :deep(.arco-card) {
    box-shadow: none !important;
  }
}

@media (max-width: 480px) {
  .logs-container :deep(.arco-card) {
    border: none !important;
    border-radius: 0 !important;
  }
}
</style>