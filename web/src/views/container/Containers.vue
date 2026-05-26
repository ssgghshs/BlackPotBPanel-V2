<template>
  <a-card class="containers-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('containers') }}</span>
        <div class="header-actions">
          <a-button type="outline" @click="openCreateDrawer">{{ t('createContainer') }}</a-button>
        </div>
      </div>
    </template>

    <!-- 容器列表表格 -->
    <a-table 
      :columns="columns" 
      :data="containers" 
      :loading="loading" 
      :pagination="pagination"
      @page-change="handlePageChange"
      @page-size-change="handlePageSizeChange"
      :scroll="scroll"
      row-key="containerID"
    >
      <template #state="{ record }">
        <a-tooltip position="bottom" >
          <a-tag :color="getStatusColor(record.state)" style="cursor: pointer;">
            {{ getStateText(record.state) }}
          </a-tag>
          <template #content>
            <div class="state-tooltip">
              <a-button 
                v-if="record.state !== 'running'" 
                type="text" 
                size="small" 
                @click="handleStartContainer(record)"
                class="state-action-btn"
              >
                <icon-play-circle />
                {{ t('start') }}
              </a-button>
              <a-button 
                v-if="record.state === 'running'" 
                type="text" 
                size="small" 
                @click="handlePauseContainer(record)"
                class="state-action-btn"
              >
                <icon-record-stop />
                {{ t('pause') }}
              </a-button>
              <a-button 
                v-if="record.state === 'paused'" 
                type="text" 
                size="small" 
                @click="handleUnpauseContainer(record)"
                class="state-action-btn"
              >
                <icon-up-circle />
                {{ t('unpause') }}
              </a-button>
              <a-button 
                v-if="record.state === 'running'" 
                type="text" 
                size="small" 
                @click="handleRestartContainer(record)"
                class="state-action-btn"
              >
                <icon-refresh />
                {{ t('restart') }}
              </a-button>
              <a-button 
                v-if="record.state === 'running' || record.state === 'paused'" 
                type="text" 
                size="small" 
                @click="handleStopContainer(record)"
                class="state-action-btn"
              >
                <icon-stop/>
                {{ t('stop') }}
              </a-button>
            </div>
          </template>
        </a-tooltip>
      </template>
      <template #network="{ record }">
        <div v-if="record.network && record.network.length > 0">
          <div v-for="(ip, index) in record.network" :key="index" class="network-item">
            {{ ip }}
          </div>
        </div>
        <span v-else>-</span>
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
      <template #resource="{ record }">
        <a-tooltip v-if="containerStats[record.containerID]" position="right">
          <div class="resource-summary">
            <div class="resource-item">CPU: {{ containerStats[record.containerID].cpu_percent }}%</div>
            <div class="resource-item">{{ t('memory') }}: {{ containerStats[record.containerID].memory_percent }}%</div>
          </div>
          <template #content>
            <div class="resource-tooltip">
              <div class="resource-tooltip-row">
                <div class="resource-tooltip-item">
                  <span class="resource-label">{{ t('memoryUsage') }}:</span>
                  <span class="resource-value">{{ formatBytes(containerStats[record.containerID].memory_usage) }}</span>
                </div>
                <div class="resource-tooltip-item">
                  <span class="resource-label">{{ t('networkRx') }}:</span>
                  <span class="resource-value">{{ formatBytes(containerStats[record.containerID].network_rx_bytes) }}</span>
                </div>
                <div class="resource-tooltip-item">
                  <span class="resource-label">{{ t('blockRead') }}:</span>
                  <span class="resource-value">{{ formatBytes(containerStats[record.containerID].block_read_bytes) }}</span>
                </div>
              </div>
              <div class="resource-tooltip-row">
                <div class="resource-tooltip-item">
                  <span class="resource-label">{{ t('memoryLimit') }}:</span>
                  <span class="resource-value">{{ formatBytes(containerStats[record.containerID].memory_limit) }}</span>
                </div>
                <div class="resource-tooltip-item">
                  <span class="resource-label">{{ t('networkTx') }}:</span>
                  <span class="resource-value">{{ formatBytes(containerStats[record.containerID].network_tx_bytes) }}</span>
                </div>
                <div class="resource-tooltip-item">
                  <span class="resource-label">{{ t('blockWrite') }}:</span>
                  <span class="resource-value">{{ formatBytes(containerStats[record.containerID].block_write_bytes) }}</span>
                </div>
              </div>
            </div>
          </template>
        </a-tooltip>
        <span v-else-if="resourceLoading && record.state === 'running'">
          {{ t('loading') }}
        </span>
        <span v-else>-</span>
      </template>
      <template #operation="{ record }">
        <a-button type="text" size="small" @click="openContainerInspect(record)">{{ t('detail') }}</a-button>
        <a-dropdown>
          <a-button type="text" size="small">
            {{ t('more') }}
            <icon-down />
          </a-button>
          <template #content>
            <a-doption key="log" @click="openContainerLog(record)">
              <icon-bookmark/>
              {{ t('log') }}
            </a-doption>
            <a-doption key="terminal" @click="openContainerTerminal(record)">
              <CodeOutlined />  
              {{ t('terminal') }}
            </a-doption>
            <!-- 容器监控 -->
            <a-doption key="monitor" @click="openContainerMonitor(record)">
              <icon-computer />
              {{ t('monitor') }}
            </a-doption>
            <!-- 容器提交镜像 -->
            <a-doption key="commit" @click="openContainerCommit(record)">
              <icon-save />
              {{ t('commit') }}
            </a-doption>
            <a-doption key="delete" @click="handleDeleteContainer(record)" danger>
              <icon-delete />
              {{ t('delete') }}
            </a-doption>
          </template>
        </a-dropdown>
      </template>
    </a-table>

    <!-- 容器详情模态框 -->
    <ContainerInspect 
      v-model:visible="inspectModalVisible" 
      :containerInfo="selectedContainer" 
    />
    
    <!-- 容器日志抽屉 -->
    <ContainerLog 
      v-model:visible="logDrawerVisible" 
      :containerInfo="selectedContainer" 
    />
    
    <!-- 容器终端抽屉 -->
    <ContainerTerminal 
      v-model:visible="terminalVisible" 
      :nodeId="selectedHostId || ''" 
      :containerInfo="selectedContainer" 
      :terminalConfig="terminalConfig" 
    />
    
    <!-- 容器终端设置对话框 -->
    <a-modal 
      v-model:visible="terminalConfigVisible" 
      :title="t('containerTerminalSettings')" 
      @ok="handleTerminalConfigConfirm" 
      @cancel="handleTerminalConfigCancel"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
    >
      <a-form layout="vertical" :model="terminalConfig">
        <a-form-item :label="t('shell')">
          <a-select 
            v-model="terminalConfig.shell" 
            :allow-clear="true"
          >
            <a-option value="bash">bash</a-option>
            <a-option value="sh">sh</a-option>
            <a-option value="ash">ash</a-option>
          </a-select>
        </a-form-item>
        <a-form-item :label="t('user')">
          <a-input 
            v-model="terminalConfig.user" 
            :placeholder="t('enterUserName')" 
            :allow-clear="true"
          />
        </a-form-item>
      </a-form>
    </a-modal>
    
    <!-- 创建容器抽屉 -->
    <ContainerCreate 
      v-model:visible="createDrawerVisible"
      @success="handleCreateSuccess"
    />
    
    <!-- 删除容器确认对话框 -->
     <a-modal 
       v-model:visible="deleteModalVisible" 
       :title="t('deleteContainerConfirmTitle')" 
       @ok="confirmDeleteContainer" 
       @cancel="cancelDeleteContainer"
       :ok-text="t('confirm')"
       :cancel-text="t('cancel')"
     >
       <p>{{ t('deleteContainerConfirmMessage') }}</p>
     </a-modal>
     
     <!-- 容器监控抽屉 -->
     <ContainerMonitor
       v-model:visible="monitorDrawerVisible"
       :container-info="selectedContainer"
     />
     
     <!-- 容器提交抽屉 -->
     <ContainerCommit
       v-model:visible="commitDrawerVisible"
       :containerInfo="selectedContainer"
       :nodeId="selectedHostId || ''"
       @success="handleCommitSuccess"
     />
  </a-card>
