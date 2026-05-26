<template>
  <a-card class="waf-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('blackwhite') }}</span>
      </div>
    </template>

<!--  内容区域  -->
    <a-tabs position="left" v-model:activeKey="activeTab">
      <a-tab-pane key="1" :title="t('ipblacklist')">
        <!-- 黑名单表格 -->
        <div class="table-container">
          <div class="search-filters">
            <a-input
              v-model="searchFilters.name"
              :placeholder="t('name')"
              size="small"
              allow-clear
              @change="applyFilters"
              class="search-input"
            />
            <a-input
              v-model="searchFilters.ip"
              :placeholder="t('ipAddress')"
              size="small"
              allow-clear
              @change="applyFilters"
              class="search-input"
            />
            <div class="flex-grow"></div>
            <a-button type="outline" size="small" @click="fetchBlackWhiteList" :loading="loading" class="refresh-btn">
              {{ t('refresh') }}
            </a-button>
            <a-button type="outline" size="small" @click="handleAdd('black')">{{ t('add') }}</a-button>
          </div>
          
          <a-table 
            :columns="blackListColumns" 
            :data="filteredBlackList" 
            :loading="loading"
            :pagination="blackListPagination"
            @page-change="handleBlackListPageChange"
            @page-size-change="handleBlackListPageSizeChange"
            :scroll="scroll"
            row-key="name"
          >
            <template #enabled="{ record }">
              <a-switch v-model="record.enabled" size="small" @change="handleEnableChange('black', record.name, record.enabled)" />
            </template>
            <template #ips="{ record }">
              <div class="ip-list">
                <a-tag v-for="(ip, index) in record.ips" :key="index" size="small" class="ip-tag">
                  {{ ip }}
                </a-tag>
              </div>
            </template>
            <template #operation="{ record }">
              <a-link type="text" size="small" @click="handleEdit('black', record)">{{ t('edit') }}</a-link>
              <a-link v-if="record.name !== 'Blocked IPs' && record.name !== 'Intelligence Blacklist Ips'"  type="text" size="small" status="danger" @click="handleDelete('black', record.name)">{{ t('delete') }}</a-link>
            </template>
          </a-table>
        </div>
      </a-tab-pane>
      <a-tab-pane key="2" :title="t('ipwhitelist')">
        <!-- 白名单表格 -->
        <div class="table-container">
          <div class="search-filters">
            <a-input
              v-model="searchFilters.name"
              :placeholder="t('name')"
              size="small"
              allow-clear
              @change="applyFilters"
              class="search-input"
            />
            <a-input
              v-model="searchFilters.ip"
              :placeholder="t('ipAddress')"
              size="small"
              allow-clear
              @change="applyFilters"
              class="search-input"
            />
            <div class="flex-grow"></div>
            <a-button type="outline" size="small" @click="fetchBlackWhiteList" :loading="loading" class="refresh-btn">
              {{ t('refresh') }}
            </a-button>
            <a-button type="outline" size="small" @click="handleAdd('white')">{{ t('add') }}</a-button>
          </div>
          
          <a-table 
            :columns="whiteListColumns" 
            :data="filteredWhiteList" 
            :loading="loading"
            :pagination="whiteListPagination"
            @page-change="handleWhiteListPageChange"
            @page-size-change="handleWhiteListPageSizeChange"
            :scroll="scroll"
            row-key="name"
          >
            <template #enabled="{ record }">
              <a-switch v-model="record.enabled" size="small" @change="handleEnableChange('white', record.name, record.enabled)" />
            </template>
            <template #ips="{ record }">
              <div class="ip-list">
                <a-tag v-for="(ip, index) in record.ips" :key="index" size="small" class="ip-tag">
                  {{ ip }}
                </a-tag>
              </div>
            </template>
            <template #operation="{ record }">
              <a-link type="text" size="small" @click="handleEdit('white', record)">{{ t('edit') }}</a-link>
              <a-link type="text" size="small" status="danger" @click="handleDelete('white', record.name)">{{ t('delete') }}</a-link>
            </template>
          </a-table>
        </div>
      </a-tab-pane>
      <a-tab-pane key="3" :title="t('urlwhitelist')">
        <UrlWhite />
      </a-tab-pane>
    </a-tabs>

    <!-- 编辑抽屉 -->
    <a-drawer
      v-model:visible="editModalVisible"
      :title="isEdit ? t('edit') : t('add')"
      width="600px"
      @close="handleEditCancel"
      :footer="false"
    >
      <div class="drawer-content">
        <a-form :model="editForm" layout="vertical">
          <a-form-item :label="t('name')">
            <a-input v-model="editForm.name" :placeholder="t('name')" required />
          </a-form-item>
          <a-form-item :label="t('description')">
            <a-textarea v-model="editForm.description" :placeholder="t('description')" :rows="3" />
          </a-form-item>
          <a-form-item :label="t('enabled')">
            <a-switch v-model="editForm.enabled" />
          </a-form-item>
          <a-form-item :label="t('ipList')">
            <a-textarea v-model="editForm.ipsText" :placeholder="t('ipListPlaceholder')" :rows="5" />
          </a-form-item>
          <div class="drawer-footer">
            <a-button @click="handleEditCancel">{{ t('cancel') }}</a-button>
            <a-button type="primary" @click="handleEditSubmit">{{ t('confirm') }}</a-button>
          </div>
        </a-form>
      </div>
    </a-drawer>

    <!-- 删除确认对话框 -->
    <a-modal
      v-model:visible="deleteModalVisible"
      :title="t('deleteIPgroupConfirm')"
      @ok="handleDeleteSubmit"
      @cancel="handleDeleteCancel"
    >
      <p>{{ t('deleteIPgroupConfirmMessage', { name: deleteTarget.name }) }}</p>
    </a-modal>
  </a-card>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue';
