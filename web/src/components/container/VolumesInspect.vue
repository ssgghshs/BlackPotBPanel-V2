<template>
  <a-drawer
    :visible="visible"
    :title="t('volumeInfo')"
    placement="right"
    :width="isMobile ? '100%' : 1000"
    :footer="false"
    @close="handleClose"
    @update:visible="handleUpdateVisible"
    unmountOnClose
    :destroyOnClose="true"
  >
    <div class="inspect-container">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-container">
        <a-spin />
      </div>

      <!-- 错误状态 -->
      <div v-else-if="error" class="error-container">
        <a-alert
          type="error"
          :title="t('loadError')"
          :description="errorMessage"
          show-icon
        />
        <a-button type="primary" @click="tryLoadVolumeDetail" style="margin-top: 16px;">
          {{ t('retry') }}
        </a-button>
      </div>

      <!-- 存储卷详情内容 -->
      <div v-else-if="volumeData" class="volume-details">
        <!-- 基本信息 -->
        <div class="info-section">
          <h3 class="section-title">{{ t('basicInfo') }}</h3>
          <a-descriptions :column="2" :label-style="{ fontWeight: 'bold' }" :bordered="true" title="">
            <a-descriptions-item :label="t('volumeName')" :span="isMobile ? 1 : 2">
              <span :title="volumeData.name">{{ volumeData.name }}</span>
            </a-descriptions-item>
            <a-descriptions-item :label="t('driver')">{{ volumeData.driver }}</a-descriptions-item>
            <a-descriptions-item :label="t('scope')">{{ volumeData.scope }}</a-descriptions-item>
            <a-descriptions-item :label="t('mountpoint')" :span="isMobile ? 1 : 2">
              <span class="code" :title="volumeData.mountpoint">{{ volumeData.mountpoint }}</span>
            </a-descriptions-item>
            <a-descriptions-item :label="t('createdAt')">{{ formatDate(volumeData.created_at) }}</a-descriptions-item>
            <a-descriptions-item :label="t('usageCount')">{{ volumeData.usage_count || 0 }}</a-descriptions-item>
            <a-descriptions-item :label="t('clusterVolume')">
              <a-tag :color="volumeData.cluster_volume ? 'green' : 'gray'">
                {{ volumeData.cluster_volume ? t('yes') : t('no') }}
              </a-tag>
            </a-descriptions-item>
          </a-descriptions>
        </div>

        <!-- 标签信息 -->
        <div class="info-section">
          <h3 class="section-title">{{ t('labels') }}</h3>
          <div v-if="volumeData.labels && Object.keys(volumeData.labels).length > 0" class="labels-list">
            <a-tag 
              v-for="(value, key) in volumeData.labels" 
              :key="key" 
              color="green"
              style="margin-right: 8px; margin-bottom: 8px"
            >
              {{ key }}{{ value ? `: ${value}` : '' }}
            </a-tag>
          </div>
          <div v-else class="empty-labels">
            <a-empty :description="t('noLabels')" />
          </div>
        </div>

        <!-- 选项信息 -->
        <div v-if="volumeData.options && Object.keys(volumeData.options).length > 0" class="info-section">
          <h3 class="section-title">{{ t('options') }}</h3>
          <div class="options-list">
            <div v-for="(value, key) in volumeData.options" :key="key" class="option-item">
              <span class="option-key">{{ key }}</span>
              <span class="option-value">{{ value }}</span>
            </div>
          </div>
        </div>

        <!-- 容器信息 -->
        <div class="info-section">
          <h3 class="section-title">{{ t('containers') }}</h3>
          <div v-if="volumeData.containers && Object.keys(volumeData.containers).length > 0" class="containers-list">
            <div v-for="(container, containerId) in volumeData.containers" :key="containerId" class="container-item">
              <div class="container-header">
                <span class="container-id">{{ containerId }}</span>
                <span v-if="container.Name" class="container-name">{{ container.Name }}</span>
              </div>
              <div v-if="container.Destination" class="container-mount">
                {{ t('mountDestination') }}: {{ container.Destination }}
              </div>
              <div v-if="container.Mode" class="container-mount">
                {{ t('mountMode') }}: {{ container.Mode }}
              </div>
              <div v-if="container.RW" class="container-mount">
                {{ t('readWrite') }}: {{ container.RW ? t('yes') : t('no') }}
              </div>
            </div>
          </div>
          <div v-else class="empty-containers">
            <a-empty :description="t('noContainers')" />
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="empty-container">
        <a-empty :description="t('noData')" />
      </div>
    </div>
  </a-drawer>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue';
import { t } from '../../utils/locale';
import { getVolumeDetail } from '../../api/container';
import { Button as AButton, Tag as ATag, Alert as AAlert, Spin as ASpin, Empty as AEmpty, Descriptions as ADescriptions, DescriptionsItem as ADescriptionsItem } from '@arco-design/web-vue';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  volumeInfo: {
    type: Object,
    default: () => ({})
  }
});

const emit = defineEmits(['update:visible', 'close']);

const isMobile = ref(false);
const currentHostId = ref(null);
const volumeData = ref(null);
const loading = ref(false);
const error = ref(false);
const errorMessage = ref('');
const isMounted = ref(true);

// 获取存储卷名称
const volumeName = computed(() => {
  return props.volumeInfo?.name || props.volumeInfo?.volumeId;
});