</template>

<script setup>
import { reactive, ref, computed, onMounted, onUnmounted } from 'vue';
import { t } from '../../utils/locale';
import { getNodeContainers, startContainer, stopContainer, pauseContainer, unpauseContainer, restartContainer, deleteContainer, getContainerStats } from '../../api/container';
import { Message, Tooltip as ATooltip } from '@arco-design/web-vue';
import { Table as ATable, Tag as ATag, Button as AButton, Select as ASelect, Option as AOption, Form as AForm, FormItem as AFormItem } from '@arco-design/web-vue';
import { IconDown, IconBookmark, IconPlayCircle, IconStop, IconRecordStop, IconUpCircle, IconRefresh, IconDelete, IconComputer, IconSave } from '@arco-design/web-vue/es/icon';
import ContainerLog from '../../components/container/ContainerLog.vue';
import ContainerInspect from '../../components/container/ContainerInspect.vue';
import ContainerTerminal from '../../components/container/ContainerTerminal.vue';
import ContainerCreate from '../../components/container/ContainerCreate.vue';
import ContainerMonitor from '../../components/container/ContainerMonitor.vue';
import ContainerCommit from '../../components/container/ContainerCommit.vue';
import { CodeOutlined } from '@ant-design/icons-vue';

// 响应式数据
const containers = ref([]);
const loading = ref(false);
const selectedHostId = ref(null);
const logDrawerVisible = ref(false);
const inspectModalVisible = ref(false);
const terminalVisible = ref(false);
const terminalConfigVisible = ref(false);
const terminalConfig = ref({ shell: 'sh', user: '' });
const createDrawerVisible = ref(false);
const selectedContainer = ref({});
const deleteModalVisible = ref(false);
const containerToDelete = ref({});
const containerStats = ref({}); // 存储容器资源占用信息
const resourceLoading = ref(false); // 资源加载状态
const monitorDrawerVisible = ref(false); // 容器监控抽屉可见状态
const commitDrawerVisible = ref(false); // 容器提交抽屉可见状态
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
      width: 150
    },
    {
      title: t.value('image'),
      dataIndex: 'imageName',
      width: 250
    },
    {
      title: t.value('state'),
      dataIndex: 'state',
      slotName: 'state',
      width: 100
    },
    {
      title: t.value('resource'),
      dataIndex: 'resource',
      slotName: 'resource',
      width: 90
    },
    {
      title: t.value('network'),
      dataIndex: 'network',
      slotName: 'network',
      width: 120
    },
    {
      title: t.value('ports'),
      dataIndex: 'ports',
      slotName: 'ports',
      width: 150
    },
    {
      title: t.value('createTime'),
      dataIndex: 'createTime',
      slotName: 'createTime',
      width: 180
    },
    {      
      title: t.value('action'),      
      dataIndex: 'operation',      
      slotName: 'operation',      
      width: 130,      
      fixed: 'right'    }
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

