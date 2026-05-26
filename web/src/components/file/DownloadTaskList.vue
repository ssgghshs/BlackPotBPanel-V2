<template>
  <a-modal
    :visible="visible"
    :title="t('downloadTaskList')"
    :width="isMobile ? '95%' : 1200"
    :footer="false"
    @cancel="handleCancel"
    :unmount-on-close="true"
    :height="isMobile ? '90%' : 600"
  >
    <div class="download-task-list">
      <div class="task-list-actions" style="margin-bottom: 16px; text-align: right;">
        <a-button type="outline" @click="refreshTasks">
          <icon-refresh />
          {{ t('refresh') }}
        </a-button>
      </div>
      
      <a-table 
        :columns="columns" 
        :data="taskList" 
        :loading="loading"
        :pagination="pagination"
        @page-change="handlePageChange"
        @page-size-change="handlePageSizeChange"
        :scroll="{ x: 'max-content', y: isMobile ? 'calc(90vh - 200px)' : '350px' }"
      >
        <template #status="{ record }">
          <a-tag :color="getStatusColor(record.status)">
            {{ getStatusText(record.status) }}
          </a-tag>
        </template>
        
        <template #progress="{ record }">
          <div v-if="record.status === 'downloading' || record.status === 'completed'">
            <!-- 只显示百分比，删除进度条 -->
            <div class="progress-text" :style="{ color: getStatusColor(record.status) }">
              {{ Math.min(100, Math.max(0, record.progress)) }}%
            </div>
          </div>
          <div v-else>
            --
          </div>
        </template>
        
        <template #size="{ record }">
          <div v-if="record.total_size > 0">
            {{ formatFileSize(record.downloaded_size) }} / {{ formatFileSize(record.total_size) }}
          </div>
          <div v-else>
            {{ formatFileSize(record.downloaded_size) }}
          </div>
        </template>
        
        <template #actions="{ record }">
          <a-space>
            <a-button type="text" size="small" @click="viewTaskDetails(record)">
              <icon-eye />
              {{ t('details') }}
            </a-button>
            <!-- 添加取消下载任务按钮 -->
            <a-button 
              v-if="record.status === 'downloading' || record.status === 'starting'" 
              type="text" 
              size="small" 
              @click="cancelDownload(record)"
              style="color: #ff7d00;"
            >
              <icon-stop />
              {{ t('cancel') }}
            </a-button>
            <!-- 添加删除下载记录按钮 -->
            <a-button 
              v-else-if="record.status === 'completed' || record.status === 'error' || record.status === 'cancelled'" 
              type="text" 
              size="small" 
              @click="deleteRecord(record)"
              style="color: #f53f3f;"
            >
              <icon-delete />
              {{ t('delete') }}
            </a-button>
          </a-space>
        </template>
      </a-table>
    </div>
    
    <!-- 任务详情模态框 -->
    <a-modal
      :visible="detailDrawer.visible"
      :title="t('downloadTaskDetails')"
      :width="isMobile ? '95%' : 800"
      :footer="false"
      @cancel="detailDrawer.visible = false"
      :unmount-on-close="true"
    >
      <a-spin :loading="detailDrawer.loading">
        <div class="task-detail" v-if="detailDrawer.task">
          <a-descriptions :column="1" size="medium">
            <a-descriptions-item :label="t('downloadTaskId')">
              {{ detailDrawer.task.download_id }}
            </a-descriptions-item>
            <a-descriptions-item :label="t('downloadTaskStatus')">
              <a-tag :color="getStatusColor(detailDrawer.task.status)">
                {{ getStatusText(detailDrawer.task.status) }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item :label="t('downloadTaskProgress')">
              <div v-if="detailDrawer.task.status === 'downloading' || detailDrawer.task.status === 'completed'">
                <!-- 只显示百分比，删除进度条 -->
                <div class="progress-text" :style="{ color: getStatusColor(detailDrawer.task.status) }">
                  {{ Math.min(100, Math.max(0, detailDrawer.task.progress)) }}%
                </div>
              </div>
              <div v-else>
                --
              </div>
            </a-descriptions-item>
            <a-descriptions-item :label="t('downloadTaskUrl')">
              {{ detailDrawer.task.url }}
            </a-descriptions-item>
            <a-descriptions-item :label="t('downloadTaskFileName')">
              {{ detailDrawer.task.filename }}
            </a-descriptions-item>
            <a-descriptions-item :label="t('downloadTaskDestination')">
              {{ detailDrawer.task.destination_path }}
            </a-descriptions-item>
            <a-descriptions-item :label="t('downloadTaskSize')">
              <div v-if="detailDrawer.task.total_size > 0">
                {{ formatFileSize(detailDrawer.task.total_size) }}
              </div>
              <div v-else>
                --
              </div>
            </a-descriptions-item>
            <a-descriptions-item :label="t('downloadTaskDownloaded')">
              {{ formatFileSize(detailDrawer.task.downloaded_size) }}
            </a-descriptions-item>
            <a-descriptions-item :label="t('downloadTaskStartTime')">
              {{ detailDrawer.task.created_at ? formatDate(detailDrawer.task.created_at) : '--' }}
            </a-descriptions-item>
            <a-descriptions-item :label="t('downloadTaskEndTime')">
              {{ detailDrawer.task.completed_at ? formatDate(detailDrawer.task.completed_at) : '--' }}
            </a-descriptions-item>
            <a-descriptions-item :label="t('downloadTaskError')" v-if="detailDrawer.task.error">
              <div class="error-message">
                {{ detailDrawer.task.error }}
              </div>
            </a-descriptions-item>
          </a-descriptions>
        </div>
      </a-spin>
    </a-modal>
  </a-modal>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue';
import { Message, Modal } from '@arco-design/web-vue';
import { IconRefresh, IconEye, IconStop, IconDelete } from '@arco-design/web-vue/es/icon';
import { getDownloadTasks, getDownloadTask, cancelAndDeleteDownloadTask } from '../../api/file';
import { t } from '../../utils/locale';

// 定义组件的 props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  }
});

