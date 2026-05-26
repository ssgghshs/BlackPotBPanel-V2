<template>
  <a-card class="logs-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('access') }}</span>
        <!-- 将自动刷新开关放在左侧 -->
        <div class="auto-refresh">
          <a-switch 
            v-model="autoRefreshEnabled"
            @change="handleAutoRefreshChange"
            :checked-text="t('autoRefreshOn')"
            :unchecked-text="t('autoRefreshOff')"
          />
        </div>
        <!-- 将配置按钮、清理按钮、导出按钮和刷新按钮放在右侧 -->
        <div class="header-actions">
          <a-button type="outline" @click="loadLogContent" class="refresh-btn">
            {{ t('refresh') }}
          </a-button>
          <a-button v-if="isAdmin" type="outline" @click="showConfigDrawer" class="config-btn">
            {{ t('configLogPath') }}
          </a-button>
          <!-- 添加导出按钮 -->
          <a-button type="outline" @click="exportLog" class="export-btn">
            {{ t('exportLog') }}
          </a-button>
          <!-- 添加清理按钮 -->
          <a-button v-if="isAdmin" type="outline" status="danger" @click="showClearLogsModal" class="clear-btn">
            {{ t('clearLogs') }}
          </a-button>
        </div>
      </div>
    </template>

    <!-- 日志类型选择和内容显示 -->
    <div class="log-content-section">
      <div class="log-type-selector">
        <span class="log-type-label">{{ t('logType') }}:</span>
        <a-radio-group v-model="selectedLogType" @change="handleLogTypeChange" size="medium">
          <a-radio value="access">{{ t('accessLog') }}</a-radio>
          <a-radio value="error">{{ t('errorLog') }}</a-radio>
        </a-radio-group>
        <!-- 添加表格和文本展示形式切换按钮 -->
        <a-button-group class="display-toggle">
          <a-button 
            :type="displayMode === 'table' ? 'primary' : 'default'" 
            @click="setDisplayMode('table')"
          >
            {{ t('tableMode') }}
          </a-button>
          <a-button 
            :type="displayMode === 'text' ? 'primary' : 'default'" 
            @click="setDisplayMode('text')"
          >
            {{ t('textMode') }}
          </a-button>
        </a-button-group>
      </div>

      <!-- 日志内容显示区域 -->
      <div class="content-area">
        <!-- 文本模式显示 -->
        <a-card v-if="logContent.length > 0 && displayMode === 'text'" class="log-content-card">
          <pre ref="logContentRef" class="log-content">{{ formatLogContent(logContent) }}</pre>
        </a-card>
        
        <!-- 表格模式显示 -->
        <a-card v-else-if="logContent.length > 0 && displayMode === 'table'" class="log-content-card">
          <a-table 
            :data="parsedLogData" 
            :columns="getCurrentTableColumns" 
            :pagination="false" 
            :scroll="{ y: tableHeight }"
            class="log-table"
          />
        </a-card>
        
        <a-empty v-else>
          <template #description>
            <span>{{ t('nodata') }}</span>
          </template>
        </a-empty>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="loading-container">
        <a-spin :size="32" />
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

    <!-- 配置抽屉 -->
    <a-drawer
      :visible="configDrawerVisible"
      :title="t('logPathConfig')"
      placement="right"
      :width="700"
      @ok="saveConfig"
      @cancel="closeConfigDrawer"
      unmountOnClose
    >
      <a-form
        :model="configFormState"
        :label-col="{ span: 6 }"
        :wrapper-col="{ span: 18 }"
      >
        <a-form-item :label="t('accessLogPath')" required>
          <a-input 
            v-model="configFormState.access_log_path" 
            :placeholder="t('enterAccessLogPath')" 
          />
        </a-form-item>
        <a-form-item :label="t('errorLogPath')" required>
          <a-input 
            v-model="configFormState.error_log_path" 
            :placeholder="t('enterErrorLogPath')" 
          />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-button @click="closeConfigDrawer">{{ t('cancel') }}</a-button>
        <a-button type="primary" @click="saveConfig">{{ t('save') }}</a-button>
      </template>
    </a-drawer>
  </a-card>
</template>

<script setup>
import { reactive, ref, onMounted, onUnmounted, nextTick, computed } from 'vue';
import { Message, Modal } from '@arco-design/web-vue';
import { t } from '../../utils/locale';
import { isAdmin } from '../../stores/user';
import {
  getLatestAccessLogConfig,
  createAccessLogConfig,
  getAccessLogContent,
  exportAccessLog,
  clearAccessLog
} from '../../api/log';

