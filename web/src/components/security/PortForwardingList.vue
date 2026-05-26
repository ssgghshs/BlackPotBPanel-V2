<template>
  <div class="port-forwarding-container">
    <div class="header-actions">
      <div class="search-controls">
        <a-input
          v-model="searchInfo"
          :placeholder="t('searchPort')"
          allow-clear
          @change="handleSearch"
          class="search-input"
        />
      </div>
      <div style="display: flex; gap: 10px;">
        <a-button type="outline" size="small" @click="openAddDrawer">
          {{ t('addRule') }}
        </a-button>
      </div>
    </div>

    <div class="table-container">
      <a-table
        :columns="columns"
        :data="forwards"
        :loading="loading"
        :pagination="pagination"
        @page-change="handlePageChange"
        @page-size-change="handlePageSizeChange"
        :scroll="scroll"
        :table-layout-fixed="true"
      >
        <template #actions="{ record }">
          <a-link type="text" size="small" @click="handleEdit(record)" :disabled="!record.id">
            {{ t('edit') }}
          </a-link>
          <a-link type="text" size="small" status="danger" @click="handleDelete(record)">
            {{ t('delete') }}
          </a-link>
        </template>
      </a-table>
    </div>

    <a-modal
      v-model:visible="showDeleteDialog"
      :title="t('deleteRule')"
      @ok="handleConfirmDelete"
      @cancel="showDeleteDialog = false"
      :ok-loading="deleteLoading"
      :cancel-text="t('cancel')"
      :ok-text="t('confirm')"
    >
      <p>{{ t('deleteRuleConfirm') }}</p>
      <p v-if="deleteTarget" style="color: var(--color-text-2); font-size: 13px;">
        {{ deleteTarget.S_Address }}:{{ deleteTarget.S_Port }} -> {{ deleteTarget.T_Address }}:{{ deleteTarget.T_Port }}
      </p>
    </a-modal>

    <a-drawer
      :visible="showAddDialog"
      :title="editMode ? t('editRule') : t('addRule')"
      :width="isMobile ? '90%' : 600"
      @cancel="handleCancelAdd"
      :footer="true"
    >
      <a-form :model="addForm" layout="vertical">
        <a-form-item :label="t('sourceAddress')" required>
          <a-input v-model="addForm.S_Address" :placeholder="'0.0.0.0'" />
        </a-form-item>
        <a-form-item :label="t('sourcePort')" required>
          <a-input v-model="addForm.S_Port" :placeholder="t('sourcePort')" />
        </a-form-item>
        <a-form-item :label="t('targetAddress')" required>
          <a-input v-model="addForm.T_Address" :placeholder="t('targetAddress')" />
        </a-form-item>
        <a-form-item :label="t('targetPort')" required>
          <a-input v-model="addForm.T_Port" :placeholder="t('targetPort')" />
        </a-form-item>
        <a-form-item :label="t('protocol')" required>
          <a-select v-model="addForm.Protocol">
            <a-option value="tcp">TCP</a-option>
            <a-option value="udp">UDP</a-option>
          </a-select>
        </a-form-item>
        <a-form-item :label="t('brief')">
          <a-input v-model="addForm.brief" :placeholder="t('brief')" />
        </a-form-item>
      </a-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: 12px;">
          <a-button @click="handleCancelAdd">{{ t('cancel') }}</a-button>
          <a-button type="primary" :loading="addLoading" @click="handleSubmit">{{ t('confirm') }}</a-button>
        </div>
      </template>
    </a-drawer>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted, onUnmounted } from 'vue';
import { t } from '../../utils/locale';
import { firewallGetForwards, firewallAddForward, firewallDeleteForward, firewallUpdateForward } from '../../api/security';
import { Message } from '@arco-design/web-vue';

const forwards = ref([]);
const loading = ref(false);
const addLoading = ref(false);
const deleteLoading = ref(false);
const searchInfo = ref('');
const showAddDialog = ref(false);
const showDeleteDialog = ref(false);
const deleteTarget = ref(null);
const editMode = ref(false);
const editingId = ref(null);

const isMobile = ref(false);
const checkIsMobile = () => {
  isMobile.value = window.innerWidth < 768;
};

const addForm = reactive({
  S_Address: '0.0.0.0',
  S_Port: '',
  T_Address: '',
  T_Port: '',
  Protocol: 'tcp',
  brief: '',
});

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showTotal: true,
  showJumper: true,
  pageSizeOptions: [10, 20, 50, 100],
  showPageSize: true,
});

const scroll = { x: 'max-content', y: 600 };

