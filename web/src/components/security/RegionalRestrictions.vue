<template>
  <div class="regional-restrictions-container">
    <div class="header-actions">
      <div class="search-controls">
        <a-input
          v-model="searchInfo"
          :placeholder="t('searchCountry')"
          allow-clear
          @change="handleSearch"
          class="search-input"
        />
      </div>
      <div style="display: flex; gap: 10px;">
        <a-button v-if="selectedKeys.length > 0" type="outline" status="danger" size="small" @click="handleBatchDelete">
          {{ t('batchDelete') }} ({{ selectedKeys.length }})
        </a-button>
        <a-button type="outline" size="small" @click="openAddDrawer">
          {{ t('addCountryRule') }}
        </a-button>
      </div>
    </div>

    <div class="table-container">
      <a-table
        :columns="columns"
        :data="countryRules"
        :loading="loading"
        :pagination="pagination"
        row-key="id"
        v-model:selectedKeys="selectedKeys"
        :row-selection="rowSelection"
        @page-change="handlePageChange"
        @page-size-change="handlePageSizeChange"
        :scroll="scroll"
        :table-layout-fixed="true"
      >
        <template #strategy="{ record }">
          <a-tag v-if="record.strategy === 'accept'" color="green">{{ t('accept') }}</a-tag>
          <a-tag v-else color="red">{{ t('drop') }}</a-tag>
        </template>
        <template #ports="{ record }">
          <span>{{ record.ports || t('allPorts') }}</span>
        </template>
        <template #actions="{ record }">
          <a-link type="text" size="small" @click="handleEdit(record)">
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
      :title="t('deleteCountryRule')"
      @ok="handleConfirmDelete"
      @cancel="showDeleteDialog = false"
      :ok-loading="deleteLoading"
      :cancel-text="t('cancel')"
      :ok-text="t('confirm')"
    >
      <p>{{ t('deleteCountryRuleConfirm') }}</p>
      <p v-if="deleteTarget" style="color: var(--color-text-2); font-size: 13px;">
        {{ deleteTarget.country_name }}({{ deleteTarget.country_code }}) - {{ deleteTarget.brief || t('brief') }}
      </p>
    </a-modal>

    <a-modal
      v-model:visible="showBatchDeleteDialog"
      :title="t('batchDeleteCountryRule')"
      @ok="handleConfirmBatchDelete"
      @cancel="showBatchDeleteDialog = false"
      :ok-loading="batchDeleteLoading"
      :cancel-text="t('cancel')"
      :ok-text="t('confirm')"
    >
      <p>{{ t('batchDeleteCountryRuleConfirm', { count: selectedKeys.length }) }}</p>
    </a-modal>

    <a-drawer
      :visible="showAddDialog"
      :title="editMode ? t('editCountryRule') : t('addCountryRule')"
      :width="isMobile ? '90%' : 600"
      @cancel="handleCancelAdd"
      :footer="true"
    >
      <a-form :model="addForm" layout="vertical">
        <a-form-item :label="t('country')" required>
          <a-select
            v-model="addForm.country_codes"
            :placeholder="t('selectCountryPlaceholder')"
            multiple
            :max-tag-count="3"
            :loading="countriesLoading"
          >
            <a-option
              v-for="c in availableCountries"
              :key="c.country_code"
              :value="c.country_code"
              :label="`${c.country_name} (${c.country_code})`"
            />
          </a-select>
        </a-form-item>
        <a-form-item :label="t('strategy')" required>
          <a-select v-model="addForm.strategy">
            <a-option value="drop">{{ t('drop') }}</a-option>
          </a-select>
        </a-form-item>
        <a-form-item :label="t('portRange')">
          <a-input v-model="addForm.ports" :placeholder="t('portRangePlaceholder')" />
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
import {
  firewallGetCountryRules,
  firewallAddCountryRule,
  firewallDeleteCountryRule,
  firewallUpdateCountryRule,
  firewallGetCountries,
  firewallBatchDeleteCountryRules,
} from '../../api/security';
import { Message } from '@arco-design/web-vue';

const countryRules = ref([]);
const loading = ref(false);
const addLoading = ref(false);
const deleteLoading = ref(false);
const batchDeleteLoading = ref(false);
const countriesLoading = ref(false);
const searchInfo = ref('');
const showAddDialog = ref(false);
const showDeleteDialog = ref(false);
const showBatchDeleteDialog = ref(false);
const deleteTarget = ref(null);
const editMode = ref(false);
const editingId = ref(null);
const availableCountries = ref([]);
const selectedKeys = ref([]);

const isMobile = ref(false);
const checkIsMobile = () => {
  isMobile.value = window.innerWidth < 768;
};

const addForm = reactive({
  country_codes: [],
  strategy: 'drop',
  ports: '',
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
  { title: t.value('country'), dataIndex: 'country_name', key: 'country_name', width: 200 },
  { title: t.value('countryCode'), dataIndex: 'country_code', key: 'country_code', width: 110 },
  { title: t.value('strategy'), dataIndex: 'strategy', key: 'strategy', slotName: 'strategy', width: 90 },
  { title: t.value('port'), dataIndex: 'ports', key: 'ports', slotName: 'ports', width: 110 },
  { title: t.value('brief'), dataIndex: 'brief', key: 'brief', width: 200, ellipsis: true },
  { title: t.value('addTime'), dataIndex: 'addtime', key: 'addtime', width: 170 },
  { title: t.value('action'), dataIndex: 'actions', key: 'actions', slotName: 'actions', width: 140, fixed: 'right' },
]);

