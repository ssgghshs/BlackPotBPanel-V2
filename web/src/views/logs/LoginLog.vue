<template>
  <a-card class="logs-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('loginLogs') }}</span>
        <div class="header-actions">
          <div class="action-controls">
            <!-- 只有管理员才显示用户选择器 -->
            <a-select 
              v-if="isAdmin && !isCardView"
              v-model="selectedUserId" 
              :placeholder="t('selectUser')" 
              @change="handleUserChange"
              class="user-select"
              allow-clear
            >
              <a-option 
                v-for="user in users" 
                :key="user.id" 
                :value="user.id"
              >
                {{ user.username }}
              </a-option>
            </a-select>
            <!-- 导出日志按钮 -->
            <a-button
              type="outline"
              size="small"
              @click="handleExportLogs"
              :loading="exporting"
              class="export-btn"
              >
              {{ t('exportLogFile') }}
            </a-button>
            <!-- 只有管理员才显示清理日志按钮 -->
            <a-button 
              v-if="isAdmin" 
              type="outline"
              status="danger"
              size="small"
              @click="showClearLogsModal" 
              :loading="clearing"
            >
              {{ t('clearLoginLogs') }}
            </a-button>
          </div>
        </div>
      </div>
    </template>

    <!-- 内容区域 -->
    <div class="content-area">
      <!-- 卡片视图：极小屏使用 -->
      <div v-if="isCardView" class="log-cards">
        <div v-for="log in loginLogs" :key="log.id" class="log-card">
          <p><strong>{{ idText }}:</strong> {{ log.id }}</p>
          <p><strong>{{ usernameText }}:</strong> {{ log.username || t('unknown') }}</p>
          <p><strong>{{ statusText }}:</strong> 
            <a-tag :color="log.status === 'success' ? 'green' : 'red'">
              {{ log.status === 'success' ? successText : failedText }}
            </a-tag>
          </p>
          <p><strong>{{ loginTimeText }}:</strong> {{ formatDate(log.login_time) }}</p>
          <p><strong>{{ ipAddressText }}:</strong> 
            <span v-if="log.ip_address">{{ log.ip_address }}</span>
            <span v-else>{{ t('unknown') }}</span>
          </p>
          <p><strong>{{ locationText }}:</strong> 
            <span v-if="log.location">{{ log.location }}</span>
            <span v-else>{{ t('unknown') }}</span>
          </p>
          <p v-if="log.user_agent" style="font-size:12px;color:#666;">
            <strong>{{ userAgentText }}:</strong> 
            <span @click="toggleExpand(log.id)" style="cursor:pointer;">
              {{ expandedUA[log.id] ? log.user_agent : truncateText(log.user_agent, 30) }}
            </span>
          </p>
        </div>
      </div>

      <!-- 表格视图：非极小屏使用 -->
      <div v-else class="table-container">
        <a-table 
          :columns="columns" 
          :data="loginLogs" 
          :loading="loading" 
          :pagination="pagination" 
          @page-change="handlePageChange"
          @page-size-change="handlePageSizeChange"
          :scroll="{ x: 'max-content' }"
        >
          <template #status="{ record }">
            <a-tag :color="record.status === 'success' ? 'green' : 'red'">
              {{ record.status === 'success' ? successText : failedText }}
            </a-tag>
          </template>
          <template #login_time="{ record }">
            {{ formatDate(record.login_time) }}
          </template>
          <template #ip_address="{ record }">
            <span v-if="record.ip_address">{{ record.ip_address }}</span>
            <span v-else>{{ t('unknown') }}</span>
          </template>
          <template #location="{ record }">
            <span v-if="record.location">{{ record.location }}</span>
            <span v-else>{{ t('unknown') }}</span>
          </template>
          <template #user_agent="{ record }">
            <div @click="toggleExpand(record.id)" style="cursor:pointer;">
              {{ expandedUA[record.id] ? record.user_agent : truncateText(record.user_agent, 40) }}
            </div>
          </template>
        </a-table>
      </div>
    </div>
    
    <!-- 清理日志确认对话框 -->
    <a-modal 
      v-model:visible="clearLogsModalVisible" 
      :title="t('clearLoginLogsConfirmTitle')" 
      @ok="handleClearLogs" 
      @cancel="cancelClearLogs"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
    >
      <p>{{ t('clearLoginLogsConfirmMessage') }}</p>
    </a-modal>
  </a-card> 
</template>

<script setup>
import { reactive, ref, onMounted, onUnmounted, computed, watch } from 'vue';
import { t } from '../../utils/locale';
import {getLoginLogs, getUserLoginLogs, clearLoginLogs, exportLoginLogs} from '../../api/log';
import { getUserList } from '../../api/user';
import { Message } from '@arco-design/web-vue';
import { isAdmin } from '../../stores/user';

// 响应式数据
const loginLogs = ref([]);
const loading = ref(false);
const clearing = ref(false);
const clearLogsModalVisible = ref(false);
const users = ref([]);
const selectedUserId = ref(undefined);
const exporting = ref(false);

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showTotal: true,
  showJumper: true,
  pageSizeOptions: [10, 20, 50, 100],
  showPageSize: true
});

// userAgent 展开状态
const expandedUA = ref({});

// 当前视图模式判断
const windowWidth = ref(window.innerWidth);
const isCardView = computed(() => windowWidth.value <= 480);

// 国际化文本（避免频繁调用 t.value）
const idText = t.value('id');
const usernameText = t.value('username');
const ipAddressText = t.value('ipAddress');
const userAgentText = t.value('userAgent');
const statusText = t.value('status');
const loginTimeText = t.value('loginTime');
const locationText = t.value('location'); // 添加地理位置文本
const successText = t.value('loginSuccess');
const failedText = t.value('loginFailed');

