<template>
  <div class="ssh-login-logs-container">
    <!-- 搜索和导出区域 -->
    <div class="header-actions">
      <div class="search-controls">
        <a-input
          v-model="searchInfo"
          :placeholder="t('searchIP')"
          allow-clear
          @change="handleSearch"
          class="search-input"
        />
        <a-select
          v-model="filterStatus"
          :placeholder="t('loginStatus')"
          allow-clear
          @change="handleSearch"
          class="status-select"
        >
          <a-option value="success">{{ t('success') }}</a-option>
          <a-option value="failed">{{ t('failed') }}</a-option>
        </a-select>
      </div>
      <div style="display: flex; gap: 10px;">
        <a-button
          type="outline"
          size="small"
          @click="showExportDialog = true"
          :loading="exporting"
          class="export-btn"
        >
          {{ t('exportLog') }}
        </a-button>
        <a-button
          type="outline"
          size="small"
          status="danger"
          @click="showCleanDialog = true"
          :loading="cleaning"
          class="clean-btn"
        >
          {{ t('clearLogs') }}
        </a-button>
      </div>
    </div>

    <!-- 表格区域 -->
    <div class="table-container">
      <a-table
        :columns="columns"
        :data="sshLoginLogs"
        :loading="loading"
        :pagination="pagination"
        @page-change="handlePageChange"
        @page-size-change="handlePageSizeChange"
        :scroll="scroll"
      >
        <template #status="{ record }">
          <a-tag :color="record.status === 'success' ? 'green' : 'red'">
            {{ record.status === 'success' ? t('success') : t('failed') }}
          </a-tag>
        </template>
      </a-table>
    </div>

    <!-- 导出对话框 -->
    <a-modal
      v-model:visible="showExportDialog"
      :title="t('exportLog')"
      :footer="null"
      width="600px"
    >
      <div class="export-dialog-content">
        <div class="form-item">
          <span class="label">{{ t('loginStatus') }}：</span>
          <a-select
            v-model="exportOptions.status"
            class="w-full"
          >
            <a-option value="all">{{ t('all') }}</a-option>
            <a-option value="success">{{ t('success') }}</a-option>
            <a-option value="failed">{{ t('failed') }}</a-option>
          </a-select>
        </div>
        <div class="form-item">
          <span class="label">{{ t('exportFormat') }}：</span>
          <a-select
            v-model="exportOptions.export_format"
            class="w-full"
          >
            <a-option value="csv">CSV</a-option>
            <a-option value="excel">Excel</a-option>
          </a-select>
        </div>
        <div class="dialog-footer">
          <a-button @click="showExportDialog = false">{{ t('cancel') }}</a-button>
          <a-button type="primary" @click="handleExportLogs" :loading="exporting">{{ t('confirm') }}</a-button>
        </div>
      </div>
    </a-modal>
    
    <!-- 清理日志确认对话框 -->
    <a-modal
      v-model:visible="showCleanDialog"
      :title="t('clearLogs')"
      :footer="null"
      width="500px"
    >
      <div class="clean-dialog-content">
        <p>{{ t('clearLogsConfirm') }}</p>
        <div class="dialog-footer">
          <a-button @click="showCleanDialog = false">{{ t('cancel') }}</a-button>
          <a-button type="primary" @click="handleCleanLogs" :loading="cleaning">{{ t('confirm') }}</a-button>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue';
import { t } from '../../utils/locale';
import { getSSHLoginLogs, exportSSHLoginLogs, cleanSSHLoginLogs } from '../../api/host';
import { Message } from '@arco-design/web-vue';

// 响应式数据
const sshLoginLogs = ref([]);
const loading = ref(false);
const exporting = ref(false);
const cleaning = ref(false);
const showCleanDialog = ref(false);
const searchInfo = ref('');
const filterStatus = ref('');

// 导出对话框相关数据
const showExportDialog = ref(false);
const exportOptions = reactive({
  status: 'all',
  export_format: 'csv'
});

// 分页配置
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showTotal: true,
  showJumper: true,
  pageSizeOptions: [10, 20, 50, 100],
  showPageSize: true
});

// 表格滚动配置
const scroll = {
  x: 'max-content',
  y: 600
};

// 表格列定义
const columns = computed(() => [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: t.value('ipAddress'), dataIndex: 'ip', key: 'ip', width: 150 },
  { title: t.value('location'), dataIndex: 'area', key: 'area', width: 180 },
  { title: t.value('port'), dataIndex: 'port', key: 'port', width: 80 },
  { title: t.value('username'), dataIndex: 'user', key: 'user', width: 120 },
  { title: t.value('loginMethod'), dataIndex: 'method', key: 'method', width: 120 },
  { title: t.value('status'), dataIndex: 'status', key: 'status', slotName: 'status', width: 100 },
  { title: t.value('loginTime'), dataIndex: 'timestamp', key: 'timestamp', width: 200 },
]);