const rowSelection = computed(() => ({
  type: 'checkbox',
  showCheckedAll: true,
}));

const fetchCountryRules = async () => {
  try {
    loading.value = true;
    const skip = (pagination.current - 1) * pagination.pageSize;
    const params = { skip, limit: pagination.pageSize };
    if (searchInfo.value) params.query = searchInfo.value;
    const res = await firewallGetCountryRules(params);
    if (res) {
      countryRules.value = res.items || [];
      pagination.total = res.total || 0;
    }
  } catch (error) {
    console.error('获取地区规则失败:', error);
    Message.error(t.value('getCountryRulesFailed'));
    countryRules.value = [];
  } finally {
    loading.value = false;
  }
};

const fetchAvailableCountries = async () => {
  countriesLoading.value = true;
  try {
    const res = await firewallGetCountries();
    availableCountries.value = Array.isArray(res) ? res : [];
  } catch (error) {
    console.error('获取国家列表失败:', error);
    availableCountries.value = [];
  } finally {
    countriesLoading.value = false;
  }
};

const handleSearch = () => {
  pagination.current = 1;
  fetchCountryRules();
};

const handlePageChange = (page) => {
  pagination.current = page;
  fetchCountryRules();
};

const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize;
  pagination.current = 1;
  fetchCountryRules();
};

const handleAdd = async () => {
  if (!addForm.country_codes || addForm.country_codes.length === 0) {
    Message.warning(t.value('selectCountryWarning'));
    return;
  }
  addLoading.value = true;
  try {
    await firewallAddCountryRule({ ...addForm });
    Message.success(t.value('operationSuccess'));
    showAddDialog.value = false;
    resetAddForm();
    fetchCountryRules();
  } catch (error) {
    Message.error(error.response?.data?.detail || error.message || t.value('operationFailed'));
  } finally {
    addLoading.value = false;
  }
};

const handleUpdate = async () => {
  if (!addForm.country_codes || addForm.country_codes.length === 0) {
    Message.warning(t.value('selectCountryWarning'));
    return;
  }
  addLoading.value = true;
  try {
    await firewallUpdateCountryRule(editingId.value, {
      strategy: addForm.strategy,
      ports: addForm.ports,
      brief: addForm.brief,
    });
    Message.success(t.value('operationSuccess'));
    showAddDialog.value = false;
    resetAddForm();
    fetchCountryRules();
  } catch (error) {
    Message.error(error.response?.data?.detail || error.message || t.value('operationFailed'));
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
  fetchAvailableCountries();
  showAddDialog.value = true;
};

const handleEdit = (record) => {
  editMode.value = true;
  editingId.value = record.id;
  addForm.country_codes = [record.country_code];
  addForm.strategy = record.strategy;
  addForm.ports = record.ports || '';
  addForm.brief = record.brief || '';
  fetchAvailableCountries();
  showAddDialog.value = true;
};

const handleCancelAdd = () => {
  resetAddForm();
  showAddDialog.value = false;
};

const resetAddForm = () => {
  editMode.value = false;
  editingId.value = null;
  addForm.country_codes = [];
  addForm.strategy = 'drop';
  addForm.ports = '';
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
    await firewallDeleteCountryRule({
      id: deleteTarget.value.id,
      country_code: deleteTarget.value.country_code,
      strategy: deleteTarget.value.strategy,
      ports: deleteTarget.value.ports || '',
    });
    Message.success(t.value('operationSuccess'));
    showDeleteDialog.value = false;
    deleteTarget.value = null;
    fetchCountryRules();
  } catch (error) {
    Message.error(error.response?.data?.detail || error.message || t.value('operationFailed'));
  } finally {
    deleteLoading.value = false;
  }
};

const handleBatchDelete = () => {
  if (selectedKeys.value.length === 0) return;
  showBatchDeleteDialog.value = true;
};

const handleConfirmBatchDelete = async () => {
  if (selectedKeys.value.length === 0) {
    showBatchDeleteDialog.value = false;
    return;
  }
  batchDeleteLoading.value = true;
  try {
    const selectedRules = countryRules.value.filter(r => selectedKeys.value.includes(r.id));
    const items = selectedRules.map(r => ({
      id: r.id,
      country_code: r.country_code,
      strategy: r.strategy,
      ports: r.ports || '',
    }));
    const res = await firewallBatchDeleteCountryRules({ items });
    Message.success(res?.message || t.value('operationSuccess'));
    showBatchDeleteDialog.value = false;
    selectedKeys.value = [];
    fetchCountryRules();
  } catch (error) {
    Message.error(error.response?.data?.detail || error.message || t.value('operationFailed'));
  } finally {
    batchDeleteLoading.value = false;
  }
};

onMounted(() => {
  checkIsMobile();
  window.addEventListener('resize', checkIsMobile);
  fetchCountryRules();
});

onUnmounted(() => {
  window.removeEventListener('resize', checkIsMobile);
});
</script>

<style scoped>
.regional-restrictions-container {
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