// 移动端检测
const checkIsMobile = () => {
  isMobile.value = window.innerWidth <= 768;
};

const handleUpdateVisible = (value) => {
  emit('update:visible', value);
};

const handleClose = () => {
  emit('update:visible', false);
  emit('close');
};

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) {
    return 'N/A';
  }
  try {
    return new Date(dateString).toLocaleString();
  } catch (e) {
    return dateString;
  }
};

// 主机变更事件处理
const handleHostChange = (event) => {
  const newHostId = event.detail?.hostId;
  if (newHostId) {
    currentHostId.value = newHostId;
    localStorage.setItem('selectedContainerHostId', newHostId);
  }
};

// 加载存储卷详情
let loadPending = false;
const tryLoadVolumeDetail = async () => {
  if (!isMounted.value) return;
  
  if (!props.visible || !currentHostId.value || !volumeName.value) {
    return;
  }
  
  if (loadPending) {
    console.log('已有加载任务 pending，跳过本次触发');
    return;
  }
  
  loadPending = true;
  loading.value = true;
  error.value = false;
  errorMessage.value = '';
  
  try {
    console.log(`[API] 请求存储卷详情: hostId=${currentHostId.value}, volumeName=${volumeName.value}`);
    const response = await getVolumeDetail(currentHostId.value, volumeName.value);
    if (isMounted.value) {
      volumeData.value = response;
      console.log('[API] 存储卷详情加载成功');
    }
  } catch (err) {
    if (isMounted.value) {
      error.value = true;
      errorMessage.value = err.message || t('unknownError');
      console.error('[API] 加载失败:', err);
    }
  } finally {
    if (isMounted.value) {
      loading.value = false;
    }
    loadPending = false;
  }
};

// 监听可见性、存储卷名称和主机ID变化
watch(
  () => [props.visible, volumeName.value, currentHostId.value],
  () => {
    nextTick(() => {
      tryLoadVolumeDetail();
    });
  },
  { immediate: true }
);

onMounted(() => {
  isMounted.value = true;
  checkIsMobile();
  window.addEventListener('resize', checkIsMobile);
  window.addEventListener('containerHostChanged', handleHostChange);
  
  const savedHostId = localStorage.getItem('selectedContainerHostId');
  if (savedHostId) {
    currentHostId.value = savedHostId;
    console.log('从 localStorage 恢复主机 ID:', savedHostId);
  }
});

onUnmounted(() => {
  isMounted.value = false;
  window.removeEventListener('resize', checkIsMobile);
  window.removeEventListener('containerHostChanged', handleHostChange);
});
</script>

<style scoped>
.inspect-container {
  padding: 16px;
  height: calc(100vh - 120px);
  overflow-y: auto;
}

/* 加载状态容器 */
.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}

/* 错误状态容器 */
.error-container {
  padding: 24px;
}

/* 空状态容器 */
.empty-container {
  padding: 48px 24px;
}

/* 存储卷详情样式 */
.volume-details {
  padding: 0;
}

.info-section {
  margin-bottom: 24px;
  background: var(--color-bg-2);
  border-radius: 4px;
  padding: 20px;
  border: 1px solid var(--color-border-2);
}

.section-title {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-1);
  border-bottom: 1px solid var(--color-border-2);
  padding-bottom: 8px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 12px;
}

.info-item {
  display: flex;
  align-items: center;
  padding: 8px 0;
}

.info-item .label {
  font-weight: 500;
  color: var(--color-text-2);
  min-width: 120px;
  margin-right: 12px;
}

.info-item .value {
  color: var(--color-text-1);
  flex: 1;
  word-break: break-all;
}

.info-item .value.code {
  font-family: var(--font-family-mono);
  font-size: 13px;
  background: var(--color-fill-2);
  padding: 2px 6px;
  border-radius: 2px;
}

/* 标签列表样式 */
.labels-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.empty-labels {
  color: var(--color-text-3);
  font-style: italic;
}

/* 容器列表样式 */
.containers-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.container-item {
  background: var(--color-fill-2);
  border-radius: 4px;
  padding: 12px;
  border: 1px solid var(--color-border-2);
}

.container-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.container-id {
  font-family: var(--font-family-mono);
  font-size: 13px;
  color: var(--color-text-1);
  font-weight: 500;
}

.container-name {
  color: var(--color-text-2);
  font-size: 14px;
}

.container-mount {
  font-family: var(--font-family-mono);
  font-size: 13px;
  color: var(--color-text-2);
  margin-top: 4px;
}

.empty-containers {
  color: var(--color-text-3);
  font-style: italic;
}

/* 选项列表样式 */
.options-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.option-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--color-fill-2);
  border-radius: 3px;
  font-size: 13px;
}

.option-key {
  font-weight: 500;
  color: var(--color-text-1);
}

.option-value {
  color: var(--color-text-2);
  font-family: var(--font-family-mono);
}

/* 移动端适配 */
@media (max-width: 768px) {
  /* 调整a-descriptions在移动端的列数 */
  :deep(.arco-descriptions) {
    --descriptions-item-column: 1;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .info-item {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .info-item .label {
    min-width: auto;
    margin-right: 0;
    margin-bottom: 4px;
  }
  
  .container-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
}

/* 暗色主题适配 */
:deep(.arco-empty) {
  color: var(--color-text-2);
}

/* 错误提示样式优化 */
:deep(.arco-alert) {
  margin-bottom: 16px;
}
</style>
