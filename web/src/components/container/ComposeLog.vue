<template>
  <a-drawer
    :width="isMobile ? '90%' : 1400"
    :visible="visible"
    :footer="false"
    @cancel="handleClose"
    unmountOnClose
  >
    <template #title>
      {{ t('composeLog') }} - {{ composeInfo.name }}
    </template>
    
    <div class="log-container">
      <!-- 固定的日志背景框 -->
      <div ref="logContainerRef" class="log-element">
        <div v-if="displayLogs.length > 0" class="log-content">
          <div v-for="(log, index) in displayLogs" :key="index" class="log-line">
            <span v-if="showTimestamps" class="log-timestamp">[{{ formatTimestamp(log.timestamp) }}] </span>
            <span v-if="showServiceName && log.service_name" class="log-service">{{ log.service_name }}: </span>
            <span>{{ log.text }}</span>
          </div>
        </div>
        <div v-else-if="!loading" class="no-logs">
          {{ t('noLogsAvailable') }}
        </div>
      </div>
      
      <!-- 加载状态 -->
      <div v-if="loading" class="log-overlay">
        <div class="status-info">
          <a-spin />
          <span>{{ t('loadingLogs') }}...</span>
        </div>
      </div>
      
      <!-- 错误状态 -->
      <div v-else-if="error" class="log-overlay">
        <div class="status-info">
          <a-alert type="error" :title="t('loadLogFailed')">
            {{ errorMessage || t('unknownError') }}
          </a-alert>
          <div class="action-buttons">
            <a-button type="primary" @click="loadLogs">
              {{ t('retry') }}
            </a-button>
          </div>
        </div>
      </div>
      
      <!-- 工具栏始终显示 -->
      <div class="log-toolbar">
        <a-button 
          type="primary" 
          size="small" 
          @click="loadLogs"
          :disabled="loading"
        >
          {{ t('refresh') }}
        </a-button>
        <a-button 
          type="outline" 
          size="small" 
          @click="clearLogs"
        >
          {{ t('clear') }}
        </a-button>
        <a-button 
          type="outline" 
          size="small" 
          @click="autoScroll = !autoScroll"
        >
          {{ autoScroll ? t('disableAutoScroll') : t('enableAutoScroll') }}
        </a-button>
        <a-button 
          type="outline" 
          size="small" 
          @click="showTimestamps = !showTimestamps"
        >
          {{ showTimestamps ? t('hideTimestamps') : t('showTimestamps') }}
        </a-button>
        <a-button 
          type="outline" 
          size="small" 
          @click="showServiceName = !showServiceName"
        >
          {{ showServiceName ? t('hideServiceName') : t('showServiceName') }}
        </a-button>
        <a-select 
          v-model="logLimit" 
          size="small" 
          style="width: 120px;"
          @change="loadLogs"
        >
          <a-option :value="100">100 {{ t('lines') }}</a-option>
          <a-option :value="500">500 {{ t('lines') }}</a-option>
          <a-option :value="1000">1000 {{ t('lines') }}</a-option>
        </a-select>
      </div>
    </div>
  </a-drawer>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue';
import { t } from '../../utils/locale';
import { Message } from '@arco-design/web-vue';
import { getComposeProjectLogs } from '../../api/container';
import { Select as ASelect, Option as AOption, Spin as ASpin, Alert as AAlert, Button as AButton } from '@arco-design/web-vue';

// Props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  composeInfo: {
    type: Object,
    default: () => ({})
  },
  hostId: {
    type: String,
    default: ''
  }
});

// Emits
const emit = defineEmits(['update:visible', 'close']);

// 响应式数据
const isMobile = ref(false);
const logData = ref({ logs: [] });
const displayLogs = ref([]);
const loading = ref(false);
const error = ref(false);
const errorMessage = ref('');
const logContainerRef = ref(null);
const autoScroll = ref(true);
const logLimit = ref(100);
const selectedService = ref('all');
const showTimestamps = ref(true);
const showServiceName = ref(true);
const refreshInterval = ref(null);

// 移动端检测
const checkIsMobile = () => {
  isMobile.value = window.innerWidth <= 768;
};

// 处理日志数据，将每个服务的日志字符串拆分为行
const processLogData = () => {
  const result = [];
  
  if (!logData.value.logs || !Array.isArray(logData.value.logs)) {
    return result;
  }
  
  logData.value.logs.forEach(logEntry => {
    if (selectedService.value !== 'all' && logEntry.service_name !== selectedService.value) {
      return;
    }
    
    if (logEntry.logs) {
      const logLines = logEntry.logs.split('\n');
      logLines.forEach(line => {
        if (line.trim()) {
          result.push({
            text: line,
            timestamp: logEntry.timestamp || new Date().toISOString(),
            service_name: logEntry.service_name
          });
        }
      });
    }
  });
  
  return result;
};