// 从store中获取用户角色信息

// 抽屉可见性
const configDrawerVisible = ref(false);

// 自动刷新相关
const autoRefreshEnabled = ref(true);
const autoRefreshInterval = ref(null);
const AUTO_REFRESH_INTERVAL_MS = 5000; // 5秒自动刷新一次
const logContentRef = ref(null); // 用于滚动到底部

const configFormState = reactive({
  access_log_path: '',
  error_log_path: ''
});

const selectedLogType = ref('access');
const logContent = ref([]);
const loading = ref(false);
const displayMode = ref('text'); // 添加展示模式，默认为文本模式
const clearLogsModalVisible = ref(false); // 清理日志确认对话框可见性

// 计算表格高度，根据屏幕尺寸动态调整
const tableHeight = computed(() => {
  const screenWidth = window.innerWidth;
  const screenHeight = window.innerHeight;
  
  // 在小屏幕设备上使用较小的高度
  if (screenWidth <= 480) {
    return 300;
  } 
  // 在中等屏幕设备上使用中等高度
  else if (screenWidth <= 768) {
    return 350;
  } 
  // 在大屏幕设备上使用较大高度
  else {
    // 根据屏幕高度动态计算，但不超过600px
    const calculatedHeight = Math.min(screenHeight - 300, 600);
    return Math.max(calculatedHeight, 400);
  }
});

// 格式化日志内容显示
const formatLogContent = (content) => {
  if (!content || content.length === 0) {
    return '';
  }
  
  // 如果content是数组，将其连接成字符串
  if (Array.isArray(content)) {
    return content.join('\n');
  }
  
  // 如果content是字符串，直接返回
  if (typeof content === 'string') {
    return content;
  }
  
  // 其他情况转换为字符串
  return String(content);
};

// 加载日志内容
const loadLogContent = async () => {
  try {
    loading.value = true;
    
    // 调用API获取日志内容
    const response = await getAccessLogContent({
      log_type: selectedLogType.value
    });
    
    // 处理响应数据
    if (response && Array.isArray(response.content)) {
      logContent.value = response.content;
    } else if (response && typeof response === 'object' && Array.isArray(response.data)) {
      logContent.value = response.data;
    } else {
      logContent.value = [];
    }
    
    // 在DOM更新后滚动到底部
    await nextTick();
    scrollToBottom();
  } catch (error) {
    console.error('获取日志内容失败:', error);
    Message.error(t.value('getLogContentFailed') + ': ' + (error.message || t.value('unknownError')));
    logContent.value = [];
  } finally {
    loading.value = false;
  }
};

// 表格列定义 - 访问日志
const accessLogTableColumns = ref([
  {
    title: t.value('logIP'),
    dataIndex: 'ip',
    width: 150,
  },
  {
    title: t.value('logDateTime'),
    dataIndex: 'datetime',
    width: 200,
  },
  {
    title: t.value('logMethod'),
    dataIndex: 'method',
    width: 100,
  },
  {
    title: t.value('logURL'),
    dataIndex: 'url',
    width: 300,
  },
  {
    title: t.value('logStatus'),
    dataIndex: 'status',
    width: 100,
  },
  {
    title: t.value('logSize'),
    dataIndex: 'size',
    width: 100,
  },
  {
    title: t.value('logReferer'),
    dataIndex: 'referer',
    width: 200,
  },
  {
    title: t.value('logUserAgent'),
    dataIndex: 'userAgent',
    width: 300,
  }
]);

// 表格列定义 - 错误日志
const errorLogTableColumns = ref([
  {
    title: t.value('logDateTime'),
    dataIndex: 'datetime',
    width: 180,
  },
  {
    title: t.value('logLevel'),
    dataIndex: 'level',
    width: 100,
  },
  {
    title: t.value('logPID'),
    dataIndex: 'pid',
    width: 100,
  },
  {
    title: t.value('logMessage'),
    dataIndex: 'message',
    width: 500,
  },
  {
    title: t.value('logClient'),
    dataIndex: 'client',
    width: 150,
  },
  {
    title: t.value('logServer'),
    dataIndex: 'server',
    width: 200,
  },
  {
    title: t.value('logRequest'),
    dataIndex: 'request',
    width: 300,
  },
  {
    title: t.value('logUpstream'),
    dataIndex: 'upstream',
    width: 200,
  },
  {
    title: t.value('logHost'),
    dataIndex: 'host',
    width: 150,
  },
  {
    title: t.value('logReferer'),
    dataIndex: 'referer',
    width: 200,
  }
]);

