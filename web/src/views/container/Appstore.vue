<template>
  <a-card>
     <!-- 容器应用列表-->
    <a-tabs v-model:active-key="activeMainTab" type="line">
      <a-tab-pane key="1" :title="t('containerApp')">
        <!-- 商店源标签 -->
        <a-tabs v-if="stores.length > 0" v-model:active-key="activeStoreTab" type="rounded">
          <a-tab-pane v-for="(store, idx) in stores" :key="String(idx)" :title="store.name">
            <div class="app-search-bar">
              <a-input
                v-model="keyword"
                :placeholder="t('searchAppPlaceholder')"
                allow-clear
                style="width: 320px;"
              />
            </div>
            <div v-if="pagedStoreApps.length > 0" class="app-grid">
              <div v-for="(app, appIdx) in pagedStoreApps" :key="appIdx" class="app-card" @click="handleAppClick(app)">
                <a-card hoverable>
                  <div class="app-wrapper">
                    <div class="app-image">
                      <img v-if="app.logo" :src="app.logo" alt="" class="app-logo" />
                      <div v-else class="app-logo-placeholder">{{ (app.title || app.name)[0] }}</div>
                    </div>
                    <div class="app-content">
                      <div class="content-top">
                        <span class="app-title">{{ app.title || app.name }}</span>
                      </div>
                      <div class="content-middle">
                        <span class="app-description">{{ getAppDescription(app) }}</span>
                      </div>
                      <div class="content-bottom">
                        <div class="app-tags">
                          <a-tag v-for="(tag, tagIdx) in (app.tags || [])" :key="tagIdx" color="gray" size="small">{{ tag }}</a-tag>
                          <a-tag v-if="Object.keys(app.versions || {}).length > 0" color="arcoblue" size="small">{{ Object.keys(app.versions).length }}版本</a-tag>
                        </div>
                      </div>
                    </div>
                  </div>
                </a-card>
              </div>
            </div>
            <a-empty v-else />
            <div v-if="filteredStoreApps.length > 0" class="app-pagination-wrap">
              <a-pagination
                :total="filteredStoreApps.length"
                :current="appPagination.current"
                :page-size="appPagination.pageSize"
                :page-size-options="appPagination.pageSizeOptions"
                :show-page-size="appPagination.showPageSize"
                :show-jumper="appPagination.showJumper"
                @change="handleAppPageChange"
                @page-size-change="handleAppPageSizeChange"
              />
            </div>
          </a-tab-pane>
        </a-tabs>
        <a-empty v-else />
      </a-tab-pane>
      <!-- 部署记录 -->
      <a-tab-pane key="2" :title="t('deployed')">
        <div class="deployed-header">
          <a-input-search
            v-model="deployKeyword"
            :placeholder="t('searchAppPlaceholder')"
            allow-clear
            style="width: 260px;"
            @search="deployKeywordSearch"
          />
        </div>
          <div v-if="filteredDeployList.length > 0" class="deployed-grid">
            <div v-for="(record, idx) in filteredDeployList" :key="record.id || idx" class="deployed-card">
              <a-card hoverable>
                <div class="deployed-wrapper">
                  <div class="deployed-image">
                    <img v-if="getDeployAppLogo(record)" :src="getDeployAppLogo(record)" alt="" class="deployed-logo" />
                    <div v-else class="deployed-logo-placeholder">{{ (record.title || record.app_name || '?')[0] }}</div>
                  </div>
                  <div class="deployed-content">
                    <div class="deployed-top">
                      <a-space>
                        <span class="deployed-title">{{ record.title || record.app_name }}</span>
                        <a-tag :color="deployStatusColor(record.status)" size="small">
                          {{ deployStatusText(record.status) }}
                        </a-tag>
                        <span v-if="record.running === true" class="running-dot running-dot-on" :title="t('containerRunning')" />
                        <span v-else-if="record.running === false" class="running-dot running-dot-off" :title="t('containerStopped')" />
                      </a-space>
                    </div>
                    <div class="deployed-middle">
                      <a-descriptions :column="2" size="mini" layout="inline-horizontal" style="margin-top:6px;">
                        <a-descriptions-item :label="t('taskName')">
                          <code class="task-name-text">{{ record.task_name }}</code>
                        </a-descriptions-item>
                        <a-descriptions-item :label="t('version')">
                          {{ record.version_name }}
                        </a-descriptions-item>
                        <a-descriptions-item :label="t('storeName')">
                          {{ record.store_name }}
                        </a-descriptions-item>
                        <a-descriptions-item :label="t('createTime')">
                          {{ formatDate(record.created_at) }}
                        </a-descriptions-item>
                      </a-descriptions>
                    </div>
                    <div class="deployed-bottom">
                      <a-space>
                        <a-button size="mini" type="outline" @click="handleViewComposeLogs(record)">
                          <template #icon><icon-bookmark /></template>
                        </a-button>
                        <a-button size="mini" type="outline" @click="handleViewComposeContainers(record)">
                          <docker-icon size="18" />
                        </a-button>
                        <a-button size="mini" type="outline" @click="handleViewDeployLog(record)">
                          <template #icon><icon-eye /></template>
                          {{ t('viewLog') }}
                        </a-button>
                        <a-button size="mini" type="primary" @click="handleRedeployDeploy(record)" :loading="redeployLoadingSet.has(record.id)">
                          <template #icon><icon-refresh /></template>
                          {{ t('redeploy') }}
                        </a-button>
                        <a-button size="mini" status="danger" @click="handleDestroyDeploy(record)" :loading="destroyLoadingSet.has(record.id)">
                          <template #icon><icon-delete /></template>
                          {{ t('destroy') }}
                        </a-button>
                      </a-space>
                    </div>
                  </div>
                </div>
              </a-card>
            </div>
          </div>
          <a-empty v-else :description="t('noData')" />

        <div v-if="filteredDeployList.length > 0" class="deployed-pagination">
          <a-pagination
            :total="filteredDeployList.length"
            :current="deployPage.current"
            :page-size="deployPage.pageSize"
            :page-size-options="deployPage.pageSizeOptions"
            :show-page-size="true"
            :show-jumper="true"
            @change="(page) => { deployPage.current = page; }"
            @page-size-change="(size) => { deployPage.pageSize = size; deployPage.current = 1; }"
          />
        </div>

        <!-- 销毁确认对话框 -->
        <a-modal
          v-model:visible="destroyModalVisible"
          :title="t('confirmDestroy')"
          @ok="confirmDestroyDeploy"
          @cancel="cancelDestroyDeploy"
          :ok-text="t('confirm')"
          :cancel-text="t('cancel')"
        >
          <p>{{ t('confirmDestroyHint') }}</p>
        </a-modal>

        <!-- 部署日志抽屉 -->
        <a-drawer
          v-model:visible="deployLogVisible"
          :title="t('deployLog')"
          :width="800"
          :footer="false"
        >
          <div v-show="deployLogLoading" style="text-align:center;padding:40px;">
            <a-spin />
          </div>
          <pre v-show="!deployLogLoading" ref="deployLogRef" class="deploy-log-content">{{ deployLogContent || t('noLog') }}</pre>
        </a-drawer>

        <!-- Compose 日志（复用） -->
        <compose-log
          :visible="composeLogVisible"
          :compose-info="composeLogProject"
          :host-id="String(selectedHostIdForCompose)"
          @update:visible="(val) => { composeLogVisible = val }"
        />

        <!-- Compose 容器列表（复用） -->
        <compose-containers
          :visible="composeContainersVisible"
          :compose-info="composeContainersProject"
          :host-id="String(selectedHostIdForCompose)"
          @update:visible="(val) => { composeContainersVisible = val }"
        />
      </a-tab-pane>
      <!-- 应用商店列表 -->
      <a-tab-pane key="3" :title="t('storeList')">
        <a-card class="store-container">
          <template #title>
            <div class="card-header">
              <div class="header-filters">
                <a-input v-model="filterTitle" :placeholder="t('titleFilterPlaceholder')" allow-clear style="width: 200px;" @input="handleFilterChange" />
                <a-input v-model="filterName" :placeholder="t('nameFilterPlaceholder')" allow-clear style="width: 200px;" @input="handleFilterChange" />
              </div>
              <div class="header-actions">
                <a-button type="primary" @click="handleCreateStore">{{ t('createStore') }}</a-button>
              </div>
            </div>
          </template>

          <a-table
            :columns="columns"
            :data="stores"
            :loading="loading"
            :pagination="pagination"
            @page-change="handlePageChange"
            @page-size-change="handlePageSizeChange"
            :scroll="scroll"
            row-key="id"
          >
            <template #type="{ record }">
              <a-tag :color="getTypeColor(record.type)">
                {{ record.type }}
              </a-tag>
            </template>
            <template #url="{ record }">
              <a v-if="record.url" :href="record.url" target="_blank" rel="noopener noreferrer">
                <a-tag color="arcoblue" style="cursor: pointer;">{{ record.url }}</a-tag>
              </a>
              <span v-else>-</span>
            </template>
            <template #appTotal="{ record }">
              <a-tag>{{ record.total }}</a-tag>
            </template>
            <template #updateTime="{ record }">
              {{ formatDate(record.updated_at) }}
            </template>
            <template #operation="{ record }">
              <a-link type="text" size="small" :disabled="record._syncing" @click="handleEditStore(record)">{{ t('edit') }}</a-link>
              <a-link type="text" size="small" :loading="record._syncing" @click="handleSyncStore(record)">{{ t('sync') }}</a-link>
              <a-link type="text" size="small" status="danger" :disabled="record._syncing" @click="handleDeleteStore(record)">{{ t('delete') }}</a-link>
            </template>
          </a-table>
        </a-card>

        <!-- 创建/编辑商店抽屉 -->
        <a-drawer
          :visible="createDrawerVisible"
          :title="isEditing ? t('edit') + ' ' + t('storeTitle') : t('createStore')"
          :width="700"
          @ok="confirmSaveStore"
          @cancel="cancelCreateStore"
          :ok-text="t('confirm')"
          :cancel-text="t('cancel')"
          :ok-loading="createLoading"
          :footer="true"
        >
          <a-form layout="vertical" :model="createForm">
            <a-form-item :label="t('storeTitle')" required>
              <a-input v-model="createForm.title" :disabled="isEditing" :placeholder="t('storeTitle')" />
            </a-form-item>
            <a-form-item :label="t('name')" required>
              <a-input v-model="createForm.name" :placeholder="t('name')" />
            </a-form-item>
            <a-form-item :label="t('type')" required>
              <a-select v-model="createForm.type" :placeholder="t('type')">
                <a-option value="one_panel">1Panel</a-option>
                <a-option value="casaos">CasaOS</a-option>
              </a-select>
            </a-form-item>
            <a-form-item :label="t('url')" required>
              <a-input v-model="createForm.url" :placeholder="t('url')" />
            </a-form-item>
          </a-form>
        </a-drawer>

        <!-- 删除确认对话框 -->
        <a-modal
          v-model:visible="deleteModalVisible"
          :title="t('confirmDelete')"
          @ok="confirmDeleteStore"
          @cancel="cancelDeleteStore"
          :ok-text="t('confirm')"
          :cancel-text="t('cancel')"
        >
          <p>{{ t('confirmDelete') }}</p>
        </a-modal>

        <!-- 同步确认对话框 -->
        <a-modal
          v-model:visible="syncModalVisible"
          :title="t('confirmSync')"
          @ok="confirmSyncStore"
          @cancel="cancelSyncStore"
          :ok-text="t('confirm')"
          :cancel-text="t('cancel')"
        >
          <p>{{ t('confirmSync') }}</p>
        </a-modal>
      </a-tab-pane>

    </a-tabs>
  </a-card>

  <!-- 应用详情抽屉 -->
  <AppDetails
    v-model:visible="detailVisible"
    :app="detailApp"
    :store-name="detailStoreName"
    :store-id="detailStoreId"
  />
