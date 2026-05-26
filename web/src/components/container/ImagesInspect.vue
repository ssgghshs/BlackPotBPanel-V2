<template>
  <a-drawer
    :visible="visible"
    :title="t('imageInfo')"
    placement="right"
    :width="isMobile ? '100%' : 900"
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
        <a-button type="primary" @click="tryLoadImageDetail" style="margin-top: 16px;">
          {{ t('retry') }}
        </a-button>
      </div>

      <!-- 镜像详情内容 -->
      <div v-else-if="imageData" class="image-details">
        <!-- 基本信息 -->
        <div class="info-section">
          <h3 class="section-title">{{ t('basicInfo') }}</h3>
          <a-descriptions :column="isMobile ? 1 : 2" :title="null"  :bordered="true">
            <a-descriptions-item :label="t('imageId')" :span="isMobile ? 1 : 2">
              <span class="code">{{ imageData.id }}</span>
            </a-descriptions-item>
            <a-descriptions-item :label="t('imageIdShort')">
              <span class="code">{{ imageData.id_short }}</span>
            </a-descriptions-item>
            <a-descriptions-item :label="t('isUsed')">
              <a-tag :color="imageData.isUsed ? 'green' : 'orange'">
                {{ imageData.isUsed ? t('yes') : t('no') }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item :label="t('size')">
              {{ formatSize(imageData.size) }}
            </a-descriptions-item>
            <a-descriptions-item :label="t('created')">
              {{ formatDate(imageData.createdAt) }}
            </a-descriptions-item>
            <a-descriptions-item :label="t('os')">
              {{ imageData.os }}
            </a-descriptions-item>
            <a-descriptions-item :label="t('architecture')">
              {{ imageData.architecture }}
            </a-descriptions-item>
            <a-descriptions-item :label="t('parentId')">
              <span class="code">{{ imageData.parent_id || 'N/A' }}</span>
            </a-descriptions-item>
          </a-descriptions>
        </div>

        <!-- 标签信息 -->
        <div class="info-section">
          <h3 class="section-title">{{ t('tags') }}</h3>
          <div v-if="imageData.tags && imageData.tags.length > 0" class="tags-list">
            <a-tag 
              v-for="(tag, index) in imageData.tags" 
              :key="index" 
              color="blue"
              style="margin-right: 8px; margin-bottom: 8px"
            >
              {{ tag }}
            </a-tag>
          </div>
          <div v-else class="empty-tags">
            <a-empty :description="t('noTags')" />
          </div>
        </div>

        <!-- 配置信息 -->
        <div class="info-section">
          <h3 class="section-title">{{ t('configInfo') }}</h3>
          <div v-if="imageData.config" class="config-details">
            <a-descriptions :column="isMobile ? 1 : 2" :title="null" :bordered="true">
              <a-descriptions-item :label="t('hostname')">
                {{ imageData.config.Hostname || 'N/A' }}
              </a-descriptions-item>
              <a-descriptions-item :label="t('user')">
                {{ imageData.config.User || 'N/A' }}
              </a-descriptions-item>
              <a-descriptions-item :label="t('workingDir')">
                <span class="code">{{ imageData.config.WorkingDir || 'N/A' }}</span>
              </a-descriptions-item>
              <a-descriptions-item :label="t('tty')">
                <a-tag :color="imageData.config.Tty ? 'green' : 'gray'">
                  {{ imageData.config.Tty ? t('yes') : t('no') }}
                </a-tag>
              </a-descriptions-item>
            </a-descriptions>

            <!-- 环境变量 -->
            <div v-if="imageData.config.Env && imageData.config.Env.length > 0" class="env-section">
              <h4 class="subsection-title">{{ t('environmentVariables') }}</h4>
              <div class="env-list">
                <div v-for="(env, index) in imageData.config.Env" :key="index" class="env-item">
                  <span class="env-key">{{ env.split('=')[0] }}</span>
                  <span class="env-separator">=</span>
                  <span class="env-value">{{ env.split('=').slice(1).join('=') }}</span>
                </div>
              </div>
            </div>

            <!-- 启动命令 -->
            <div v-if="imageData.config.Cmd && imageData.config.Cmd.length > 0" class="cmd-section">
              <h4 class="subsection-title">{{ t('command') }}</h4>
              <div class="cmd-content">
                <code>{{ imageData.config.Cmd.join(' ') }}</code>
              </div>
            </div>

            <!-- 暴露端口 -->
            <div v-if="imageData.config.ExposedPorts" class="ports-section">
              <h4 class="subsection-title">{{ t('exposedPorts') }}</h4>
              <div class="ports-list">
                <div 
                  v-for="(portConfig, port) in imageData.config.ExposedPorts" 
                  :key="port"
                  class="port-item"
                >
                  <a-tag color="blue">{{ port }}</a-tag>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="empty-config">
            <a-empty :description="t('noConfig')" />
          </div>
        </div>

        <!-- 图驱动信息 -->
        <div v-if="imageData.graph_driver" class="info-section">
          <h3 class="section-title">{{ t('graphDriver') }}</h3>
          <a-descriptions :column="isMobile ? 1 : 2" :title="null" :bordered="true">
            <a-descriptions-item :label="t('driverName')">
              {{ imageData.graph_driver.Name }}
            </a-descriptions-item>
          </a-descriptions>
        </div>

        <!-- 镜像摘要 -->
        <div v-if="imageData.repo_digests && imageData.repo_digests.length > 0" class="info-section">
          <h3 class="section-title">{{ t('repoDigests') }}</h3>
          <div class="repo-digests-list">
            <div v-for="(digest, index) in imageData.repo_digests" :key="index" class="digest-item code">
              {{ digest }}
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
import { getImageDetail } from '../../api/container';
import { Button as AButton, Tag as ATag, Alert as AAlert, Spin as ASpin, Empty as AEmpty, Checkbox as ACheckbox, Descriptions as ADescriptions, DescriptionsItem as ADescriptionsItem } from '@arco-design/web-vue';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  imageInfo: {
    type: Object,
    default: () => ({})
  }
});

