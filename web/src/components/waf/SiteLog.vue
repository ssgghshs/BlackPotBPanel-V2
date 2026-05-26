<template>
  <a-drawer
    :visible="visible"
    @update:visible="(value) => emit('update:visible', value)"
    :title="t('siteLog')"
    :width="isMobile ? '100%' : '1200px'"
    :footer="false"
  >
    <div class="site-log">
      
      <a-tabs v-model:active-key="activeTab" @change="handleTabChange" :loading="loading">
        <a-tab-pane key="1" :title="t('accessLog')">
          <div class="tab-header-actions">
            <a-button type="outline" size="small" @click="fetchSiteLogs">{{ t('refresh') }}</a-button>
            <a-button type="outline" size="small" status="danger" @click="showCleanLogModal('access')">{{ t('clearLogs') }}</a-button>
          </div>
          <div v-if="accessLog" class="log-content-card">
            <pre class="log-content" ref="accessLogRef"><span v-html="formatLogContent(accessLog)"></span></pre>
          </div>
          <a-empty v-else>
            <template #description>
              <span>{{ t('noLogContent') }}</span>
            </template>
          </a-empty>
        </a-tab-pane>
        <a-tab-pane key="2" :title="t('errorLog')">
          <div class="tab-header-actions">
            <a-button type="outline" size="small" @click="fetchSiteLogs">{{ t('refresh') }}</a-button>
            <a-button type="outline" size="small" status="danger" @click="showCleanLogModal('error')">{{ t('clearLogs') }}</a-button>
          </div>
          <div v-if="errorLog" class="log-content-card">
            <pre class="log-content" ref="errorLogRef"><span v-html="formatLogContent(errorLog)"></span></pre>
          </div>
          <a-empty v-else>
            <template #description>
              <span>{{ t('noLogContent') }}</span>
            </template>
          </a-empty>
        </a-tab-pane>
     </a-tabs>

    </div>
    
    <!-- 清理日志确认对话框 -->
    <a-modal 
      v-model:visible="cleanLogModalVisible" 
      :title="t('clearLogsConfirmTitle')" 
      @ok="handleCleanLog" 
      @cancel="cancelCleanLog"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
    >
      <p>{{ t('clearLogConfirmMessage', { logType: selectedLogType === 'access' ? t('accessLog') : t('errorLog') }) }}</p>
    </a-modal>
  </a-drawer>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { t } from '../../utils/locale';
import { getSiteLogs, cleanSiteLogs } from '../../api/waf';
import { Message } from '@arco-design/web-vue';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  siteName: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['update:visible']);

// 响应式布局相关
const isMobile = ref(false);

const checkIsMobile = () => {
  isMobile.value = window.innerWidth < 768;
};

// 响应式数据
const activeTab = ref('1');
const loading = ref(false);
const accessLog = ref('');
const errorLog = ref('');
const accessLogRef = ref(null);
const errorLogRef = ref(null);
const cleanLogModalVisible = ref(false);
const selectedLogType = ref('');

// 监听visible变化，当抽屉打开时获取日志
watch(() => props.visible, async (newValue) => {
  if (newValue && props.siteName) {
    await fetchSiteLogs();
  }
});

// 监听siteName变化，重新获取日志
watch(() => props.siteName, async (newValue) => {
  if (newValue && props.visible) {
    await fetchSiteLogs();
  }
});

// 获取站点日志
const fetchSiteLogs = async () => {
  if (!props.siteName) return;
  
  try {
    loading.value = true;
    const response = await getSiteLogs(props.siteName);
    
    if (response) {
      accessLog.value = response.access_log || '';
      errorLog.value = response.error_log || '';
      
      // 在DOM更新后滚动到底部
      await nextTick();
      scrollToBottom();
    }
  } catch (error) {
    console.error('获取站点日志失败:', error);
    Message.error(t.value('getSiteLogsFailed'));
    accessLog.value = '';
    errorLog.value = '';
  } finally {
    loading.value = false;
  }
};

// 处理标签页切换
const handleTabChange = () => {
  // 在DOM更新后滚动到底部
  nextTick(() => {
    scrollToBottom();
  });
};

// 滚动到底部
const scrollToBottom = () => {
  if (activeTab.value === '1' && accessLogRef.value) {
    accessLogRef.value.scrollTop = accessLogRef.value.scrollHeight;
  } else if (activeTab.value === '2' && errorLogRef.value) {
    errorLogRef.value.scrollTop = errorLogRef.value.scrollHeight;
  }
};

// 显示清理日志确认对话框
const showCleanLogModal = (logType) => {
  selectedLogType.value = logType;
  cleanLogModalVisible.value = true;
};

// 取消清理日志
const cancelCleanLog = () => {
  cleanLogModalVisible.value = false;
  selectedLogType.value = '';
};

// 清理日志
const handleCleanLog = async () => {
  if (!props.siteName || !selectedLogType.value) return;
  
  try {
    const response = await cleanSiteLogs(props.siteName, { log_type: selectedLogType.value });
    Message.success(response.message || t.value('clearLogSuccess'));
    
    // 关闭对话框
    cleanLogModalVisible.value = false;
    selectedLogType.value = '';
    
    // 重新获取日志
    await fetchSiteLogs();
  } catch (error) {
    console.error('清理站点日志失败:', error);
    Message.error(`${t.value('clearLogFailed')}: ${error.message || t.value('unknownError')}`);
    
    // 关闭对话框
    cleanLogModalVisible.value = false;
    selectedLogType.value = '';
  }
};

// 格式化日志内容
const formatLogContent = (content) => {
  if (!content) return '';
  
  // 限制日志内容长度，防止渲染过大的内容导致卡顿
  const maxLength = 50000; // 限制为50000个字符
  let processedContent = content;
  if (content.length > maxLength) {
    processedContent = content.substring(content.length - maxLength);
  }
  
  // 替换换行符为HTML换行
  let formattedContent = processedContent.replace(/\n/g, '<br>');
  
  // 如果原始内容被截断，添加提示信息
  if (content.length > maxLength) {
    return `<span style="color: #FFA500;">[log content truncated, only showing latest part]</span><br>${formattedContent}`;
  }
  
  return formattedContent;
};

// 组件挂载时获取数据
onMounted(() => {
  window.addEventListener('resize', checkIsMobile);
  checkIsMobile();
  if (props.visible && props.siteName) {
    fetchSiteLogs();
  }
});

onUnmounted(() => {
  window.removeEventListener('resize', checkIsMobile);
});
</script>

<style scoped>
.site-log {
  padding: 20px;
  line-height: 1.6;
}

.tab-header-actions {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.log-content-card {
  margin-top: 10px;
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
  max-height: 800px;
  overflow-y: auto;
}
</style>