// 格式化字节数
const formatBytes = (bytes) => {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// 获取容器资源占用信息
const fetchContainerStats = async (nodeId, containerId) => {
  if (!nodeId || !containerId) return;
  
  try {
    const stats = await getContainerStats(nodeId, containerId);
    // 更新资源信息，保存所有需要的数据
    containerStats.value[containerId] = {
      cpu_percent: stats.cpu_percentage ? stats.cpu_percentage.toFixed(2) : '0.00',
      memory_percent: stats.memory_percentage ? stats.memory_percentage.toFixed(2) : '0.00',
      memory_usage: stats.memory_usage || 0,
      memory_limit: stats.memory_limit || 0,
      network_rx_bytes: stats.network_rx_bytes || 0,
      network_tx_bytes: stats.network_tx_bytes || 0,
      block_read_bytes: stats.block_read_bytes || 0,
      block_write_bytes: stats.block_write_bytes || 0
    };
  } catch (error) {
    console.error(`获取容器${containerId}资源占用信息失败:`, error);
    // 如果获取失败，设置默认值
    containerStats.value[containerId] = {
      cpu_percent: '0.00',
      memory_percent: '0.00',
      memory_usage: 0,
      memory_limit: 0,
      network_rx_bytes: 0,
      network_tx_bytes: 0,
      block_read_bytes: 0,
      block_write_bytes: 0
    };
  }
};

// 批量获取容器资源占用信息
const fetchAllContainerStats = async (nodeId, containersList) => {
  if (!nodeId || !containersList || containersList.length === 0) return;
  
  // 设置资源加载状态
  resourceLoading.value = true;
  
  try {
    // 并行获取所有容器的资源信息
    const promises = containersList
      .filter(container => container.state === 'running') // 只获取运行中容器的资源信息
      .map(container => fetchContainerStats(nodeId, container.containerID));
    
    await Promise.all(promises);
  } catch (error) {
    console.error('批量获取容器资源信息失败:', error);
  } finally {
    // 资源获取完成后更新状态
    resourceLoading.value = false;
  }
};

// 获取容器列表
const fetchContainers = async (nodeId, page = 1) => {
  if (!nodeId) return;
  
  try {
    loading.value = true;
    const response = await getNodeContainers(nodeId);
    
    if (response && response.items && Array.isArray(response.items)) {
      // 立即更新容器列表
      containers.value = response.items;
      pagination.total = response.total || response.items.length;
      
      // 先重置资源信息，避免显示旧数据
      containerStats.value = {};
      
      // 在列表加载完成后，异步获取资源占用信息
      // 这里不使用await，让资源获取在后台进行，不阻塞UI显示
      fetchAllContainerStats(nodeId, response.items);
    } else {
      containers.value = [];
      pagination.total = 0;
      containerStats.value = {};
    }
  } catch (error) {
    console.error('获取容器列表失败:', error);
    Message.error(t.value('getContainersFailed'));
    containers.value = [];
    pagination.total = 0;
    containerStats.value = {};
  } finally {
    loading.value = false;
  }
};

// 处理分页变化
const handlePageChange = (page) => {
  pagination.current = page;
  fetchContainers(selectedHostId.value, page);
};

// 处理分页大小变化
const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize;
  pagination.current = 1; // 重置到第一页
  fetchContainers(selectedHostId.value, 1);
};

