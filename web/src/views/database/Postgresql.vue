<template>
  <a-card class="database-container">
    <template #title>
      <div class="card-header">
        <span class="title">PostgreSQL</span>
        <div class="header-actions">
          <a-button type="outline" size="small" @click="openAddDrawer">
            {{ t('addServer') }}
          </a-button>
        </div>
      </div>
    </template>

    <!-- 服务器列表表格 -->
    <a-table
      :columns="columns"
      :data="serverList"
      :loading="loading"
      :pagination="pagination"
      @page-change="handlePageChange"
      @page-size-change="handlePageSizeChange"
      :scroll="scroll"
    >
      <template #host="{ record }">
        <a-tooltip :content="`${record.host}:${record.port}`" placement="top">
          <span>{{ record.host }}:{{ record.port }}</span>
        </a-tooltip>
      </template>
      <template #description="{ record }">
        <span>{{ record.description || '-' }}</span>
      </template>
      <template #created_at="{ record }">
        {{ formatDate(record.created_at) }}
      </template>
      <template #actions="{ record }">
        <a-space>
          <a-link @click="openManagePage(record)">{{ t('manage') }}</a-link>
          <a-link @click="openBackupDrawer(record)">{{ t('backup') }}</a-link>
          <a-link @click="openEditDrawer(record)">{{ t('edit') }}</a-link>
          <a-link status="danger" @click="confirmDelete(record)">{{ t('delete') }}</a-link>
        </a-space>
      </template>
    </a-table>

    <!-- 添加服务器抽屉 -->
    <a-drawer
      :visible="addDrawerVisible"
      :title="t('addPgsqlServer')"
      :width="500"
      :footer="true"
      @cancel="cancelAddDrawer"
      unmountOnClose
    >
      <a-form layout="vertical" :model="addForm">
        <a-form-item :label="t('serverHost')" required>
          <a-input
            v-model="addForm.host"
            :placeholder="t('serverHostPlaceholder')"
            allow-clear
          />
        </a-form-item>
        <a-form-item :label="t('serverPort')" required>
          <a-input-number
            v-model="addForm.port"
            :min="1"
            :max="65535"
            :placeholder="t('serverPortPlaceholder')"
            style="width: 100%"
          />
        </a-form-item>
        <a-form-item :label="t('username')" required>
          <a-input
            v-model="addForm.username"
            :placeholder="t('usernamePlaceholder')"
            allow-clear
          />
        </a-form-item>
        <a-form-item :label="t('password')" required>
          <a-input-password
            v-model="addForm.password"
            :placeholder="t('passwordPlaceholder')"
            allow-clear
          />
        </a-form-item>
        <a-form-item :label="t('databaseDescription')">
          <a-input
            v-model="addForm.description"
            :placeholder="t('databaseDescriptionPlaceholder')"
            allow-clear
          />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-button @click="cancelAddDrawer">{{ t('cancel') }}</a-button>
        <a-button type="primary" @click="handleAddServer" :loading="addLoading">{{ t('confirm') }}</a-button>
      </template>
    </a-drawer>

    <!-- 编辑服务器抽屉 -->
    <a-drawer
      :visible="editDrawerVisible"
      :title="t('editPgsqlServer')"
      :width="500"
      :footer="true"
      @cancel="cancelEditDrawer"
      unmountOnClose
    >
      <a-form layout="vertical" :model="editForm">
        <a-form-item :label="t('serverHost')" required>
          <a-input
            v-model="editForm.host"
            :placeholder="t('serverHostPlaceholder')"
            allow-clear
          />
        </a-form-item>
        <a-form-item :label="t('serverPort')" required>
          <a-input-number
            v-model="editForm.port"
            :min="1"
            :max="65535"
            :placeholder="t('serverPortPlaceholder')"
            style="width: 100%"
          />
        </a-form-item>
        <a-form-item :label="t('username')" required>
          <a-input
            v-model="editForm.username"
            :placeholder="t('usernamePlaceholder')"
            allow-clear
          />
        </a-form-item>
        <a-form-item :label="t('password')">
          <a-input-password
            v-model="editForm.password"
            :placeholder="t('passwordLeaveEmpty')"
            allow-clear
          />
        </a-form-item>
        <a-form-item :label="t('databaseDescription')">
          <a-input
            v-model="editForm.description"
            :placeholder="t('databaseDescriptionPlaceholder')"
            allow-clear
          />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-button @click="cancelEditDrawer">{{ t('cancel') }}</a-button>
        <a-button type="primary" @click="handleTestConnectionForEdit" :loading="testConnectionLoading">{{ t('testConnection') }}</a-button>
        <a-button type="primary" @click="handleEditServer" :loading="editLoading">{{ t('save') }}</a-button>
      </template>
    </a-drawer>

    <!-- 删除确认对话框 -->
    <a-modal
      v-model:visible="deleteModalVisible"
      :title="t('confirmDelete')"
      @ok="handleDeleteServer"
      @cancel="cancelDelete"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
      :ok-loading="deleteLoading"
    >
      <p>{{ t('confirmDeleteServer') }} <strong>{{ deleteTarget.host }}:{{ deleteTarget.port }}</strong> ?</p>
    </a-modal>

    <!-- 测试连接结果对话框 -->
    <a-modal
      v-model:visible="testResultVisible"
      :title="t('testConnectionResult')"
      :ok-text="t('confirm')"
      @ok="testResultVisible = false"
      @cancel="testResultVisible = false"
    >
      <a-alert v-if="testResult.success" type="success" :title="t('connectionSuccess')">
        {{ testResult.message }}
      </a-alert>
      <a-alert v-else type="error" :title="t('connectionFailed')">
        {{ testResult.message }}
      </a-alert>
    </a-modal>

    <!-- 备份管理抽屉 -->
    <a-drawer
      :visible="backupDrawerVisible"
      :title="t('backupManagement') + ' - ' + backupServerName"
      :width="900"
      :footer="false"
      @cancel="closeBackupDrawer"
      unmountOnClose
    >
      <div class="backup-header">
        <a-select
          v-model="selectedDatabase"
          :placeholder="t('selectDatabase')"
          :loading="databasesLoading"
          @change="handleDatabaseChange"
          style="width: 300px"
        >
          <a-option v-for="db in databases" :key="db" :value="db">{{ db }}</a-option>
        </a-select>
        <a-button
          type="primary"
          size="small"
          @click="handleCreateBackup"
          :loading="createBackupLoading"
          :disabled="!selectedDatabase"
        >
          {{ t('createBackup') }}
        </a-button>
      </div>
      <a-table
        :columns="backupColumns"
        :data="backupList"
        :loading="backupLoading"
        :pagination="false"
        :scroll="{ y: 400 }"
      >
        <template #backup_name="{ record }">
          {{ formatBackupName(record.backup_path) }}
        </template>
        <template #file_size="{ record }">
          {{ formatSize(record.file_size) }}
        </template>
        <template #status="{ record }">
          <a-tag :color="record.status === 1 ? 'green' : 'red'">
            {{ record.status === 1 ? t('success') : t('failed') }}
          </a-tag>
        </template>
        <template #created_at="{ record }">
          {{ formatDate(record.created_at) }}
        </template>
        <template #backupActions="{ record }">
          <a-space>
            <a-link @click="handleRestoreBackup(record)">{{ t('restore') }}</a-link>
            <a-link status="danger" @click="confirmDeleteBackup(record)">{{ t('delete') }}</a-link>
          </a-space>
        </template>
      </a-table>
    </a-drawer>

    <!-- 删除备份确认对话框 -->
    <a-modal
      v-model:visible="deleteBackupModalVisible"
      :title="t('confirmDelete')"
      @ok="handleDeleteBackup"
      @cancel="cancelDeleteBackup"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
      :ok-loading="deleteBackupLoading"
    >
      <p>{{ t('confirmDeleteBackup') }}</p>
    </a-modal>

    <!-- 恢复备份确认对话框 -->
    <a-modal
      v-model:visible="restoreBackupModalVisible"
      :title="t('confirmRestore')"
      @ok="handleRestoreBackupConfirm"
      @cancel="cancelRestoreBackup"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
      :ok-loading="restoreBackupLoading"
    >
      <p>{{ t('confirmRestoreBackup') }}</p>
    </a-modal>
  </a-card>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { t } from '../../utils/locale';
