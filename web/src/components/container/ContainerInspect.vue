<template>
  <a-drawer
    :visible="visible"
    :title="t('containerInfo')"
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
        <a-button type="primary" @click="tryLoadContainerInspect" style="margin-top: 16px;">
          {{ t('retry') }}
        </a-button>
      </div>

      <!-- 容器详情内容 -->
      <div v-else-if="containerData" class="container-details">
        <!-- 基本信息 -->
        <div class="info-section">
          <h3 class="section-title">{{ t('basicInfo') }}</h3>
          <a-descriptions
            bordered
            :column="isMobile ? 1 : 2"
            size="small"
            title=""
          >
            <a-descriptions-item :label="t('containerName')">
              {{ containerData.name }}
            </a-descriptions-item>
            <a-descriptions-item :label="t('containerId')" :span="isMobile ? 1 : 2">
              <span class="code">{{ containerData.id }}</span>
            </a-descriptions-item>
            <a-descriptions-item :label="t('image')">
              {{ containerData.image }}
            </a-descriptions-item>
            <a-descriptions-item :label="t('status')">
              <a-tag :color="getStatusColor(containerData.state?.Status)">
                {{ containerData.state?.Status }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item :label="t('created')">
              {{ formatDate(containerData.created) }}
            </a-descriptions-item>
            <a-descriptions-item :label="t('pid')">
              {{ containerData.state?.Pid || 'N/A' }}
            </a-descriptions-item>
          </a-descriptions>
        </div>

        <!-- 状态信息 -->
        <div class="info-section">
          <h3 class="section-title">{{ t('stateInfo') }}</h3>
          <a-descriptions
            bordered
            :column="isMobile ? 1 : 2"
            size="small"
            title=""
          >
            <a-descriptions-item :label="t('running')">
              <a-tag :color="containerData.state?.Running ? 'green' : 'red'">
                {{ containerData.state?.Running ? t('yes') : t('no') }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item :label="t('paused')">
              <a-tag :color="containerData.state?.Paused ? 'orange' : 'green'">
                {{ containerData.state?.Paused ? t('yes') : t('no') }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item :label="t('restarting')">
              <a-tag :color="containerData.state?.Restarting ? 'orange' : 'green'">
                {{ containerData.state?.Restarting ? t('yes') : t('no') }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item :label="t('startedAt')">
              {{ formatDate(containerData.state?.StartedAt) }}
            </a-descriptions-item>
            <a-descriptions-item :label="t('exitCode')">
              {{ containerData.state?.ExitCode }}
            </a-descriptions-item>
          </a-descriptions>
        </div>

        <!-- 网络信息 -->
        <div class="info-section">
          <h3 class="section-title">{{ t('networkInfo') }}</h3>
          <a-descriptions
            bordered
            :column="isMobile ? 1 : 2"
            size="small"
            title=""
          >
            <a-descriptions-item :label="t('ipAddress')">
              <span class="code">{{ containerData.network_settings?.IPAddress || 'N/A' }}</span>
            </a-descriptions-item>
            <a-descriptions-item :label="t('gateway')">
              <span class="code">{{ containerData.network_settings?.Gateway || 'N/A' }}</span>
            </a-descriptions-item>
            <a-descriptions-item :label="t('macAddress')">
              <span class="code">{{ containerData.network_settings?.MacAddress || 'N/A' }}</span>
            </a-descriptions-item>
          </a-descriptions>
          
          <!-- 端口映射 -->
          <div v-if="containerData.network_settings?.Ports" class="ports-section">
            <h4 class="subsection-title">{{ t('portMappings') }}</h4>
            <div class="ports-list">
              <div 
                v-for="(portBindings, containerPort) in containerData.network_settings.Ports" 
                :key="containerPort"
                class="port-item"
              >
                <span class="container-port">{{ containerPort }}</span>
                <span class="arrow">→</span>
                <div class="host-ports">
                  <span 
                    v-for="(binding, index) in portBindings" 
                    :key="index"
                    class="host-port"
                  >
                    {{ binding.HostIp || '0.0.0.0' }}:{{ binding.HostPort }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 配置信息 -->
        <div class="info-section">
          <h3 class="section-title">{{ t('configInfo') }}</h3>
          <a-descriptions
            bordered
            :column="isMobile ? 1 : 2"
            size="small"
            title=""
          >
            <a-descriptions-item :label="t('hostname')">
              {{ containerData.config?.Hostname || 'N/A' }}
            </a-descriptions-item>
            <a-descriptions-item :label="t('workingDir')">
              <span class="code">{{ containerData.config?.WorkingDir || 'N/A' }}</span>
            </a-descriptions-item>
            <a-descriptions-item :label="t('user')">
              {{ containerData.config?.User || 'root' }}
            </a-descriptions-item>
          </a-descriptions>

          <!-- 环境变量 -->
          <div v-if="containerData.config?.Env?.length" class="env-section">
            <h4 class="subsection-title">{{ t('environmentVariables') }}</h4>
            <div class="env-list">
              <div v-for="(env, index) in containerData.config.Env" :key="index" class="env-item">
                <span class="env-key">{{ env.split('=')[0] }}</span>
                <span class="env-separator">=</span>
                <span class="env-value">{{ env.split('=').slice(1).join('=') }}</span>
              </div>
            </div>
          </div>

          <!-- 启动命令 -->
          <div v-if="containerData.config?.Cmd?.length" class="cmd-section">
            <h4 class="subsection-title">{{ t('command') }}</h4>
            <div class="cmd-content">
              <code>{{ containerData.config.Cmd.join(' ') }}</code>
            </div>
          </div>
        </div>

        <!-- 主机配置 -->
        <div class="info-section">
          <h3 class="section-title">{{ t('hostConfig') }}</h3>
          <a-descriptions
            bordered
            :column="isMobile ? 1 : 2"
            size="small"
            title=""
          >
            <a-descriptions-item :label="t('restartPolicy')">
              {{ containerData.host_config?.RestartPolicy?.Name || 'no' }}
            </a-descriptions-item>
            <a-descriptions-item :label="t('networkMode')">
              {{ containerData.host_config?.NetworkMode || 'default' }}
            </a-descriptions-item>
            <a-descriptions-item :label="t('privileged')">
              <a-tag :color="containerData.host_config?.Privileged ? 'red' : 'green'">
                {{ containerData.host_config?.Privileged ? t('yes') : t('no') }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item :label="t('memory')">
              {{ formatMemory(containerData.host_config?.Memory) }}
            </a-descriptions-item>
            <a-descriptions-item :label="t('cpuShares')">
              {{ containerData.host_config?.CpuShares || t('unlimited') }}
            </a-descriptions-item>
          </a-descriptions>
        </div>

        <!-- 挂载点 -->
        <div v-if="containerData.mounts?.length" class="info-section">
          <h3 class="section-title">{{ t('mounts') }}</h3>
          <div class="mounts-list">
            <div v-for="(mount, index) in containerData.mounts" :key="index" class="mount-item">
              <div class="mount-source">{{ mount.Source }}</div>
              <div class="mount-arrow">→</div>
              <div class="mount-destination">{{ mount.Destination }}</div>
              <div class="mount-type">{{ mount.Type }}</div>
            </div>
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
import { getContainerInspect } from '../../api/container';
import { Button as AButton, Tag as ATag, Descriptions as ADescriptions, DescriptionsItem as ADescriptionsItem } from '@arco-design/web-vue';

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

const emit = defineEmits(['update:visible', 'close']);

const isMobile = ref(false);
const currentHostId = ref(null);
const containerData = ref(null);
const loading = ref(false);
const error = ref(false);
const errorMessage = ref('');
const isMounted = ref(true); // 用于防止卸载后更新状态
const showRawData = ref(false);


// 获取容器ID
const containerId = computed(() => {
  return props.containerInfo?.id || props.containerInfo?.containerId || props.containerInfo?.container_id;
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

// 状态颜色映射
const getStatusColor = (status) => {
  const statusColors = {
    'running': 'green',
    'exited': 'red',
    'paused': 'orange',
    'restarting': 'blue',
    'dead': 'red',
    'created': 'gray'
  };
  return statusColors[status?.toLowerCase()] || 'gray';
};

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString || dateString === '0001-01-01T00:00:00Z') {
    return 'N/A';
  }
  try {
    return new Date(dateString).toLocaleString();
  } catch (e) {
    return dateString;
  }
};

// 格式化内存大小
const formatMemory = (bytes) => {
  if (!bytes || bytes === 0) {
    return t.value('unlimited');
  }
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unitIndex = 0;
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  
  return `${size.toFixed(1)} ${units[unitIndex]}`;
};



// 主机变更事件处理
const handleHostChange = (event) => {
  const newHostId = event.detail?.hostId;
  if (newHostId) {
    currentHostId.value = newHostId;
    localStorage.setItem('selectedContainerHostId', newHostId);
  }
};

// ✅ 核心：统一加载逻辑（只在此处调用 API）
let loadPending = false; // 防止短时间内多次触发

const tryLoadContainerInspect = async () => {
  // 如果组件已卸载，不执行
  if (!isMounted.value) return;

  // 条件检查：必须可见、有 hostId、有 containerId
  if (!props.visible || !currentHostId.value || !containerId.value) {
    return;
  }

  // 防重入：已有请求 pending
  if (loadPending) {
    console.log('已有加载任务 pending，跳过本次触发');
    return;
  }

  loadPending = true;
  loading.value = true;
  error.value = false;
  errorMessage.value = '';

  try {
    console.log(`[API] 请求容器详情: hostId=${currentHostId.value}, containerId=${containerId.value}`);
    const response = await getContainerInspect(currentHostId.value, containerId.value);
    if (isMounted.value) {
      containerData.value = response;
      console.log('[API] 容器详情加载成功');
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

// ✅ 关键：只监听一个组合信号（visible + containerId + currentHostId）
watch(
  () => [props.visible, containerId.value, currentHostId.value],
  () => {
    // 使用 nextTick 确保 DOM 和状态同步后再加载
    nextTick(() => {
      tryLoadContainerInspect();
    });
  },
  { immediate: true } // 允许初始化时检查
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

/* 容器详情样式 */
.container-details {
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

/* 端口映射样式 */
.ports-section {
  margin-top: 16px;
}

.ports-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.port-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: var(--color-fill-1);
  border-radius: 3px;
  font-family: var(--font-family-mono);
  font-size: 13px;
}

.container-port {
  color: var(--color-text-1);
  font-weight: 500;
}

.arrow {
  margin: 0 12px;
  color: var(--color-text-3);
}

.host-ports {
  display: flex;
  gap: 8px;
}

.host-port {
  background: var(--color-primary-light-1);
  color: var(--color-primary-6);
  padding: 2px 8px;
  border-radius: 2px;
  font-size: 12px;
}

/* 环境变量样式 */
.env-section {
  margin-top: 16px;
}

.env-list {
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid var(--color-border-2);
  border-radius: 3px;
}

.env-item {
  display: flex;
  align-items: center;
  padding: 6px 12px;
  border-bottom: 1px solid var(--color-border-2);
  font-family: var(--font-family-mono);
  font-size: 13px;
}

.env-item:last-child {
  border-bottom: none;
}

.env-key {
  color: var(--color-text-1);
  font-weight: 500;
  min-width: 150px;
}

.env-separator {
  color: var(--color-text-3);
  margin: 0 8px;
}

.env-value {
  color: var(--color-text-2);
  flex: 1;
  word-break: break-all;
}

/* 命令样式 */
.cmd-section {
  margin-top: 16px;
}

.cmd-content {
  background: var(--color-fill-2);
  border: 1px solid var(--color-border-2);
  border-radius: 3px;
  padding: 12px;
}

.cmd-content code {
  font-family: var(--font-family-mono);
  font-size: 13px;
  color: var(--color-text-1);
  word-break: break-all;
}

/* 挂载点样式 */
.mounts-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mount-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: var(--color-fill-1);
  border-radius: 3px;
  font-family: var(--font-family-mono);
  font-size: 13px;
}

.mount-source {
  color: var(--color-text-1);
  flex: 1;
  word-break: break-all;
}

.mount-arrow {
  margin: 0 12px;
  color: var(--color-text-3);
}

.mount-destination {
  color: var(--color-text-1);
  flex: 1;
  word-break: break-all;
}

.mount-type {
  background: var(--color-primary-light-1);
  color: var(--color-primary-6);
  padding: 2px 8px;
  border-radius: 2px;
  font-size: 12px;
  margin-left: 12px;
}

/* 原始数据样式 */
.raw-data-container {
  background: var(--color-fill-2);
  border: 1px solid var(--color-border-2);
  border-radius: 3px;
  padding: 16px;
  max-height: 400px;
  overflow-y: auto;
}

.raw-data-container pre {
  margin: 0;
  font-family: var(--font-family-mono);
  font-size: 12px;
  line-height: 1.5;
  color: var(--color-text-1);
  white-space: pre-wrap;
  word-break: break-all;
}

/* Code样式 */
.code {
  font-family: var(--font-family-mono);
  font-size: 13px;
  background: var(--color-fill-2);
  padding: 2px 6px;
  border-radius: 2px;
}

/* 移动端适配 */
@media (max-width: 768px) {
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
  
  .port-item,
  .mount-item {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .arrow,
  .mount-arrow {
    margin: 4px 0;
  }
  
  /* a-descriptions移动端适配 */
  :deep(.arco-descriptions-item-label) {
    font-weight: 500;
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