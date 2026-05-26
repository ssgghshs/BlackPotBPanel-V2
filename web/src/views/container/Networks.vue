<template>
  <a-card class="containers-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('networks') }}</span>
        <div style="display: flex; gap: 10px;">
          <a-button type="outline" @click="showCreateNetworkDrawer">{{ t('create') }}</a-button>
          <a-button type="outline" danger @click="showPruneNetworksModal" :disabled="!selectedHostId">
            {{ t('pruneNetworks')}}  
          </a-button>
        </div>
      </div>
    </template>

    <!-- 网络列表表格 -->
    <a-table 
      :columns="columns" 
      :data="networks" 
      :loading="loading" 
      :pagination="pagination"
      @page-change="handlePageChange"
      @page-size-change="handlePageSizeChange"
      :scroll="scroll"
      row-key="id"
    >
      <template #id_short="{ record }">
        <a-tooltip :content="record.id" placement="top">
          <span>{{ record.id_short }}</span>
        </a-tooltip>
      </template>
      <template #name="{ record }">
        <a-tag color="blue" style="margin-right: 4px;">
          {{ record.name }}
        </a-tag>
      </template>
      <template #labels="{ record }">
        <div v-if="record.labels && record.labels.length > 0">
          <a-tooltip 
            v-for="(label, index) in record.labels" 
            :key="index" 
            :content="label" 
            placement="top"
          >
            <a-tag 
              color="green"
              style="margin-right: 4px; margin-bottom: 4px; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: inline-block;"
            >
              {{ label }}
            </a-tag>
          </a-tooltip>
        </div>
        <span v-else>-</span>
      </template>
      <template #subnet="{ record }">
        {{ record.subnet || '-' }}
      </template>
      <template #gateway="{ record }">
        {{ record.gateway || '-' }}
      </template>
      <template #createdAt="{ record }">
        {{ formatDate(record.createdAt) }}
      </template>
      <template #operation="{ record }">
          <a-button type="text" size="small" @click="openNetworkDetail(record)">{{ t('detail') }}</a-button>
          <a-dropdown>
            <a-button type="text" size="small">
              {{ t('more') }}
              <icon-down />
            </a-button>
            <template #content>
              <a-doption key="delete" :disabled="!canDeleteNetwork(record)" @click="showDeleteNetworkModal(record)" danger>
                <icon-delete />
                {{ t('delete') }}
              </a-doption>
            </template>
          </a-dropdown>
        </template>
    </a-table>

    <!-- 删除网络确认对话框 -->
    <a-modal 
      v-model:visible="deleteNetworkModalVisible" 
      :title="t('confirmDelete')" 
      @ok="confirmDeleteNetwork" 
      @cancel="cancelDeleteNetwork"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
    >
      <p>{{ t('confirmDeleteNetwork')}}</p>
    </a-modal>

    <!-- 网络详情抽屉 -->
    <network-inspect
      v-model:visible="networkInspectVisible"
      :network-info="selectedNetwork"
      @close="handleNetworkInspectClose"
    />

    <!-- 网络创建抽屉 -->
    <network-create
      v-model:visible="createNetworkVisible"
      @success="handleNetworkCreated"
    />
    
    <!-- 清理未使用网络确认对话框 -->
    <a-modal 
      v-model:visible="pruneNetworksModalVisible" 
      :title="t('confirmClear')" 
      @ok="confirmPruneNetworks" 
      @cancel="cancelPruneNetworks"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
    >
      <p>{{ t('confirmClearUnusedNetworks') }}</p>
    </a-modal>
  </a-card>
</template>

<script setup>
import { reactive, ref, computed, onMounted, onUnmounted } from 'vue';
import { t } from '../../utils/locale';
import { getNetworks, deleteNetwork as deleteNetworkApi, pruneNetworks as pruneNetworksApi } from '../../api/container';
import { Message } from '@arco-design/web-vue';
import { Table as ATable, Tag as ATag, Tooltip as ATooltip, Button as AButton, Dropdown as ADropdown, Doption as ADoption } from '@arco-design/web-vue';
import { IconDown, IconDelete } from '@arco-design/web-vue/es/icon';
import NetworkInspect from '../../components/container/NetworkInspect.vue';
import NetworkCreate from '../../components/container/NetworkCreate.vue';