import { Message } from '@arco-design/web-vue';
import {
  getPgsqlServers,
  addPgsqlServer,
  updatePgsqlServer,
  deletePgsqlServer,
  testPgsqlConnection,
  getPgsqlBackups,
  createPgsqlBackup,
  restorePgsqlBackup,
  deletePgsqlBackup,
  getPgsqlDatabases,
} from '../../api/database';

const router = useRouter();
const loading = ref(false);
const serverList = ref([]);

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showTotal: true,
  showJumper: true,
  pageSizeOptions: [10, 20, 50, 100],
  showPageSize: true
});

const scroll = reactive({ x: 600 });

const columns = computed(() => [
  { title: t.value('serverAddress'), slotName: 'host', width: 200, ellipsis: true },
  { title: t.value('username'), dataIndex: 'username', width: 150, ellipsis: true },
  { title: t.value('databaseDescription'), slotName: 'description', width: 350, ellipsis: true },
  { title: t.value('createdAt'), slotName: 'created_at', width: 170 },
  { title: t.value('action'), slotName: 'actions', width: 150, fixed: 'right' }
]);

const addDrawerVisible = ref(false);
const addLoading = ref(false);
const addForm = reactive({
  host: '',
  port: 5432,
  username: '',
  password: '',
  description: ''
});

