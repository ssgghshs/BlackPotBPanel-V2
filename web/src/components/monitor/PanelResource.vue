<template>
  <div class="panel-resource">
    <a-tooltip position="bottom" :content-style="{ padding: '12px', background: 'var(--color-bg-2)', color: 'var(--color-text-1)', border: '1px solid var(--color-border-2)' }">
      <icon-storage class="panel-resource-icon" @mouseenter="fetchPanelResource" />
      <template #content>
        <div class="panel-resource-tooltip">
          <div class="tooltip-title">{{ title }}</div>
          <div class="resource-item">
            <span class="resource-label">CPU</span>
            <span class="resource-value">{{ panelResource.cpu_percent }}%</span>
          </div>
          <div class="resource-item">
            <span class="resource-label">{{ t('memory') }}</span>
            <span class="resource-value">{{ panelResource.memory_percent }}%</span>
          </div>
          <div class="resource-item">
            <span class="resource-label">RSS</span>
            <span class="resource-value">{{ panelResource.memory_rss_mb }} MB</span>
          </div>
          <div class="resource-item">
            <span class="resource-label">VMS</span>
            <span class="resource-value">{{ panelResource.memory_vms_mb }} MB</span>
          </div>
          <div class="resource-divider"></div>
          <div class="resource-item">
            <span class="resource-label">{{ t('threads') }}</span>
            <span class="resource-value">{{ panelResource.num_threads }}</span>
          </div>
          <div class="resource-item">
            <span class="resource-label">FDs</span>
            <span class="resource-value">{{ panelResource.num_fds }}</span>
          </div>
        </div>
      </template>
    </a-tooltip>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { IconStorage } from '@arco-design/web-vue/es/icon'
import { Tooltip } from '@arco-design/web-vue'
import '@arco-design/web-vue/es/tooltip/style/css.js'
import { getPanelResource } from '../../api/monitor.js'
import { t } from '../../utils/locale'

const props = defineProps({
  title: {
    type: String,
    default: '面板资源'
  }
})

const panelResource = reactive({
  cpu_percent: '-',
  memory_percent: '-',
  memory_rss_mb: '-',
  memory_vms_mb: '-',
  num_threads: '-',
  num_fds: '-'
})

const fetchPanelResource = async () => {
  try {
    const res = await getPanelResource()
    const data = res.data || res
    panelResource.cpu_percent = data.cpu_percent ?? '-'
    panelResource.memory_percent = data.memory_percent ?? '-'
    panelResource.memory_rss_mb = data.memory_rss_mb ?? '-'
    panelResource.memory_vms_mb = data.memory_vms_mb ?? '-'
    panelResource.num_threads = data.num_threads ?? '-'
    panelResource.num_fds = data.num_fds ?? '-'
  } catch {
    // 静默失败
  }
}
</script>

<style scoped>
.panel-resource {
  display: flex;
  align-items: center;
}

.panel-resource-icon {
  font-size: 20px;
  color: #666;
  cursor: pointer;
  transition: color 0.2s ease;
}

.panel-resource-icon:hover {
  color: rgb(var(--primary-6));
}

.panel-resource-tooltip {
  min-width: 180px;
}

.tooltip-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-1);
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--color-border-2);
}

.resource-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  gap: 20px;
  font-size: 13px;
}

.resource-label {
  color: var(--color-text-3);
}

.resource-value {
  color: var(--color-text-1);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.resource-divider {
  height: 1px;
  background: var(--color-border-2);
  margin: 6px 0;
}
</style>