</template>

<script setup>
import { reactive, ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { t, currentLocale } from '../../utils/locale';
import { resolveStoreLogo } from '../../utils/container/image';
import { listStores, createStore, updateStore, deleteStore, syncStore, listStoreDeploys, destroyStoreDeploy, getStoreDeployLog, redeployStoreDeploy } from '../../api/container';
import { Message } from '@arco-design/web-vue';
import { IconEye, IconDelete, IconRefresh, IconBookmark } from '@arco-design/web-vue/es/icon';
import AppDetails from '../../components/container/AppDetails.vue';
import DockerIcon from '../../components/icon/DockerIcon.vue';
import ComposeLog from '../../components/container/ComposeLog.vue';
import ComposeContainers from '../../components/container/ComposeContainers.vue';

// 响应式数据
const stores = ref([]);
const loading = ref(false);
const activeStoreTab = ref('0');
const filterTitle = ref('');
const filterName = ref('');
const keyword = ref('');
let filterTimer = null;
const createDrawerVisible = ref(false);
const createLoading = ref(false);
const isEditing = ref(false);
const editingStoreId = ref(null);
const deleteModalVisible = ref(false);
const syncModalVisible = ref(false);
const selectedStore = ref({});
const detailVisible = ref(false);
const detailApp = ref(null);
const detailStoreName = ref('');
const detailStoreId = ref(0);

// 主标签页切换
const activeMainTab = ref('1');

watch(activeMainTab, (key) => {
  if (key === '2') {
    fetchDeploys();
    startDeployPoll();
  } else {
    stopDeployPoll();
  }
});

// 部署记录
const deployList = ref([]);
const deployLoading = ref(false);
const deployKeyword = ref('');
const destroyModalVisible = ref(false);
const selectedDeploy = ref(null);
const redeployLoadingSet = ref(new Set());
const destroyLoadingSet = ref(new Set());
const deployLogVisible = ref(false);
const deployLogContent = ref('');
const deployLogLoading = ref(false);
const deployLogRef = ref(null);
const deployLogRecord = ref(null);

const deployPage = reactive({
  current: 1,
  pageSize: 12,
  pageSizeOptions: [12, 24, 48],
});

const filteredDeployList = computed(() => {
  let list = deployList.value;
  const kw = deployKeyword.value.trim().toLowerCase();
  if (kw) {
    list = list.filter(r =>
      (r.task_name || '').toLowerCase().includes(kw) ||
      (r.title || r.app_name || '').toLowerCase().includes(kw) ||
      (r.store_name || '').toLowerCase().includes(kw)
    );
  }
  const start = (deployPage.current - 1) * deployPage.pageSize;
  const end = start + deployPage.pageSize;
  return list.slice(start, end);
});

const deployKeywordSearch = () => {
  deployPage.current = 1;
};

// 从商店数据中查找已部署应用的 logo
const getDeployAppLogo = (record) => {
  if (!record || !record.store_name || !record.app_name) return '';
  const store = stores.value.find(s => s.name === record.store_name);
  if (!store || !store.apps) return '';
  const app = store.apps.find(a => a.name === record.app_name);
  if (!app || !app.logo) return '';
  return resolveStoreLogo(app.logo, store.name);
};
let deployLogPollTimer = null;
let deployPollTimer = null;

// Compose 日志/容器抽屉（复用 ComposeLog / ComposeContainers）
const composeLogVisible = ref(false);
const composeLogProject = ref({ name: '' });
const composeContainersVisible = ref(false);
const composeContainersProject = ref({ name: '' });
const selectedHostIdForCompose = ref('');

// 查看 Compose 日志（复用 ComposeLog 组件）
const handleViewComposeLogs = (record) => {
  const hostId = localStorage.getItem('selectedContainerHostId');
  if (!hostId) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  selectedHostIdForCompose.value = hostId;
  composeLogProject.value = { name: record.task_name };
  composeLogVisible.value = true;
};

// 查看 Compose 容器列表（复用 ComposeContainers 组件）
const handleViewComposeContainers = (record) => {
  const hostId = localStorage.getItem('selectedContainerHostId');
  if (!hostId) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  selectedHostIdForCompose.value = hostId;
  composeContainersProject.value = { name: record.task_name };
  composeContainersVisible.value = true;
};

// 部署日志抽屉关闭时停止轮询
watch(deployLogVisible, (visible) => {
  if (!visible) {
    stopDeployLogPolling();
    deployLogRecord.value = null;
  }
});

const scrollDeployLogToBottom = async () => {
  await nextTick();
  if (deployLogRef.value) {
    deployLogRef.value.scrollTop = deployLogRef.value.scrollHeight;
  }
};

const deployStatusColor = (status) => {
  switch (status) {
    case 'running': return 'green';
    case 'error': return 'red';
    case 'deploying': return 'blue';
    default: return 'gray';
  }
};

const deployStatusText = (status) => {
  if (status === 'running') return t.value('deploySuccess');
  if (status === 'error') return t.value('deployFailed');
  if (status === 'deploying') return t.value('deployRunning');
  return status;
};

const fetchDeploys = async () => {
  try {
    // 按当前选中节点筛选
    const savedHostId = localStorage.getItem('selectedContainerHostId');
    const params = savedHostId ? { node_id: parseInt(savedHostId, 10) } : {};
    const res = await listStoreDeploys(params);
    deployList.value = res || [];
  } catch {
    deployList.value = [];
  }
};

// 自动刷新部署记录（切到标签3时启动）
const startDeployPoll = () => {
  stopDeployPoll();
  deployPollTimer = setInterval(fetchDeploys, 5000);
};

const stopDeployPoll = () => {
  if (deployPollTimer) {
    clearInterval(deployPollTimer);
    deployPollTimer = null;
  }
};

// 重新部署
const handleRedeployDeploy = async (record) => {
  if (redeployLoadingSet.value.has(record.id)) return;
  redeployLoadingSet.value.add(record.id);
  try {
    await redeployStoreDeploy(record.id);
    Message.success(t.value('redeploySuccess'));
    fetchDeploys();
    startDeployPoll();
  } catch (error) {
    console.error('重新部署失败:', error);
    Message.error(t.value('redeployFailed'));
  } finally {
    redeployLoadingSet.value.delete(record.id);
  }
};

const handleDestroyDeploy = (record) => {
  selectedDeploy.value = record;
  destroyModalVisible.value = true;
};

const confirmDestroyDeploy = async () => {
  if (!selectedDeploy.value) return;
  const recordId = selectedDeploy.value.id;
  destroyLoadingSet.value.add(recordId);
  try {
    await destroyStoreDeploy(recordId);
    Message.success(t.value('destroySuccess'));
    destroyModalVisible.value = false;
    selectedDeploy.value = null;
    fetchDeploys();
  } catch {
    Message.error(t.value('destroyFailed'));
  } finally {
    destroyLoadingSet.value.delete(recordId);
  }
};

const cancelDestroyDeploy = () => {
  destroyModalVisible.value = false;
  selectedDeploy.value = null;
};

const handleViewDeployLog = async (record) => {
  deployLogVisible.value = true;
  deployLogLoading.value = true;
  deployLogContent.value = '';
  deployLogRecord.value = record;
  try {
    const res = await getStoreDeployLog(record.operation_id || `deploy_${record.id}`);
    deployLogContent.value = res.log_content || '';
  } catch {
    deployLogContent.value = '';
  } finally {
    deployLogLoading.value = false;
    scrollDeployLogToBottom();
  }
  startDeployLogPolling();
};

const startDeployLogPolling = () => {
  stopDeployLogPolling();
  deployLogPollTimer = setInterval(async () => {
    if (!deployLogRecord.value) return;
    try {
      const res = await getStoreDeployLog(deployLogRecord.value.operation_id || `deploy_${deployLogRecord.value.id}`);
      if (res.log_content) {
        deployLogContent.value = res.log_content;
        scrollDeployLogToBottom();
      }
    } catch {
      // 静默失败，不中断轮询
    }
  }, 3000);
};

const stopDeployLogPolling = () => {
  if (deployLogPollTimer) {
    clearInterval(deployLogPollTimer);
    deployLogPollTimer = null;
  }
};

const createForm = reactive({
  title: '',
  name: '',
  type: 'one_panel',
  url: ''
});

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showTotal: true,
  showJumper: true,
  pageSizeOptions: [10, 20, 50, 100],
  showPageSize: true
});