// 响应式数据
const networks = ref([]);
const loading = ref(false);
const selectedHostId = ref(null);
const deleteNetworkModalVisible = ref(false);
const networkToDelete = ref({});
const networkInspectVisible = ref(false);
const selectedNetwork = ref({});
const createNetworkVisible = ref(false);
const pruneNetworksModalVisible = ref(false);
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
    title: t.value('id'),
    dataIndex: 'id_short',
    slotName: 'id_short',
    width: 120
  },
  {
    title: t.value('name'),
    dataIndex: 'name',
    slotName: 'name',
    width: 150
  },
  {
    title: t.value('driver'),
    dataIndex: 'driver',
    width: 120
  },
  {
    title: t.value('subnet'),
    dataIndex: 'subnet',
    slotName: 'subnet',
    width: 150
  },
  {
    title: t.value('gateway'),
    dataIndex: 'gateway',
    slotName: 'gateway',
    width: 150
  },
  {
    title: t.value('labels'),
    dataIndex: 'labels',
    slotName: 'labels',
    width: 200
  },
  {
    title: t.value('createdAt'),
    dataIndex: 'createdAt',
    slotName: 'createdAt',
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

// 获取网络列表
const fetchNetworks = async (nodeId, page = 1) => {
  if (!nodeId) return;
  
  try {
    loading.value = true;
    console.log('开始请求网络列表，节点ID:', nodeId);
    const response = await getNetworks(nodeId, {
      page: page,
      page_size: pagination.pageSize
    });
    
    console.log('获取到网络列表响应:', response);
    
    // 调整响应结构处理，适配不同可能的后端返回格式
    let networkData = [];
    let totalCount = 0;
    
    if (response && response.items && Array.isArray(response.items)) {
      // 后端直接返回items和total的情况
      networkData = response.items;
      totalCount = response.total || response.items.length;
    } else if (response && response.data && response.data.items && Array.isArray(response.data.items)) {
      // 后端返回嵌套结构的情况
      networkData = response.data.items;
      totalCount = response.data.total || response.data.items.length;
    } else {
      // 未知格式，尝试作为直接数据处理
      console.warn('响应格式不符合预期，尝试直接处理:', response);
      networkData = Array.isArray(response) ? response : [];
      totalCount = networkData.length;
    }
    
    // 处理每个网络数据，添加id_short字段
    networks.value = networkData.map(network => ({
      ...network,
      id_short: network.id ? network.id.substring(0, 12) : ''
    }));
    pagination.total = totalCount;
    
    console.log('处理后的网络数据:', networks.value);
  } catch (error) {
    console.error('获取网络列表失败:', error);
    Message.error(t.value('getNetworksFailed'));
    networks.value = [];
    pagination.total = 0;
  } finally {
    loading.value = false;
  }
};

// 判断网络是否可以删除（某些默认网络如bridge、host等不应该被删除）
const canDeleteNetwork = (network) => {
  // 排除默认网络
  const defaultNetworks = ['bridge', 'host', 'none', 'ingress'];
  return !defaultNetworks.includes(network.name);
};

// 处理分页变化
const handlePageChange = (page) => {
  pagination.current = page;
  fetchNetworks(selectedHostId.value, page);
};

// 处理分页大小变化
const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize;
  pagination.current = 1; // 重置到第一页
  fetchNetworks(selectedHostId.value, 1);
};

// 处理容器宿主变化事件
const handleContainerHostChange = (event) => {
  selectedHostId.value = event.detail.hostId;
  pagination.current = 1;
  fetchNetworks(selectedHostId.value, 1);
};

// 打开网络详情
const openNetworkDetail = (network) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  selectedNetwork.value = network;
  networkInspectVisible.value = true;
};

// 显示删除网络确认对话框
const showDeleteNetworkModal = (network) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  if (!canDeleteNetwork(network)) {
    Message.warning(t.value('cannotDeleteDefaultNetwork'));
    return;
  }
  
  networkToDelete.value = network;
  deleteNetworkModalVisible.value = true;
};

// 取消删除网络
const cancelDeleteNetwork = () => {
  deleteNetworkModalVisible.value = false;
  networkToDelete.value = {};
};

// 确认删除网络
const confirmDeleteNetwork = async () => {
  try {
    loading.value = true;
    // 调用删除网络API
    await deleteNetworkApi(selectedHostId.value, networkToDelete.value.id, { force: false });
    Message.success(t.value('deleteNetworkSuccess'));
    // 使用setTimeout延迟重新获取网络列表
    setTimeout(() => {
      fetchNetworks(selectedHostId.value);
    }, 500);
  } catch (error) {
    console.error('删除网络失败:', error);
    // 处理API返回的错误信息
    const errorMsg = error.response?.data?.detail || error.message || t.value('deleteNetworkFailed');
    Message.error(errorMsg);
  } finally {
    loading.value = false;
    deleteNetworkModalVisible.value = false;
    networkToDelete.value = {};
  }
};

// 组件挂载时
onMounted(() => {
  // 从localStorage获取已保存的宿主ID
  const savedHostId = localStorage.getItem('selectedContainerHostId');
  if (savedHostId) {
    selectedHostId.value = savedHostId;
    fetchNetworks(savedHostId, 1);
  }
  
  // 监听宿主变化事件
  window.addEventListener('containerHostChanged', handleContainerHostChange);
});

// 处理网络详情抽屉关闭
const handleNetworkInspectClose = () => {
  networkInspectVisible.value = false;
  selectedNetwork.value = {};
};

// 显示创建网络抽屉
const showCreateNetworkDrawer = () => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  createNetworkVisible.value = true;
};

// 处理网络创建成功
const handleNetworkCreated = () => {
  // 重新获取网络列表
  fetchNetworks(selectedHostId.value, pagination.current);
};

// 显示清理未使用网络确认对话框
const showPruneNetworksModal = () => {
  try {
    if (!selectedHostId.value) {
      Message.warning(t.value('pleaseSelectHost'));
      return;
    }
    pruneNetworksModalVisible.value = true;
  } catch (error) {
    console.error('Error showing prune networks modal:', error);
    Message.error(t.value('operationFailed'));
  }
};

// 取消清理未使用网络
const cancelPruneNetworks = () => {
  pruneNetworksModalVisible.value = false;
};

// 确认清理未使用网络
const confirmPruneNetworks = async () => {
  try {
    loading.value = true;
    const response = await pruneNetworksApi(selectedHostId.value);
    Message.success(t.value('pruneNetworksSuccess', { count: response.pruned || 0 }));
    // 重新加载网络列表
    fetchNetworks(selectedHostId.value, 1);
  } catch (error) {
    console.error('清理未使用网络失败:', error);
    Message.error(error.message || t.value('pruneNetworksFailed'));
  } finally {
    loading.value = false;
    pruneNetworksModalVisible.value = false;
  }
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
</style>