<template>
  <a-card class="sqlite-container">
    <template #title>
      <div class="card-header">
        <span class="title">SQLite</span>
        <div class="header-actions">
          <a-button type="outline" size="small" @click="openAddModal">
            {{ t('addDatabase') }}
          </a-button>
        </div>
      </div>
    </template>

    <!-- 数据库列表表格 -->
    <a-table
      :columns="columns"
      :data="databaseList"
      :loading="loading"
      :pagination="pagination"
      @page-change="handlePageChange"
      @page-size-change="handlePageSizeChange"
      :scroll="scroll"
    >
      <template #path="{ record }">
        <a-tooltip :content="record.path" placement="top">
          <icon-folder 
            size="large"
            :style="{
              cursor: 'pointer', 
              color: '#FFB300'
            }"
            @click="openFileManager(record.path)"
          />
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
          <a-link @click="openTablesManager(record)">{{ t('manage') }}</a-link>
          <a-link @click="openBackupModal(record)">{{ t('backup') }}</a-link>
          <a-link @click="openEditModal(record)">{{ t('edit') }}</a-link>
          <a-link status="danger" @click="confirmDelete(record)">{{ t('delete') }}</a-link>
        </a-space>
      </template>
    </a-table>

    <!-- 添加数据库弹窗 -->
    <a-modal
      v-model:visible="addModalVisible"
      :title="t('addDatabase')"
      @ok="handleAddDatabase"
      @cancel="cancelAddModal"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
      :ok-loading="addLoading"
    >
      <a-form layout="vertical" :model="addForm">
        <a-form-item :label="t('databaseName')">
          <a-input
            v-model="addForm.name"
            :placeholder="t('databaseNamePlaceholder')"
            allow-clear
          />
        </a-form-item>
        <a-form-item :label="t('databasePath')" required>
          <a-input
            v-model="addForm.path"
            :placeholder="t('databasePathPlaceholder')"
            allow-clear
          >
            <template #suffix>
              <a-button
                type="text"
                size="small"
                style="margin-right: -10px;"
                @click="showFileManager"
              >
                <icon-folder />
              </a-button>
            </template>
          </a-input>
        </a-form-item>
        <a-form-item :label="t('databaseDescription')">
          <a-input
            v-model="addForm.description"
            :placeholder="t('databaseDescriptionPlaceholder')"
            allow-clear
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 编辑数据库弹窗 -->
    <a-modal
      v-model:visible="editModalVisible"
      :title="t('editDatabase')"
      @ok="handleEditDatabase"
      @cancel="cancelEditModal"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
      :ok-loading="editLoading"
    >
      <a-form layout="vertical" :model="editForm">
        <a-form-item :label="t('databaseName')">
          <a-input
            v-model="editForm.name"
            :placeholder="t('databaseNamePlaceholder')"
            allow-clear
          />
        </a-form-item>
        <a-form-item :label="t('databasePath')">
          <a-input
            :model-value="editForm.path"
            disabled
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
    </a-modal>

    <!-- 删除确认对话框 -->
    <a-modal
      v-model:visible="deleteModalVisible"
      :title="t('confirmDelete')"
      @ok="handleDeleteDatabase"
      @cancel="cancelDelete"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
      :ok-loading="deleteLoading"
    >
      <p>{{ t('confirmDeleteDatabase') }} <strong>{{ deleteTarget.name }}</strong> ?</p>
    </a-modal>

    <!-- 备份管理抽屉 -->
    <a-drawer
      :visible="backupModalVisible"
      :title="t('backupManagement') + ' - ' + backupDatabaseName"
      :width="900"
      :footer="false"
      @cancel="closeBackupModal"
    >
      <div class="backup-header">
        <a-button type="primary" size="small" @click="handleCreateBackup" :loading="createBackupLoading">
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

    <!-- 文件管理器组件 -->
    <MiniFileManager
      :visible="fileManagerVisible"
      :initial-path="'/'"
      select-mode="file"
      @update:visible="fileManagerVisible = $event"
      @select="handleFileSelect"
    />

    <!-- 文件浏览组件 -->
    <file-cat
      :visible="showFileCat"
      :initial-path="selectedFilePath"
      @update:visible="(val) => { showFileCat = val }"
    />
  </a-card>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { t } from '../../utils/locale';
import { Message } from '@arco-design/web-vue';
import { IconFolder } from '@arco-design/web-vue/es/icon';
import {
  getSqliteList,
  addSqliteDatabase,
  updateSqliteDatabase,
  deleteSqliteDatabase,
  getSqliteBackups,
  createSqliteBackup,
  deleteSqliteBackup,
  restoreSqliteBackup
} from '../../api/database';
import MiniFileManager from '../../components/file/MiniFileManager.vue';
import FileCat from '../../components/file/FileCat.vue';

const router = useRouter();
const loading = ref(false);
const databaseList = ref([]);
const fileManagerVisible = ref(false);
const showFileCat = ref(false);
const selectedFilePath = ref('');

