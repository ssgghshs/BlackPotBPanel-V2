<template>
  <a-card class="mysql-manager-card">
    <template #title>
      <div class="card-header">
        <div class="header-left">
          <a-button type="text" size="small" @click="goBack">
            <template #icon><icon-left /></template>
          </a-button>
          <span class="title">{{ serverName }}</span>
        </div>
        <div class="header-actions">
          <a-select
            v-model="selectedDatabase"
            :placeholder="t('selectDatabase')"
            :loading="databasesLoading"
            @change="handleDatabaseChange"
            style="width: 200px"
            size="small"
          >
            <a-option v-for="db in databases" :key="db" :value="db">{{ db }}</a-option>
          </a-select>
          <a-button type="primary" size="small" @click="openCreateDbDrawer">
            <template #icon><icon-plus /></template>
            {{ t('createDatabase') }}
          </a-button>
          <a-button type="outline" size="small" @click="openSqlEditor" :disabled="!selectedDatabase">
            <template #icon><icon-code /></template>
            {{ t('executeSql') }}
          </a-button>
          <a-button size="small" @click="fetchTables" :disabled="!selectedDatabase">
            <template #icon><icon-refresh /></template>
            {{ t('refresh') }}
          </a-button>
          <a-button type="outline" status="danger" size="small" @click="confirmDeleteDatabase" :disabled="!selectedDatabase">
            <template #icon><icon-delete /></template>
            {{ t('delete') }}
          </a-button>
          <a-button type="outline" size="small" @click="openUserManagerTab">
            <template #icon><icon-user /></template>
            {{ t('userManagement') }}
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
            <a-button size="mini" type="primary" @click="openCreateTableDialog" :disabled="!selectedDatabase">
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
            <span class="table-count">{{ table.rows || 0 }}</span>
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
            :title="tab.isSql ? (tab.title || t('executeSql')) : (tab.isInfo ? tab.title : (tab.isUser ? tab.title : tab.name))"
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

            <!-- 用户管理标签页 -->
            <template v-else-if="tab.isUser">
              <div class="tab-toolbar">
                <a-space>
                  <a-button type="primary" size="small" @click="openCreateUserDrawer">
                    <template #icon><icon-plus /></template>
                    {{ t('createUser') }}
                  </a-button>
                  <a-button size="small" @click="fetchUsers">
                    <template #icon><icon-refresh /></template>
                    {{ t('refresh') }}
                  </a-button>
                </a-space>
              </div>
              <a-table
                :columns="userColumns"
                :data="usersList"
                :loading="usersLoading"
                :pagination="false"
                :scroll="{ x: '100%', y: 'calc(100vh - 280px)' }"
                size="small"
              >
                <template #operations="{ record }">
                  <a-space>
                    <a-link size="mini" @click="openEditUserDrawer(record)">{{ t('edit') }}</a-link>
                    <a-link size="mini" @click="openGrantUserDrawer(record)">{{ t('grant') }}</a-link>
                    <a-link status="danger" size="mini" @click="confirmDeleteUser(record)">{{ t('delete') }}</a-link>
                  </a-space>
                </template>
              </a-table>
            </template>

            <!-- 表数据标签页 -->
            <template v-else>
              <div class="tab-toolbar">
                <a-space>
                  <a-button type="primary" size="small" @click="openAddDataDrawer(tab.name)">
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
                    <a-link @click="openEditDataDrawer(tab.name, record)">{{ t('edit') }}</a-link>
                    <a-link status="danger" @click="confirmDeleteData(tab.name, record)">{{ t('delete') }}</a-link>
                  </a-space>
                </template>
              </a-table>
            </template>
          </a-tab-pane>
        </a-tabs>

        <div v-else class="empty-content">
          <a-empty :description="selectedDatabase ? t('selectTableToView') : t('selectDatabaseFirst')" />
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
          :key="col.field"
          :label="col.field + (col.key === 'PRI' ? ' (PK)' : '') + ' [' + col.type + ']'"
          :required="col.null === 'NO' && !col.default && col.key !== 'PRI'"
        >
          <a-input
            v-if="col.extra !== 'auto_increment'"
            v-model="addDataForm[col.field]"
            :placeholder="col.default ? t('default') + ': ' + col.default : ''"
          />
          <a-input
            v-else
            v-model="addDataForm[col.field]"
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
          :key="col.field"
          :label="col.field + (col.key === 'PRI' ? ' (PK)' : '') + ' [' + col.type + ']'"
          :required="col.key === 'PRI'"
        >
          <a-input
            v-if="col.key === 'PRI'"
            v-model="editDataForm[col.field]"
            disabled
          />
          <a-input
            v-else
            v-model="editDataForm[col.field]"
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

    <!-- 创建数据库抽屉 -->
    <a-drawer
      :visible="createDbDrawerVisible"
      :title="t('createDatabase')"
      :width="400"
      :footer="true"
      @cancel="cancelCreateDb"
    >
      <a-form layout="vertical" :model="createDbForm">
        <a-form-item :label="t('databaseName')" required>
          <a-input v-model="createDbForm.name" :placeholder="t('enterDatabaseName')" />
        </a-form-item>
        <a-form-item :label="t('charset')">
          <a-select v-model="createDbForm.charset" style="width: 100%">
            <a-option value="utf8mb4">utf8mb4</a-option>
            <a-option value="utf8">utf8</a-option>
            <a-option value="latin1">latin1</a-option>
            <a-option value="gbk">gbk</a-option>
            <a-option value="gb2312">gb2312</a-option>
            <a-option value="big5">big5</a-option>
          </a-select>
        </a-form-item>
      </a-form>
      <template #footer>
        <a-space>
          <a-button @click="cancelCreateDb">{{ t('cancel') }}</a-button>
          <a-button type="primary" @click="handleCreateDb" :loading="createDbLoading">{{ t('confirm') }}</a-button>
        </a-space>
      </template>
    </a-drawer>

    <!-- 创建用户抽屉 -->
    <a-drawer
      :visible="createUserDrawerVisible"
      :title="t('createUser')"
      :width="600"
      :footer="true"
      @cancel="cancelCreateUser"
    >
      <a-form layout="vertical" :model="createUserForm">
        <a-form-item :label="t('username')" required>
          <a-input v-model="createUserForm.username" :placeholder="t('enterUsername')" />
        </a-form-item>
        <a-form-item :label="t('password')" required>
          <a-input-password v-model="createUserForm.password" :placeholder="t('enterPassword')" />
        </a-form-item>
        <a-form-item :label="t('host')">
          <a-select v-model="createUserForm.host" style="width: 100%">
            <a-option value="%">{{ t('anyHost') }}（%）</a-option>
            <a-option value="localhost">{{ t('localHostOnly') }}（localhost）</a-option>
            <a-option value="127.0.0.1">{{ t('localHostOnly') }}（127.0.0.1）</a-option>
            <a-option value="ip">{{ t('specifyIp') }}</a-option>
          </a-select>
          <a-input
            v-if="createUserForm.host === 'ip'"
            v-model="customHost"
            :placeholder="t('enterIpAddress')"
            style="margin-top: 8px;"
          />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-space>
          <a-button @click="cancelCreateUser">{{ t('cancel') }}</a-button>
          <a-button type="primary" @click="handleCreateUser" :loading="createUserLoading">{{ t('confirm') }}</a-button>
        </a-space>
      </template>
    </a-drawer>

    <!-- 授权用户抽屉 -->
    <a-drawer
      :visible="grantUserDrawerVisible"
      :title="t('grant') + ' - ' + grantUserForm.username"
      :width="600"
      :footer="true"
      @cancel="cancelGrantUser"
    >
      <template v-if="grantUserForm.existingGrants && grantUserForm.existingGrants.length > 0">
        <a-descriptions :title="t('currentGrants')" layout="horizontal" :column="1" size="small" style="margin-bottom: 16px;">
          <a-descriptions-item v-for="(grant, idx) in grantUserForm.existingGrants" :key="idx" :label="'@' + grant.database_name">
            <a-tag v-for="priv in grant.privileges" :key="priv" color="arcoblue" style="margin-right: 4px;">{{ priv }}</a-tag>
          </a-descriptions-item>
        </a-descriptions>
        <a-divider />
      </template>
      <a-form layout="vertical" :model="grantUserForm">
        <a-form-item :label="t('database')">
          <a-select v-model="grantUserForm.database_name" style="width: 100%">
            <a-option value="*">*</a-option>
            <a-option v-for="db in databases" :key="db" :value="db">{{ db }}</a-option>
          </a-select>
        </a-form-item>
        <a-form-item :label="t('privileges')">
          <a-checkbox-group v-model="grantUserForm.privileges">
            <a-checkbox value="ALL PRIVILEGES">ALL PRIVILEGES</a-checkbox>
            <a-checkbox value="SELECT">SELECT</a-checkbox>
            <a-checkbox value="INSERT">INSERT</a-checkbox>
            <a-checkbox value="UPDATE">UPDATE</a-checkbox>
            <a-checkbox value="DELETE">DELETE</a-checkbox>
            <a-checkbox value="CREATE">CREATE</a-checkbox>
            <a-checkbox value="DROP">DROP</a-checkbox>
            <a-checkbox value="ALTER">ALTER</a-checkbox>
            <a-checkbox value="INDEX">INDEX</a-checkbox>
            <a-checkbox value="EXECUTE">EXECUTE</a-checkbox>
          </a-checkbox-group>
        </a-form-item>
      </a-form>
      <template #footer>
        <a-space>
          <a-button @click="cancelGrantUser">{{ t('cancel') }}</a-button>
          <a-button type="primary" @click="handleGrantUser" :loading="grantUserLoading">{{ t('confirm') }}</a-button>
        </a-space>
      </template>
    </a-drawer>

    <!-- 编辑用户抽屉 -->
    <a-drawer
      :visible="editUserDrawerVisible"
      :title="t('editUser') + ' - ' + editUserForm.username + '@' + editUserForm.host"
      :width="600"
      :footer="true"
      @cancel="cancelEditUser"
    >
      <a-form layout="vertical" :model="editUserForm">
        <a-form-item :label="t('username')">
          <a-input v-model="editUserForm.new_username" :placeholder="editUserForm.username" />
        </a-form-item>
        <a-form-item :label="t('password')">
          <a-input-password v-model="editUserForm.new_password" :placeholder="t('enterNewPassword')" />
        </a-form-item>
        <a-form-item :label="t('host')">
          <a-select v-model="editUserForm.new_host" style="width: 100%" allow-clear>
            <a-option value="%">{{ t('anyHost') }}（%）</a-option>
            <a-option value="localhost">{{ t('localHostOnly') }}（localhost）</a-option>
            <a-option value="127.0.0.1">{{ t('localHostOnly') }}（127.0.0.1）</a-option>
            <a-option value="ip">{{ t('specifyIp') }}</a-option>
          </a-select>
          <a-input
            v-if="editUserForm.new_host === 'ip'"
            v-model="editUserCustomHost"
            :placeholder="t('enterIpAddress')"
            style="margin-top: 8px;"
          />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-space>
          <a-button @click="cancelEditUser">{{ t('cancel') }}</a-button>
          <a-button type="primary" @click="handleEditUser" :loading="editUserLoading">{{ t('confirm') }}</a-button>
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

    <!-- 创建表抽屉 -->
    <a-drawer
      :visible="createTableModalVisible"
      :title="t('createTable')"
      :width="650"
      :footer="true"
      @cancel="cancelCreateTable"
    >
      <a-form layout="vertical" :model="createTableForm">
        <a-form-item :label="t('createTableSql')" required>
          <a-textarea
            v-model="createTableForm.sql"
            :placeholder="t('createTableSqlPlaceholder')"
            :auto-size="{ minRows: 8, maxRows: 16 }"
            style="font-family: 'Courier New', monospace; font-size: 13px;"
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
  IconDelete,
  IconUser
} from '@arco-design/web-vue/es/icon';
import { t } from '../../utils/locale';
import * as monaco from 'monaco-editor';
import {
  getMysqlServers,
  getMysqlDatabases,
  getMysqlTables,
  getMysqlTableColumns,
  getMysqlTableData,
  addMysqlData,
  updateMysqlData,
  deleteMysqlData,
  executeMysqlSql,
  queryMysqlSql,
  createMysqlDatabase,
  deleteMysqlDatabase,
  createMysqlTable,
  deleteMysqlTable,
  getMysqlUsers,
  createMysqlUser,
  deleteMysqlUser,
  grantMysqlPrivileges,
  updateMysqlUser,
} from '../../api/database';

