<template>
  <a-card class="containers-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('compose') }}</span>
        <a-button type="outline" @click="showCreateDrawer = true" :disabled="!selectedHostId">
          {{ t('create') }}
        </a-button>
      </div>
    </template>

    <!-- Compose项目列表表格 -->
    <a-table 
      :columns="columns" 
      :data="composeList" 
      :loading="loading" 
      :pagination="pagination"
      @page-change="handlePageChange"
      @page-size-change="handlePageSizeChange"
      :scroll="scroll"
      row-key="name"
    >
      <template #name="{ record }">
        <a-tooltip :content="record.name" placement="top">
          <span>{{ record.name }}</span>
        </a-tooltip>
      </template>
      <template #path="{ record }">
        <a-tooltip :content="record.path" placement="top">
          <icon-folder 
            size="large"
            :style="{
              cursor: record.compose_file === 'notfound' ? 'not-allowed' : 'pointer', 
              color: record.compose_file === 'notfound' ? '#ccc' : '#FFB300'
            }"
            @click="record.compose_file !== 'notfound' && openFileManager(record.path)"
          />
        </a-tooltip>
      </template>
      <template #status="{ record }">
        <a-tag 
          :color="getStatusColor(record.status, record.name)" 
          style="margin-right: 4px;"
        >
          {{ getStateText(record.status, record.name) }}
        </a-tag>
      </template>
      <template #created_at="{ record }">
        {{ formatDate(record.created_at) }}
      </template>
      <template #compose_file="{ record }">
        <a-tag :color="record.compose_file === 'notfound' ? 'red' : 'green'" style="margin-right: 4px;">
          {{ record.compose_file === 'notfound' ? t('notFound') : getFileName(record.compose_file) }}
        </a-tag>
      </template>
      <template #container_status="{ record }">
        <a-tooltip position="bottom" content-class="services-tooltip-popup">
          <a-tag color="cyan" style="cursor: pointer;">
            {{ record.runningCount }}/{{ record.containerCount }}
          </a-tag>
          <template #content>
            <div class="services-tooltip">
              <div 
                v-for="service in record.services || []" 
                :key="service" 
                class="service-item"
              >
                {{ service }}
              </div>
              <div v-if="!record.services || record.services.length === 0" class="service-item no-service">
                {{ t('noServices')}}
              </div>
            </div>
          </template>
        </a-tooltip>
      </template>
      <template #operation="{ record }">
        <a-button type="text" size="small" @click="showComposeDetail(record)">{{ t('detail') }}</a-button>
        <a-dropdown>
          <a-button type="text" size="small">
            {{ t('more') }}
            <icon-down />
          </a-button>
          <template #content>
            <a-doption key="logs" @click="showComposeLogs(record)">
              <icon-bookmark/>
              {{ t('log') }}
            </a-doption>
            <a-doption key="logs" @click="openFileManager(record.path)" :disabled="record.compose_file === 'notfound'">
                <icon-edit />
                {{ t('edit') }}
              </a-doption>
              <a-doption key="restart" @click="handleRestartCompose(record)" :disabled="record.compose_file === 'notfound' || operationLoading.get(`${record.name}-restart`) || (record.status !== 'running' && record.status !== 'stopped')">
                <icon-refresh />
                {{ operationLoading.get(`${record.name}-restart`) ? t('restarting') : t('restart') }}
              </a-doption>
            <a-doption key="start" @click="handleStartCompose(record)" :disabled="record.status === 'running' || record.compose_file === 'notfound' || operationLoading.get(`${record.name}-start`)">
              <icon-play-circle/>
              {{ operationLoading.get(`${record.name}-start`) ? t('starting') : t('start') }}
            </a-doption>
            <a-doption key="stop" @click="handleStopCompose(record)" :disabled="record.status !== 'running' || record.compose_file === 'notfound' || operationLoading.get(`${record.name}-stop`)" >
              <icon-stop/>
              {{ operationLoading.get(`${record.name}-stop`) ? t('stopping') : t('stop') }}
            </a-doption>
            <a-doption key="delete" @click="handleDeleteCompose(record)" :disabled="record.compose_file === 'notfound' || operationLoading.get(`${record.name}-delete`)">
              <icon-delete/>
              {{t('delete') }}
            </a-doption>
          </template>
        </a-dropdown>
      </template>
    </a-table>

  </a-card>
  
  <!-- 文件管理器组件 -->
  <file-cat
    :visible="showFileManager"
    :initial-path="selectedFilePath"
    @update:visible="(val) => { showFileManager = val }"
  />
  
  <!-- Compose日志抽屉组件 -->
  <compose-log
    :visible="showLogDrawer"
    :compose-info="selectedComposeProject"
    :host-id="String(selectedHostId)"
    @update:visible="(val) => { showLogDrawer = val }"
  />
  
  <!-- Compose容器抽屉组件 -->
  <compose-containers
    :visible="showContainersDrawer"
    :compose-info="selectedComposeProject"
    :host-id="String(selectedHostId)"
    @update:visible="(val) => { showContainersDrawer = val }"
  />
  
  <!-- Compose创建抽屉组件 -->
  <compose-create
    v-model:visible="showCreateDrawer"
    :node-id="selectedHostId"
    @created="handleProjectCreated"
  />
  
  <!-- 删除Compose确认对话框 -->
  <a-modal 
    v-model:visible="deleteModalVisible" 
    :title="t('deleteComposeConfirmTitle')" 
    @ok="confirmDeleteCompose" 
    @cancel="cancelDeleteCompose"
    :ok-text="t('confirm')"
    :cancel-text="t('cancel')"
  >
    <p>{{ t('deleteComposeConfirmMessage') }}</p>
  </a-modal>
