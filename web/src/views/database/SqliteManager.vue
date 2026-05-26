<template>
  <a-card class="sqlite-manager-card">
    <template #title>
      <div class="card-header">
        <div class="header-left">
          <a-button type="text" size="small" @click="goBack">
            <template #icon><icon-left /></template>
          </a-button>
          <span class="title">{{ t('tableManagement') }} - {{ databaseName }}</span>
        </div>
        <div class="header-actions">
          <a-button type="outline" size="small" @click="openSqlEditor">
            <template #icon><icon-code /></template>
            {{ t('executeSql') }}
          </a-button>
          <a-button size="small" @click="fetchTables">
            <template #icon><icon-refresh /></template>
            {{ t('refresh') }}
          </a-button>
        </div>
      </div>
    </template>

    <div class="manager-body">
      <!-- 左侧表列表 -->
      <div class="table-sidebar">
        <div class="sidebar-header">
          <span class="sidebar-title">{{ t('tableList') }}</span>
          <a-space>
            <a-button type="primary" size="mini" @click="openCreateTableDrawer">
              <template #icon><icon-plus /></template>
            </a-button>
            <a-tag color="arcoblue" size="small">{{ tableList.length }}</a-tag>
          </a-space>
        </div>
        <div class="table-list">
          <div
            v-for="table in tableList"
            :key="table.name"
            class="table-item"
            :class="{ active: activeTabKey === table.name }"
            @click="openTableTab(table.name)"
            @contextmenu.prevent="showContextMenu($event, table.name)"
          >
            <icon-storage :style="{ color: '#4A90D9', marginRight: '8px' }" />
            <span class="table-name">{{ table.name }}</span>
            <span class="table-count">{{ table.count }}</span>
          </div>
          <a-empty v-if="!tablesLoading && tableList.length === 0" :description="t('noTables')" size="small" />
          <a-spin v-if="tablesLoading" :style="{ width: '100%', marginTop: '40px', display: 'flex', justifyContent: 'center' }" />
        </div>
      </div>

      <!-- 右侧标签页数据区 -->
      <div class="data-content">
        <a-tabs
          v-if="openTabs.length > 0"
          type="card"
          :editable="true"
          v-model:active-key="activeTabKey"
          @delete="handleTabDelete"
          auto-switch
        >
          <a-tab-pane
            v-for="tab in openTabs"
            :key="tab.name"
            :title="tab.isSql ? (tab.title || t('executeSql')) : (tab.isInfo ? tab.title : tab.name)"
            :closable="true"
          >
            <!-- SQL 编辑器标签页 -->
            <template v-if="tab.isSql">
              <div class="sql-tab-content">
                <div class="sql-editor-header">
                  <a-space>
                    <a-button type="primary" size="small" @click="handleExecuteSql" :loading="tab.sqlLoading">
                      <template #icon><icon-play-arrow /></template>
                      {{ t('execute') }}
                    </a-button>
                    <a-button size="small" @click="handleQuerySql" :loading="tab.sqlLoading">
                      <template #icon><icon-search /></template>
                      {{ t('query') }}
                    </a-button>
                    <span class="sql-tip">{{ t('ctrlEnterToExecute') }}</span>
                  </a-space>
                </div>
                <div id="sql-monaco-editor" class="monaco-editor-container"></div>
                <div v-if="tab.sqlResult" class="sql-result">
                  <a-alert
                    :type="tab.sqlResult.success ? 'success' : 'error'"
                    :content="tab.sqlResult.message"
                    style="margin-bottom: 12px;"
                  />
                  <a-table
                    v-if="tab.sqlResult.columns && tab.sqlResult.data"
                    :columns="getSqlResultColumns(tab.sqlResult.columns)"
                    :data="tab.sqlResult.data"
                    :pagination="false"
                    :scroll="{ x: '100%', y: 250 }"
                    size="small"
                  />
                </div>
              </div>
            </template>

            <!-- 表信息标签页 -->
            <template v-else-if="tab.isInfo">
              <a-table
                :columns="columnInfoColumns"
                :data="tab.infoData"
                :pagination="false"
                :scroll="{ x: '100%', y: 'calc(100vh - 250px)' }"
                size="small"
              />
            </template>

            <!-- 表数据标签页 -->
            <template v-else>
            <div class="tab-toolbar">
              <a-space>
                <a-button type="primary" size="small" @click="openAddDataModal(tab.name)">
                  <template #icon><icon-plus /></template>
                  {{ t('addData') }}
                </a-button>
                <a-button size="small" @click="refreshTabData(tab.name)">
                  <template #icon><icon-refresh /></template>
                  {{ t('refresh') }}
                </a-button>
              </a-space>
              <a-input-search
                v-model="tab.searchText"
                :placeholder="t('searchData')"
                size="small"
                style="width: 250px;"
                @search="handleTabSearch(tab.name)"
                @press-enter="handleTabSearch(tab.name)"
                allow-clear
              />
            </div>

            <a-table
              :columns="getTabColumns(tab.name)"
              :data="tab.data"
              :loading="tab.loading"
              :pagination="tab.pagination"
              :scroll="{ x: '100%', y: 'calc(100vh - 310px)' }"
              size="small"
              @page-change="(page) => handleTabDataPageChange(tab.name, page)"
              @page-size-change="(pageSize) => handleTabDataPageSizeChange(tab.name, pageSize)"
            >
              <template #operation="{ record }">
                <a-space>
                  <a-link @click="openEditDataModal(tab.name, record)">{{ t('edit') }}</a-link>
                  <a-link status="danger" @click="confirmDeleteData(tab.name, record)">{{ t('delete') }}</a-link>
                </a-space>
              </template>
            </a-table>
            </template>
          </a-tab-pane>
        </a-tabs>

        <div v-else class="empty-content">
          <a-empty :description="t('selectTableToView')" />
        </div>
      </div>
    </div>

    <!-- 添加数据抽屉 -->
    <a-drawer
      :visible="addDataDrawerVisible"
      :title="t('addData') + ' - ' + addDataTargetTable"
      :width="500"
      :footer="true"
      @cancel="cancelAddData"
    >
      <a-form layout="vertical" :model="addDataForm">
        <a-form-item
          v-for="col in addDataColumns"
          :key="col.name"
          :label="col.name + (col.pk ? ' (PK)' : '') + ' [' + col.type + ']'"
          :required="col.notnull === 1 && !col.default_value && col.pk !== 1"
        >
          <a-input
            v-if="col.pk !== 1"
            v-model="addDataForm[col.name]"
            :placeholder="col.default_value ? t('default') + ': ' + col.default_value : ''"
          />
          <a-input
            v-else
            v-model="addDataForm[col.name]"
            :placeholder="t('autoIncrement')"
            disabled
          />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-space>
          <a-button @click="cancelAddData">{{ t('cancel') }}</a-button>
          <a-button type="primary" @click="handleAddData" :loading="addDataLoading">{{ t('confirm') }}</a-button>
        </a-space>
      </template>
    </a-drawer>

    <!-- 编辑数据抽屉 -->
    <a-drawer
      :visible="editDataDrawerVisible"
      :title="t('editData') + ' - ' + editDataTargetTable"
      :width="500"
      :footer="true"
      @cancel="cancelEditData"
    >
      <a-form layout="vertical" :model="editDataForm">
        <a-form-item
          v-for="col in editDataColumns"
          :key="col.name"
          :label="col.name + (col.pk ? ' (PK)' : '') + ' [' + col.type + ']'"
          :required="col.pk === 1"
        >
          <a-input
            v-if="col.pk === 1"
            v-model="editDataForm[col.name]"
            disabled
          />
          <a-input
            v-else
            v-model="editDataForm[col.name]"
          />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-space>
          <a-button @click="cancelEditData">{{ t('cancel') }}</a-button>
          <a-button type="primary" @click="handleEditData" :loading="editDataLoading">{{ t('confirm') }}</a-button>
        </a-space>
      </template>
    </a-drawer>

    <!-- 删除数据确认弹窗 -->
    <a-modal
      v-model:visible="deleteDataModalVisible"
      :title="t('confirmDelete')"
      @ok="handleDeleteData"
      @cancel="cancelDeleteData"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
      :ok-loading="deleteDataLoading"
    >
      <p>{{ t('confirmDeleteRow') }}</p>
    </a-modal>

    <!-- 右键菜单 -->
    <div
      v-if="contextMenuVisible"
      class="context-menu"
      :style="{ left: contextMenuX + 'px', top: contextMenuY + 'px' }"
    >
      <div class="context-menu-item" @click="openTableInfo">
        <icon-info-circle />
        <span>{{ t('tableInfo') }}</span>
      </div>
      <div class="context-menu-item context-menu-item-delete" @click="deleteTableOperation">
        <icon-delete />
        <span>{{ t('deleteTable') }}</span>
      </div>
    </div>

    <!-- 创建表抽屉 -->
    <a-drawer
      :visible="createTableDrawerVisible"
      :title="t('createTable')"
      :width="600"
      :footer="true"
      @cancel="cancelCreateTable"
    >
      <a-form layout="vertical" :model="createTableForm">
        <a-form-item :label="t('createTableSql')" required>
          <a-textarea
            v-model="createTableForm.sql"
            :placeholder="t('createTableSqlPlaceholder')"
            :auto-size="{ minRows: 8, maxRows: 20 }"
          />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-space>
          <a-button @click="cancelCreateTable">{{ t('cancel') }}</a-button>
          <a-button type="primary" @click="handleCreateTable" :loading="createTableLoading">{{ t('confirm') }}</a-button>
        </a-space>
      </template>
    </a-drawer>
  </a-card>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Message, Modal } from '@arco-design/web-vue';