const route = useRoute();
const router = useRouter();
const serverId = computed(() => Number(route.params.id));
const serverName = ref('');

const databases = ref([]);
const databasesLoading = ref(false);
const selectedDatabase = ref('');

const tableList = ref([]);
const tablesLoading = ref(false);
const openTabs = ref([]);
const activeTabKey = ref('');

const addDataDrawerVisible = ref(false);
const addDataLoading = ref(false);
const addDataTargetTable = ref('');
const addDataColumns = ref([]);
const addDataForm = ref({});

const editDataDrawerVisible = ref(false);
const editDataLoading = ref(false);
const editDataTargetTable = ref('');
const editDataColumns = ref([]);
const editDataForm = ref({});
const editOriginalData = ref({});

const createDbDrawerVisible = ref(false);
const createDbLoading = ref(false);
const createDbForm = ref({ name: '', charset: 'utf8mb4' });

const deleteDataModalVisible = ref(false);
const deleteDataLoading = ref(false);
const deleteTargetTable = ref('');
const deleteTargetRow = ref({});

const createTableModalVisible = ref(false);
const createTableLoading = ref(false);
const createTableForm = ref({ sql: '' });

const usersList = ref([]);
const usersLoading = ref(false);
const createUserDrawerVisible = ref(false);
const createUserLoading = ref(false);
const createUserForm = ref({ username: '', password: '', host: '%' });
const customHost = ref('');
const grantUserDrawerVisible = ref(false);
const grantUserLoading = ref(false);
const grantUserForm = ref({ username: '', host: '', database_name: '*', privileges: [], existingGrants: [] });