// 应用卡片分页
const appPagination = reactive({
  current: 1,
  pageSize: 20,
  showPageSize: true,
  showJumper: true,
  pageSizeOptions: [20, 40, 60, 100]
});

const scroll = {
  x: 1000,
  y: 600
};

const columns = computed(() => [
  {
    title: t.value('storeTitle'),
    dataIndex: 'title',
    width: 200
  },
  {
    title: t.value('name'),
    dataIndex: 'name',
    width: 180
  },
  {
    title: t.value('type'),
    dataIndex: 'type',
    slotName: 'type',
    width: 120
  },
  {
    title: t.value('url'),
    dataIndex: 'url',
    slotName: 'url',
    width: 300,
  },
  {
    title: t.value('appCount'),
    dataIndex: 'total',
    slotName: 'appTotal',
    width: 100
  },
  {
    title: t.value('updateTime'),
    dataIndex: 'updated_at',
    slotName: 'updateTime',
    width: 180
  },
  {
    title: t.value('action'),
    dataIndex: 'operation',
    slotName: 'operation',
    width: 160,
    fixed: 'right'
  }
]);

const formatDate = (dateString) => {
  if (!dateString) return '';
  try {
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString;
    const pad = (n) => String(n).padStart(2, '0');
    return (
      d.getFullYear() + '-' +
      pad(d.getMonth() + 1) + '-' +
      pad(d.getDate()) + ' ' +
      pad(d.getHours()) + ':' +
      pad(d.getMinutes()) + ':' +
      pad(d.getSeconds())
    );
  } catch {
    return dateString;
  }
};