import { t } from '../../utils/locale';
import { getBlackWhiteList, addBlackWhiteGroup, updateBlackWhiteGroup, deleteBlackWhiteGroup } from '../../api/waf';
import { Message } from '@arco-design/web-vue';
import UrlWhite from '../../components/waf/UrlWhite.vue';

const activeTab = ref('1');
const loading = ref(false);
const blackWhiteList = ref({ white_list: [], black_list: [] });
const searchFilters = reactive({ name: '', ip: '' });

// 黑名单分页
const blackListPagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showTotal: true,
  showJumper: true,
  pageSizeOptions: [10, 20, 50, 100],
  showPageSize: true
});

// 白名单分页
const whiteListPagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showTotal: true,
  showJumper: true,
  pageSizeOptions: [10, 20, 50, 100],
  showPageSize: true
});

const scroll = {
  x: 1000,
  y: 600
};

// 过滤后的黑名单
const filteredBlackList = computed(() => {
  let filtered = [...blackWhiteList.value.black_list];
  
  if (searchFilters.name) {
    const nameFilter = searchFilters.name.toLowerCase();
    filtered = filtered.filter(item => 
      item.name.toLowerCase().includes(nameFilter)
    );
  }
  
  if (searchFilters.ip) {
    const ipFilter = searchFilters.ip.toLowerCase();
    filtered = filtered.filter(item => 
      item.ips.some(ip => ip.toLowerCase().includes(ipFilter))
    );
  }
  
  blackListPagination.total = filtered.length;
  const start = (blackListPagination.current - 1) * blackListPagination.pageSize;
  const end = start + blackListPagination.pageSize;
  return filtered.slice(start, end);
});