const editUserDrawerVisible = ref(false);
const editUserLoading = ref(false);
const editUserForm = ref({ username: '', host: '', new_username: '', new_password: '', new_host: '' });
const editUserCustomHost = ref('');

const SQL_TAB_KEY = '__sql_editor__';
const USER_TAB_KEY = '__user_manager__';
let monacoEditorInstance = null;

const contextMenuVisible = ref(false);
const contextMenuX = ref(0);
const contextMenuY = ref(0);
const contextMenuTable = ref('');

const columnInfoColumns = [
  { title: t.value('field'), dataIndex: 'field', width: 120 },
  { title: t.value('type'), dataIndex: 'type', width: 120 },
  { title: t.value('null'), dataIndex: 'null', width: 80 },
  { title: t.value('key'), dataIndex: 'key', width: 80 },
  { title: t.value('defaultValue'), dataIndex: 'default', width: 100 },
  { title: t.value('extra'), dataIndex: 'extra', width: 120 }
];

const userColumns = [
  { title: t.value('username'), dataIndex: 'User', width: 120 },
  { title: t.value('host'), dataIndex: 'Host', width: 150 },
  { title: t.value('grants'), dataIndex: 'grants', width: 200, ellipsis: true, tooltip: true,
    render: ({ record }) => {
      if (!record.grants || record.grants.length === 0) return '-';
      return record.grants.map(g => `${g.database_name}: ${g.privileges.join(', ')}`).join(' | ');
    }
  },
  { title: t.value('action'), slotName: 'operations', width: 150, fixed: 'right' }
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
    title: col.field + (col.key === 'PRI' ? ' ★' : ''),
    dataIndex: col.field,
    width: Math.max(120, Math.min(300, col.field.length * 12 + 40)),
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
  router.push('/database/mysql');
};