const getTypeColor = (type) => {
  switch (type) {
    case 'one_panel': return 'blue';
    case 'casaos': return 'green';
    default: return 'gray';
  }
};

// 根据面板语言选择 app 描述
const getAppDescription = (app) => {
  if (!app.descriptions) return app.description || '';
  const isZh = currentLocale.value === 'zh-CN';
  if (isZh) return app.descriptions.zh || app.descriptions.zh_cn || app.description || '';
  return app.descriptions.en || app.descriptions.en_us || app.description || '';
};

const storeApps = computed(() => {
  const idx = parseInt(activeStoreTab.value, 10);
  if (isNaN(idx) || !stores.value[idx]) return [];
  const store = stores.value[idx];
  const apps = store.apps || [];
  return apps.map(app => ({
    ...app,
    logo: resolveStoreLogo(app.logo, store.name)
  }));
});

// 根据关键词过滤应用
const filteredStoreApps = computed(() => {
  const kw = keyword.value.trim().toLowerCase();
  if (!kw) return storeApps.value;
  return storeApps.value.filter(app => {
    const text = [
      app.title,
      app.name,
      app.description,
      ...(app.descriptions ? Object.values(app.descriptions) : []),
      ...(app.tags || [])
    ].filter(Boolean).join(' ').toLowerCase();
    return text.includes(kw);
  });
});