// 定义组件的 emits
const emit = defineEmits(['update:visible', 'close']);

// 响应式数据
const taskList = ref([]);
const loading = ref(false);
const isMobile = ref(false);

// 定时器引用
const refreshTimer = ref(null);

// 分页配置
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showTotal: true,
  showJumper: true,
  showPageSize: true,
});

// 详情模态框
const detailDrawer = reactive({
  visible: false,
  loading: false,
  task: null
});

// 表格列定义
const columns = [
  {
    title: t.value('downloadTaskId'),
    dataIndex: 'download_id',
    ellipsis: true,
    width: 300
  },
  {
    title: t.value('downloadTaskFileName'),
    dataIndex: 'filename',
    ellipsis: true
  },
  {
    title: t.value('downloadTaskStatus'),
    dataIndex: 'status',
    slotName: 'status',
    width: 120
  },
  {
    title: t.value('downloadTaskProgress'),
    dataIndex: 'progress',
    slotName: 'progress',
    width: 150
  },
  {
    title: t.value('downloadTaskSize'),
    dataIndex: 'size',
    slotName: 'size',
    width: 150
  },
  {
    title: t.value('downloadTaskStartTime'),
    dataIndex: 'created_at',
    render: ({ record }) => record.created_at ? formatDate(record.created_at) : '--',
    width: 180
  },
  {
    title: t.value('downloadTaskActions'),
    slotName: 'actions',
    width: 100
  }
];

// 处理取消事件
const handleCancel = () => {
  emit('update:visible', false);
  emit('close');
};

// 获取任务列表
// 在 fetchTasks 方法中，处理数据前规范化 progress
const fetchTasks = async () => {
  try {
    const response = await getDownloadTasks();
    const data = response.data || [];

    // 归一化 progress：确保是 0-100 的数值
    const normalizedData = data.map(item => {
      let progress = Number(item.progress);
      if (isNaN(progress)) progress = 0;
      // 如果 progress > 100，但小于 1000，可能是误传的整数百分比（如 3500 表示 35%？）
      // 但根据你的数据，正常是 35，所以如果 > 100，很可能是计算错了
      if (progress > 100 && progress <= 10000) {
        // 可能是 3500 想表示 35%，尝试除以 100
        const guess = progress / 100;
        if (guess <= 100) {
          progress = guess;
        }
      } else if (progress > 100) {
        progress = 100; // 强制上限
      }
      return { ...item, progress: Math.max(0, Math.min(100, progress)) };
    });

    taskList.value = normalizedData;
    pagination.total = normalizedData.length;
  } catch (error) {
    console.error('获取下载任务列表失败:', error);
    Message.error(t.value('getDownloadTasksFailed'));
  }
};

// 开始定时刷新
const startAutoRefresh = () => {
  // 先清除已存在的定时器
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value);
  }
  
  // 设置2秒间隔的定时器
  refreshTimer.value = setInterval(() => {
    if (props.visible) {
      fetchTasks();
    }
  }, 2000);
};

// 停止定时刷新
const stopAutoRefresh = () => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value);
    refreshTimer.value = null;
  }
};

// 刷新任务列表
const refreshTasks = () => {
  fetchTasks();
};