// 动态列定义（根据屏幕宽度）
const columns = computed(() => {
  const width = windowWidth.value;

  const allColumns = [
    { title: idText, dataIndex: 'id', width: 80 },
    { title: usernameText, dataIndex: 'username' },
    { title: ipAddressText, dataIndex: 'ip_address', slotName: 'ip_address' },
    { title: locationText, dataIndex: 'location', slotName: 'location' }, // 添加地理位置列
    { title: userAgentText, dataIndex: 'user_agent', slotName: 'user_agent' },
    { title: statusText, dataIndex: 'status', slotName: 'status', width: 120 },
    { title: loginTimeText, dataIndex: 'login_time', slotName: 'login_time', width: 200 }
  ];

  if (width <= 480) return []; // 卡片模式下表格不显示
  if (width <= 768) return allColumns.filter(col => col.dataIndex !== 'user_agent');
  return allColumns;
});

// 工具函数
const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });
};

const truncateText = (text, len) => {
  if (!text) return t.value('unknown');
  return text.length <= len ? text : text.slice(0, len) + '...';
};

const toggleExpand = (id) => {
  expandedUA.value[id] = !expandedUA.value[id];
};

// 获取用户列表
const fetchUsers = async () => {
  if (!isAdmin) return;

  try {
    const response = await getUserList();
    users.value = Array.isArray(response) ? response : (response.data || []);
  } catch (error) {
    console.error('获取用户列表失败:', error);
  }
};

// 获取登录日志
const fetchLoginLogs = async (page = 1) => {
  try {
    loading.value = true;
    let response;

    if (selectedUserId.value && isAdmin) {
      response = await getUserLoginLogs(selectedUserId.value, {
        page: page,
        size: pagination.pageSize
      });
    } else {
      response = await getLoginLogs({
        page: page,
        size: pagination.pageSize
      });
    }

    // 统一解析响应
    if (Array.isArray(response)) {
      loginLogs.value = response;
      pagination.total = response.length;
    } else if (response?.items && Array.isArray(response.items)) {
      loginLogs.value = response.items;
      pagination.total = response.total || response.items.length;
    } else if (response?.data && Array.isArray(response.data)) {
      loginLogs.value = response.data;
      pagination.total = response.total || response.data.length;
    } else if (response?.data?.items && Array.isArray(response.data.items)) {
      loginLogs.value = response.data.items;
      pagination.total = response.data.total || response.data.items.length;
    } else {
      loginLogs.value = [];
      pagination.total = 0;
    }
  } catch (error) {
    console.error('获取登录日志失败:', error);
    Message.error(t.value('getLoginLogsFailed'));
    loginLogs.value = [];
    pagination.total = 0;
  } finally {
    loading.value = false;
  }
};

// 导出登录日志
const handleExportLogs = async () => {
  try {
    exporting.value = true;
    const response = await exportLoginLogs({
      skip: 0,
      limit: pagination.total // 导出所有日志
    });

    // 创建下载链接
    const blob = new Blob([response], { type: 'application/octet-stream' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'login_logs_export.csv';
    document.body.appendChild(link);
    link.click();

    // 清理
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);

    Message.success(t.value('exportLogsSuccess'));
  } catch (error) {
    console.error('导出日志失败:', error);
    Message.error(`${t.value('exportLogFileFailed')}: ${error.message || t.value('unknownError')}`);
  } finally {
    exporting.value = false;
  }
};


// 事件处理
const handleUserChange = () => {
  pagination.current = 1;
  fetchLoginLogs(1);
};

// 页码改变处理
const handlePageChange = (page) => {
  pagination.current = page;
  fetchLoginLogs(page);
};

// 每页条数改变处理
const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize;
  pagination.current = 1; // 重置到第一页
  fetchLoginLogs(1);
};

const showClearLogsModal = () => {
  clearLogsModalVisible.value = true;
};

const cancelClearLogs = () => {
  clearLogsModalVisible.value = false;
};

const handleClearLogs = async () => {
  try {
    clearing.value = true;
    await clearLoginLogs();
    Message.success(t.value('clearLogsSuccess'));
    await fetchLoginLogs();
  } catch (error) {
    console.error('清理日志失败:', error);
    Message.error(t.value('clearLogsFailed'));
  } finally {
    clearing.value = false;
    clearLogsModalVisible.value = false;
  }
};

// 监听窗口大小变化
const handleResize = () => {
  windowWidth.value = window.innerWidth;
};

onMounted(() => {
  window.addEventListener('resize', handleResize);
  fetchLoginLogs();
  if (isAdmin) fetchUsers();
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
.logs-container {
  padding: 20px;
}

.content-area {
  margin-top: 16px;
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
}

.header-actions {
  display: flex;
  align-items: center;
}

.action-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-select {
  min-width: 120px;
  width: 150px;
}

/* 表格容器支持横向滚动 */
.table-container {
  overflow-x: auto;
  width: 100%;
}

/* 卡片视图样式 */
.log-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.log-card {
  padding: 12px;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  background-color: #fafafa;
  font-size: 14px;
}

.log-card p {
  margin: 4px 0;
  word-break: break-word;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .logs-container {
    padding: 15px;
  }
  
  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
    font-size: 1.2em;
    padding: 15px;
  }
  
  .action-controls {
    width: 100%;
    justify-content: flex-end;
  }
  
  .user-select {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .card-header {
    font-size: 1.1em;
    padding: 12px;
  }

  :deep(.arco-table-cell),
  :deep(.arco-table-th) {
    padding: 6px 4px !important;
    font-size: 13px;
  }

  :deep(.arco-table-tr) {
    min-height: 36px;
  }

  .clear-btn {
    font-size: 13px;
    height: 32px;
    padding: 0 8px;
  }
}


</style>