// 分页后的应用列表
const pagedStoreApps = computed(() => {
  const total = filteredStoreApps.value.length;
  const start = (appPagination.current - 1) * appPagination.pageSize;
  const end = Math.min(start + appPagination.pageSize, total);
  return filteredStoreApps.value.slice(start, end);
});

const handleAppPageChange = (page) => {
  appPagination.current = page;
};

const handleAppPageSizeChange = (pageSize) => {
  appPagination.pageSize = pageSize;
  appPagination.current = 1;
};

const handleAppClick = (app) => {
  const idx = parseInt(activeStoreTab.value, 10);
  if (isNaN(idx) || !stores.value[idx]) return;
  detailApp.value = app;
  detailStoreName.value = stores.value[idx].name;
  detailStoreId.value = stores.value[idx].id || 0;
  detailVisible.value = true;
};

const fetchStores = async (page = 1) => {
  try {
    loading.value = true;
    const params = {};
    if (filterTitle.value) params.title = filterTitle.value;
    if (filterName.value) params.name = filterName.value;
    const response = await listStores(params);
    if (response && response.items && Array.isArray(response.items)) {
      stores.value = response.items;
      pagination.total = response.total || response.items.length;
    } else {
      stores.value = [];
      pagination.total = 0;
    }
  } catch (error) {
    console.error('获取商店列表失败:', error);
    Message.error(t.value('getStoreListFailed'));
    stores.value = [];
    pagination.total = 0;
  } finally {
    loading.value = false;
  }
};