import {
  IconLeft,
  IconRefresh,
  IconPlus,
  IconCode,
  IconStorage,
  IconPlayArrow,
  IconSearch,
  IconInfoCircle,
  IconDelete
} from '@arco-design/web-vue/es/icon';
import { t } from '../../utils/locale';
import * as monaco from 'monaco-editor';
import {
  getSqliteList,
  getSqliteTables,
  getSqliteTableColumns,
  getSqliteTableData,
  addSqliteData,
  updateSqliteData,
  deleteSqliteData,
  createSqliteTable,
  deleteSqliteTable,
  executeSql,
  querySql
} from '../../api/database';

const route = useRoute();
const router = useRouter();
const databaseId = computed(() => Number(route.params.id));
const databaseName = ref('');

const tableList = ref([]);
const tablesLoading = ref(false);
const openTabs = ref([]);
const activeTabKey = ref('');

const addDataDrawerVisible = ref(false);
const addDataLoading = ref(false);
const addDataTargetTable = ref('');
const addDataColumns = ref([]);
const addDataForm = ref({});

const createTableDrawerVisible = ref(false);
const createTableLoading = ref(false);
const createTableForm = ref({ sql: `CREATE TABLE table_name (\n  id INTEGER PRIMARY KEY AUTOINCREMENT,\n  name TEXT NOT NULL,\n  created_at DATETIME DEFAULT CURRENT_TIMESTAMP\n);` });