// 根据日志类型获取表格列定义
const getCurrentTableColumns = computed(() => {
  if (selectedLogType.value === 'access') {
    return accessLogTableColumns.value;
  } else {
    return errorLogTableColumns.value;
  }
});

// 解析后的日志数据
const parsedLogData = computed(() => {
  if (displayMode.value !== 'table' || !logContent.value || logContent.value.length === 0) {
    return [];
  }
  
  // 根据日志类型使用不同的解析逻辑
  if (selectedLogType.value === 'access') {
    // 解析访问日志
    return logContent.value.map(line => {
      // 解析Nginx访问日志格式
      // 示例: 110.185.255.177 - - [16/Oct/2025:18:09:50 +0800] "GET /demo/v1/api/docker/containers HTTP/1.1" 200 137 "https://demo.blackpotbp.cn/security/docker/containers" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0" "-"
      const regex = /^(\S+) \S+ \S+ \[([^\]]+)\] "(\S+) ([^"]+)" (\d+) (\d+|-) "(.*?)" "(.*?)" "(.*?)"$/;
      const match = line.match(regex);
      
      if (match) {
        return {
          ip: match[1],
          datetime: match[2],
          method: match[3],
          url: match[4],
          status: match[5],
          size: match[6],
          referer: match[7],
          userAgent: match[8]
        };
      }
      
      // 如果不匹配，则将整行作为url显示
      return {
        ip: '',
        datetime: '',
        method: '',
        url: line,
        status: '',
        size: '',
        referer: '',
        userAgent: ''
      };
    });
  } else {
    // 解析错误日志
    return logContent.value.map(line => {
      // 解析Nginx错误日志格式
      // 示例: 2025/10/16 17:53:00 [error] 544522#0: *35318 connect() failed (111: Connection refused) while connecting to upstream, client: 110.185.255.177, server: demo.blackpotbp.cn, request: "GET /demo/v1/api/user/profile HTTP/1.1", upstream: "http://[::1]:5000/user/profile", host: "demo.blackpotbp.cn", referrer: "https://demo.blackpotbp.cn/logs/attack"
      const regex = /^(\d{4}\/\d{2}\/\d{2} \d{2}:\d{2}:\d{2}) \[(\w+)\] (\d+)#.*?: \*?\d* (.+?), client: ([^,]+), server: ([^,]+), request: "(.*?)", upstream: "(.*?)", host: "(.*?)", referrer: "(.*?)"$/;
      const match = line.match(regex);
      
      if (match) {
        return {
          datetime: match[1],
          level: match[2],
          pid: match[3],
          message: match[4],
          client: match[5].trim(),
          server: match[6].trim(),
          request: match[7],
          upstream: match[8],
          host: match[9],
          referer: match[10]
        };
      }
      
      // 如果不匹配，则将整行作为message显示
      return {
        datetime: '',
        level: '',
        pid: '',
        message: line,
        client: '',
        server: '',
        request: '',
        upstream: '',
        host: '',
        referer: ''
      };
    });
  }
});

// 设置展示模式
const setDisplayMode = (mode) => {
  displayMode.value = mode;
};

// 显示清理日志确认对话框
const showClearLogsModal = () => {
  clearLogsModalVisible.value = true;
};

// 取消清理日志
const cancelClearLogs = () => {
  clearLogsModalVisible.value = false;
};

// 处理清理日志
const handleClearLogs = async () => {
  try {
    // 发起清理请求
    await clearAccessLog(selectedLogType.value);
    
    // 关闭对话框
    clearLogsModalVisible.value = false;
    
    // 重新加载日志内容
    await loadLogContent();
    
    Message.success(t.value('clearLogsSuccess'));
  } catch (error) {
    console.error('清理日志文件失败:', error);
    Message.error(t.value('clearLogsFailed'));
    
    // 关闭对话框
    clearLogsModalVisible.value = false;
  }
};

// 显示配置抽屉
const showConfigDrawer = () => {
  configDrawerVisible.value = true;
};

// 关闭配置抽屉
const closeConfigDrawer = () => {
  configDrawerVisible.value = false;
};

// 保存配置
const saveConfig = async () => {
  try {
    const data = {
      access_log_path: configFormState.access_log_path,
      error_log_path: configFormState.error_log_path
    };
    
    const response = await createAccessLogConfig(data);
    
    // 使用前端的国际化消息，不直接使用后端返回的消息
    let message = t.value('configSavedNoRestart');
    if (response && typeof response === 'object') {
      // 可以根据需要添加其他逻辑，但始终使用前端的国际化消息
      message = t.value('configSavedNoRestart');
    }
    
    Message.success(message);
    
    closeConfigDrawer();
    
    // 保存配置后重新加载日志内容
    await loadLogContent();
  } catch (error) {
    console.error('保存配置失败:', error);
    Message.error(t.value('saveConfigFailed'));
  }
};