const handleFilterChange = () => {
  if (filterTimer) clearTimeout(filterTimer);
  filterTimer = setTimeout(() => {
    pagination.current = 1;
    fetchStores(1);
  }, 300);
};

const handlePageChange = (page) => {
  pagination.current = page;
  fetchStores(page);
};

const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize;
  pagination.current = 1;
  fetchStores(1);
};

const handleCreateStore = () => {
  isEditing.value = false;
  editingStoreId.value = null;
  createForm.title = '';
  createForm.name = '';
  createForm.type = 'one_panel';
  createForm.url = '';
  createDrawerVisible.value = true;
};

const handleEditStore = (store) => {
  isEditing.value = true;
  editingStoreId.value = store.id;
  createForm.title = store.title || '';
  createForm.name = store.name || '';
  createForm.type = store.type || 'one_panel';
  createForm.url = store.url || '';
  createDrawerVisible.value = true;
};

const confirmSaveStore = async () => {
  if (!createForm.title || !createForm.name || !createForm.url) {
    Message.error(t.value('pleaseFillCompleteInfo'));
    return;
  }
  try {
    createLoading.value = true;
    if (isEditing.value) {
      await updateStore({
        id: editingStoreId.value,
        title: createForm.title,
        name: createForm.name,
        type: createForm.type,
        url: createForm.url
      });
      Message.success(t.value('update') + t.value('success'));
    } else {
      await createStore({
        title: createForm.title,
        name: createForm.name,
        type: createForm.type,
        url: createForm.url
      });
      Message.success(t.value('createStore') + t.value('success'));
      createDrawerVisible.value = false;
      fetchStores();
    }
  } catch (error) {
    console.error('保存商店失败:', error);
    Message.error(isEditing.value ? t('update') + t('failed') : t('createStore') + t('failed'));
  } finally {
    createLoading.value = false;
  }
};