const editDataDrawerVisible = ref(false);
const editDataLoading = ref(false);
const editDataTargetTable = ref('');
const editDataColumns = ref([]);
const editDataForm = ref({});
const editOriginalData = ref({});

const deleteDataModalVisible = ref(false);
const deleteDataLoading = ref(false);
const deleteTargetTable = ref('');
const deleteTargetRow = ref({});

const SQL_TAB_KEY = '__sql_editor__';
let monacoEditorInstance = null;

const contextMenuVisible = ref(false);
const contextMenuX = ref(0);
const contextMenuY = ref(0);
const contextMenuTable = ref('');

const columnInfoColumns = [
  { title: t.value('columnName'), dataIndex: 'name', width: 120 },
  { title: t.value('columnType'), dataIndex: 'type', width: 100 },
  { title: t.value('notNull'), dataIndex: 'notnull', width: 80 },
  { title: t.value('defaultValue'), dataIndex: 'default_value', width: 100 },
  { title: t.value('primaryKey'), dataIndex: 'pk', width: 80 }
];

const getSqlResultColumns = (columns) => {
  if (!columns) return [];
  return columns.map(col => ({
    title: col,
    dataIndex: col,
    width: Math.max(100, Math.min(250, col.length * 10 + 40)),
    ellipsis: true,
    tooltip: true
  }));
};

const getTabColumns = (tableName) => {
  const tab = openTabs.value.find(t => t.name === tableName);
  if (!tab || !tab.columns.length) return [];
  const cols = tab.columns.map(col => ({
    title: col.name + (col.pk ? ' ★' : ''),
    dataIndex: col.name,
    width: Math.max(120, Math.min(300, col.name.length * 12 + 40)),
    ellipsis: true,
    tooltip: true
  }));
  cols.push({
    title: t.value('action'),
    slotName: 'operation',
    width: 120,
    fixed: 'right'
  });
  return cols;
};