const fetchServerInfo = async () => {
  try {
    const res = await getMysqlServers({ skip: 0, limit: 1000 });
    const server = (res.items || []).find(item => item.id === serverId.value);
    if (server) {
      serverName.value = `${server.host}:${server.port}`;
    }
  } catch (error) {
    console.error('获取服务器信息失败:', error);
  }
};

const fetchDatabases = async () => {
  if (!serverId.value) return;
  try {
    databasesLoading.value = true;
    const res = await getMysqlDatabases(serverId.value);
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
    openTabs.value = [];
    activeTabKey.value = '';
    await fetchTables();
  } else {
    tableList.value = [];
    openTabs.value = [];
    activeTabKey.value = '';
  }
};

const fetchTables = async () => {
  if (!serverId.value || !selectedDatabase.value) return;
  try {
    tablesLoading.value = true;
    const res = await getMysqlTables(serverId.value, selectedDatabase.value);
    tableList.value = res.tables || [];
  } catch (error) {
    console.error('获取表列表失败:', error);
    Message.error(t.value('getTablesFailed'));
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
    const res = await getMysqlTableData(serverId.value, selectedDatabase.value, tableName, params);
    tab.columns = (res.columns || []).map(col => ({
      field: col,
      type: '',
      null: 'YES',
      key: '',
      default: null,
      extra: ''
    }));
    tab.data = (res.data || []).map((row, idx) => ({ ...row, _rowKey: idx }));
    tab.pagination.total = res.total || 0;
  } catch (error) {
    console.error('获取表数据失败:', error);
    Message.error(t.value('getTableDataFailed'));
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

const openSqlEditor = () => {
  const existing = openTabs.value.find(t => t.isSql);
  if (existing) {
    activeTabKey.value = SQL_TAB_KEY;
    return;
  }
  const newTab = {
    name: SQL_TAB_KEY,
    title: t.value('executeSql'),
    isSql: true,
    sqlLoading: false,
    sqlResult: null
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
  }
  monacoEditorInstance = monaco.editor.create(container, {
    value: 'SELECT * FROM ',
    language: 'sql',
    theme: 'vs-dark',
    minimap: { enabled: false },
    fontSize: 14,
    lineNumbers: 'on',
    scrollBeyondLastLine: false,
    automaticLayout: true
  });
  monacoEditorInstance.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
    handleQuerySql();
  });
};

