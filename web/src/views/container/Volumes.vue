<template>
  <a-card class="containers-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('volumes') }}</span>
        <div style="display: flex; gap: 10px;">
          <a-button type="outline" @click="showCreateVolumeDrawer" :disabled="!selectedHostId">
            {{ t('createVolume')}}
          </a-button>
          <a-button type="outline" danger @click="showPruneVolumesModal" :disabled="!selectedHostId">
            {{ t('pruneVolumes')}}
          </a-button>
        </div>
      </div>
    </template>

    <!-- 存储卷列表表格 -->
    <a-table 
      :columns="columns" 
      :data="volumes" 
      :loading="loading" 
      :pagination="pagination"
      @page-change="handlePageChange"
      @page-size-change="handlePageSizeChange"
      :scroll="scroll"
      row-key="name"
    >
      <template #name="{ record }">
        <a-tooltip :content="record.name" placement="top">
          <span>{{ record.name_short }}</span>
        </a-tooltip>
      </template>
      <template #driver="{ record }">
        <a-tag color="blue" style="margin-right: 4px;">
          {{ record.driver }}
        </a-tag>
      </template>
      <template #labels="{ record }">
        <div v-if="record.labels && Object.keys(record.labels).length > 0">
          <a-tag 
            v-for="(value, key) in record.labels" 
            :key="key" 
            color="green"
            style="margin-right: 4px; margin-bottom: 4px"
          >
            {{ key }}{{ value ? `: ${value}` : '' }}
          </a-tag>
        </div>
        <span v-else>-</span>
      </template>
      <template #mountpoint="{ record }">
        <a-tooltip :content="record.mountpoint" placement="top">
          <span>{{ record.mountpoint_short }}</span>
        </a-tooltip>
      </template>
      <template #created_at="{ record }">
        {{ formatDate(record.created_at) }}
      </template>
      <template #operation="{ record }">
        <a-dropdown>
          <a-button type="text" size="small" @click="openVolumeDetail(record)" style="margin-left: 8px;">
            {{ t('detail') }}
          </a-button>           
          <a-button type="text" size="small" @click="showDeleteVolumeModal(record)" style="margin-left: 8px;">
              {{ t('delete') }}
          </a-button>
        </a-dropdown>
      </template>
    </a-table>

    <!-- 存储卷详情抽屉 -->
    <volumes-inspect
      v-model:visible="volumeInspectVisible"
      :volume-info="selectedVolume"
      @close="handleVolumeInspectClose"
    />

    <!-- 删除存储卷确认对话框 -->
    <a-modal 
      v-model:visible="deleteVolumeModalVisible" 
      :title="t('confirmDelete')" 
      @ok="confirmDeleteVolume" 
      @cancel="cancelDeleteVolume"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
    >
      <p>{{ t('confirmDeleteVolume')}}</p>
    </a-modal>

    <!-- 清理未使用存储卷确认对话框 -->
    <a-modal 
      v-model:visible="pruneVolumesModalVisible" 
      :title="t('confirmClear')" 
      @ok="confirmPruneVolumes" 
      @cancel="cancelPruneVolumes"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
    >
      <p>{{ t('confirmClearUnusedVolumes') || '确定要清理所有未使用的存储卷吗？此操作不可撤销。' }}</p>
    </a-modal>

    <!-- 创建存储卷抽屉 -->
    <volumes-create
      v-model:visible="createVolumeDrawerVisible"
      @success="handleCreateVolumeSuccess"
      @close="handleCreateVolumeClose"
    />
  </a-card>
</template>

<script setup>
import { reactive, ref, computed, onMounted, onUnmounted } from 'vue';
import { t } from '../../utils/locale';
import { getVolumes, deleteVolume as deleteVolumeApi, pruneVolumes as pruneVolumesApi } from '../../api/container';
import { Message } from '@arco-design/web-vue';
import { Table as ATable, Tag as ATag, Tooltip as ATooltip, Button as AButton, Dropdown as ADropdown, Doption as ADoption, Modal as AModal } from '@arco-design/web-vue';
import VolumesInspect from '../../components/container/VolumesInspect.vue';
import VolumesCreate from '../../components/container/VolumesCreate.vue';