// 分页配置
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showTotal: true,
  showJumper: true,
  pageSizeOptions: [10, 20, 50, 100],
  showPageSize: true
});

const scroll = reactive({ x: 700 });

// 表格列定义
const columns = computed(() => [
  { title: t.value('databaseName'), dataIndex: 'name', width: 160, ellipsis: true },
  { title: t.value('databasePath'), slotName: 'path', width: 200, ellipsis: true },
  { title: t.value('databaseDescription'), slotName: 'description', width: 350, ellipsis: true },
  { title: t.value('createdAt'), slotName: 'created_at', width: 170 },
  { title: t.value('action'), slotName: 'actions', width: 200, fixed: 'right' }
]);

// 添加数据库相关
const addModalVisible = ref(false);
const addLoading = ref(false);
const addForm = reactive({
  name: '',
  path: '',
  description: ''
});

// 编辑数据库相关
const editModalVisible = ref(false);
const editLoading = ref(false);
const editForm = reactive({
  id: null,
  name: '',
  path: '',
  description: ''
});

// 删除数据库相关
const deleteModalVisible = ref(false);
const deleteLoading = ref(false);
const deleteTarget = reactive({ id: 0, name: '' });

// 备份管理相关
const backupModalVisible = ref(false);
const backupLoading = ref(false);
const backupDatabaseId = ref(null);
const backupDatabaseName = ref('');
const backupList = ref([]);
const createBackupLoading = ref(false);

// 删除备份相关
const deleteBackupModalVisible = ref(false);
const deleteBackupLoading = ref(false);
const backupToDelete = ref(null);

// 恢复备份相关
const restoreBackupModalVisible = ref(false);
const restoreBackupLoading = ref(false);
const backupToRestore = ref(null);

// 格式化备份名称（只显示文件名）
const formatBackupName = (path) => {
  if (!path) return '-';
  const parts = path.split(/[/\\]/);
  return parts[parts.length - 1] || path;
};

// 备份表格列定义
const backupColumns = computed(() => [
  { title: t.value('id'), dataIndex: 'id', width: 70 },
  { title: t.value('backupName'), slotName: 'backup_name', width: 250, ellipsis: true },
  { title: t.value('size'), slotName: 'file_size', width: 120 },
  { title: t.value('status'), slotName: 'status', width: 100 },
  { title: t.value('createdAt'), slotName: 'created_at', width: 170 },
  { title: t.value('action'), slotName: 'backupActions', width: 150 }
]);

// 格式化大小
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

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '-';
  try {
    const date = new Date(dateString);
    return date.toLocaleString();
  } catch {
    return dateString;
  }
};

// 获取数据库列表
const fetchDatabaseList = async (page = 1) => {
  try {
    loading.value = true;
    const params = {
      skip: (page - 1) * pagination.pageSize,
      limit: pagination.pageSize
    };
    const res = await getSqliteList(params);
    databaseList.value = res.items || [];
    pagination.total = res.total || 0;
  } catch (error) {
    console.error('获取数据库列表失败:', error);
    Message.error('获取数据库列表失败');
    databaseList.value = [];
    pagination.total = 0;
  } finally {
    loading.value = false;
  }
};

// 处理分页变化
const handlePageChange = (page) => {
  pagination.current = page;
  fetchDatabaseList(page);
};

// 处理分页大小变化
const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize;
  pagination.current = 1;
  fetchDatabaseList(1);
};

// 显示文件管理器
const showFileManager = () => {
  fileManagerVisible.value = true;
};

// 文件选择回调
const handleFileSelect = (result) => {
  if (result.path) {
    addForm.path = result.path;
    if (result.name) {
      addForm.path = result.path === '/' ? `/${result.name}` : `${result.path}/${result.name}`;
    }
  }
};

// 打开添加弹窗
const openAddModal = () => {
  addForm.name = '';
  addForm.path = '';
  addForm.description = '';
  addModalVisible.value = true;
};

// 取消添加
const cancelAddModal = () => {
  addModalVisible.value = false;
};

// 处理添加数据库
const handleAddDatabase = async () => {
  if (!addForm.path) {
    Message.warning(t.value('databasePathRequired'));
    return;
  }

  addLoading.value = true;
  try {
    const data = {
      name: addForm.name || addForm.path.split('/').pop() || 'unnamed.db',
      path: addForm.path,
      description: addForm.description || null
    };
    await addSqliteDatabase(data);
    Message.success(t.value('addDatabaseSuccess'));
    addModalVisible.value = false;
    await fetchDatabaseList(pagination.current);
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    Message.error(errMsg || t.value('addDatabaseFailed'));
  } finally {
    addLoading.value = false;
  }
};

// 打开编辑弹窗
const openEditModal = (record) => {
  editForm.id = record.id;
  editForm.name = record.name;
  editForm.path = record.path;
  editForm.description = record.description || '';
  editModalVisible.value = true;
};