const goBack = () => {
  router.push('/database/sqlite');
};

const fetchDatabaseInfo = async () => {
  try {
    const res = await getSqliteList({ skip: 0, limit: 1000 });
    const db = (res.items || []).find(item => item.id === databaseId.value);
    if (db) {
      databaseName.value = db.name;
    }
  } catch (error) {
    console.error('获取数据库信息失败:', error);
  }
};

const fetchTables = async () => {
  if (!databaseId.value) return;
  try {
    tablesLoading.value = true;
    const res = await getSqliteTables(databaseId.value);
    tableList.value = Array.isArray(res) ? res : [];
  } catch (error) {
    console.error('获取表列表失败:', error);
    Message.error(error?.response?.data?.detail || t.value('getTablesFailed'));
    tableList.value = [];
  } finally {
    tablesLoading.value = false;
  }
};

const openTableTab = async (tableName) => {
  const existing = openTabs.value.find(t => t.name === tableName);
  if (existing) {
    activeTabKey.value = tableName;
    return;
  }
  const newTab = {
    name: tableName,
    columns: [],
    data: [],
    loading: false,
    searchText: '',
    pagination: {
      current: 1,
      pageSize: 50,
      total: 0,
      showTotal: true,
      showJumper: true,
      pageSizeOptions: [20, 50, 100, 200],
      showPageSize: true
    }
  };
  openTabs.value.push(newTab);
  activeTabKey.value = tableName;
  await fetchTabData(tableName);
};

const handleTabDelete = (key) => {
  const idx = openTabs.value.findIndex(t => t.name === key);
  if (idx === -1) return;
  if (key === SQL_TAB_KEY && monacoEditorInstance) {
    monacoEditorInstance.dispose();
    monacoEditorInstance = null;
  }
  openTabs.value.splice(idx, 1);
  if (activeTabKey.value === key && openTabs.value.length > 0) {
    activeTabKey.value = openTabs.value[Math.min(idx, openTabs.value.length - 1)].name;
  }
};

const fetchTabData = async (tableName) => {
  const tab = openTabs.value.find(t => t.name === tableName);
  if (!tab) return;
  try {
    tab.loading = true;
    const params = {
      page: tab.pagination.current,
      page_size: tab.pagination.pageSize,
      search: tab.searchText || undefined
    };
    const res = await getSqliteTableData(databaseId.value, tableName, params);
    tab.columns = res.columns || [];
    tab.data = (res.data || []).map((row, idx) => ({ ...row, _rowKey: idx }));
    tab.pagination.total = res.total || 0;
  } catch (error) {
    console.error('获取表数据失败:', error);
    Message.error(error?.response?.data?.detail || t.value('getTableDataFailed'));
    tab.data = [];
    tab.pagination.total = 0;
  } finally {
    tab.loading = false;
  }
};

const refreshTabData = (tableName) => {
  fetchTabData(tableName);
};

const handleTabSearch = (tableName) => {
  const tab = openTabs.value.find(t => t.name === tableName);
  if (tab) {
    tab.pagination.current = 1;
  }
  fetchTabData(tableName);
};

const handleTabDataPageChange = (tableName, page) => {
  const tab = openTabs.value.find(t => t.name === tableName);
  if (tab) {
    tab.pagination.current = page;
  }
  fetchTabData(tableName);
};

const handleTabDataPageSizeChange = (tableName, pageSize) => {
  const tab = openTabs.value.find(t => t.name === tableName);
  if (tab) {
    tab.pagination.pageSize = pageSize;
    tab.pagination.current = 1;
  }
  fetchTabData(tableName);
};

const openAddDataModal = (tableName) => {
  const tab = openTabs.value.find(t => t.name === tableName);
  if (!tab) return;
  addDataTargetTable.value = tableName;
  addDataColumns.value = tab.columns;
  addDataForm.value = {};
  tab.columns.forEach(col => {
    if (col.pk === 1) {
      addDataForm.value[col.name] = undefined;
    } else if (col.default_value !== null && col.default_value !== undefined) {
      addDataForm.value[col.name] = String(col.default_value);
    } else {
      addDataForm.value[col.name] = '';
    }
  });
  addDataDrawerVisible.value = true;
};

const cancelAddData = () => {
  addDataDrawerVisible.value = false;
};