// 响应式数据
const volumes = ref([]);
const loading = ref(false);
const selectedHostId = ref(null);
const deleteVolumeModalVisible = ref(false);
const volumeToDelete = ref({});
const volumeInspectVisible = ref(false);
const selectedVolume = ref({});
const createVolumeDrawerVisible = ref(false);
const pruneVolumesModalVisible = ref(false);
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
    title: t.value('driver'),
    dataIndex: 'driver',
    slotName: 'driver',
    width: 120
  },
  {
    title: t.value('mountpoint'),
    dataIndex: 'mountpoint',
    slotName: 'mountpoint',
    width: 250
  },
  {
    title: t.value('labels'),
    dataIndex: 'labels',
    slotName: 'labels',
    width: 200
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

// 获取存储卷列表
const fetchVolumes = async (nodeId, page = 1) => {
  if (!nodeId) return;
  
  try {
    loading.value = true;
    console.log('开始请求存储卷列表，节点ID:', nodeId);
    const response = await getVolumes(nodeId, {
      page: page,
      page_size: pagination.pageSize
    });
    
    console.log('获取到存储卷列表响应:', response);
    
    // 调整响应结构处理，适配不同可能的后端返回格式
    let volumeData = [];
    let totalCount = 0;
    
    if (response && response.items && Array.isArray(response.items)) {
      // 后端直接返回items和total的情况
      volumeData = response.items;
      totalCount = response.total || response.items.length;
    } else if (response && response.data && response.data.items && Array.isArray(response.data.items)) {
      // 后端返回嵌套结构的情况
      volumeData = response.data.items;
      totalCount = response.data.total || response.data.items.length;
    } else {
      // 未知格式，尝试作为直接数据处理
      console.warn('响应格式不符合预期，尝试直接处理:', response);
      volumeData = Array.isArray(response) ? response : [];
      totalCount = volumeData.length;
    }
    
    // 处理每个存储卷数据，添加短名称和短路径字段
    volumes.value = volumeData.map(volume => ({
      ...volume,
      name_short: volume.name ? volume.name.substring(0, 15) + (volume.name.length > 15 ? '...' : '') : '',
      mountpoint_short: volume.mountpoint ? volume.mountpoint.substring(0, 30) + (volume.mountpoint.length > 30 ? '...' : '') : ''
    }));
    pagination.total = totalCount;
    
    console.log('处理后的存储卷数据:', volumes.value);
  } catch (error) {
    console.error('获取存储卷列表失败:', error);
    Message.error(t.value('getVolumesFailed') || '获取存储卷列表失败');
    volumes.value = [];
    pagination.total = 0;
  } finally {
    loading.value = false;
  }
};

// 处理分页变化
const handlePageChange = (page) => {
  pagination.current = page;
  fetchVolumes(selectedHostId.value, page);
};

// 处理分页大小变化
const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize;
  pagination.current = 1; // 重置到第一页
  fetchVolumes(selectedHostId.value, 1);
};

// 监听宿主变化事件
const handleContainerHostChange = (event) => {
  try {
    if (event && event.detail && event.detail.hostId) {
      selectedHostId.value = event.detail.hostId;
      // 确保 fetchVolumes 存在且是函数
      if (typeof fetchVolumes === 'function') {
        fetchVolumes(event.detail.hostId, 1);
      }
    }
  } catch (error) {
    console.error('Error handling container host change:', error);
  }
};

// 显示删除存储卷确认对话框
const showDeleteVolumeModal = (volume) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  volumeToDelete.value = volume;
  deleteVolumeModalVisible.value = true;
};

// 取消删除存储卷
const cancelDeleteVolume = () => {
  deleteVolumeModalVisible.value = false;
  volumeToDelete.value = {};
};

