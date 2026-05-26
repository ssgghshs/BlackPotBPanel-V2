<template>
  <a-drawer
    :visible="visible"
    :title="t('networkInfo')"
    placement="right"
    :width="isMobile ? '100%' : 800"
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
        <a-button type="primary" @click="tryLoadNetworkDetail" style="margin-top: 16px;">
          {{ t('retry') }}
        </a-button>
      </div>

      <!-- 网络详情内容 -->
      <div v-else-if="networkData" class="network-details">
        <!-- 基本信息 -->
        <div class="info-section">
          <h3 class="section-title">{{ t('basicInfo') }}</h3>
          <a-descriptions :column="2" :label-style="{ fontWeight: 'bold' }" :bordered="true" title="">
            <a-descriptions-item :label="t('networkId')" :span="2">
              <span class="code">{{ networkData.id }}</span>
            </a-descriptions-item>
            <a-descriptions-item :label="t('networkIdShort')">
              <span class="code">{{ networkData.id_short }}</span>
            </a-descriptions-item>
            <a-descriptions-item :label="t('networkName')">{{ networkData.name }}</a-descriptions-item>
            <a-descriptions-item :label="t('driver')">{{ networkData.driver }}</a-descriptions-item>
            <a-descriptions-item :label="t('scope')">{{ networkData.scope }}</a-descriptions-item>
            <a-descriptions-item :label="t('internal')">
              <a-tag :color="networkData.internal ? 'red' : 'green'">
                {{ networkData.internal ? t('yes') : t('no') }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item :label="t('enableIPv6')">
              <a-tag :color="networkData.enableIPv6 ? 'green' : 'gray'">
                {{ networkData.enableIPv6 ? t('yes') : t('no') }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item :label="t('created')">{{ formatDate(networkData.created) }}</a-descriptions-item>
          </a-descriptions>
        </div>

        <!-- IPAM 配置信息 -->
        <div v-if="networkData.ipamConfig" class="info-section">
          <h3 class="section-title">{{ t('ipamConfig') }}</h3>
          <a-descriptions :column="2" :label-style="{ fontWeight: 'bold' }" :bordered="true" title="">
            <a-descriptions-item :label="t('subnet')">
              <span class="code">{{ networkData.ipamConfig.Subnet || 'N/A' }}</span>
            </a-descriptions-item>
            <a-descriptions-item :label="t('gateway')">
              <span class="code">{{ networkData.ipamConfig.Gateway || 'N/A' }}</span>
            </a-descriptions-item>
          </a-descriptions>
        </div>

        <!-- 容器信息 -->
        <div class="info-section">
          <h3 class="section-title">{{ t('containers') }}</h3>
          <div v-if="networkData.containers && Object.keys(networkData.containers).length > 0">
            <a-table
              :data="containerTableData"
              :columns="containerColumns"
              :row-key="'id'"
              size="small"
              :scroll="{ x: 'max-content' }"
            />
          </div>
          <div v-else class="empty-containers">
            <a-empty :description="t('noContainers')" />
          </div>
        </div>

        <!-- 选项信息 -->
        <div v-if="networkData.options && Object.keys(networkData.options).length > 0" class="info-section">
          <h3 class="section-title">{{ t('options') }}</h3>
          <div class="options-list">
            <div v-for="(value, key) in networkData.options" :key="key" class="option-item">
              <span class="option-key">{{ key }}</span>
              <span class="option-value">{{ value }}</span>
            </div>
          </div>
        </div>

        <!-- 标签信息 -->
        <div class="info-section">
          <h3 class="section-title">{{ t('labels') }}</h3>
          <div v-if="networkData.labels && Object.keys(networkData.labels).length > 0" class="labels-list">
            <a-tag 
              v-for="(value, key) in networkData.labels" 
              :key="key" 
              color="green"
              style="margin-right: 8px; margin-bottom: 8px"
            >
              {{ key }}: {{ value }}
            </a-tag>
          </div>
          <div v-else class="empty-labels">
            <a-empty :description="t('noLabels')" />
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
import { getNetworkDetail } from '../../api/container';
import { Button as AButton, Tag as ATag, Alert as AAlert, Spin as ASpin, Empty as AEmpty, Descriptions as ADescriptions, DescriptionsItem as ADescriptionsItem, Table as ATable } from '@arco-design/web-vue';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  networkInfo: {
    type: Object,
    default: () => ({})
  }
});

const emit = defineEmits(['update:visible', 'close']);

const isMobile = ref(false);
const currentHostId = ref(null);
const networkData = ref(null);
const loading = ref(false);
const error = ref(false);
const errorMessage = ref('');
const isMounted = ref(true);

// 获取网络ID
const networkId = computed(() => {
  return props.networkInfo?.id || props.networkInfo?.networkId;
});

// 容器表格数据
const containerTableData = computed(() => {
  if (!networkData.value?.containers) return [];
  return Object.entries(networkData.value.containers).map(([containerId, container]) => ({
    id: containerId,
    id_short: containerId.substring(0, 12),
    name: container.Name || '',
    ipv4: container.IPv4Address || '-',
    ipv6: container.IPv6Address || '-'
  }));
});

// 容器表格列配置
const containerColumns = [
  {
    title: t.value('containerId'),
    dataIndex: 'id_short',
    key: 'id_short',
    ellipsis: true,
    tooltip: (text, record) => record.id,
    width: 120
  },
  {
    title: t.value('containerName'),
    dataIndex: 'name',
    key: 'name',
    ellipsis: true,
    width: 200
  },
  {
    title: 'IPv4',
    dataIndex: 'ipv4',
    key: 'ipv4',
    ellipsis: true,
    width: 200
  },
  {
    title: 'IPv6',
    dataIndex: 'ipv6',
    key: 'ipv6',
    ellipsis: true,
    width: 300
  }
];

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

// 加载网络详情
let loadPending = false;
const tryLoadNetworkDetail = async () => {
  if (!isMounted.value) return;
  
  if (!props.visible || !currentHostId.value || !networkId.value) {
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
    console.log(`[API] 请求网络详情: hostId=${currentHostId.value}, networkId=${networkId.value}`);
    const response = await getNetworkDetail(currentHostId.value, networkId.value);
    if (isMounted.value) {
      // 添加id_short字段
      networkData.value = {
        ...response,
        id_short: response.id ? response.id.substring(0, 12) : ''
      };
      console.log('[API] 网络详情加载成功');
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

// 监听可见性、网络ID和主机ID变化
watch(
  () => [props.visible, networkId.value, currentHostId.value],
  () => {
    nextTick(() => {
      tryLoadNetworkDetail();
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

/* 网络详情样式 */
.network-details {
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

.subsection-title {
  margin: 16px 0 12px 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-2);
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

.container-ip {
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

/* 代码样式优化 */
.code {
  font-family: var(--font-family-mono);
  font-size: 13px;
  background: var(--color-fill-2);
  padding: 2px 6px;
  border-radius: 2px;
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