const handleExecuteSql = async () => {
  const sqlTab = openTabs.value.find(t => t.isSql);
  if (!sqlTab || !monacoEditorInstance) return;
  const sql = monacoEditorInstance.getValue().trim();
  if (!sql) {
    Message.warning(t.value('inputSqlStatement'));
    return;
  }
  try {
    sqlTab.sqlLoading = true;
    const res = await executeMysqlSql(serverId.value, selectedDatabase.value, { sql });
    sqlTab.sqlResult = {
      success: res.success,
      message: res.message,
      columns: res.columns || null,
      data: res.data || null
    };
    if (res.success) {
      Message.success(res.message);
    }
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    sqlTab.sqlResult = {
      success: false,
      message: errMsg || t.value('executeFailed')
    };
  } finally {
    sqlTab.sqlLoading = false;
  }
};

const handleQuerySql = async () => {
  const sqlTab = openTabs.value.find(t => t.isSql);
  if (!sqlTab || !monacoEditorInstance) return;
  const sql = monacoEditorInstance.getValue().trim();
  if (!sql) {
    Message.warning(t.value('inputSqlStatement'));
    return;
  }
  try {
    sqlTab.sqlLoading = true;
    const res = await queryMysqlSql(serverId.value, selectedDatabase.value, { sql });
    sqlTab.sqlResult = {
      success: res.success,
      message: res.message,
      columns: res.columns || null,
      data: res.data || null
    };
    if (res.success) {
      Message.success(res.message);
    }
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    sqlTab.sqlResult = {
      success: false,
      message: errMsg || t.value('queryFailed')
    };
  } finally {
    sqlTab.sqlLoading = false;
  }
};

const openAddDataDrawer = async (tableName) => {
  const tab = openTabs.value.find(t => t.name === tableName);
  if (!tab) return;
  addDataTargetTable.value = tableName;
  try {
    const res = await getMysqlTableColumns(serverId.value, selectedDatabase.value, tableName);
    addDataColumns.value = res.columns || [];
  } catch (error) {
    console.error('获取列信息失败:', error);
    addDataColumns.value = tab.columns;
  }
  addDataForm.value = {};
  addDataColumns.value.forEach(col => {
    if (col.extra === 'auto_increment') {
      addDataForm.value[col.field] = undefined;
    } else if (col.default !== null && col.default !== undefined) {
      addDataForm.value[col.field] = String(col.default);
    } else {
      addDataForm.value[col.field] = '';
    }
  });
  addDataDrawerVisible.value = true;
};

const cancelAddData = () => {
  addDataDrawerVisible.value = false;
  addDataForm.value = {};
};