const cancelCreateStore = () => {
  createDrawerVisible.value = false;
};

const handleSyncStore = (store) => {
  selectedStore.value = store;
  syncModalVisible.value = true;
};

const confirmSyncStore = async () => {
  try {
    selectedStore.value._syncing = true;
    await syncStore({
      title: selectedStore.value.title || '',
      name: selectedStore.value.name,
      type: selectedStore.value.type,
      url: selectedStore.value.url
    });
    Message.success(t.value('storeSyncSuccess'));
    syncModalVisible.value = false;
    fetchStores();
  } catch (error) {
    console.error('同步商店失败:', error);
    Message.error(t.value('storeSyncFailed'));
  } finally {
    selectedStore.value._syncing = false;
  }
};

const cancelSyncStore = () => {
  syncModalVisible.value = false;
  selectedStore.value = {};
};

const handleDeleteStore = (store) => {
  selectedStore.value = store;
  deleteModalVisible.value = true;
};

const confirmDeleteStore = async () => {
  try {
    await deleteStore({ store_id: selectedStore.value.id });
    Message.success(t.value('deleteSuccess'));
    deleteModalVisible.value = false;
    fetchStores();
  } catch (error) {
    console.error('删除商店失败:', error);
    Message.error(t.value('deleteFailed'));
  }
};