</template>

<script setup>
import { reactive, ref, computed, onMounted, onUnmounted } from 'vue';
import { t } from '../../utils/locale';
import { getComposeList, startComposeProject, stopComposeProject, deleteComposeProject, restartComposeProject } from '../../api/container';
import { Message } from '@arco-design/web-vue';
import { Table as ATable, Tag as ATag, Tooltip as ATooltip, Button as AButton, Dropdown as ADropdown, Modal as AModal, Doption as ADoption } from '@arco-design/web-vue';
import { IconFolder, IconDown, IconBookmark, IconPlayCircle, IconStop, IconDelete, IconEdit, IconRefresh } from '@arco-design/web-vue/es/icon';
import FileCat from '../../components/file/FileCat.vue';
import ComposeLog from '../../components/container/ComposeLog.vue';
import ComposeContainers from '../../components/container/ComposeContainers.vue';
import ComposeCreate from '../../components/container/ComposeCreate.vue';

// 响应式数据
const composeList = ref([]);
const loading = ref(false);
const selectedHostId = ref(null);
const showCreateDrawer = ref(false);
// FileCat相关状态
const showFileManager = ref(false);
const selectedFilePath = ref('');
// Compose日志相关状态
const showLogDrawer = ref(false);
const selectedComposeProject = ref({});
// Compose容器抽屉相关状态
const showContainersDrawer = ref(false);
// 操作加载状态
const operationLoading = ref(new Map());
// 删除对话框相关状态
const deleteModalVisible = ref(false);
const composeToDelete = ref({});
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showTotal: true,
  showJumper: true,
  pageSizeOptions: [10, 20, 50, 100],
  showPageSize: true
});

// 表格滚动配置
const scroll = {
  x: 1300,
  y: 600
};

// 表格列定义
const columns = computed(() => [
  {
    title: t.value('name'),
    dataIndex: 'name',
    slotName: 'name',
    width: 200
  },
  {
    title: t.value('path'),
    dataIndex: 'path',
    slotName: 'path',
    width: 150
  },
  {
    title: t.value('configFile'),
    dataIndex: 'compose_file',
    slotName: 'compose_file',
    width: 150
  },
  {
    title: t.value('runningContainers'),
    dataIndex: 'container_status',
    slotName: 'container_status',
    width: 150
  },
  {
    title: t.value('status'),
    dataIndex: 'status',
    slotName: 'status',
    width: 120
  },
  {
    title: t.value('createdAt'),
    dataIndex: 'created_at',
    slotName: 'created_at',
    width: 180
  },
  {
    title: t.value('action'),
    dataIndex: 'operation',
    slotName: 'operation',
    width: 130,
    fixed: 'right'
  }
]);

// 获取文件名
const getFileName = (path) => {
  if (!path || typeof path !== 'string') return '';
  return path.substring(path.lastIndexOf('/') + 1);
};

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '';
  
  try {
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  } catch (error) {
    console.error('日期格式化错误:', error);
    return dateString; // 发生错误时返回原始字符串
  }
};

// 获取状态颜色
const getStatusColor = (state, projectName) => {
  // 检查是否正在启动、停止或重启
  if (operationLoading.value && projectName) {
    if (operationLoading.value.get(`${projectName}-start`) || operationLoading.value.get(`${projectName}-stop`) || operationLoading.value.get(`${projectName}-restart`)) {
      return 'orange';
    }
  }
  
  switch (state) {
    case 'running': return 'green';
    case 'stopped': return 'red';
    case 'exited': return 'red';
    default: return 'gray';
  }
};