const handleAddData = async () => {
  try {
    addDataLoading.value = true;
    const data = {};
    for (const col of addDataColumns.value) {
      const val = addDataForm.value[col.name];
      if (col.pk === 1 && (val === undefined || val === '' || val === null)) continue;
      if (val !== undefined && val !== '' && val !== null) {
        data[col.name] = val;
      } else if (col.notnull === 1 && !col.default_value && col.pk !== 1) {
        Message.warning(`${col.name} ${t.value('fieldRequired')}`);
        addDataLoading.value = false;
        return;
      }
    }
    await addSqliteData(databaseId.value, {
      table: addDataTargetTable.value,
      data
    });
    Message.success(t.value('addDataSuccess'));
    addDataDrawerVisible.value = false;
    await fetchTabData(addDataTargetTable.value);
    await fetchTables();
  } catch (error) {
    Message.error(error?.response?.data?.detail || t.value('addDataFailed'));
  } finally {
    addDataLoading.value = false;
  }
};

const openEditDataModal = (tableName, record) => {
  const tab = openTabs.value.find(t => t.name === tableName);
  if (!tab) return;
  editDataTargetTable.value = tableName;
  editDataColumns.value = tab.columns;
  editDataForm.value = {};
  editOriginalData.value = {};
  tab.columns.forEach(col => {
    const val = record[col.name];
    editDataForm.value[col.name] = val !== null && val !== undefined ? String(val) : '';
    editOriginalData.value[col.name] = val !== null && val !== undefined ? String(val) : '';
  });
  editDataDrawerVisible.value = true;
};

const cancelEditData = () => {
  editDataDrawerVisible.value = false;
};

const handleEditData = async () => {
  try {
    editDataLoading.value = true;
    const whereData = {};
    const newData = {};
    for (const col of editDataColumns.value) {
      if (col.pk === 1) {
        whereData[col.name] = editOriginalData.value[col.name];
      }
    }
    for (const col of editDataColumns.value) {
      if (col.pk !== 1) {
        newData[col.name] = editDataForm.value[col.name] || null;
      }
    }
    await updateSqliteData(databaseId.value, {
      table: editDataTargetTable.value,
      where_data: whereData,
      new_data: newData
    });
    Message.success(t.value('editDataSuccess'));
    editDataDrawerVisible.value = false;
    await fetchTabData(editDataTargetTable.value);
    await fetchTables();
  } catch (error) {
    Message.error(error?.response?.data?.detail || t.value('editDataFailed'));
  } finally {
    editDataLoading.value = false;
  }
};

const confirmDeleteData = (tableName, record) => {
  const tab = openTabs.value.find(t => t.name === tableName);
  if (!tab) return;
  deleteTargetTable.value = tableName;
  deleteTargetRow.value = {};
  tab.columns.forEach(col => {
    if (col.pk === 1) {
      deleteTargetRow.value[col.name] = record[col.name];
    }
  });
  if (Object.keys(deleteTargetRow.value).length === 0) {
    tab.columns.forEach(col => {
      deleteTargetRow.value[col.name] = record[col.name];
    });
  }
  deleteDataModalVisible.value = true;
};

const cancelDeleteData = () => {
  deleteDataModalVisible.value = false;
};

const handleDeleteData = async () => {
  try {
    deleteDataLoading.value = true;
    await deleteSqliteData(databaseId.value, {
      table: deleteTargetTable.value,
      where_data: deleteTargetRow.value
    });
    Message.success(t.value('deleteDataSuccess'));
    deleteDataModalVisible.value = false;
    await fetchTabData(deleteTargetTable.value);
    await fetchTables();
  } catch (error) {
    Message.error(error?.response?.data?.detail || t.value('deleteDataFailed'));
  } finally {
    deleteDataLoading.value = false;
  }
};

const openCreateTableDrawer = () => {
  createTableForm.value = {
    sql: `CREATE TABLE table_name (\n  id INTEGER PRIMARY KEY AUTOINCREMENT,\n  name TEXT NOT NULL,\n  created_at DATETIME DEFAULT CURRENT_TIMESTAMP\n);`
  };
  createTableDrawerVisible.value = true;
};

const cancelCreateTable = () => {
  createTableDrawerVisible.value = false;
};