// 打开容器详情模态框
const openContainerInspect = (container) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  selectedContainer.value = {
    id: container.containerID,
    name: container.name,
    hostId: selectedHostId.value
  };
  inspectModalVisible.value = true;
};

// 打开容器日志抽屉
const openContainerLog = (container) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  selectedContainer.value = {
    id: container.containerID,
    name: container.name,
    hostId: selectedHostId.value
  };
  logDrawerVisible.value = true;
};

// 打开容器终端设置对话框
const openContainerTerminal = (container) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  selectedContainer.value = {
    id: container.containerID,
    name: container.name,
    hostId: selectedHostId.value
  };
  // 重置配置为默认值
  terminalConfig.value = { shell: 'sh', user: '' };
  // 显示终端设置对话框
  terminalConfigVisible.value = true;
};

// 处理终端配置确认
const handleTerminalConfigConfirm = () => {
  terminalConfigVisible.value = false;
  terminalVisible.value = true;
};

// 处理终端配置取消
const handleTerminalConfigCancel = () => {
  terminalConfigVisible.value = false;
  terminalConfig.value = { shell: 'bash', user: '' };
};

const openCreateDrawer = () => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  createDrawerVisible.value = true;
};

const handleCreateSuccess = () => {
  fetchContainers(selectedHostId.value);
};