// 获取状态文本
const getStateText = (state, projectName) => {
  // 检查是否正在启动、停止或重启
  if (operationLoading.value && projectName) {
    if (operationLoading.value.get(`${projectName}-start`)) {
      return t.value('starting') || 'Starting';
    }
    if (operationLoading.value.get(`${projectName}-stop`)) {
      return t.value('stopping') || 'Stopping';
    }
    if (operationLoading.value.get(`${projectName}-restart`)) {
      return t.value('restarting') || 'Restarting';
    }
  }
  
  switch (state) {
    case 'running': return t.value('running');
    case 'stopped': return t.value('stopped');
    case 'exited': return t.value('stopped');
    default: return state;
  }
};

// 获取Compose项目列表
const fetchComposeList = async (nodeId, page = 1) => {
  if (!nodeId) return;
  
  try {
    loading.value = true;
    console.log('开始请求Compose项目列表，节点ID:', nodeId);
    const response = await getComposeList(nodeId, {
      page: page,
      page_size: pagination.pageSize
    });
    
    console.log('获取到Compose项目列表响应:', response);
    
    // 调整响应结构处理，适配不同可能的后端返回格式
    let composeData = [];
    let totalCount = 0;
    
    if (response && response.items && Array.isArray(response.items)) {
      // 后端直接返回items和total的情况
      composeData = response.items;
      totalCount = response.total || response.items.length;
    } else if (response && response.data && response.data.items && Array.isArray(response.data.items)) {
      // 后端返回嵌套结构的情况
      composeData = response.data.items;
      totalCount = response.data.total || response.data.items.length;
    } else if (Array.isArray(response)) {
      // 后端直接返回数组的情况
      composeData = response;
      totalCount = response.length;
    } else {
      // 未知格式，尝试作为直接数据处理
      console.warn('响应格式不符合预期，尝试直接处理:', response);
      composeData = [];
      totalCount = 0;
    }
    
    // 处理每个Compose项目数据，添加短路径字段
    composeList.value = composeData.map(project => ({
      ...project,
      path_short: project.path ? project.path.substring(0, 30) + (project.path.length > 30 ? '...' : '') : ''
    }));
    pagination.total = totalCount;
    
    console.log('处理后的Compose项目数据:', composeList.value);
  } catch (error) {
    console.error('获取Compose项目列表失败:', error);
    Message.error(t.value('getComposeListFailed') || '获取Compose项目列表失败');
    composeList.value = [];
    pagination.total = 0;
  } finally {
    loading.value = false;
  }
};

// 处理分页变化
const handlePageChange = (page) => {
  pagination.current = page;
  fetchComposeList(selectedHostId.value, page);
};

// 处理分页大小变化
const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize;
  pagination.current = 1; // 重置到第一页
  fetchComposeList(selectedHostId.value, 1);
};

// 处理容器宿主变化事件
const handleContainerHostChange = (event) => {
  selectedHostId.value = event.detail.hostId;
  pagination.current = 1;
  fetchComposeList(selectedHostId.value, 1);
};

// 显示Compose项目详情
const showComposeDetail = (project) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  selectedComposeProject.value = project;
  showContainersDrawer.value = true;
};

// 显示Compose项目日志
const showComposeLogs = (project) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  selectedComposeProject.value = project;
  showLogDrawer.value = true;
};

// 打开文件管理器
const openFileManager = (path) => {
  selectedFilePath.value = path;
  showFileManager.value = true;
};

// 启动Compose项目
const handleStartCompose = async (project) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  try {
    // 设置操作加载状态
    const operationKey = `${project.name}-start`;
    operationLoading.value.set(operationKey, true);
    
    await startComposeProject(selectedHostId.value, project.name);
    Message.success(t.value('startSuccess') || '启动成功');
    // 刷新列表
    fetchComposeList(selectedHostId.value, pagination.current);
  } catch (error) {
    console.error('启动Compose项目失败:', error);
    Message.error(t.value('startFailed') || '启动失败');
    // 即使出错也确保加载状态被重置
    setTimeout(() => {
      operationLoading.value.delete(`${project.name}-start`);
    }, 0);
    return;
  } finally {
    // 确保在异步操作完成后重置加载状态
    setTimeout(() => {
      operationLoading.value.delete(`${project.name}-start`);
    }, 100);
  }
};

// 停止Compose项目
const handleStopCompose = async (project) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  try {
    // 设置操作加载状态
    const operationKey = `${project.name}-stop`;
    operationLoading.value.set(operationKey, true);
    
    await stopComposeProject(selectedHostId.value, project.name);
    Message.success(t.value('stopSuccess') || '停止成功');
    // 刷新列表
    fetchComposeList(selectedHostId.value, pagination.current);
  } catch (error) {
    console.error('停止Compose项目失败:', error);
    Message.error(t.value('stopFailed') || '停止失败');
    // 即使出错也确保加载状态被重置
    setTimeout(() => {
      operationLoading.value.delete(`${project.name}-stop`);
    }, 0);
    return;
  } finally {
    // 确保在异步操作完成后重置加载状态
    setTimeout(() => {
      operationLoading.value.delete(`${project.name}-stop`);
    }, 100);
  }
};