const editDrawerVisible = ref(false);
const editLoading = ref(false);
const editForm = reactive({
  id: null,
  host: '',
  port: 5432,
  username: '',
  password: '',
  description: ''
});

const testConnectionLoading = ref(false);

const deleteModalVisible = ref(false);
const deleteLoading = ref(false);
const deleteTarget = reactive({ id: 0, host: '', port: 5432 });

const testResultVisible = ref(false);
const testResult = reactive({ success: false, message: '' });

const formatDate = (dateString) => {
  if (!dateString) return '-';
  try {
    const date = new Date(dateString);
    return date.toLocaleString();
  } catch {
    return dateString;
  }
};

const fetchServerList = async (page = 1) => {
  try {
    loading.value = true;
    const params = {
      skip: (page - 1) * pagination.pageSize,
      limit: pagination.pageSize
    };
    const res = await getPgsqlServers(params);
    serverList.value = res.items || [];
    pagination.total = res.total || 0;
  } catch (error) {
    console.error('获取服务器列表失败:', error);
    Message.error(t.value('getServerListFailed'));
    serverList.value = [];
    pagination.total = 0;
  } finally {
    loading.value = false;
  }
};

const handlePageChange = (page) => {
  pagination.current = page;
  fetchServerList(page);
};

const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize;
  pagination.current = 1;
  fetchServerList(1);
};

const openAddDrawer = () => {
  addForm.host = '';
  addForm.port = 5432;
  addForm.username = '';
  addForm.password = '';
  addForm.description = '';
  addDrawerVisible.value = true;
};

const cancelAddDrawer = () => {
  addDrawerVisible.value = false;
};

