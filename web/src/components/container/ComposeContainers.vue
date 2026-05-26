<template>
  <a-drawer
    :width="isMobile ? '90%' : 1000"
    v-bind:visible="visible"
    v-on:update:visible="(value) => emit('update:visible', value)"
    :title="t('composeContainers') + ': ' + (composeInfo.name || '')"
    placement="right"
    size="large"
    :footer="null"
  >
    <div class="compose-containers-drawer">
      <!-- 容器列表表格 -->
      <a-table 
        :columns="columns" 
        :data="containers" 
        :loading="loading"
        :scroll="scroll"
        row-key="name"
      >
        <template #state="{ record }">
          <a-tag :color="getStatusColor(record.state)">
            {{ getStateText(record.state) }}
          </a-tag>
        </template>
        <template #ports="{ record }">
          <div v-if="record.ports && record.ports.length > 0">
            <a-tag
              v-for="(port, index) in record.ports"
              :key="index"
              color="blue"
              class="port-tag"
              style="margin-right: 4px; margin-bottom: 4px"
            >
              {{ port }}
            </a-tag>
          </div>
          <span v-else>-</span>
        </template>
        <template #createTime="{ record }">
          {{ formatDate(record.createTime) }}
        </template>
      </a-table>
    </div>
  </a-drawer>
</template>

<script setup>
import { reactive, ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { t } from '../../utils/locale';
import { getComposeProjectContainers } from '../../api/container';
import { Message } from '@arco-design/web-vue';
import { Table as ATable, Tag as ATag, Drawer as ADrawer } from '@arco-design/web-vue';

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
const emit = defineEmits(['update:visible']);

// 响应式数据
const containers = ref([]);
const loading = ref(false);
const selectedHostId = ref(props.hostId);
const isMobile = ref(window.innerWidth < 768);

// 监听窗口大小变化
const handleResize = () => {
  isMobile.value = window.innerWidth < 768;
};

// 表格滚动配置
const scroll = {
  x: 600,
  y: 'calc(100vh - 200px)'
};

// 表格列定义
const columns = computed(() => [
  {
    title: t.value('name'),
    dataIndex: 'name',
    width: 100
  },
  {
    title: t.value('state'),
    dataIndex: 'state',
    slotName: 'state',
    width: 100
  },
  {
    title: t.value('ports'),
    dataIndex: 'ports',
    slotName: 'ports',
    width: 100
  },
  {
    title: t.value('createTime'),
    dataIndex: 'createTime',
    slotName: 'createTime',
    width: 100
  }
]);

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '';
  return dateString;
};

// 获取状态颜色
const getStatusColor = (state) => {
  switch (state) {
    case 'running': return 'green';
    case 'stopped': return 'red';
    case 'exited': return 'red';
    case 'paused': return 'orange';
    default: return 'gray';
  }
};

// 获取状态文本
const getStateText = (state) => {
  switch (state) {
    case 'running': return t.value('running');
    case 'stopped': return t.value('stopped');
    case 'exited': return t.value('stopped');
    case 'paused': return t.value('paused');
    default: return state;
  }
};

// 获取Compose项目容器列表
const fetchComposeContainers = async () => {
  if (!selectedHostId.value || !props.composeInfo.name) return;
  
  try {
    loading.value = true;
    const response = await getComposeProjectContainers(selectedHostId.value, props.composeInfo.name);
    
    if (response && response.items && Array.isArray(response.items)) {
      containers.value = response.items;
    } else {
      containers.value = [];
      Message.warning(t.value('noContainersFound'));
    }
  } catch (error) {
    console.error('获取Compose项目容器列表失败:', error);
    Message.error(t.value('getContainersFailed') || '获取容器列表失败');
    containers.value = [];
  } finally {
    loading.value = false;
  }
};

// 监听宿主变化事件
const handleContainerHostChange = (event) => {
  selectedHostId.value = event.detail.hostId;
  if (props.visible && props.composeInfo.name) {
    fetchComposeContainers();
  }
};

// 监听可见性变化
watch(() => props.visible, (newVal) => {
  if (newVal && selectedHostId.value && props.composeInfo.name) {
    fetchComposeContainers();
  }
});

// 监听hostId变化
watch(() => props.hostId, (newVal) => {
  selectedHostId.value = newVal;
  if (props.visible && props.composeInfo.name) {
    fetchComposeContainers();
  }
});

// 组件挂载时
onMounted(() => {
  window.addEventListener('containerHostChanged', handleContainerHostChange);
  window.addEventListener('resize', handleResize);
});

// 组件卸载时
onUnmounted(() => {
  window.removeEventListener('containerHostChanged', handleContainerHostChange);
  window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
.compose-containers-drawer {
  padding: 10px;
}

.port-item {
  font-size: 12px;
  line-height: 1.5;
}
</style>