const handleAddData = async () => {
  try {
    addDataLoading.value = true;
    const data = {};
    Object.keys(addDataForm.value).forEach(key => {
      if (addDataForm.value[key] !== undefined && addDataForm.value[key] !== '') {
        data[key] = addDataForm.value[key];
      }
    });
    await addMysqlData(serverId.value, selectedDatabase.value, {
      table: addDataTargetTable.value,
      data
    });
    Message.success(t.value('addDataSuccess'));
    addDataDrawerVisible.value = false;
    await refreshTabData(addDataTargetTable.value);
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    Message.error(errMsg || t.value('addDataFailed'));
  } finally {
    addDataLoading.value = false;
  }
};

const openEditDataDrawer = async (tableName, record) => {
  editDataTargetTable.value = tableName;
  try {
    const res = await getMysqlTableColumns(serverId.value, selectedDatabase.value, tableName);
    editDataColumns.value = res.columns || [];
  } catch (error) {
    console.error('获取列信息失败:', error);
    const tab = openTabs.value.find(t => t.name === tableName);
    editDataColumns.value = tab ? tab.columns : [];
  }
  editDataForm.value = { ...record };
  editOriginalData.value = { ...record };
  editDataDrawerVisible.value = true;
};

const cancelEditData = () => {
  editDataDrawerVisible.value = false;
  editDataForm.value = {};
  editOriginalData.value = {};
};

const handleEditData = async () => {
  try {
    editDataLoading.value = true;
    const whereData = {};
    const newData = {};
    editDataColumns.value.forEach(col => {
      if (col.key === 'PRI') {
        whereData[col.field] = editOriginalData.value[col.field];
      } else {
        newData[col.field] = editDataForm.value[col.field];
      }
    });
    await updateMysqlData(serverId.value, selectedDatabase.value, {
      table: editDataTargetTable.value,
      where_data: whereData,
      new_data: newData
    });
    Message.success(t.value('editDataSuccess'));
    editDataDrawerVisible.value = false;
    await refreshTabData(editDataTargetTable.value);
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    Message.error(errMsg || t.value('editDataFailed'));
  } finally {
    editDataLoading.value = false;
  }
};

const confirmDeleteData = (tableName, record) => {
  deleteTargetTable.value = tableName;
  deleteTargetRow.value = { ...record };
  deleteDataModalVisible.value = true;
};

const cancelDeleteData = () => {
  deleteDataModalVisible.value = false;
  deleteTargetRow.value = {};
};