// 显示删除确认对话框
const handleDeleteCompose = (project) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  composeToDelete.value = {
    name: project.name,
    hostId: selectedHostId.value
  };
  deleteModalVisible.value = true;
};

// 确认删除Compose项目
const confirmDeleteCompose = async () => {
  try {
    // 设置操作加载状态
    const operationKey = `${composeToDelete.value.name}-delete`;
    operationLoading.value.set(operationKey, true);
    
    await deleteComposeProject(composeToDelete.value.hostId, composeToDelete.value.name);
    Message.success(t.value('deleteSuccess') || '删除成功');
    // 刷新列表
    fetchComposeList(composeToDelete.value.hostId, pagination.current);
  } catch (error) {
    console.error('删除Compose项目失败:', error);
    Message.error(t.value('deleteFailed') || '删除失败');
    // 即使出错也确保加载状态被重置
    setTimeout(() => {
      const operationKey = `${composeToDelete.value.name}-delete`;
      operationLoading.value.delete(operationKey);
    }, 0);
    return;
  } finally {
    deleteModalVisible.value = false;
    // 确保在异步操作完成后重置加载状态
    setTimeout(() => {
      const operationKey = `${composeToDelete.value.name}-delete`;
      operationLoading.value.delete(operationKey);
    }, 100);
  }
};

// 取消删除Compose项目
const cancelDeleteCompose = () => {
  deleteModalVisible.value = false;
  composeToDelete.value = {};
};

// 重启Compose项目
const handleRestartCompose = async (project) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  try {
    // 设置操作加载状态
    const operationKey = `${project.name}-restart`;
    operationLoading.value.set(operationKey, true);
    
    await restartComposeProject(selectedHostId.value, project.name);
    Message.success(t.value('restartSuccess') || '重启成功');
    // 刷新列表
    fetchComposeList(selectedHostId.value, pagination.current);
  } catch (error) {
    console.error('重启Compose项目失败:', error);
    Message.error(t.value('restartFailed') || '重启失败');
    // 即使出错也确保加载状态被重置
    setTimeout(() => {
      operationLoading.value.delete(`${project.name}-restart`);
    }, 0);
    return;
  } finally {
    // 确保在异步操作完成后重置加载状态
    setTimeout(() => {
      operationLoading.value.delete(`${project.name}-restart`);
    }, 100);
  }
};



// 组件挂载时
onMounted(() => {
  // 从localStorage获取已保存的宿主ID
  const savedHostId = localStorage.getItem('selectedContainerHostId');
  if (savedHostId) {
    selectedHostId.value = savedHostId;
    fetchComposeList(savedHostId, 1);
  }
  
  // 监听宿主变化事件
  window.addEventListener('containerHostChanged', handleContainerHostChange);
});

// 处理项目创建成功
const handleProjectCreated = () => {
  // 刷新Compose项目列表
  fetchComposeList(selectedHostId.value, pagination.current);
};

// 组件卸载时
onUnmounted(() => {
  window.removeEventListener('containerHostChanged', handleContainerHostChange);
});
</script>

<style scoped>
.containers-container {
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 15px;
  font-size: 1.3em;
  padding: 20px 20px;
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

/* 服务列表气泡样式 */
.services-tooltip {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 4px 0;
  max-height: 300px;
  overflow-y: auto;
}

.service-item {
  padding: 6px 12px;
  font-size: 13px;
  color: var(--color-text-1);
  border-radius: 6px;
  transition: background-color 0.2s;
  white-space: nowrap;
}

.service-item:hover {
  background-color: var(--color-fill-2);
}

.service-item.no-service {
  color: var(--color-text-3);
  font-style: italic;
}

/* 服务tooltip弹出框样式 */
:deep(.services-tooltip-popup) {
  border-radius: 10px !important;
  padding: 8px !important;
  max-width: 300px !important;
  background-color: var(--color-bg-popup) !important;
}

:deep(.services-tooltip-popup .arco-tooltip-content) {
  padding: 0 !important;
}

/* 自定义滚动条样式 */
.services-tooltip::-webkit-scrollbar {
  width: 6px;
  display: block;
}

.services-tooltip::-webkit-scrollbar-track {
  background: var(--color-fill-2);
  border-radius: 3px;
}

.services-tooltip::-webkit-scrollbar-thumb {
  background: var(--color-fill-4);
  border-radius: 3px;
}

.services-tooltip::-webkit-scrollbar-thumb:hover {
  background: var(--color-fill-5);
}
</style>