const handleCreateTable = async () => {
  const sql = createTableForm.value.sql?.trim();
  if (!sql) {
    Message.warning(t.value('createTableSqlRequired'));
    return;
  }
  try {
    createTableLoading.value = true;
    await createSqliteTable(databaseId.value, {
      sql: sql
    });
    Message.success(t.value('createTableSuccess'));
    createTableDrawerVisible.value = false;
    await fetchTables();
  } catch (error) {
    Message.error(error?.response?.data?.detail || t.value('createTableFailed'));
  } finally {
    createTableLoading.value = false;
  }
};

const openSqlEditor = () => {
  const existing = openTabs.value.find(t => t.name === SQL_TAB_KEY);
  if (existing) {
    activeTabKey.value = SQL_TAB_KEY;
    return;
  }
  const newTab = {
    name: SQL_TAB_KEY,
    title: t.value('executeSql'),
    isSql: true,
    sqlLoading: false,
    sqlResult: null,
    columns: [],
    data: [],
    loading: false,
    searchText: '',
    pagination: {
      current: 1,
      pageSize: 50,
      total: 0,
      showTotal: true,
      showJumper: true,
      pageSizeOptions: [20, 50, 100, 200],
      showPageSize: true
    }
  };
  openTabs.value.push(newTab);
  activeTabKey.value = SQL_TAB_KEY;
  nextTick(() => {
    initMonacoEditor();
  });
};

const initMonacoEditor = () => {
  const container = document.getElementById('sql-monaco-editor');
  if (!container) return;
  if (monacoEditorInstance) {
    monacoEditorInstance.dispose();
    monacoEditorInstance = null;
  }
  monacoEditorInstance = monaco.editor.create(container, {
    value: 'SELECT * FROM table_name LIMIT 100;',
    language: 'sql',
    theme: 'vs-dark',
    fontSize: 14,
    fontFamily: "'Consolas', 'Monaco', 'Courier New', monospace",
    lineHeight: 21,
    automaticLayout: true,
    wordWrap: 'on',
    lineNumbers: 'on',
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    smoothScrolling: true,
    cursorBlinking: 'smooth',
    padding: { top: 10, bottom: 10 },
    suggest: {
      showKeywords: true,
      showSnippets: true
    }
  });
  monacoEditorInstance.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
    handleQuerySql();
  });
};

const getSqlEditorValue = () => {
  if (monacoEditorInstance) {
    return monacoEditorInstance.getValue();
  }
  return '';
};

const handleExecuteSql = async () => {
  const sql = getSqlEditorValue().trim();
  if (!sql) {
    Message.warning(t.value('inputSqlStatement'));
    return;
  }
  const tab = openTabs.value.find(t => t.name === SQL_TAB_KEY);
  if (!tab) return;
  try {
    tab.sqlLoading = true;
    const res = await executeSql(databaseId.value, {
      database_id: databaseId.value,
      sql: sql
    });
    tab.sqlResult = res;
    if (res.success) {
      Message.success(res.message);
      if (activeTabKey.value && activeTabKey.value !== SQL_TAB_KEY) {
        await fetchTabData(activeTabKey.value);
      }
      await fetchTables();
    }
  } catch (error) {
    tab.sqlResult = {
      success: false,
      message: error?.response?.data?.detail || t.value('executeFailed')
    };
  } finally {
    tab.sqlLoading = false;
  }
};

const handleQuerySql = async () => {
  const sql = getSqlEditorValue().trim();
  if (!sql) {
    Message.warning(t.value('inputSqlStatement'));
    return;
  }
  const tab = openTabs.value.find(t => t.name === SQL_TAB_KEY);
  if (!tab) return;
  try {
    tab.sqlLoading = true;
    const res = await querySql(databaseId.value, {
      database_id: databaseId.value,
      sql: sql
    });
    tab.sqlResult = res;
    if (res.success) {
      Message.success(res.message);
    }
  } catch (error) {
    tab.sqlResult = {
      success: false,
      message: error?.response?.data?.detail || t.value('queryFailed')
    };
  } finally {
    tab.sqlLoading = false;
  }
};

const showContextMenu = (event, tableName) => {
  event.preventDefault();
  contextMenuX.value = event.clientX;
  contextMenuY.value = event.clientY;
  contextMenuTable.value = tableName;
  contextMenuVisible.value = true;
};

const hideContextMenu = () => {
  contextMenuVisible.value = false;
};