// 取消编辑
const cancelEditModal = () => {
  editModalVisible.value = false;
};

// 处理编辑数据库
const handleEditDatabase = async () => {
  editLoading.value = true;
  try {
    const data = {
      name: editForm.name,
      description: editForm.description || null
    };
    await updateSqliteDatabase(editForm.id, data);
    Message.success(t.value('editDatabaseSuccess'));
    editModalVisible.value = false;
    await fetchDatabaseList(pagination.current);
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    Message.error(errMsg || t.value('editDatabaseFailed'));
  } finally {
    editLoading.value = false;
  }
};

// 确认删除
const confirmDelete = (record) => {
  deleteTarget.id = record.id;
  deleteTarget.name = record.name;
  deleteModalVisible.value = true;
};

// 取消删除
const cancelDelete = () => {
  deleteModalVisible.value = false;
};

// 处理删除数据库
const handleDeleteDatabase = async () => {
  deleteLoading.value = true;
  try {
    await deleteSqliteDatabase(deleteTarget.id);
    Message.success(t.value('deleteDatabaseSuccess'));
    deleteModalVisible.value = false;
    await fetchDatabaseList(pagination.current);
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    Message.error(errMsg || t.value('deleteDatabaseFailed'));
  } finally {
    deleteLoading.value = false;
  }
};

// 打开表管理器
const openTablesManager = (record) => {
  router.push(`/database/sqlite/${record.id}/manage`);
};

// 打开备份管理弹窗
const openBackupModal = async (record) => {
  backupDatabaseId.value = record.id;
  backupDatabaseName.value = record.name;
  backupModalVisible.value = true;
  await fetchBackupList(record.id);
};

// 关闭备份管理弹窗
const closeBackupModal = () => {
  backupModalVisible.value = false;
  backupDatabaseId.value = null;
  backupDatabaseName.value = '';
  backupList.value = [];
};

// 获取备份列表
const fetchBackupList = async (databaseId) => {
  try {
    backupLoading.value = true;
    const res = await getSqliteBackups({ database_id: databaseId, skip: 0, limit: 100 });
    backupList.value = res.items || [];
  } catch (error) {
    console.error('获取备份列表失败:', error);
    Message.error('获取备份列表失败');
    backupList.value = [];
  } finally {
    backupLoading.value = false;
  }
};

// 创建备份
const handleCreateBackup = async () => {
  if (!backupDatabaseId.value) return;
  
  try {
    createBackupLoading.value = true;
    await createSqliteBackup(backupDatabaseId.value);
    Message.success(t.value('createBackupSuccess'));
    await fetchBackupList(backupDatabaseId.value);
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    Message.error(errMsg || t.value('createBackupFailed'));
  } finally {
    createBackupLoading.value = false;
  }
};

// 确认删除备份
const confirmDeleteBackup = (record) => {
  backupToDelete.value = record;
  deleteBackupModalVisible.value = true;
};

// 取消删除备份
const cancelDeleteBackup = () => {
  deleteBackupModalVisible.value = false;
  backupToDelete.value = null;
};

// 删除备份
const handleDeleteBackup = async () => {
  if (!backupToDelete.value) return;
  
  try {
    deleteBackupLoading.value = true;
    await deleteSqliteBackup(backupToDelete.value.id);
    Message.success(t.value('deleteBackupSuccess'));
    deleteBackupModalVisible.value = false;
    await fetchBackupList(backupDatabaseId.value);
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    Message.error(errMsg || t.value('deleteBackupFailed'));
  } finally {
    deleteBackupLoading.value = false;
  }
};

// 恢复备份
const handleRestoreBackup = (record) => {
  backupToRestore.value = record;
  restoreBackupModalVisible.value = true;
};

// 取消恢复备份
const cancelRestoreBackup = () => {
  restoreBackupModalVisible.value = false;
  backupToRestore.value = null;
};

// 确认恢复备份
const handleRestoreBackupConfirm = async () => {
  if (!backupToRestore.value) return;
  
  try {
    restoreBackupLoading.value = true;
    await restoreSqliteBackup(backupToRestore.value.id);
    Message.success(t.value('restoreBackupSuccess'));
    restoreBackupModalVisible.value = false;
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    Message.error(errMsg || t.value('restoreBackupFailed'));
  } finally {
    restoreBackupLoading.value = false;
  }
};

// 打开文件管理器
const openFileManager = (filePath) => {
  // 提取目录路径（去掉文件名）
  const lastSlashIndex = filePath.lastIndexOf('/');
  const dirPath = lastSlashIndex > 0 ? filePath.substring(0, lastSlashIndex) : '/';
  selectedFilePath.value = dirPath;
  showFileCat.value = true;
};

onMounted(() => {
  fetchDatabaseList();
});
</script>

<style scoped>
.sqlite-container {
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
  margin-bottom: 16px;
  display: flex;
  justify-content: flex-start;
}
</style>