// 确认删除存储卷
const confirmDeleteVolume = async () => {
  try {
    loading.value = true;
    // 调用删除存储卷API
    await deleteVolumeApi(selectedHostId.value, volumeToDelete.value.name, { force: false });
    Message.success(t.value('deleteVolumeSuccess') || '删除存储卷成功');
    // 使用setTimeout延迟重新获取存储卷列表
    setTimeout(() => {
      fetchVolumes(selectedHostId.value);
    }, 500);
  } catch (error) {
    console.error('删除存储卷失败:', error);
    // 处理API返回的错误信息
    const errorMsg = error.response?.data?.detail || error.message || t.value('deleteVolumeFailed') || '删除存储卷失败';
    Message.error(errorMsg);
  } finally {
    loading.value = false;
    deleteVolumeModalVisible.value = false;
    volumeToDelete.value = {};
  }
};

// 打开存储卷详情抽屉
const openVolumeDetail = (volume) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  selectedVolume.value = volume;
  volumeInspectVisible.value = true;
};

// 处理存储卷详情抽屉关闭
const handleVolumeInspectClose = () => {
  volumeInspectVisible.value = false;
  selectedVolume.value = {};
};

// 显示创建存储卷抽屉
const showCreateVolumeDrawer = () => {
  try {
    if (!selectedHostId.value) {
      Message.warning(t.value('pleaseSelectHost') || '请先选择容器宿主');
      return;
    }
    createVolumeDrawerVisible.value = true;
  } catch (error) {
    console.error('Error showing create volume drawer:', error);
    Message.error(t.value('operationFailed') || '操作失败');
  }
};

// 处理创建存储卷成功
const handleCreateVolumeSuccess = (newVolume) => {
  try {
    console.log('新创建的存储卷:', newVolume);
    // 重新获取存储卷列表
    if (selectedHostId.value) {
      fetchVolumes(selectedHostId.value, pagination.current);
    }
  } catch (error) {
    console.error('Error handling create volume success:', error);
    // 即使出错也要确保抽屉关闭
    try {
      createVolumeDrawerVisible.value = false;
    } catch (err) {
      console.error('Error closing create volume drawer:', err);
    }
  }
};

// 处理创建存储卷抽屉关闭
const handleCreateVolumeClose = () => {
  try {
    if (createVolumeDrawerVisible && typeof createVolumeDrawerVisible.value !== 'undefined') {
      createVolumeDrawerVisible.value = false;
    }
  } catch (error) {
    console.error('Error closing create volume drawer:', error);
  }
};

// 显示清理未使用存储卷确认对话框
const showPruneVolumesModal = () => {
  try {
    if (!selectedHostId.value) {
      Message.warning(t.value('pleaseSelectHost') || '请先选择容器宿主');
      return;
    }
    pruneVolumesModalVisible.value = true;
  } catch (error) {
    console.error('Error showing prune volumes modal:', error);
    Message.error(t.value('operationFailed') || '操作失败');
  }
};

// 取消清理未使用存储卷
const cancelPruneVolumes = () => {
  pruneVolumesModalVisible.value = false;
};

// 确认清理未使用存储卷
const confirmPruneVolumes = async () => {
  try {
    loading.value = true;
    const response = await pruneVolumesApi(selectedHostId.value);
    Message.success(t.value('pruneVolumesSuccess', { count: response.pruned || 0 }) || `成功清理了 ${response.pruned || 0} 个未使用的存储卷`);
    // 重新加载存储卷列表
    fetchVolumes(selectedHostId.value, 1);
  } catch (error) {
    console.error('清理未使用存储卷失败:', error);
    Message.error(error.message || t.value('pruneVolumesFailed') || '清理未使用存储卷失败');
  } finally {
    loading.value = false;
    pruneVolumesModalVisible.value = false;
  }
};

// 组件挂载时
onMounted(() => {
  try {
    // 从localStorage获取已保存的宿主ID
    const savedHostId = localStorage.getItem('selectedContainerHostId');
    if (savedHostId) {
      selectedHostId.value = savedHostId;
      fetchVolumes(savedHostId, 1);
    }
    
    // 监听宿主变化事件
    window.addEventListener('containerHostChanged', handleContainerHostChange);
  } catch (error) {
    console.error('Error in onMounted:', error);
  }
});

// 组件卸载时
onUnmounted(() => {
  try {
    window.removeEventListener('containerHostChanged', handleContainerHostChange);
  } catch (error) {
    console.error('Error in onUnmounted:', error);
  }
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