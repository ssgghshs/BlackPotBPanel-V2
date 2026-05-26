<template>
  <div class="ip-rules-container">
    <div class="header-actions">
      <div class="search-controls">
        <a-input
          v-model="searchInfo"
          :placeholder="t('searchIP')"
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
        :data="ipRules"
        :loading="loading"
        :pagination="pagination"
        @page-change="handlePageChange"
        @page-size-change="handlePageSizeChange"
        :scroll="scroll"
        :table-layout-fixed="true"
      >
        <template #strategy="{ record }">
          <a-tag v-if="record.strategy === 'accept'" color="green">{{ t('accept') }}</a-tag>
          <a-tag v-else color="red">{{ t('drop') }}</a-tag>
        </template>
        <template #stype="{ record }">
          <a-tag v-if="record.stype === '1'" color="blue">{{ t('panelRule') }}</a-tag>
          <a-tag v-else color="orange">{{ t('systemRule') }}</a-tag>
        </template>
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
        {{ deleteTarget.address }} - {{ deleteTarget.brief || t('brief') }}
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
        <a-form-item :label="t('address')" required>
          <a-input v-model="addForm.address" :placeholder="'192.168.1.100'" />
        </a-form-item>
        <a-form-item :label="t('strategy')" required>
          <a-select v-model="addForm.strategy">
            <a-option value="drop">{{ t('drop') }}</a-option>
            <a-option value="accept">{{ t('accept') }}</a-option>
          </a-select>
        </a-form-item>
        <a-form-item :label="t('chain')">
          <a-select v-model="addForm.chain">
            <a-option value="INPUT">INPUT</a-option>
            <a-option value="OUTPUT">OUTPUT</a-option>
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
import { firewallGetIpRules, firewallAddIpRule, firewallDeleteIpRule, firewallUpdateIpRule } from '../../api/security';
import { Message } from '@arco-design/web-vue';

const ipRules = ref([]);
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
  address: '',
  strategy: 'drop',
  chain: 'INPUT',
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
  { title: t.value('address'), dataIndex: 'address', key: 'address', width: 180 },
  { title: t.value('strategy'), dataIndex: 'strategy', key: 'strategy', slotName: 'strategy', width: 90 },
  { title: t.value('chain'), dataIndex: 'chain', key: 'chain', width: 90 },
  { title: t.value('brief'), dataIndex: 'brief', key: 'brief', width: 200, ellipsis: true },
  { title: t.value('addTime'), dataIndex: 'addtime', key: 'addtime', width: 170 },
  { title: t.value('type'), dataIndex: 'stype', key: 'stype', slotName: 'stype', width: 100 },
  { title: t.value('action'), dataIndex: 'actions', key: 'actions', slotName: 'actions', width: 140, fixed: 'right' },
]);

const fetchIpRules = async () => {
  try {
    loading.value = true;
    const skip = (pagination.current - 1) * pagination.pageSize;
    const params = { skip, limit: pagination.pageSize };
    if (searchInfo.value) params.query = searchInfo.value;
    const res = await firewallGetIpRules(params);
    if (res) {
      ipRules.value = res.items || [];
      pagination.total = res.total || 0;
    }
  } catch (error) {
    console.error('获取IP规则失败:', error);
    Message.error('获取IP规则失败: ' + (error.message || ''));
    ipRules.value = [];
  } finally {
    loading.value = false;
  }
};

const handleSearch = () => {
  pagination.current = 1;
  fetchIpRules();
};

const handlePageChange = (page) => {
  pagination.current = page;
  fetchIpRules();
};

const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize;
  pagination.current = 1;
  fetchIpRules();
};

const handleAdd = async () => {
  if (!addForm.address || !addForm.strategy) {
    Message.warning('请填写必要字段');
    return;
  }
  addLoading.value = true;
  try {
    await firewallAddIpRule({ ...addForm });
    Message.success(t.value('operationSuccess'));
    showAddDialog.value = false;
    resetAddForm();
    fetchIpRules();
  } catch (error) {
    Message.error(error.message || t.value('operationFailed'));
  } finally {
    addLoading.value = false;
  }
};

const handleUpdate = async () => {
  if (!addForm.address || !addForm.strategy) {
    Message.warning('请填写必要字段');
    return;
  }
  addLoading.value = true;
  try {
    await firewallUpdateIpRule(editingId.value, { ...addForm });
    Message.success(t.value('operationSuccess'));
    showAddDialog.value = false;
    resetAddForm();
    fetchIpRules();
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
    Message.warning('系统规则无法编辑');
    return;
  }
  editMode.value = true;
  editingId.value = record.id;
  addForm.address = record.address;
  addForm.strategy = record.strategy;
  addForm.chain = record.chain;
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
  addForm.address = '';
  addForm.strategy = 'drop';
  addForm.chain = 'INPUT';
  addForm.brief = '';
};

const handleDelete = (record) => {
  deleteTarget.value = record;
  showDeleteDialog.value = true;
};

const handleConfirmDelete = async () => {
  if (!deleteTarget.value) {
    showDeleteDialog.value = false;
    return;
  }
  deleteLoading.value = true;
  try {
    await firewallDeleteIpRule({
      id: deleteTarget.value.id || 0,
      address: deleteTarget.value.address,
      strategy: deleteTarget.value.strategy,
    });
    Message.success(t.value('operationSuccess'));
    showDeleteDialog.value = false;
    deleteTarget.value = null;
    fetchIpRules();
  } catch (error) {
    Message.error(error.message || t.value('operationFailed'));
  } finally {
    deleteLoading.value = false;
  }
};

onMounted(() => {
  checkIsMobile();
  window.addEventListener('resize', checkIsMobile);
  fetchIpRules();
});

onUnmounted(() => {
  window.removeEventListener('resize', checkIsMobile);
});
</script>

<style scoped>
.ip-rules-container {
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