// 过滤后的白名单
const filteredWhiteList = computed(() => {
  let filtered = [...blackWhiteList.value.white_list];
  
  if (searchFilters.name) {
    const nameFilter = searchFilters.name.toLowerCase();
    filtered = filtered.filter(item => 
      item.name.toLowerCase().includes(nameFilter)
    );
  }
  
  if (searchFilters.ip) {
    const ipFilter = searchFilters.ip.toLowerCase();
    filtered = filtered.filter(item => 
      item.ips.some(ip => ip.toLowerCase().includes(ipFilter))
    );
  }
  
  whiteListPagination.total = filtered.length;
  const start = (whiteListPagination.current - 1) * whiteListPagination.pageSize;
  const end = start + whiteListPagination.pageSize;
  return filtered.slice(start, end);
});

// 黑名单表格列
const blackListColumns = [
  {
    title: t.value('name'),
    dataIndex: 'name',
    width: 150
  },
  {
    title: t.value('description'),
    dataIndex: 'description',
    width: 200,
    ellipsis: true,
    tooltip: true
  },
  {
    title: t.value('enabled'),
    dataIndex: 'enabled',
    slotName: 'enabled',
    width: 100
  },
  {
    title: t.value('ipList'),
    dataIndex: 'ips',
    slotName: 'ips',
    width: 300
  },
  {
    title: t.value('action'),
    dataIndex: 'operation',
    slotName: 'operation',
    width: 150,
    fixed: 'right'
  }
];

// 白名单表格列
const whiteListColumns = [
  {
    title: t.value('name'),
    dataIndex: 'name',
    width: 150
  },
  {
    title: t.value('description'),
    dataIndex: 'description',
    width: 200,
    ellipsis: true,
    tooltip: true
  },
  {
    title: t.value('enabled'),
    dataIndex: 'enabled',
    slotName: 'enabled',
    width: 100
  },
  {
    title: t.value('ipList'),
    dataIndex: 'ips',
    slotName: 'ips',
    width: 300
  },
  {
    title: t.value('action'),
    dataIndex: 'operation',
    slotName: 'operation',
    width: 150,
    fixed: 'right'
  }
];

// 编辑相关
const editModalVisible = ref(false);
const isEdit = ref(false);
const editForm = reactive({
  name: '',
  description: '',
  enabled: true,
  ipsText: ''
});
const currentEditType = ref('');
const currentEditName = ref('');

// 删除相关
const deleteModalVisible = ref(false);
const deleteTarget = reactive({ type: '', name: '' });

// 获取黑白名单数据
const fetchBlackWhiteList = async () => {
  loading.value = true;
  try {
    const response = await getBlackWhiteList();
    if (response && (response.white_list || response.black_list)) {
      blackWhiteList.value = {
        white_list: response.white_list || [],
        black_list: response.black_list || []
      };
    }
  } catch (error) {
    console.error('获取黑白名单失败:', error);
    Message.error(t.value('fetchFailed'));
  } finally {
    loading.value = false;
  }
};

// 应用过滤
const applyFilters = () => {
  if (activeTab.value === '1') {
    blackListPagination.current = 1;
  } else {
    whiteListPagination.current = 1;
  }
};

// 黑名单分页处理
const handleBlackListPageChange = (page) => {
  blackListPagination.current = page;
};

const handleBlackListPageSizeChange = (pageSize) => {
  blackListPagination.pageSize = pageSize;
  blackListPagination.current = 1;
};

// 白名单分页处理
const handleWhiteListPageChange = (page) => {
  whiteListPagination.current = page;
};

const handleWhiteListPageSizeChange = (pageSize) => {
  whiteListPagination.pageSize = pageSize;
  whiteListPagination.current = 1;
};

