<template>
  <a-card class="containers-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('overview') }}</span>
      </div>
    </template>

<!-- 内容区域  -->
  <!-- 3:7 -->
  <div class="content-layout">
    <!-- Docker信息卡片3/10 -->
    <div class="docker-info">
      <div class="header-controls">
        <h3>{{ t('dockerInfo') }}</h3>
        <button @click="fetchDockerInfo" :disabled="loading">{{ t('refresh') }}</button>
      </div>

      <div v-if="loading">{{ t('loading') }}</div>
      <div v-else-if="error" class="error">{{ error }}</div>
      <div v-else-if="dockerInfo" class="info-list">
        <div class="info-item" v-for="(value, key) in formattedDockerInfo" :key="key">
          <span>{{ value.label }}:</span>
          <span>{{ value.content }}</span>
        </div>
      </div>
    </div>
    
    <!-- 右侧内容区域 -->
    <div class="right-content">
      <!-- containerStats卡片 -->
      <div class="new-card">
        <div class="header-controls">
          <h3>{{ t('container') }}</h3>
        </div>
        <div class="card-content">
          <!-- 卡片内容区域 -->
          <div class="stats-overview">
            <div class="stat-item">
              <span class="stat-label">{{ t('runningContainers') }}</span>
              <span class="stat-value">{{ dockerInfo?.running_containers !== undefined ? dockerInfo.running_containers : '--' }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">{{ t('stoppedContainers') }}</span>
              <span class="stat-value">{{ dockerInfo?.stopped_containers !== undefined ? dockerInfo.stopped_containers : '--' }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">{{ t('totalContainers') }}</span>
              <span class="stat-value">{{ dockerInfo?.container_count !== undefined ? dockerInfo.container_count : '--' }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 2x2网格卡片区域 -->
      <div class="grid-cards">
        <!-- 卡片1 -->
        <div class="grid-card">
          <div class="header-controls">
            <h3>{{ t('image') }}</h3>
          </div>
          <div class="card-content">
            <div class="grid-card-content">
              <!-- 卡片1内容 -->
              <span class="grid-value">{{ dockerInfo?.image_count !== undefined ? dockerInfo.image_count : '--' }}</span>
            </div>
          </div>
        </div>

        <!-- 卡片2 -->
        <div class="grid-card">
          <div class="header-controls">
            <h3>{{ t('network') }}</h3>
          </div>
          <div class="card-content">
            <div class="grid-card-content">
              <!-- 卡片2内容 -->
              <span class="grid-value">{{ dockerInfo?.network_count !== undefined ? dockerInfo.network_count : '--' }}</span>
            </div>
          </div>
        </div>

        <!-- 卡片3 -->
        <div class="grid-card">
          <div class="header-controls">
            <h3>{{ t('volumes') }}</h3>
          </div>
          <div class="card-content">
            <div class="grid-card-content">
              <!-- 卡片3内容 -->
              <span class="grid-value">{{ dockerInfo?.volume_count !== undefined ? dockerInfo.volume_count : '--' }}</span>
            </div>
          </div>
        </div>

        <!-- 卡片4 -->
        <div class="grid-card">
          <div class="header-controls">
            <h3>{{ t('compose') }}</h3>
          </div>
          <div class="card-content">
            <div class="grid-card-content">
              <!-- 卡片4内容 -->
              <span class="grid-value">{{ dockerInfo?.compose_count !== undefined ? dockerInfo.compose_count : '--' }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  </a-card>
</template>

<script setup>
import { reactive, ref, onMounted, onBeforeUnmount, computed } from 'vue';
import { t } from '../../utils/locale'
import { getContainerNodeInfo } from '../../api/container.js'

// 响应式数据
const dockerInfo = ref(null)
const loading = ref(false)
const error = ref(null)
let isComponentMounted = true
const selectedHostId = ref(null)
let hostChangeEventListener = null

// 组件卸载时标记
onBeforeUnmount(() => {
  isComponentMounted = false
  // 移除事件监听
  if (hostChangeEventListener) {
    window.removeEventListener('containerHostChanged', hostChangeEventListener)
    hostChangeEventListener = null
  }
  // 清空数据，避免内存泄漏
  dockerInfo.value = null
  error.value = null
  loading.value = false
})

// 格式化Docker信息用于显示
const formattedDockerInfo = computed(() => {
  if (!dockerInfo.value) return {}
  
  // 处理storage_plugins，显示为逗号分隔的字符串
  const volumePlugins = Array.isArray(dockerInfo.value.storage_plugins)
    ? dockerInfo.value.storage_plugins.join(', ')
    : '-'  
  
  // 处理network_plugins，显示为逗号分隔的字符串
  const networkPlugins = Array.isArray(dockerInfo.value.network_plugins)
    ? dockerInfo.value.network_plugins.join(', ')
    : '-'  
  
  return {
    dockerHost: {
      label: t.value('dockerHost'),
      content: dockerInfo.value.docker_host || '-'  
    },
    dockerServerVersion: {
      label: t.value('dockerServerVersion'),
      content: dockerInfo.value.server_version || '-'  
    },
    volumePlugins: {
      label: t.value('volumePlugins'),
      content: volumePlugins  
    },
    networkPlugins: {
      label: t.value('networkPlugins'),
      content: networkPlugins  
    },
    rootDir: {
      label: t.value('rootDir'),
      content: dockerInfo.value.root_dir || '-'  
    },
    cpus: {
      label: t.value('cpus'),
      content: dockerInfo.value.cpus || '-'  
    },
    memory: {
      label: t.value('memory'),
      content: dockerInfo.value.total_memory || '-'  
    },
    storageDriver: {
      label: t.value('storageDriver'),
      content: dockerInfo.value.storage_driver || '-'  
    },
    logDriver: {
      label: t.value('logDriver'),
      content: dockerInfo.value.log_driver || '-'  
    }
  }
})

// 获取Docker信息
const fetchDockerInfo = async () => {
  // 检查组件是否仍然挂载
  if (!isComponentMounted) {
    return
  }
  
  try {
    loading.value = true
    error.value = null

    // 获取当前选中的宿主ID
    const hostId = selectedHostId.value
    if (!hostId) {
      throw new Error(t.value('noHostSelected'))
    }
    
    // 调用真实API获取Docker节点信息
    const response = await getContainerNodeInfo(hostId)
    
    // 检查组件是否仍然挂载
    if (!isComponentMounted) {
      return
    }
    
    // 设置获取到的数据
    dockerInfo.value = response.data || response
  } catch (err) {
    // 检查组件是否仍然挂载
    if (!isComponentMounted) {
      return
    }
    
    console.error('获取Docker信息失败:', err)
    
    // 增强错误处理，根据不同错误类型显示不同消息
    if (err.message === t.value('noHostSelected')) {
      error.value = err.message
    } else if (err.response?.status === 401) {
      error.value = t.value('unauthorizedAccess')
    } else if (err.response?.status === 404) {
      error.value = t.value('hostNotFound')
    } else if (err.response?.status === 500) {
      error.value = t.value('serverError')
    } else if (err.name === 'NetworkError' || err.message?.includes('Network')) {
      error.value = t.value('networkError')
    } else {
      error.value = t.value('getDockerInfoFailed')
    }
  } finally {
    // 检查组件是否仍然挂载
    if (!isComponentMounted) {
      return
    }
    loading.value = false
  }
}

// 处理宿主变化事件
const handleHostChange = (event) => {
  if (!isComponentMounted) return
  
  const newHostId = event.detail?.hostId
  if (newHostId && newHostId !== selectedHostId.value) {
    selectedHostId.value = newHostId
    // 重新获取数据
    fetchDockerInfo()
  }
}

// 组件挂载时获取数据
onMounted(() => {
  // 从 localStorage 获取保存的宿主 ID
  const savedHostId = localStorage.getItem('selectedContainerHostId')
  if (savedHostId) {
    selectedHostId.value = savedHostId
  } else {
    // 默认使用 '1' 作为备用值
    selectedHostId.value = '1'
  }
  
  // 添加事件监听
  hostChangeEventListener = handleHostChange.bind(this)
  window.addEventListener('containerHostChanged', hostChangeEventListener)
  
  // 获取初始数据
  fetchDockerInfo()
})
</script>

<style scoped>
.containers-container {
  padding: 30px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 15px;
  font-size: 1.3em;
  padding: 25px 25px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.title {
  margin: 0;
  padding: 0;
}

.desc {
  margin-top: 4px;
  color: #8c8c8c;
  font-size: 12px;
}

/* 内容布局 */
.content-layout {
  display: flex;
  gap: 20px;
}

/* Docker信息卡片样式 */
.docker-info {
  width: 30%; /* 占据整个宽度的3/10 */
  background: var(--color-bg-1);
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  height: 500px;
  display: flex;
  flex-direction: column;
}

/* 右侧内容区域 */
.right-content {
  width: 70%; /* 占据整个宽度的7/10 */
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 新卡片样式 */
.new-card {
  width: 96.5%;
  background: var(--color-bg-1);
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  height: 140px;
  display: flex;
  flex-direction: column;
}

/* 2x2网格卡片容器 */
.grid-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

/* 单个网格卡片 */
.grid-card {
  background: var(--color-bg-1);
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  height: 120px;
  display: flex;
  flex-direction: column;
}

/* 网格卡片内容 */
.grid-card-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.grid-value {
  font-size: 28px;
  font-weight: 600;
  color: var(--color-text-1);
}

/* 新卡片内容区域 */
.card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* 统计数据概览 */
.stats-overview {
  display: flex;
  gap: 15px;
  flex: 1;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  padding: 10px 0;
}  

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 12px 10px;
  background: var(--color-bg-2);
  border-radius: 6px;
  border: 1px solid var(--color-neutral-3);
  flex: 1;
  min-height: 60px;
}

.stat-label {
  font-size: 12px;
  color: var(--color-text-2);
  margin-bottom: 8px;
  text-align: center;
}

.stat-value {
  font-size: 22px;
  font-weight: 600;
  color: var(--color-text-1);
  text-align: center;
}



/* 响应式布局适配 - 右侧内容和网格卡片 */
@media (max-width: 1024px) {
  .right-content {
    width: 60%;
    gap: 15px;
  }

  .new-card {
    width: 100%;
    height: 140px; /* 调整高度以适应不同屏幕 */
    padding: 15px;
  }

  .grid-cards {
    gap: 15px;
  }

  .grid-card {
    height: 140px;
    padding: 15px;
  }

  .grid-value {
    font-size: 24px;
  }
  
  .stats-overview {
    gap: 12px;
    padding: 8px 0;
  }
  
  .stat-item {
    padding: 12px 8px;
    min-height: 70px;
  }
  
  .stat-label {
    font-size: 11px;
    margin-bottom: 6px;
  }
  
  .stat-value {
    font-size: 19px;
  }
}

@media (max-width: 768px) {
  .right-content {
    width: 100%;
    gap: 15px;
  }

  .new-card {
    width: 100%;
    height: 130px; /* 调整高度以适应不同屏幕 */
    padding: 15px;
  }

  .grid-cards {
    grid-template-columns: 1fr;
    gap: 15px;
  }

  .grid-card {
    height: 130px;
    padding: 15px;
  }

  .grid-value {
    font-size: 22px;
  }
  
  .stats-overview {
    gap: 10px;
    padding: 6px 0;
  }
  
  .stat-item {
    padding: 10px 6px;
    min-height: 65px;
  }
  
  .stat-label {
    font-size: 10px;
    margin-bottom: 5px;
  }
  
  .stat-value {
    font-size: 17px;
  }
}

@media (max-width: 480px) {
  .right-content {
    gap: 10px;
  }

  .new-card {
    height: 110px; /* 调整高度以适应不同屏幕 */
    padding: 10px;
  }

  .grid-cards {
    gap: 10px;
  }

  .grid-card {
    height: 110px;
    padding: 10px;
  }

  .grid-value {
    font-size: 20px;
  }
  
  .stats-overview {
    gap: 6px;
    padding: 4px 0;
  }
  
  .stat-item {
    padding: 8px 4px;
    min-height: 55px;
  }
  
  .stat-label {
    font-size: 9px;
    margin-bottom: 4px;
  }
  
  .stat-value {
    font-size: 15px;
  }
}

.header-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.header-controls h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-1);
}

.header-controls button {
  padding: 6px 12px;
  border: 1px solid var(--color-neutral-3);
  border-radius: 4px;
  background: var(--color-bg-2);
  cursor: pointer;
  font-size: 14px;
  color: var(--color-text-1);
}

.header-controls button:hover {
  background: var(--color-bg-3);
}

.header-controls button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error {
  color: var(--color-danger-light-5);
  padding: 8px;
  text-align: center;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  flex: 1;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 12px;
  background: var(--color-bg-2);
  border-radius: 6px;
  font-size: 14px;
  border: 1px solid var(--color-neutral-3);
}

.info-item span:first-child {
  font-weight: 500;
  color: var(--color-text-1);
  flex-shrink: 0;
  margin-right: 10px;
}

.info-item span:last-child {
  flex: 1;
  text-align: right;
  word-break: break-all;
  color: var(--color-text-2);
}

/* 响应式布局适配 */
@media (max-width: 1024px) {
  .docker-info {
    width: 40%;
    height: 600px;
    padding: 15px;
  }
  
  .header-controls {
    margin-bottom: 8px;
  }
  
  .header-controls h3 {
    font-size: 15px;
  }
  
  .header-controls button {
    padding: 5px 10px;
    font-size: 13px;
  }
  
  .info-item {
    padding: 8px 10px;
    font-size: 13px;
  }
}

@media (max-width: 768px) {
  .content-layout {
    flex-direction: column;
  }
  
  .docker-info {
    width: 100%;
    height: 580px;
    padding: 15px;
    border-radius: 6px;
  }
  
  .header-controls {
    margin-bottom: 12px;
  }
  
  .header-controls h3 {
    font-size: 16px;
  }
  
  .header-controls button {
    padding: 5px 10px;
    font-size: 12px;
  }
  
  .info-item {
    padding: 8px;
    font-size: 12px;
    flex-direction: row;
  }
  
  .info-item span:first-child {
    font-weight: 500;
    margin-right: 8px;
  }
  
  .info-item span:last-child {
    text-align: right;
  }
}

@media (max-width: 480px) {
  .docker-info {
    height: 530px;
    padding: 10px;
    border-radius: 4px;
  }
  
  .header-controls {
    margin-bottom: 10px;
  }
  
  .header-controls h3 {
    font-size: 15px;
  }
  
  .header-controls button {
    padding: 4px 8px;
    font-size: 11px;
  }
  
  .info-item {
    padding: 6px;
    font-size: 11px;
    gap: 3px;
    border-radius: 4px;
  }
  
  .info-item span:first-child {
    font-weight: 600;
    color: var(--color-text-1);
  }
  
  .info-item span:last-child {
    font-weight: 400;
    text-align: left;
    word-break: break-word;
    color: var(--color-text-2);
  }
}

@media (max-width: 320px) {
  .header-controls h3 {
    font-size: 14px;
  }
  
  .header-controls button {
    padding: 3px 6px;
    font-size: 10px;
  }
  
  .info-item {
    padding: 5px;
    font-size: 10px;
    gap: 2px;
  }
}

/* 暗色主题适配 */
[arco-theme="dark"] .docker-info {
  background: var(--color-bg-1) !important;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3) !important;
}

[arco-theme="dark"] .new-card {
  background: var(--color-bg-1) !important;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3) !important;
}

[arco-theme="dark"] .grid-card {
  background: var(--color-bg-1) !important;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3) !important;
}