// 监听日志数据变化，更新显示的日志
watch([logData, selectedService], () => {
  displayLogs.value = processLogData();
  nextTick(() => {
    scrollToBottom();
  });
}, { deep: true });

// 加载日志（使用实际API调用）
const loadLogs = async () => {
  if (!props.composeInfo.name || !props.hostId) return;
  
  try {
    loading.value = true;
    error.value = false;
    errorMessage.value = '';
    
    // 使用实际API调用获取Compose项目日志
    const params = {
      tail: logLimit.value
    };
    
    const response = await getComposeProjectLogs(props.hostId, props.composeInfo.name, params);
    
    // 根据返回的数据格式处理日志
    if (response && response.logs) {
      logData.value = response;
    } else {
      logData.value = { logs: [] };
    }
    
    // 自动滚动到底部
    nextTick(() => {
      scrollToBottom();
    });
    
  } catch (err) {
    console.error('加载Compose项目日志失败:', err);
    error.value = true;
    errorMessage.value = err.message || t('loadLogFailed');
    Message.error(t('loadLogFailed') + ': ' + (err.message || t('unknownError')));
  } finally {
    loading.value = false;
  }
};

// 滚动到底部
const scrollToBottom = () => {
  if (logContainerRef.value && autoScroll.value) {
    logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight;
  }
};

// 清除日志
const clearLogs = () => {
  displayLogs.value = [];
};

// 切换服务
const onServiceChange = () => {
  displayLogs.value = processLogData();
  nextTick(() => {
    scrollToBottom();
  });
};

// 格式化时间戳
const formatTimestamp = (timestamp) => {
  if (!timestamp) return '';
  
  try {
    const date = new Date(timestamp);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  } catch (error) {
    return timestamp;
  }
};

// 关闭抽屉
const handleClose = () => {
  emit('update:visible', false);
  emit('close');
};

// 监听 visible
watch(() => props.visible, (newVal) => {
  if (newVal) {
    selectedService.value = 'all';
    loadLogs();
    // 每5秒自动刷新一次日志
    refreshInterval.value = setInterval(() => {
      loadLogs();
    }, 5000);
  } else {
    if (refreshInterval.value) {
      clearInterval(refreshInterval.value);
      refreshInterval.value = null;
    }
  }
});

// 监听 composeInfo
watch(() => props.composeInfo, (newVal, oldVal) => {
  if (props.visible && newVal && newVal.name && JSON.stringify(newVal) !== JSON.stringify(oldVal)) {
    selectedService.value = 'all';
    loadLogs();
  }
}, { deep: true });

// 监听 hostId
watch(() => props.hostId, (newVal) => {
  if (props.visible && newVal) {
    loadLogs();
  }
});

onMounted(() => {
  checkIsMobile();
  window.addEventListener('resize', checkIsMobile);
});

onUnmounted(() => {
  window.removeEventListener('resize', checkIsMobile);
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value);
  }
});
</script>

<style>
/* 日志区域字体样式 */
.log-element {
  font-family: Consolas, "Courier New", "SFMono-Regular", "Menlo", "Monaco", "Roboto Mono", "Ubuntu Mono", monospace !important;
  font-size: 14px !important;
  line-height: 1.5;
}
</style>

<style scoped>
.log-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
}

.service-selector {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.service-label {
  font-size: 14px;
  color: #666;
  white-space: nowrap;
}

.log-element {
  flex: 1;
  background-color: #000000;
  border-radius: 4px;
  overflow: auto;
  margin-bottom: 16px;
  padding: 12px;
  color: #ffffff;
}

.log-content {
  white-space: pre-wrap;
  word-break: break-all;
}

.log-line {
  margin-bottom: 4px;
  font-size: 14px;
}

.log-timestamp {
  color: #888888;
  font-size: 12px;
}

.log-service {
  color: #3c7eff;
  font-weight: 500;
}

.no-logs {
  color: #888888;
  text-align: center;
  padding: 20px;
  font-style: italic;
}

.log-overlay {
  position: absolute;
  top: 60px; /* 调整为服务选择器下方 */
  left: 24px;
  right: 24px;
  bottom: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(0, 0, 0, 0.7);
  border-radius: 4px;
  z-index: 10;
}

.status-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 20px;
  max-width: 80%;
}

.status-info .arco-spin {
  margin-bottom: 16px;
}

.status-info span {
  font-size: 14px;
  color: #fff;
}

.action-buttons {
  margin-top: 20px;
}

.log-toolbar {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  align-items: center;
  flex-wrap: wrap;
}

:deep(.arco-alert) {
  margin-bottom: 20px;
  color: #fff;
}

:deep(.arco-alert-error) {
  background-color: rgba(255, 0, 0, 0.2);
  border-color: #f53f3f;
}

/* 暗色主题适配 */
body[arco-theme="dark"] .service-label {
  color: #cccccc !important;
}
</style>