const emit = defineEmits(['update:visible', 'close']);

const isMobile = ref(false);
const currentHostId = ref(null);
const imageData = ref(null);
const loading = ref(false);
const error = ref(false);
const errorMessage = ref('');
const isMounted = ref(true);


// 获取镜像ID
const imageId = computed(() => {
  return props.imageInfo?.id || props.imageInfo?.imageId || props.imageInfo?.image_id;
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
  if (!dateString || dateString === '0001-01-01T00:00:00Z') {
    return 'N/A';
  }
  try {
    return new Date(dateString).toLocaleString();
  } catch (e) {
    return dateString;
  }
};

// 格式化大小
const formatSize = (bytes) => {
  if (!bytes || bytes === 0) {
    return '0 B';
  }
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = bytes;
  let unitIndex = 0;
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  
  return `${size.toFixed(2)} ${units[unitIndex]}`;
};



// 主机变更事件处理
const handleHostChange = (event) => {
  const newHostId = event.detail?.hostId;
  if (newHostId) {
    currentHostId.value = newHostId;
    localStorage.setItem('selectedContainerHostId', newHostId);
  }
};

// 加载镜像详情
let loadPending = false;
const tryLoadImageDetail = async () => {
  if (!isMounted.value) return;
  
  if (!props.visible || !currentHostId.value || !imageId.value) {
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
    console.log(`[API] 请求镜像详情: hostId=${currentHostId.value}, imageId=${imageId.value}`);
    const response = await getImageDetail(currentHostId.value, imageId.value);
    if (isMounted.value) {
      imageData.value = response;
      console.log('[API] 镜像详情加载成功');
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

// 监听可见性、镜像ID和主机ID变化
watch(
  () => [props.visible, imageId.value, currentHostId.value],
  () => {
    nextTick(() => {
      tryLoadImageDetail();
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

/* 镜像详情样式 */
.image-details {
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
.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.empty-tags {
  color: var(--color-text-3);
  font-style: italic;
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

/* 暴露端口样式 */
.ports-section {
  margin-top: 16px;
}

.ports-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.port-item {
  margin-bottom: 4px;
}

/* 摘要样式 */
.repo-digests-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.digest-item {
  background: var(--color-fill-2);
  padding: 8px 12px;
  border-radius: 3px;
  font-size: 12px;
  word-break: break-all;
}

/* code样式 */
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
  
  /* 移动端适配a-descriptions组件 */
  :deep(.arco-descriptions) {
    .arco-descriptions-item-label {
      font-weight: 500;
    }
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