const handleDeleteData = async () => {
  try {
    deleteDataLoading.value = true;
    const tab = openTabs.value.find(t => t.name === deleteTargetTable.value);
    if (!tab) return;
    const whereData = {};
    tab.columns.forEach(col => {
      if (col.key === 'PRI') {
        whereData[col.field] = deleteTargetRow.value[col.field];
      }
    });
    await deleteMysqlData(serverId.value, selectedDatabase.value, {
      table: deleteTargetTable.value,
      where_data: whereData
    });
    Message.success(t.value('deleteDataSuccess'));
    deleteDataModalVisible.value = false;
    await refreshTabData(deleteTargetTable.value);
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    Message.error(errMsg || t.value('deleteDataFailed'));
  } finally {
    deleteDataLoading.value = false;
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
    const res = await getMysqlTableColumns(serverId.value, selectedDatabase.value, tableName);
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
        await deleteMysqlTable(serverId.value, selectedDatabase.value, tableName);
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

const openCreateDbDrawer = () => {
  createDbForm.value = { name: '', charset: 'utf8mb4' };
  createDbDrawerVisible.value = true;
};

const cancelCreateDb = () => {
  createDbDrawerVisible.value = false;
  createDbForm.value = { name: '', charset: 'utf8mb4' };
};

const handleCreateDb = async () => {
  if (!createDbForm.value.name.trim()) {
    Message.warning(t.value('enterDatabaseName'));
    return;
  }
  try {
    createDbLoading.value = true;
    await createMysqlDatabase(serverId.value, { 
      name: createDbForm.value.name, 
      charset: createDbForm.value.charset 
    });
    Message.success(t.value('createDatabaseSuccess'));
    createDbDrawerVisible.value = false;
    createDbForm.value = { name: '', charset: 'utf8mb4' };
    await fetchDatabases();
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    Message.error(errMsg || t.value('createDatabaseFailed'));
  } finally {
    createDbLoading.value = false;
  }
};

const confirmDeleteDatabase = () => {
  if (!selectedDatabase.value) return;
  Modal.confirm({
    title: t.value('confirmDelete'),
    content: `${t.value('confirmDeleteDatabase')} "${selectedDatabase.value}"?`,
    okText: t.value('confirm'),
    cancelText: t.value('cancel'),
    okType: 'danger',
    async onOk() {
      try {
        await deleteMysqlDatabase(serverId.value, selectedDatabase.value);
        Message.success(t.value('deleteDatabaseSuccess'));
        selectedDatabase.value = '';
        openTabs.value = [];
        activeTabKey.value = '';
        tableList.value = [];
        await fetchDatabases();
      } catch (error) {
        const errMsg = error?.response?.data?.detail;
        Message.error(errMsg || t.value('deleteDatabaseFailed'));
      }
    }
  });
};

const openCreateTableDialog = () => {
  createTableForm.value = { sql: '' };
  createTableModalVisible.value = true;
};

const cancelCreateTable = () => {
  createTableModalVisible.value = false;
  createTableForm.value = { sql: '' };
};

const handleCreateTable = async () => {
  if (!createTableForm.value.sql.trim()) {
    Message.warning(t.value('createTableSqlRequired'));
    return;
  }
  try {
    createTableLoading.value = true;
    const res = await createMysqlTable(serverId.value, selectedDatabase.value, { sql: createTableForm.value.sql.trim() });
    if (res.success) {
      Message.success(res.message || t.value('createTableSuccess'));
      createTableModalVisible.value = false;
      createTableForm.value = { sql: '' };
      await fetchTables();
    } else {
      Message.error(res.message || t.value('createTableFailed'));
    }
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    Message.error(errMsg || t.value('createTableFailed'));
  } finally {
    createTableLoading.value = false;
  }
};

const openUserManagerTab = async () => {
  const existing = openTabs.value.find(t => t.name === USER_TAB_KEY);
  if (existing) {
    activeTabKey.value = USER_TAB_KEY;
    return;
  }
  const newTab = {
    name: USER_TAB_KEY,
    title: t.value('userManagement'),
    isUser: true
  };
  openTabs.value.push(newTab);
  activeTabKey.value = USER_TAB_KEY;
  await fetchUsers();
};

const fetchUsers = async () => {
  try {
    usersLoading.value = true;
    const res = await getMysqlUsers(serverId.value);
    usersList.value = res.users || [];
  } catch (error) {
    console.error('获取用户列表失败:', error);
    Message.error(t.value('getUsersFailed'));
  } finally {
    usersLoading.value = false;
  }
};

const openCreateUserDrawer = () => {
  createUserForm.value = { username: '', password: '', host: '%' };
  customHost.value = '';
  createUserDrawerVisible.value = true;
};

const cancelCreateUser = () => {
  createUserDrawerVisible.value = false;
  createUserForm.value = { username: '', password: '', host: '%' };
  customHost.value = '';
};

const handleCreateUser = async () => {
  if (!createUserForm.value.username.trim()) {
    Message.warning(t.value('enterUsername'));
    return;
  }
  if (!createUserForm.value.password.trim()) {
    Message.warning(t.value('enterPassword'));
    return;
  }
  let host = createUserForm.value.host;
  if (host === 'ip') {
    if (!customHost.value.trim()) {
      Message.warning(t.value('enterIpAddress'));
      return;
    }
    host = customHost.value.trim();
  }
  try {
    createUserLoading.value = true;
    await createMysqlUser(serverId.value, {
      username: createUserForm.value.username,
      password: createUserForm.value.password,
      host: host
    });
    Message.success(t.value('createUserSuccess'));
    createUserDrawerVisible.value = false;
    createUserForm.value = { username: '', password: '', host: '%' };
    customHost.value = '';
    await fetchUsers();
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    Message.error(errMsg || t.value('createUserFailed'));
  } finally {
    createUserLoading.value = false;
  }
};

const confirmDeleteUser = (record) => {
  Modal.confirm({
    title: t.value('confirmDelete'),
    content: `${t.value('confirmDeleteUser')} "${record.User}"@${record.Host}?`,
    okText: t.value('confirm'),
    cancelText: t.value('cancel'),
    okType: 'danger',
    async onOk() {
      try {
        await deleteMysqlUser(serverId.value, { username: record.User, host: record.Host });
        Message.success(t.value('deleteUserSuccess'));
        await fetchUsers();
      } catch (error) {
        const errMsg = error?.response?.data?.detail;
        Message.error(errMsg || t.value('deleteUserFailed'));
      }
    }
  });
};

const openGrantUserDrawer = async (record) => {
  const grants = record.grants || [];
  const firstGrant = grants.length > 0 ? grants[0] : null;

  grantUserForm.value = {
    username: record.User,
    host: record.Host,
    database_name: firstGrant ? firstGrant.database_name : '*',
    privileges: firstGrant ? firstGrant.privileges : [],
    existingGrants: grants
  };
  grantUserDrawerVisible.value = true;
};

const cancelGrantUser = () => {
  grantUserDrawerVisible.value = false;
  grantUserForm.value = { username: '', host: '', database_name: '*', privileges: [], existingGrants: [] };
};

const handleGrantUser = async () => {
  if (!grantUserForm.value.privileges.length) {
    Message.warning(t.value('selectPrivileges'));
    return;
  }
  try {
    grantUserLoading.value = true;
    await grantMysqlPrivileges(serverId.value, {
      username: grantUserForm.value.username,
      host: grantUserForm.value.host,
      database_name: grantUserForm.value.database_name,
      privileges: grantUserForm.value.privileges
    });
    Message.success(t.value('grantSuccess'));
    grantUserDrawerVisible.value = false;
    grantUserForm.value = { username: '', host: '', database_name: '*', privileges: [] };
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    Message.error(errMsg || t.value('grantFailed'));
  } finally {
    grantUserLoading.value = false;
  }
};

const openEditUserDrawer = (record) => {
  let newHostValue = '';
  let customHostValue = '';
  
  if (record.Host === '%' || record.Host === 'localhost' || record.Host === '127.0.0.1') {
    newHostValue = record.Host;
  } else {
    newHostValue = 'ip';
    customHostValue = record.Host;
  }
  
  editUserForm.value = {
    username: record.User,
    host: record.Host,
    new_username: '',
    new_password: '',
    new_host: newHostValue
  };
  editUserCustomHost.value = customHostValue;
  editUserDrawerVisible.value = true;
};

const cancelEditUser = () => {
  editUserDrawerVisible.value = false;
  editUserForm.value = { username: '', host: '', new_username: '', new_password: '', new_host: '' };
  editUserCustomHost.value = '';
};

const handleEditUser = async () => {
  if (!editUserForm.value.new_username && !editUserForm.value.new_password && !editUserForm.value.new_host) {
    Message.warning(t.value('noChanges'));
    return;
  }
  const payload = {
    username: editUserForm.value.username,
    host: editUserForm.value.host
  };
  if (editUserForm.value.new_username) payload.new_username = editUserForm.value.new_username;
  if (editUserForm.value.new_password) payload.new_password = editUserForm.value.new_password;
  if (editUserForm.value.new_host) {
    if (editUserForm.value.new_host === 'ip') {
      if (!editUserCustomHost.value.trim()) {
        Message.warning(t.value('enterIpAddress'));
        return;
      }
      payload.new_host = editUserCustomHost.value.trim();
    } else {
      payload.new_host = editUserForm.value.new_host;
    }
  }
  try {
    editUserLoading.value = true;
    await updateMysqlUser(serverId.value, payload);
    Message.success(t.value('editUserSuccess'));
    editUserDrawerVisible.value = false;
    editUserForm.value = { username: '', host: '', new_username: '', new_password: '', new_host: '' };
    editUserCustomHost.value = '';
    await fetchUsers();
  } catch (error) {
    const errMsg = error?.response?.data?.detail;
    Message.error(errMsg || t.value('editUserFailed'));
  } finally {
    editUserLoading.value = false;
  }
};

onMounted(async () => {
  document.addEventListener('click', hideContextMenu);
  await fetchServerInfo();
  await fetchDatabases();
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
.mysql-manager-card {
  height: calc(100vh - 80px);
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

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 15px;
  padding: 10px 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.title {
  font-size: 16px;
  font-weight: 500;
}

.manager-body {
  display: flex;
  gap: 16px;
  height: calc(100vh - 180px);
}

.table-sidebar {
  width: 240px;
  min-width: 240px;
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
</style>
