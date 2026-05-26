<template>
  <div class="system-info">
    <div class="header-controls">
      <h3>{{ t('hostInfo') }}</h3>
      <button @click="fetchHostInfo" :disabled="loading">{{ t('refresh') }}</button>
    </div>

    <div v-if="loading">{{ t('loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="hostInfo" class="info-list">
      <div class="info-item" v-for="(value, key) in formattedHostInfo" :key="key">
        <span>{{ value.label }}:</span>
        <span>{{ value.content }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { getHostInfo } from '../../api/monitor'
import { t } from '../../utils/locale'

// 响应式数据
const hostInfo = ref(null)
const loading = ref(false)
const error = ref(null)
let isComponentMounted = true

// 组件卸载时标记
onBeforeUnmount(() => {
  isComponentMounted = false
})

// 格式化主机信息用于显示
const formattedHostInfo = computed(() => {
  if (!hostInfo.value) return {}
  
  return {
    hostname: {
      label: t.value('hostname'),
      content: hostInfo.value.hostname
    },
    platform_version: {
      label: t.value('systemVersion'),
      content: hostInfo.value.platform_version
    },
    kernel_version: {
      label: t.value('kernelVersion'),
      content: hostInfo.value.kernel_version
    },
    architecture: {
      label: t.value('systemArchitecture'),
      content: hostInfo.value.architecture
    },
    ip_address: {
      label: t.value('ipAddress'),
      content: hostInfo.value.ip_address
    },
    boot_time: {
      label: t.value('bootTime'),
      content: hostInfo.value.boot_time
    },
    uptime: {
      label: t.value('uptime'),
      content: hostInfo.value.uptime
    }
  }
})

// 获取主机信息
const fetchHostInfo = async () => {
  // 检查组件是否仍然挂载
  if (!isComponentMounted) {
    return
  }
  
  try {
    loading.value = true
    error.value = null

    const response = await getHostInfo()
    console.log('主机信息API响应:', response)
    
    // 检查组件是否仍然挂载
    if (!isComponentMounted) {
      return
    }
    
    // 检查不同的响应结构
    let data = null
    if (response && response.code === 200 && response.data) {
      // 直接返回的数据结构: {code: 200, data: {...}}
      data = response.data
    } else if (response.data && response.data.code === 200 && response.data.data) {
      // 嵌套的数据结构: {data: {code: 200, data: {...}}}
      data = response.data.data
    }
    
    if (data) {
      console.log('主机数据:', data)
      // 检查组件是否仍然挂载
      if (!isComponentMounted) {
        return
      }
      hostInfo.value = data
    } else {
      // 检查组件是否仍然挂载
      if (!isComponentMounted) {
        return
      }
      error.value = t.value('dataFormatError')
      console.error('API返回错误:', response)
    }
  } catch (err) {
    // 检查组件是否仍然挂载
    if (!isComponentMounted) {
      return
    }
    console.error('获取主机信息失败:', err)
    error.value = err.message || t.value('getHostInfoFailed')
  } finally {
    // 检查组件是否仍然挂载
    if (!isComponentMounted) {
      return
    }
    loading.value = false
  }
}

// 组件挂载时获取数据
onMounted(() => {
  fetchHostInfo()
})
</script>

<style scoped>
.system-info {
  background: var(--color-bg-1);
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  height: 390px;
  display: flex;
  flex-direction: column;
}

/* 平板适配 */
@media (max-width: 1024px) {
  .system-info {
    height: 450px;
    padding: 12px;
  }
}

/* 移动端适配 */
@media (max-width: 768px) {
  .system-info {
    height: 430px;
    padding: 10px;
    border-radius: 6px;
  }
}

/* 小屏幕适配 */
@media (max-width: 480px) {
  .system-info {
    height: 390px;
    padding: 8px;
    border-radius: 4px;
  }
}

/* 超小屏幕适配 */
@media (max-width: 320px) {
  .system-info {
    height: 360px;
    padding: 6px;
    border-radius: 4px;
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

/* 平板适配 */
@media (max-width: 1024px) {
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

/* 移动端适配 */
@media (max-width: 768px) {
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

/* 小屏幕适配 */
@media (max-width: 480px) {
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

/* 超小屏幕适配 */
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
[arco-theme="dark"] .system-info {
  background: var(--color-bg-1) !important;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3) !important;
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
</style>