[arco-theme="dark"] .grid-value {
  color: var(--color-text-1) !important;
}

[arco-theme="dark"] .header-controls h3 {
  color: var(--color-text-1) !important;
}

[arco-theme="dark"] .header-controls button {
  border: 1px solid var(--color-neutral-3) !important;
  background: var(--color-bg-2) !important;
  color: var(--color-text-1) !important;
}

[arco-theme="dark"] .header-controls button:hover {
  background: var(--color-bg-3) !important;
}

[arco-theme="dark"] .error {
  color: var(--color-danger-light-5) !important;
}

[arco-theme="dark"] .info-item {
  background: var(--color-bg-2) !important;
}

[arco-theme="dark"] .info-item span:first-child {
  color: var(--color-text-1) !important;
}

[arco-theme="dark"] .info-item span:last-child {
  color: var(--color-text-2) !important;
}

/* 新卡片暗色主题适配 */
[arco-theme="dark"] .stat-item {
  background: var(--color-bg-2) !important;
  border-color: var(--color-neutral-3) !important;
  justify-content: center !important;
  text-align: center !important;
}

[arco-theme="dark"] .stat-label {
  color: var(--color-text-2) !important;
  text-align: center !important;
}

[arco-theme="dark"] .stat-value {
  color: var(--color-text-1) !important;
  text-align: center !important;
}


</style>