const handleAddServer = async () => {
  if (!addForm.host) {
    Message.warning(t.value('serverHostRequired'));
    return;
  }
  if (!addForm.username) {
    Message.warning(t.value('usernameRequired'));
    return;
  }
  if (!addForm.password) {
    Message.warning(t.value('passwordRequired'));
    return;
  }

  addLoading.value = true;
  try {
    await addPgsqlServer({
      host: addForm.host,
      port: addForm.port,
      username: addForm.username,
      password: addForm.password,
      description: addForm.description || null
    });
    Message.success(t.value('addServerSuccess'));
    addDrawerVisible.value = false;
    await fetchServerList(pagination.current);
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    Message.error(errMsg || t.value('addServerFailed'));
  } finally {
    addLoading.value = false;
  }
};

const openEditDrawer = (record) => {
  editForm.id = record.id;
  editForm.host = record.host;
  editForm.port = record.port;
  editForm.username = record.username;
  editForm.password = '';
  editForm.description = record.description || '';
  editDrawerVisible.value = true;
};

const cancelEditDrawer = () => {
  editDrawerVisible.value = false;
};

const handleEditServer = async () => {
  if (!editForm.host) {
    Message.warning(t.value('serverHostRequired'));
    return;
  }
  if (!editForm.username) {
    Message.warning(t.value('usernameRequired'));
    return;
  }

  editLoading.value = true;
  try {
    const data = {
      host: editForm.host,
      port: editForm.port,
      username: editForm.username,
      description: editForm.description || null
    };
    if (editForm.password) {
      data.password = editForm.password;
    }
    await updatePgsqlServer(editForm.id, data);
    Message.success(t.value('editServerSuccess'));
    editDrawerVisible.value = false;
    await fetchServerList(pagination.current);
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    Message.error(errMsg || t.value('editServerFailed'));
  } finally {
    editLoading.value = false;
  }
};

const handleTestConnectionForEdit = async () => {
  if (!editForm.id) return;

  testConnectionLoading.value = true;
  try {
    const res = await testPgsqlConnection(editForm.id);
    testResult.success = res.success;
    testResult.message = res.message || (res.success ? t.value('connectionSuccess') : t.value('connectionFailed'));
    testResultVisible.value = true;
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    testResult.success = false;
    testResult.message = errMsg || t.value('connectionFailed');
    testResultVisible.value = true;
  } finally {
    testConnectionLoading.value = false;
  }
};

const confirmDelete = (record) => {
  deleteTarget.id = record.id;
  deleteTarget.host = record.host;
  deleteTarget.port = record.port;
  deleteModalVisible.value = true;
};

const cancelDelete = () => {
  deleteModalVisible.value = false;
};

const handleDeleteServer = async () => {
  deleteLoading.value = true;
  try {
    await deletePgsqlServer(deleteTarget.id);
    Message.success(t.value('deleteServerSuccess'));
    deleteModalVisible.value = false;
    await fetchServerList(pagination.current);
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    Message.error(errMsg || t.value('deleteServerFailed'));
  } finally {
    deleteLoading.value = false;
  }
};

const openManagePage = (record) => {
  router.push(`/database/postgresql/${record.id}/manage`);
};

// ==================== 备份管理 ====================

const backupDrawerVisible = ref(false);
const backupServerId = ref(null);
const backupServerName = ref('');
const databases = ref([]);
const databasesLoading = ref(false);
const selectedDatabase = ref('');
const backupList = ref([]);
const backupLoading = ref(false);
const createBackupLoading = ref(false);

const deleteBackupModalVisible = ref(false);
const deleteBackupLoading = ref(false);
const backupToDelete = ref(null);

const restoreBackupModalVisible = ref(false);
const restoreBackupLoading = ref(false);
const backupToRestore = ref(null);

const backupColumns = computed(() => [
  { title: t.value('id'), dataIndex: 'id', width: 70 },
  { title: t.value('backupName'), slotName: 'backup_name', width: 250, ellipsis: true },
  { title: t.value('size'), slotName: 'file_size', width: 120 },
  { title: t.value('status'), slotName: 'status', width: 100 },
  { title: t.value('createdAt'), slotName: 'created_at', width: 170 },
  { title: t.value('action'), slotName: 'backupActions', width: 150 }
]);