const openTableInfo = async () => {
  const tableName = contextMenuTable.value;
  hideContextMenu();
  const infoTabKey = `__info_${tableName}__`;
  const existing = openTabs.value.find(t => t.name === infoTabKey);
  if (existing) {
    activeTabKey.value = infoTabKey;
    return;
  }
  try {
    const res = await getSqliteTableColumns(databaseId.value, tableName);
    const infoData = res.columns || [];
    const newTab = {
      name: infoTabKey,
      title: `${t.value('tableInfo')} - ${tableName}`,
      isInfo: true,
      infoData: infoData
    };
    openTabs.value.push(newTab);
    activeTabKey.value = infoTabKey;
  } catch (error) {
    console.error('获取列信息失败:', error);
    Message.error(t.value('getColumnsFailed'));
  }
};

const deleteTableOperation = async () => {
  const tableName = contextMenuTable.value;
  hideContextMenu();
  Modal.confirm({
    title: t.value('deleteTable'),
    content: t.value('confirmDeleteTable', { table: tableName }),
    okText: t.value('confirm'),
    cancelText: t.value('cancel'),
    okButtonProps: { status: 'danger' },
    async onOk() {
      try {
        await deleteSqliteTable(databaseId.value, tableName);
        Message.success(t.value('deleteTableSuccess') || `表 ${tableName} 已删除`);
        const tabKey = tableName;
        const tabIndex = openTabs.value.findIndex(t => t.name === tabKey);
        if (tabIndex !== -1) {
          openTabs.value.splice(tabIndex, 1);
          if (activeTabKey.value === tabKey) {
            activeTabKey.value = openTabs.value.length > 0 ? openTabs.value[openTabs.value.length - 1].name : '';
          }
        }
        await fetchTables();
      } catch (error) {
        const errMsg = error?.response?.data?.detail || error.message || '删除表失败';
        Message.error(errMsg);
      }
    }
  });
};

onMounted(async () => {
  document.addEventListener('click', hideContextMenu);
  await fetchDatabaseInfo();
  await fetchTables();
  if (tableList.value.length > 0) {
    await openTableTab(tableList.value[0].name);
  }
});

onUnmounted(() => {
  document.removeEventListener('click', hideContextMenu);
  if (monacoEditorInstance) {
    monacoEditorInstance.dispose();
    monacoEditorInstance = null;
  }
});
</script>

<style scoped>
.sqlite-manager-card {
  height: calc(100vh - 80px);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 15px;
  font-size: 1.2em;
  padding: 10px 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.title {
  margin: 0;
  padding: 0;
}

.manager-body {
  display: flex;
  height: calc(100vh - 160px);
  gap: 16px;
}

.table-sidebar {
  width: 220px;
  min-width: 220px;
  border: 1px solid var(--color-border-2);
  border-radius: 4px;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-bottom: 1px solid var(--color-border-2);
}

.sidebar-title {
  font-weight: 500;
}

.table-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.table-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.table-item:hover {
  background-color: var(--color-fill-2);
}

.table-item.active {
  background-color: var(--color-primary-light-1);
  color: var(--color-primary-6);
}

.table-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table-count {
  font-size: 12px;
  color: var(--color-text-3);
}

.data-content {
  flex: 1;
  overflow: hidden;
}

.empty-content {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.tab-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.sql-editor {
  display: flex;
  flex-direction: column;
}

.sql-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.sql-result {
  margin-top: 12px;
}

.sql-tab-content {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 250px);
}

.sql-editor-header {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
}

.sql-tip {
  font-size: 12px;
  color: var(--color-text-3);
  margin-left: 8px;
}

.monaco-editor-container {
  height: 250px;
  min-height: 200px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  overflow: hidden;
}

.monaco-editor-container :deep(.monaco-editor) {
  border-radius: 4px;
}

.sql-result {
  flex: 1;
  overflow: auto;
  margin-top: 12px;
}

.context-menu {
  position: fixed;
  z-index: 1000;
  background: var(--color-bg-popup);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  padding: 4px 0;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
  min-width: 150px;
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 13px;
  color: var(--color-text-1);
  transition: background-color 0.2s;
}

.context-menu-item:hover {
  background-color: var(--color-fill-2);
}

.context-menu-item-delete {
  color: var(--color-danger-6) !important;
  border-top: 1px solid var(--color-fill-3);
}

.context-menu-item-delete:hover {
  background-color: var(--color-danger-1) !important;
}
</style>