// 处理启用状态变更
const handleEnableChange = async (listType, groupName, enabled) => {
  // 禁止修改Blocked IPs组的启用状态，始终保持启用
  if (groupName === 'Blocked IPs') {
    // 恢复为启用状态
    const list = blackWhiteList.value.black_list;
    const group = list.find(item => item.name === groupName);
    if (group) {
      group.enabled = true;
    }
    Message.info('Blocked IPs group must always be enabled');
    return;
  }
  
  try {
    await updateBlackWhiteGroup(listType, groupName, { enabled });
    Message.success(t.value('updateSuccess'));
  } catch (error) {
    console.error('更新状态失败:', error);
    Message.error(t.value('updateFailed'));
    // 恢复原状态
    const list = listType === 'white' ? blackWhiteList.value.white_list : blackWhiteList.value.black_list;
    const group = list.find(item => item.name === groupName);
    if (group) {
      group.enabled = !enabled;
    }
  }
};

// 处理添加
const handleAdd = (listType) => {
  currentEditType.value = listType;
  currentEditName.value = '';
  isEdit.value = false;
  
  // 重置表单
  editForm.name = '';
  editForm.description = '';
  editForm.enabled = true;
  editForm.ipsText = '';
  
  editModalVisible.value = true;
};

// 处理编辑
const handleEdit = (listType, record) => {
  currentEditType.value = listType;
  currentEditName.value = record.name;
  isEdit.value = true;
  
  editForm.name = record.name;
  editForm.description = record.description;
  editForm.enabled = record.enabled;
  editForm.ipsText = record.ips.join('\n');
  
  editModalVisible.value = true;
};

// 处理编辑提交
const handleEditSubmit = async () => {
  if (!editForm.name.trim()) {
    Message.warning(t.value('fillRequiredFields'));
    return;
  }

  const ips = editForm.ipsText.split('\n').filter(ip => ip.trim());

  try {
    const formData = {
      name: editForm.name.trim(),
      description: editForm.description.trim(),
      enabled: editForm.enabled,
      ips
    };
    
    if (isEdit.value) {
      await updateBlackWhiteGroup(currentEditType.value, currentEditName.value, formData);
      Message.success(t.value('updateSuccess'));
    } else {
      await addBlackWhiteGroup(currentEditType.value, formData);
      Message.success(t.value('addSuccess'));
    }
    
    editModalVisible.value = false;
    await fetchBlackWhiteList();
  } catch (error) {
    console.error('操作失败:', error);
    Message.error(isEdit.value ? t.value('updateFailed') : t.value('addFailed'));
  }
};

// 处理编辑取消
const handleEditCancel = () => {
  editModalVisible.value = false;
  // 重置表单
  editForm.name = '';
  editForm.description = '';
  editForm.enabled = true;
  editForm.ipsText = '';
};

// 处理删除
const handleDelete = (listType, groupName) => {
  deleteTarget.type = listType;
  deleteTarget.name = groupName;
  deleteModalVisible.value = true;
};

// 处理删除提交
const handleDeleteSubmit = async () => {
  try {
    await deleteBlackWhiteGroup(deleteTarget.type, deleteTarget.name);
    Message.success(t.value('deleteSuccess'));
    deleteModalVisible.value = false;
    await fetchBlackWhiteList();
  } catch (error) {
    console.error('删除失败:', error);
    Message.error(t.value('deleteFailed'));
  }
};

// 处理删除取消
const handleDeleteCancel = () => {
  deleteModalVisible.value = false;
  deleteTarget.type = '';
  deleteTarget.name = '';
};

onMounted(() => {
  fetchBlackWhiteList();
});
</script>

<style scoped>
.waf-container {
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

.header-buttons {
  display: flex;
  gap: 10px;
  align-items: center;
}

.table-container {
  padding: 20px;
}

.search-filters {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 20px;
}

.flex-grow {
  flex-grow: 1;
}

.search-input {
  width: 200px;
}

.ip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-height: 100px;
  overflow-y: auto;
}

.ip-tag {
  margin-bottom: 4px;
}

.desc {
  margin-top: 4px;
  color: #8c8c8c;
  font-size: 12px;
}

.drawer-content {
  padding: 20px;
}

.drawer-footer {
  margin-top: 30px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* 根据需要调整其他样式 */
</style>