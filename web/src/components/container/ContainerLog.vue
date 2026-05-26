<template>
  <a-drawer
    :width="isMobile ? '90%' : 1000"
    :visible="visible"
    :footer="false"
    @cancel="handleClose"
    unmountOnClose
  >
    <template #title>
      {{ t('containerLog') }} - {{ containerInfo.name }}
    </template>
    
    <div class="log-container">
      <!-- 固定的日志背景框 -->
      <div ref="logContainerRef" class="log-element">
        <div v-if="logs.length > 0" class="log-content">
          <div v-for="(log, index) in logs" :key="index" class="log-line">
            {{ log }}
          </div>
        </div>
        <div v-else class="no-logs">
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
import { getContainerLogs } from '../../api/container';

// Props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  containerInfo: {
    type: Object,
    default: () => ({})
  }
});

// Emits
const emit = defineEmits(['update:visible', 'close']);

// 响应式数据
const isMobile = ref(false);
const logs = ref([]);
const loading = ref(false);
const error = ref(false);
const errorMessage = ref('');
const logContainerRef = ref(null);
const autoScroll = ref(true);
const logLimit = ref(100);
const refreshInterval = ref(null);

// 移动端检测
const checkIsMobile = () => {
  isMobile.value = window.innerWidth <= 768;
};

// 加载日志（使用实际API调用）
const loadLogs = async () => {
  if (!props.containerInfo.id || !props.containerInfo.hostId) return;
  
  try {
    loading.value = true;
    error.value = false;
    errorMessage.value = '';
    
    // 使用实际API调用获取容器日志
    const params = {
      tail: logLimit.value
    };
    
    const response = await getContainerLogs(props.containerInfo.hostId, props.containerInfo.id, params);
    
    // 根据返回的数据格式处理日志
    if (response && response.logs) {
      if (typeof response.logs === 'string') {
        // 按照换行符分割日志字符串
        logs.value = response.logs.split('\n').filter(line => line.trim() !== '');
      } else if (Array.isArray(response.logs)) {
        logs.value = response.logs;
      } else {
        logs.value = [];
      }
    } else {
      logs.value = [];
    }
    
    // 自动滚动到底部
    nextTick(() => {
      scrollToBottom();
    });
    
  } catch (err) {
    console.error('加载日志失败:', err);
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
  logs.value = [];
};

// 关闭抽屉
const handleClose = () => {
  emit('update:visible', false);
  emit('close');
};

// 监听 visible
watch(() => props.visible, (newVal) => {
  if (newVal) {
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

// 监听 containerInfo
watch(() => props.containerInfo, (newVal, oldVal) => {
  if (props.visible && newVal && newVal.id && JSON.stringify(newVal) !== JSON.stringify(oldVal)) {
    loadLogs();
  }
}, { deep: true });

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

.no-logs {
  color: #888888;
  text-align: center;
  padding: 20px;
  font-style: italic;
}

.log-overlay {
  position: absolute;
  top: 8px;
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
}

:deep(.arco-alert) {
  margin-bottom: 20px;
  color: #fff;
}

:deep(.arco-alert-error) {
  background-color: rgba(255, 0, 0, 0.2);
  border-color: #f53f3f;
}
</style>