const formatBackupName = (path) => {
  if (!path) return '-';
  const parts = path.split(/[/\\]/);
  return parts[parts.length - 1] || path;
};

const formatSize = (bytes) => {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = bytes;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`;
};

const openBackupDrawer = async (record) => {
  backupServerId.value = record.id;
  backupServerName.value = `${record.host}:${record.port}`;
  backupDrawerVisible.value = true;
  selectedDatabase.value = '';
  backupList.value = [];
  await fetchDatabases(record.id);
};

const closeBackupDrawer = () => {
  backupDrawerVisible.value = false;
  backupServerId.value = null;
  backupServerName.value = '';
  databases.value = [];
  selectedDatabase.value = '';
  backupList.value = [];
};

const fetchDatabases = async (serverId) => {
  try {
    databasesLoading.value = true;
    const res = await getPgsqlDatabases(serverId);
    databases.value = res.databases || [];
  } catch (error) {
    console.error('获取数据库列表失败:', error);
    Message.error(t.value('getDatabasesFailed'));
    databases.value = [];
  } finally {
    databasesLoading.value = false;
  }
};

const handleDatabaseChange = async (databaseName) => {
  if (databaseName) {
    await fetchBackupList(backupServerId.value, databaseName);
  } else {
    backupList.value = [];
  }
};

const fetchBackupList = async (serverId, databaseName) => {
  try {
    backupLoading.value = true;
    const res = await getPgsqlBackups({ server_id: serverId });
    backupList.value = (res.items || []).filter(item => item.database_name === databaseName);
  } catch (error) {
    console.error('获取备份列表失败:', error);
    Message.error(t.value('getBackupListFailed'));
    backupList.value = [];
  } finally {
    backupLoading.value = false;
  }
};

const handleCreateBackup = async () => {
  if (!backupServerId.value || !selectedDatabase.value) return;
  try {
    createBackupLoading.value = true;
    await createPgsqlBackup(backupServerId.value, selectedDatabase.value);
    Message.success(t.value('createBackupSuccess'));
    await fetchBackupList(backupServerId.value, selectedDatabase.value);
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    Message.error(errMsg || t.value('createBackupFailed'));
  } finally {
    createBackupLoading.value = false;
  }
};

const confirmDeleteBackup = (record) => {
  backupToDelete.value = record;
  deleteBackupModalVisible.value = true;
};

const cancelDeleteBackup = () => {
  deleteBackupModalVisible.value = false;
  backupToDelete.value = null;
};

const handleDeleteBackup = async () => {
  if (!backupToDelete.value) return;
  deleteBackupLoading.value = true;
  try {
    await deletePgsqlBackup(backupToDelete.value.id);
    Message.success(t.value('deleteBackupSuccess'));
    deleteBackupModalVisible.value = false;
    backupToDelete.value = null;
    await fetchBackupList(backupServerId.value, selectedDatabase.value);
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    Message.error(errMsg || t.value('deleteBackupFailed'));
  } finally {
    deleteBackupLoading.value = false;
  }
};

const handleRestoreBackup = (record) => {
  backupToRestore.value = record;
  restoreBackupModalVisible.value = true;
};

const cancelRestoreBackup = () => {
  restoreBackupModalVisible.value = false;
  backupToRestore.value = null;
};

const handleRestoreBackupConfirm = async () => {
  if (!backupToRestore.value) return;
  restoreBackupLoading.value = true;
  try {
    await restorePgsqlBackup(backupToRestore.value.id);
    Message.success(t.value('restoreSuccess'));
    restoreBackupModalVisible.value = false;
    backupToRestore.value = null;
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    Message.error(errMsg || t.value('restoreFailed'));
  } finally {
    restoreBackupLoading.value = false;
  }
};

onMounted(() => {
  fetchServerList();
});
</script>

<style scoped>
.database-container {
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

.header-actions {
  display: flex;
  gap: 10px;
}

.backup-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
</style>