const cancelDeleteStore = () => {
  deleteModalVisible.value = false;
  selectedStore.value = {};
};

onMounted(() => {
  fetchStores();
  // 节点切换时重新加载部署列表
  window.addEventListener('containerHostChanged', fetchDeploys);
});

onUnmounted(() => {
  stopDeployPoll();
  window.removeEventListener('containerHostChanged', fetchDeploys);
});
</script>

<style scoped>
.store-container {
  min-height: 400px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.header-filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.card-header .title {
  font-size: 16px;
  font-weight: 500;
}

.header-actions {
  display: flex;
  gap: 8px;
}

/* App 卡片网格 */
.app-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 12px;
}

.app-card {
  cursor: pointer;
}

.app-card .arco-card {
  border: 1px solid var(--color-border);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.app-card .arco-card:hover {
  border-color: rgb(var(--arcoblue-5));
  box-shadow: 0 2px 8px rgba(var(--arcoblue-5), 0.15);
}

.app-card :deep(.arco-card-body) {
  padding: 12px !important;
}

.app-wrapper {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.app-image {
  flex-shrink: 0;
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s;
}

.app-card:hover .app-image {
  transform: scale(1.15);
}

.app-logo {
  width: 60px;
  height: 60px;
  object-fit: contain;
  border-radius: 4px;
}

.app-logo-placeholder {
  width: 60px;
  height: 60px;
  border-radius: 4px;
  background: var(--color-fill-3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 600;
  color: var(--color-text-3);
}

.app-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.content-top {
  display: flex;
  align-items: center;
}

.app-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--color-text-1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.content-middle {
  flex: 1;
}

.app-description {
  font-size: 13px;
  color: var(--color-text-3);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.4;
  min-height: calc(1.4em * 2);
}

.content-bottom {
  display: flex;
  align-items: center;
}

.app-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.app-pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding: 16px 0;
}

.deploy-log-content {
  background: #1e1e1e;
  color: #d4d4d4;
  font-size: 12px;
  line-height: 1.6;
  padding: 16px;
  border-radius: 4px;
  max-height: 500px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'Consolas', 'Courier New', monospace;
}

body[arco-theme="dark"] .deploy-log-content {
  background: #0d0d0d;
  color: #cccccc;
}

.app-search-bar {
  margin-bottom: 12px;
}

/* ====== 已部署卡片样式 ====== */
.deployed-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.deployed-count {
  font-size: 14px;
  color: var(--color-text-2);
}
.deployed-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 12px;
}
.deployed-card .arco-card {
  border: 1px solid var(--color-border-2);
  transition: border-color 0.2s;
}
.deployed-card .arco-card:hover {
  border-color: rgb(var(--arcoblue-5));
}
.deployed-wrapper {
  display: flex;
  gap: 14px;
}
.deployed-image {
  flex-shrink: 0;
  width: 56px;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 4px;
}
.deployed-logo-placeholder {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  background: linear-gradient(135deg, rgb(var(--arcoblue-5)), rgb(var(--purple-5)));
  color: #fff;
  font-size: 22px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.deployed-logo {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  object-fit: contain;
  flex-shrink: 0;
}
.deployed-content {
  flex: 1;
  min-width: 0;
}
.deployed-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.deployed-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--color-text-1);
}
.deployed-middle {
  margin: 6px 0 10px;
}
.task-name-text {
  font-size: 12px;
  background: var(--color-fill-2);
  padding: 1px 6px;
  border-radius: 3px;
}

/* 运行状态指示点 */
.running-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.running-dot-on {
  background-color: #00d42a;
  box-shadow: 0 0 4px rgba(0, 212, 42, 0.6);
}
.running-dot-off {
  background-color: #f53f3f;
  box-shadow: 0 0 4px rgba(245, 63, 63, 0.6);
}
.deployed-bottom {
  display: flex;
  justify-content: flex-end;
}
.deployed-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
@media (max-width: 768px) {
  .deployed-grid {
    grid-template-columns: 1fr;
  }
}
</style>