// 查看任务详情
const viewTaskDetails = async (record) => {
  try {
    detailDrawer.loading = true;
    detailDrawer.visible = true;
    const response = await getDownloadTask(record.download_id);
    let task = response.data;

    // 同样归一化 progress
    if (task) {
      let progress = Number(task.progress);
      if (isNaN(progress)) progress = 0;
      if (progress > 100 && progress <= 10000) {
        const guess = progress / 100;
        if (guess <= 100) progress = guess;
      } else if (progress > 100) {
        progress = 100;
      }
      task.progress = Math.max(0, Math.min(100, progress));
    }

    detailDrawer.task = task;
  } catch (error) {
    console.error('获取下载任务详情失败:', error);
    Message.error(t.value('getDownloadTaskFailed'));
  } finally {
    detailDrawer.loading = false;
  }
};

// 获取状态颜色
const getStatusColor = (status) => {
  switch (status) {
    case 'starting':
      return '#165DFF';  // blue
    case 'downloading':
      return '#FF7D00';  // orange
    case 'completed':
      return '#00B42A';  // green
    case 'error':
      return '#F53F3F';  // red
    default:
      return '#86909C';  // gray
  }
};

// 获取状态文本
const getStatusText = (status) => {
  switch (status) {
    case 'starting':
      return t.value('downloadTaskStatusStarting');
    case 'downloading':
      return t.value('downloadTaskStatusDownloading');
    case 'completed':
      return t.value('downloadTaskStatusCompleted');
    case 'error':
      return t.value('downloadTaskStatusError');
    default:
      return status;
  }
};

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// 格式化日期
const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleString();
};

// 处理分页变化
const handlePageChange = (current) => {
  pagination.current = current;
};

// 处理页面大小变化
const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize;
  pagination.current = 1;
};

// 取消下载任务并删除记录
const cancelDownload = async (record) => {
  try {
    await cancelAndDeleteDownloadTask(record.download_id);
    Message.success(t.value('downloadTaskCancelledAndDeleted'));
    // 刷新任务列表
    await fetchTasks();
  } catch (error) {
    console.error('取消下载任务并删除记录失败:', error);
    Message.error(t.value('cancelDownloadTaskFailed'));
  }
};

// 删除下载记录（对于已完成、错误或已取消的任务）
const deleteRecord = async (record) => {
  Modal.confirm({
    title: t.value('deleteDownloadTaskRecord'),
    content: t.value('deleteDownloadTaskRecordConfirm'),
    okText: t.value('confirm'),
    cancelText: t.value('cancel'),
    onOk: async () => {
      try {
        await cancelAndDeleteDownloadTask(record.download_id);
        Message.success(t.value ('downloadTaskRecordDeleted'));
        // 刷新任务列表
        await fetchTasks();
      } catch (error) {
        console.error('删除下载记录失败:', error);
        Message.error(t.value('deleteDownloadTaskRecordFailed'));
      }
    }
  });
};

// 检测是否为移动端
const checkIsMobile = () => {
  isMobile.value = window.innerWidth <= 768;
};

// 监听 visible prop 的变化
import { watch } from 'vue';

watch(() => props.visible, (newVal) => {
  if (newVal) {
    fetchTasks();
    checkIsMobile();
    // 启动自动刷新
    startAutoRefresh();
  } else {
    // 停止自动刷新
    stopAutoRefresh();
  }
});

// 组件挂载时检测设备类型
onMounted(() => {
  checkIsMobile();
  window.addEventListener('resize', checkIsMobile);
});

// 组件卸载时移除事件监听器和定时器
onUnmounted(() => {
  window.removeEventListener('resize', checkIsMobile);
  // 确保定时器被清除
  stopAutoRefresh();
});
</script>

<style scoped>
.download-task-list {
  padding: 0;
  height: 100%;
}

.task-list-card {
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  border: 1px solid var(--color-border);
  height: 100%;
}

.card-header {
  display: flex;
  align-items: center;
}

.error-message {
  color: #f53f3f;
  white-space: pre-wrap;
  word-break: break-all;
}

.task-list-actions {
  text-align: right;
}

/* 进度百分比文本样式 */
.progress-text {
  font-size: 12px;
  font-weight: bold;
  margin-top: 4px;
  text-align: center;
}

/* 响应式优化 */
@media (max-width: 768px) {
  .download-task-list {
    padding: 8px;
  }
  
  .task-list-actions {
    margin-bottom: 12px;
  }
  
  /* 移动端表格适配 */
  :deep(.arco-table-container) {
    max-height: calc(100vh - 200px);
  }
  
  :deep(.arco-table-cell),
  :deep(.arco-table-th) {
    padding: 8px 6px !important;
    font-size: 13px;
  }
  
  :deep(.arco-table-tr) {
    min-height: 40px;
  }
}

@media (min-width: 769px) {
  .download-task-list {
    padding: 16px;
  }
  
  /* 桌面端表格适配 */
  :deep(.arco-table-container) {
    max-height: 400px;
  }
}
</style>