// 处理启动容器
const handleStartContainer = async (container) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  try {
    loading.value = true;
    await startContainer(selectedHostId.value, container.containerID);
    Message.success(t.value('startContainerSuccess'));
    // 使用setTimeout延迟重新获取容器列表，确保DOM有足够时间更新
    setTimeout(() => {
      fetchContainers(selectedHostId.value);
    }, 500);
  } catch (error) {
    console.error('启动容器失败:', error);
    Message.error(t.value('startContainerFailed') || '启动容器失败');
    // 即使出错也确保加载状态被重置
    setTimeout(() => {
      loading.value = false;
    }, 0);
    return;
  }
  
  // 确保在异步操作完成后重置加载状态，使用setTimeout确保在DOM更新后执行
  setTimeout(() => {
    loading.value = false;
  }, 100);
};

// 显示删除确认对话框
const handleDeleteContainer = (container) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  containerToDelete.value = {
    id: container.containerID,
    name: container.name,
    hostId: selectedHostId.value
  };
  deleteModalVisible.value = true;
};

// 确认删除容器
const confirmDeleteContainer = async () => {
  try {
    loading.value = true;
    await deleteContainer(containerToDelete.value.hostId, containerToDelete.value.id, { force: true });
    Message.success(t.value('deleteContainerSuccess'));
    // 使用更长的setTimeout延迟重新获取容器列表，确保DOM有足够时间更新
    setTimeout(() => {
      fetchContainers(containerToDelete.value.hostId);
    }, 800);
  } catch (error) {
    console.error('删除容器失败:', error);
    Message.error(t.value('deleteContainerFailed'));
    // 即使出错也确保加载状态被重置
    setTimeout(() => {
      loading.value = false;
    }, 0);
    return;
  } finally {
    deleteModalVisible.value = false;
    // 确保在异步操作完成后重置加载状态，使用setTimeout确保在DOM更新后执行
    setTimeout(() => {
      loading.value = false;
    }, 100);
  }
};

// 取消删除容器
const cancelDeleteContainer = () => {
  deleteModalVisible.value = false;
  containerToDelete.value = {};
};

// 打开容器监控抽屉
const openContainerMonitor = (container) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  selectedContainer.value = {
    id: container.containerID,
    name: container.name,
    hostId: selectedHostId.value
  };
  monitorDrawerVisible.value = true;
};

// 打开容器提交抽屉
const openContainerCommit = (container) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  selectedContainer.value = {
    id: container.containerID,
    name: container.name,
    hostId: selectedHostId.value
  };
  commitDrawerVisible.value = true;
};

// 处理提交成功
const handleCommitSuccess = () => {
  fetchContainers(selectedHostId.value);
};

// 处理停止容器
const handleStopContainer = async (container) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  try {
    loading.value = true;
    await stopContainer(selectedHostId.value, container.containerID);
    Message.success(t.value('stopContainerSuccess'));
    // 使用setTimeout延迟重新获取容器列表，确保DOM有足够时间更新
    setTimeout(() => {
      fetchContainers(selectedHostId.value);
    }, 500);
  } catch (error) {
    console.error('停止容器失败:', error);
    Message.error(t.value('stopContainerFailed') || '停止容器失败');
    // 即使出错也确保加载状态被重置
    setTimeout(() => {
      loading.value = false;
    }, 0);
    return;
  }
  
  // 确保在异步操作完成后重置加载状态，使用setTimeout确保在DOM更新后执行
  setTimeout(() => {
    loading.value = false;
  }, 100);
};