// 处理日志类型变化
const handleLogTypeChange = () => {
  // 日志类型变化时重新加载内容
  loadLogContent();
};

// 处理自动刷新开关变化
const handleAutoRefreshChange = () => {
  if (autoRefreshEnabled.value) {
    startAutoRefresh();
  } else {
    stopAutoRefresh();
  }
};

// 启动自动刷新
const startAutoRefresh = () => {
  // 先清除已存在的定时器
  if (autoRefreshInterval.value) {
    clearInterval(autoRefreshInterval.value);
  }
  
  // 设置新的定时器
  autoRefreshInterval.value = setInterval(() => {
    if (!loading.value) {
      loadLogContent();
    }
  }, AUTO_REFRESH_INTERVAL_MS);
};

// 停止自动刷新
const stopAutoRefresh = () => {
  if (autoRefreshInterval.value) {
    clearInterval(autoRefreshInterval.value);
    autoRefreshInterval.value = null;
  }
};

// 滚动到底部
const scrollToBottom = () => {
  if (logContentRef.value) {
    logContentRef.value.scrollTop = logContentRef.value.scrollHeight;
  }
};

// 导出日志文件
const exportLog = async () => {
  try {
    // 发起导出请求
    const response = await exportAccessLog(selectedLogType.value);
    
    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${selectedLogType.value}.log`);
    document.body.appendChild(link);
    link.click();
    
    // 清理
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    
    Message.success(t.value('exportLogFileSuccess'));
  } catch (error) {
    console.error('导出日志文件失败:', error);
    Message.error(t.value('exportLogFileFailed'));
  }
};

// 组件挂载时加载配置和日志内容
onMounted(async () => {
  try {
    // 加载最新的配置
    if (isAdmin.value) {
      const response = await getLatestAccessLogConfig();
      
      // 修复：正确处理响应数据结构
      if (response && typeof response === 'object' && !response.hasOwnProperty('data')) {
        // 直接使用响应对象
        configFormState.access_log_path = response.access_log_path || '';
        configFormState.error_log_path = response.error_log_path || '';
      } else if (response?.data) {
        // 如果响应有data属性，则使用response.data
        configFormState.access_log_path = response.data.access_log_path || '';
        configFormState.error_log_path = response.data.error_log_path || '';
      }
    }
    
    // 加载默认的日志内容
    await loadLogContent();
    
    // 如果自动刷新启用，则启动定时器
    if (autoRefreshEnabled.value) {
      startAutoRefresh();
    }
    
    // 添加窗口大小变化监听器
    window.addEventListener('resize', handleWindowResize);
  } catch (error) {
    console.error('初始化失败:', error);
    Message.error(t.value('initFailed'));
  }
});

// 组件卸载时清除定时器和事件监听器
onUnmounted(() => {
  stopAutoRefresh();
  window.removeEventListener('resize', handleWindowResize);
});

// 处理窗口大小变化
const handleWindowResize = () => {
  // 触发重新计算表格高度
  // Vue 3的响应式系统会自动更新依赖tableHeight的地方
};
</script>


<style scoped>
.logs-container {
  padding: 20px;
  overflow-x: hidden; /* 隐藏水平滚动条 */
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 15px;
  font-size: 1.3em;
  padding: 20px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  flex-wrap: wrap; /* 允许换行 */
}

.title {
  margin: 0;
  padding: 0;
  white-space: nowrap;
}

/* 自动刷新开关样式 */
.auto-refresh {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-right: auto; /* 将开关推到左侧 */
}

/* 表单和清理按钮在标题行的样式 */
.header-actions {
  display: flex;
  align-items: center;
  gap: 10px; /* 减小间距 */
  flex-shrink: 0; /* 防止压缩 */
}

.log-content-section {
  margin-top: 20px;
}

.log-type-selector {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.log-type-label {
  font-weight: 500;
  color: #333;
}

.display-toggle {
  margin-left: 10px;
}

.content-area {
  margin-top: 20px;
}

.log-content-card {
  margin-top: 20px;
}

.log-content {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.4;
  margin: 0;
  padding: 15px;
  background-color: #000000; /* 黑色背景 */
  color: #ffffff; /* 白色字体 */
  border-radius: 4px;
  max-height: 600px;
  overflow-y: auto;
}

.log-table {
  font-size: 12px;
}

/* 移除了固定的背景色设置，让表头跟随主题色变化 */
.log-table :deep(.arco-table-th) {
  font-weight: 500;
}

/* 响应式设计 - 中等屏幕 */
@media (max-width: 768px) {
  .logs-container {
    padding: 10px;
  }
  
  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
    padding: 15px;
  }
  
  .auto-refresh {
    margin-right: 0;
  }
  
  .header-actions {
    width: 100%;
    justify-content: space-between;
  }
  
  :deep(.arco-button) {
    font-size: 12px;
    padding: 0 12px;
  }
  
  .log-content {
    font-size: 11px;
    padding: 10px;
    max-height: 400px;
  }
  
  .log-type-selector {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .display-toggle {
    margin-left: 0;
    margin-top: 10px;
  }
}

/* 响应式设计 - 小屏幕 */
@media (max-width: 480px) {
  .card-header {
    gap: 8px;
    padding: 12px;
  }
  
  .header-actions {
    gap: 8px;
    width: 100%;
  }
  
  :deep(.arco-button) {
    font-size: 11px;
    padding: 0 10px;
  }
  
  .title {
    font-size: 1.1em;
  }
  
  .log-content {
    font-size: 10px;
    padding: 8px;
    max-height: 300px;
  }
  
  .log-table :deep(.arco-table-th),
  .log-table :deep(.arco-table-td) {
    padding: 8px 4px;
    font-size: 10px;
  }
}
</style>

<!-- 使用非scoped样式确保在所有主题下保持一致 -->
<style>
/* 确保卡片容器在所有主题下保持白色背景 */
.logs-container :deep(.arco-card) {
  background: #ffffff !important;
  border: 1px solid #ebebeb !important;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
}

/* 确保表单标签在所有主题下保持黑色文字 */
.logs-container :deep(.arco-form-item-label) {
  color: #333 !important;
}

/* 确保按钮在所有主题下保持一致 */
.logs-container :deep(.arco-btn) {
  background-color: #ffffff !important;
  border-color: #ebebeb !important;
  color: #333 !important;
}

.logs-container :deep(.arco-btn:hover) {
  background-color: #ffffff !important;
  border-color: #cccccc !important;
}

.logs-container :deep(.arco-btn:focus) {
  background-color: #ffffff !important;
  border-color: #3c7eff !important;
  box-shadow: 0 0 0 2px rgba(64, 132, 255, 0.2) !important;
}

.logs-container :deep(.arco-btn-primary) {
  background-color: #1890ff !important;
  border-color: #1890ff !important;
  color: #ffffff !important;
}

.logs-container :deep(.arco-btn-primary:hover) {
  background-color: #40a9ff !important;
  border-color: #40a9ff !important;
}

.logs-container :deep(.arco-btn-primary:focus) {
  background-color: #1890ff !important;
  border-color: #1890ff !important;
  box-shadow: 0 0 0 2px rgba(64, 132, 255, 0.2) !important;
}

/* 确保开关在所有主题下保持一致 */
.logs-container :deep(.arco-switch) {
  background-color: #ffffff !important;
  border: 1px solid #ebebeb !important;
}

.logs-container :deep(.arco-switch-checked) {
  background-color: #1890ff !important;
  border-color: #1890ff !important;
}

.logs-container :deep(.arco-switch:hover) {
  background-color: #ffffff !important;
  border-color: #cccccc !important;
}

.logs-container :deep(.arco-switch-checked:hover) {
  background-color: #40a9ff !important;
  border-color: #40a9ff !important;
}

/* 表格样式适配 */
.logs-container :deep(.arco-table-th) {
  background-color: var(--color-fill-2) !important;
  font-weight: 500;
}

.logs-container :deep(.arco-table-td) {
  background-color: var(--color-bg-2) !important;
}

/* 移动端全局样式适配 */
@media (max-width: 768px) {
  .logs-container :deep(.arco-card) {
    box-shadow: none !important;
  }
  
  .logs-container :deep(.arco-form-item-label) {
    font-size: 12px;
  }
  
  .logs-container :deep(.arco-btn) {
    font-size: 12px;
  }
}

@media (max-width: 480px) {
  .logs-container :deep(.arco-card) {
    border: none !important;
    border-radius: 0 !important;
  }
  
  .logs-container :deep(.arco-form-item-label) {
    font-size: 11px;
  }
  
  .logs-container :deep(.arco-btn) {
    font-size: 11px;
  }
}
</style>