const columns = computed(() => [
  { title: t.value('sourceAddress'), dataIndex: 'S_Address', key: 'S_Address', width: 150 },
  { title: t.value('sourcePort'), dataIndex: 'S_Port', key: 'S_Port', width: 100 },
  { title: t.value('targetAddress'), dataIndex: 'T_Address', key: 'T_Address', width: 150 },
  { title: t.value('targetPort'), dataIndex: 'T_Port', key: 'T_Port', width: 100 },
  { title: t.value('protocol'), dataIndex: 'Protocol', key: 'Protocol', width: 80 },
  { title: t.value('brief'), dataIndex: 'brief', key: 'brief', width: 150, ellipsis: true },
  { title: t.value('addTime'), dataIndex: 'addtime', key: 'addtime', width: 170 },
  { title: t.value('action'), dataIndex: 'actions', key: 'actions', slotName: 'actions', width: 140, fixed: 'right' },
]);

const fetchForwards = async () => {
  try {
    loading.value = true;
    const skip = (pagination.current - 1) * pagination.pageSize;
    const params = { skip, limit: pagination.pageSize };
    const res = await firewallGetForwards(params);
    if (res) {
      forwards.value = res.items || [];
      pagination.total = res.total || 0;
    }
  } catch (error) {
    console.error('获取端口转发失败:', error);
    Message.error('获取端口转发失败: ' + (error.message || ''));
    forwards.value = [];
  } finally {
    loading.value = false;
  }
};

const handleSearch = () => {
  pagination.current = 1;
  fetchForwards();
};

const handlePageChange = (page) => {
  pagination.current = page;
  fetchForwards();
};

const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize;
  pagination.current = 1;
  fetchForwards();
};

const handleAdd = async () => {
  if (!addForm.S_Port || !addForm.T_Address || !addForm.T_Port) {
    Message.warning('请填写必要字段');
    return;
  }
  addLoading.value = true;
  try {
    await firewallAddForward({ ...addForm });
    Message.success(t.value('operationSuccess'));
    showAddDialog.value = false;
    resetAddForm();
    fetchForwards();
  } catch (error) {
    Message.error(error.message || t.value('operationFailed'));
  } finally {
    addLoading.value = false;
  }
};

const handleUpdate = async () => {
  if (!addForm.S_Port || !addForm.T_Address || !addForm.T_Port) {
    Message.warning('请填写必要字段');
    return;
  }
  addLoading.value = true;
  try {
    await firewallUpdateForward(editingId.value, { ...addForm });
    Message.success(t.value('operationSuccess'));
    showAddDialog.value = false;
    resetAddForm();
    fetchForwards();
  } catch (error) {
    Message.error(error.message || t.value('operationFailed'));
  } finally {
    addLoading.value = false;
  }
};

const handleSubmit = () => {
  if (editMode.value) {
    handleUpdate();
  } else {
    handleAdd();
  }
};

const openAddDrawer = () => {
  editMode.value = false;
  editingId.value = null;
  resetAddForm();
  showAddDialog.value = true;
};

const handleEdit = (record) => {
  if (!record.id) {
    Message.warning('转发规则ID无效');
    return;
  }
  editMode.value = true;
  editingId.value = record.id;
  addForm.S_Address = record.S_Address;
  addForm.S_Port = record.S_Port;
  addForm.T_Address = record.T_Address;
  addForm.T_Port = record.T_Port;
  addForm.Protocol = record.Protocol;
  addForm.brief = record.brief || '';
  showAddDialog.value = true;
};

const handleCancelAdd = () => {
  resetAddForm();
  showAddDialog.value = false;
};

const resetAddForm = () => {
  editMode.value = false;
  editingId.value = null;
  addForm.S_Address = '0.0.0.0';
  addForm.S_Port = '';
  addForm.T_Address = '';
  addForm.T_Port = '';
  addForm.Protocol = 'tcp';
  addForm.brief = '';
};

const handleDelete = (record) => {
  deleteTarget.value = record;
  showDeleteDialog.value = true;
};

const handleConfirmDelete = async () => {
  if (!deleteTarget.value || !deleteTarget.value.id) {
    Message.warning('转发规则ID无效');
    showDeleteDialog.value = false;
    return;
  }
  deleteLoading.value = true;
  try {
    await firewallDeleteForward(deleteTarget.value.id);
    Message.success(t.value('operationSuccess'));
    showDeleteDialog.value = false;
    deleteTarget.value = null;
    fetchForwards();
  } catch (error) {
    Message.error(error.message || t.value('operationFailed'));
  } finally {
    deleteLoading.value = false;
  }
};

onMounted(() => {
  checkIsMobile();
  window.addEventListener('resize', checkIsMobile);
  fetchForwards();
});

onUnmounted(() => {
  window.removeEventListener('resize', checkIsMobile);
});
</script>

<style scoped>
.port-forwarding-container {
  padding: 16px;
}

.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 16px;
}

.search-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.search-input {
  width: 300px;
}

.table-container {
  overflow-x: auto;
  width: 100%;
}

@media (max-width: 768px) {
  .header-actions {
    flex-direction: column;
    align-items: stretch;
  }
  .search-input {
    width: 100%;
  }
}
</style>