// 处理暂停容器
const handlePauseContainer = async (container) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  try {
    loading.value = true;
    await pauseContainer(selectedHostId.value, container.containerID);
    Message.success(t.value('pauseContainerSuccess'));
    // 使用setTimeout延迟重新获取容器列表，确保DOM有足够时间更新
    setTimeout(() => {
      fetchContainers(selectedHostId.value);
    }, 500);
  } catch (error) {
    console.error('暂停容器失败:', error);
    Message.error(t.value('pauseContainerFailed'));
    // 即使出错也确保加载状态被重置
    setTimeout(() => {
      loading.value = false;
    }, 0);
    return;
  }
  
  // 确保在异步操作完成后重置加载状态，使用setTimeout确保在DOM更新后执行
  setTimeout(() => {
    loading.value = false;
  }, 100);
};

// 处理恢复容器
const handleUnpauseContainer = async (container) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  try {
    loading.value = true;
    await unpauseContainer(selectedHostId.value, container.containerID);
    Message.success(t.value('unpauseContainerSuccess'));
    // 使用setTimeout延迟重新获取容器列表，确保DOM有足够时间更新
    setTimeout(() => {
      fetchContainers(selectedHostId.value);
    }, 500);
  } catch (error) {
    console.error('恢复容器失败:', error);
    Message.error(t.value('unpauseContainerFailed'));
    // 即使出错也确保加载状态被重置
    setTimeout(() => {
      loading.value = false;
    }, 0);
    return;
  }
  
  // 确保在异步操作完成后重置加载状态，使用setTimeout确保在DOM更新后执行
  setTimeout(() => {
    loading.value = false;
  }, 100);
};

// 处理重启容器
const handleRestartContainer = async (container) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  try {
    loading.value = true;
    await restartContainer(selectedHostId.value, container.containerID);
    Message.success(t.value('restartContainerSuccess'));
    // 使用setTimeout延迟重新获取容器列表，确保DOM有足够时间更新
    setTimeout(() => {
      fetchContainers(selectedHostId.value);
    }, 500);
  } catch (error) {
    console.error('重启容器失败:', error);
    Message.error(t.value('restartContainerFailed'));
    // 即使出错也确保加载状态被重置
    setTimeout(() => {
      loading.value = false;
    }, 0);
    return;
  }
  
  // 确保在异步操作完成后重置加载状态
  loading.value = false;
};

// 处理容器宿主变化事件
const handleContainerHostChange = (event) => {
  selectedHostId.value = event.detail.hostId;
  pagination.current = 1;
  fetchContainers(selectedHostId.value, 1);
};

// 组件挂载时
onMounted(() => {
  // 从localStorage获取已保存的宿主ID
  const savedHostId = localStorage.getItem('selectedContainerHostId');
  if (savedHostId) {
    selectedHostId.value = savedHostId;
    fetchContainers(savedHostId, 1);
  }
  
  // 监听宿主变化事件
  window.addEventListener('containerHostChanged', handleContainerHostChange);
});

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
  justify-content: flex-start;
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

.network-item,
.port-item {
  font-size: 12px;
  line-height: 1.5;
}

.header-actions {
  margin-left: auto;
}


/* 资源展示样式 */
.resource-summary {
  cursor: pointer;
}

.resource-item {
  font-size: 12px;
  line-height: 1.5;
  white-space: nowrap;
}

/* 资源加载状态样式 */
.resource-loading {
  color: #8c8c8c;
  font-size: 12px;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
  100% {
    opacity: 1;
  }
}

/* 资源气泡样式 */
.resource-tooltip {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 400px;
}

.resource-tooltip-row {
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.resource-tooltip-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.resource-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  white-space: nowrap;
}

.resource-value {
  font-size: 13px;
  font-weight: 500;
  color: #fff;
  white-space: nowrap;
}

/* 状态气泡样式 */
.state-tooltip {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 2px 0;
}

.state-action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  justify-content: flex-start;
  color: #fff !important;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
  font-size: 12px;
  white-space: nowrap;
}

.state-action-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
}
</style>