// 获取SSH登录日志数据
const fetchSSHLoginLogs = async () => {
  try {
    loading.value = true;
    
    // 计算skip值
    const skip = (pagination.current - 1) * pagination.pageSize;
    
    // 准备请求参数
    const requestParams = {
      skip: skip,
      limit: pagination.pageSize,
      info: searchInfo.value || undefined,
      status: filterStatus.value || undefined
    };
    
    // 移除undefined值
    Object.keys(requestParams).forEach(key => {
      if (requestParams[key] === undefined) {
        delete requestParams[key];
      }
    });
    
    const response = await getSSHLoginLogs(requestParams);
    
    // 处理响应数据
    if (response?.items && Array.isArray(response.items)) {
      sshLoginLogs.value = response.items.map((item, index) => ({
        ...item,
        id: skip + index + 1 // 生成临时ID
      }));
      pagination.total = response.total || 0;
    } else {
      sshLoginLogs.value = [];
      pagination.total = 0;
    }
  } catch (error) {
    console.error('获取SSH登录日志失败:', error);
    Message.error('获取SSH登录日志失败: ' + (error.message || '未知错误'));
    sshLoginLogs.value = [];
    pagination.total = 0;
  } finally {
    loading.value = false;
  }
};

// 搜索处理
const handleSearch = () => {
  pagination.current = 1; // 重置到第一页
  fetchSSHLoginLogs();
};

// 页码改变处理
const handlePageChange = (page) => {
  pagination.current = page;
  fetchSSHLoginLogs();
};

// 每页条数改变处理
const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize;
  pagination.current = 1; // 重置到第一页
  fetchSSHLoginLogs();
};

// 导出日志处理
const handleExportLogs = async () => {
  try {
    exporting.value = true;
    
    // 关闭对话框
    showExportDialog.value = false;
    
    // 准备导出参数 - 使用exportOptions中的值
    const exportParams = {
      status: exportOptions.status,
      export_format: exportOptions.export_format
    };
    
    const response = await exportSSHLoginLogs(exportParams);
    
    // 创建下载链接
    const blob = new Blob([response], { type: 'application/octet-stream' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    
    // 根据导出格式设置文件名
    const fileExtension = exportOptions.export_format === 'excel' ? 'xlsx' : 'csv';
    link.download = `ssh_login_logs_${new Date().toISOString().split('T')[0]}.${fileExtension}`;
    
    document.body.appendChild(link);
    link.click();
    
    // 清理
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    
    Message.success(t('exportLogSuccess'));
  } catch (error) {
    console.error('导出日志失败:', error);
    Message.error(t('exportLogFailed') + (error.message || ''));
  } finally {
    exporting.value = false;
  }
};

// 清理日志处理
const handleCleanLogs = async () => {
  try {
    cleaning.value = true;
    
    // 关闭对话框
    showCleanDialog.value = false;
    
    const response = await cleanSSHLoginLogs();
    
    // 处理响应
    if (response?.success) {
      Message.success(t.value('clearLogsSuccess') + (response.cleaned_count ? `：${response.cleaned_count}strips` : ''));
      // 重新获取日志数据
      fetchSSHLoginLogs();
    } else {
      Message.error(t.value('clearLogsFailed') + (response?.message || ''));
    }
  } catch (error) {
    console.error('清理日志失败:', error);
    Message.error(t.value('clearLogsFailed') + (error.message || ''));
  } finally {
    cleaning.value = false;
  }
};

// 组件挂载时获取数据
onMounted(() => {
  fetchSSHLoginLogs();
});
</script>

<style scoped>
.ssh-login-logs-container {
  padding: 16px;
}

.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 16px;
}

.search-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.search-input {
  width: 300px;
}

.status-select {
  width: 150px;
}

.table-container {
  overflow-x: auto;
  width: 100%;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .header-actions {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-controls {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-input,
  .status-select {
    width: 100%;
  }
  
  
  .export-btn {
  margin-right: 12px;
}
  
  /* 在移动设备上调整表格高度 */
  .table-container {
    height: 400px;
  }
}

/* 导出对话框样式 */
.export-dialog-content {
  padding: 16px 0;
}

.form-item {
  margin-bottom: 20px;
}

.form-item .label {
  display: inline-block;
  margin-bottom: 8px;
  font-weight: 500;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}
</style>
