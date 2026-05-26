<template>
  <div class="block-log-container">
    <div class="card-header">
      <div class="search-filters">
        <a-input
          v-model="searchFilters.application_url"
          :placeholder="t('application')"
          size="small"
          allow-clear
          @change="handleSearch"
          class="search-input"
        />
        <a-input
          v-model="searchFilters.client_ip"
          :placeholder="t('attackIp')"
          size="small"
          allow-clear
          @change="handleSearch"
          class="search-input"
        />
      </div>
      <div class="header-buttons">
        <a-button type="outline" size="small" @click="fetchLogs(1)" :loading="loading" class="refresh-btn">
          {{ t('refresh') }}
        </a-button>
        <a-button type="outline" status="danger" size="small" @click="showClearLogsModal" :loading="cleaning" class="clear-btn">
          {{ t('clearLogs') }}
        </a-button>
      </div>
    </div>

    <!-- 黑白名单日志表格 -->
    <a-table 
      :columns="columns" 
      :data="logs" 
      :loading="loading" 
      :pagination="pagination"
      @page-change="handlePageChange"
      @page-size-change="handlePageSizeChange"
      :scroll="scroll"
      row-key="timestamp"
    >
      <template #action="{ record }">
        <a-tag :color="getActionColor(record.action)">
          {{ getActionText(record.action) }}
        </a-tag>
      </template>
      <template #client_ip="{ record }">
        <div class="ip-with-location">
          <div class="ip-address">{{ record.client_ip }}</div>
          <div class="ip-location">{{ record.geoip.city }}, {{ record.geoip.country }}</div>
        </div>
      </template>
      <template #group="{ record }">
        <a-tag v-if="record.group" color="blue">{{ record.group }}</a-tag>
        <span v-else>-</span>
      </template>
      <template #operation="{ record }">
        <a-button type="text" size="small" @click="openLogDetail(record)">{{ t('detail') }}</a-button>
      </template>
    </a-table>

    <!-- 日志详情抽屉 -->
    <a-drawer
      v-model:visible="detailDrawerVisible"
      :title="t('logDetail')"
      width="600px"
      :footer="false"
    >
      <div v-if="selectedLog" class="log-detail">
        <a-descriptions :column="1" bordered>
          <a-descriptions-item :label="t('action')">
            <a-tag :color="getActionColor(selectedLog.action)">
              {{ getActionText(selectedLog.action) }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item :label="t('clientIp')">
            {{ selectedLog.client_ip }}
          </a-descriptions-item>
          <a-descriptions-item :label="t('group')">
            {{ selectedLog.group || '-' }}
          </a-descriptions-item>
          <a-descriptions-item :label="t('userAgent')" v-if="selectedLog.user_agent">
            <div class="user-agent-content">{{ selectedLog.user_agent }}</div>
          </a-descriptions-item>
          <a-descriptions-item :label="t('application')">            
            {{ selectedLog.application_url }}          
          </a-descriptions-item>
          <a-descriptions-item :label="t('datetime')">
            {{ selectedLog.datetime }}
          </a-descriptions-item>
          <a-descriptions-item :label="t('timestamp')">
            {{ selectedLog.timestamp }}
          </a-descriptions-item>
          <a-descriptions-item :label="t('geoip')">
            <div class="geoip-detail">
              <div class="geoip-row">
                <span class="geoip-label">{{ t('countryCode') }}:</span>
                <span class="geoip-value">{{ selectedLog.geoip.country_code }}</span>
              </div>
              <div class="geoip-row">
                <span class="geoip-label">{{ t('city') }}:</span>
                <span class="geoip-value">{{ selectedLog.geoip.city }}</span>
              </div>
              <div class="geoip-row">
                <span class="geoip-label">{{ t('country') }}:</span>
                <span class="geoip-value">{{ selectedLog.geoip.country }}</span>
              </div>
              <div class="geoip-row">
                <span class="geoip-label">{{ t('latitude') }}:</span>
                <span class="geoip-value">{{ selectedLog.geoip.latitude || '-' }}</span>
              </div>
              <div class="geoip-row">
                <span class="geoip-label">{{ t('longitude') }}:</span>
                <span class="geoip-value">{{ selectedLog.geoip.longitude || '-' }}</span>
              </div>
              <div class="geoip-row">
                <span class="geoip-label">{{ t('location') }}:</span>
                <span class="geoip-value">{{ selectedLog.geoip.location }}</span>
              </div>
            </div>
          </a-descriptions-item>
        </a-descriptions>
      </div>
    </a-drawer>

    <!-- 清理日志确认对话框 -->
    <a-modal 
      v-model:visible="clearLogsModalVisible" 
      :title="t('clearLoginLogsConfirmTitle')" 
      @ok="handleClearLogs" 
      @cancel="cancelClearLogs"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
    >
      <p>{{ t('clearIPblackLogsConfirmMessage') }}</p>
    </a-modal>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue';
import { t } from '../../utils/locale';
import { getBlackWhiteLog, cleanBlackWhiteLog } from '../../api/waf';
import { Message } from '@arco-design/web-vue';
import { Table, Tag, Button, Drawer, Descriptions, DescriptionsItem } from '@arco-design/web-vue';

const logs = ref([]);
const allLogs = ref([]);
const loading = ref(false);
const cleaning = ref(false);
const detailDrawerVisible = ref(false);
const clearLogsModalVisible = ref(false);
const selectedLog = ref(null);
const pagination = reactive({
  current: 1,
  pageSize: 50,
  total: 0,
  showTotal: true,
  showJumper: true,
  pageSizeOptions: [10, 20, 50, 100],
  showPageSize: true
});

const searchFilters = reactive({
  application_url: '',
  client_ip: ''
});

const scroll = {
  x: 1200,
  y: 600
};

const columns = computed(() => [
  {
    title: t.value('datetime'),
    dataIndex: 'datetime',
    width: 180
  },
  {
    title: t.value('action'),
    dataIndex: 'action',
    slotName: 'action',
    width: 100
  },
  {
    title: t.value('application'),
    dataIndex: 'application_url',
    width: 150
  },
  {
    title: t.value('attackIp'),
    dataIndex: 'client_ip',
    slotName: 'client_ip',
    width: 150
  },
  {
    title: t.value('MatchingIPgroup'),
    dataIndex: 'group',
    slotName: 'group',
    width: 120
  },
  {
    title: t.value('action'),
    dataIndex: 'operation',
    slotName: 'operation',
    width: 100,
    fixed: 'right'
  }
]);

const getActionColor = (action) => {
  const colorMap = {
    'block': 'red',
    'allow': 'green'
  };
  return colorMap[action] || 'gray';
};

const getActionText = (action) => {
  const textMap = {
    'block': t.value('blocked'),
    'allow': t.value('allowed')
  };
  return textMap[action] || action;
};

const fetchLogs = async (page = 1) => {
  loading.value = true;
  try {
    const response = await getBlackWhiteLog({
      skip: 0,
      limit: 10000
    });

    if (response && response.logs) {
      allLogs.value = response.logs;
      applyFilters();
    } else {
      allLogs.value = [];
      logs.value = [];
      pagination.total = 0;
    }
  } catch (error) {
    console.error('获取黑白名单日志失败:', error);
    Message.error(t.value('fetchFailed'));
    allLogs.value = [];
    logs.value = [];
    pagination.total = 0;
  } finally {
    loading.value = false;
  }
};

const applyFilters = () => {
  let filtered = [...allLogs.value];

  if (searchFilters.application_url) {
    const appFilter = searchFilters.application_url.toLowerCase();
    filtered = filtered.filter(log =>
      log.application_url && log.application_url.toLowerCase().includes(appFilter)
    );
  }

  if (searchFilters.client_ip) {
    const ipFilter = searchFilters.client_ip.toLowerCase();
    filtered = filtered.filter(log =>
      log.client_ip && log.client_ip.toLowerCase().includes(ipFilter)
    );
  }

  pagination.total = filtered.length;
  const start = (pagination.current - 1) * pagination.pageSize;
  const end = start + pagination.pageSize;
  logs.value = filtered.slice(start, end);
};

const handleSearch = () => {
  pagination.current = 1;
  applyFilters();
};

const handlePageChange = (page) => {
  pagination.current = page;
  applyFilters();
};

const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize;
  pagination.current = 1;
  applyFilters();
};

const openLogDetail = (log) => {
  selectedLog.value = log;
  detailDrawerVisible.value = true;
};

const showClearLogsModal = () => {
  clearLogsModalVisible.value = true;
};

const cancelClearLogs = () => {
  clearLogsModalVisible.value = false;
};

const handleClearLogs = async () => {
  cleaning.value = true;
  try {
    const response = await cleanBlackWhiteLog({});
    if (response && response.message) {
      Message.success(t.value('cleanSuccess'));
      // 重新获取日志列表
      await fetchLogs(1);
    }
  } catch (error) {
    console.error('清理日志失败:', error);
    Message.error(t.value('cleanFailed'));
  } finally {
    cleaning.value = false;
    clearLogsModalVisible.value = false;
  }
};

onMounted(() => {
  fetchLogs(1);
});
</script>

<style scoped>
.block-log-container {
  padding: 0;
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

.search-filters {
  display: flex;
  gap: 10px;
  align-items: center;
  flex: 1;
}

.search-input {
  width: 200px;
}

.header-buttons {
  display: flex;
  gap: 10px;
  align-items: center;
}

.title {
  margin: 0;
  padding: 0;
}

.geoip-tooltip {
  padding: 8px;
}

.geoip-item {
  margin-bottom: 4px;
}

.geoip-label {
  font-weight: bold;
  margin-right: 8px;
  color: #86909c;
}

.geoip-value {
  color: #1d2129;
}

.log-detail {
  padding: 16px;
}

.user-agent-content {
  word-break: break-all;
  max-width: 400px;
}

.geoip-detail {
  padding: 8px;
}

.geoip-row {
  margin-bottom: 8px;
  display: flex;
  align-items: center;
}

.geoip-row .geoip-label {
  font-weight: bold;
  margin-right: 8px;
  min-width: 80px;
  color: #86909c;
}

.geoip-row .geoip-value {
  color: var(--primary-color);
}

.ip-with-location {
  display: flex;
  flex-direction: column;
  line-height: 1.4;
}

.ip-address {
  font-weight: 500;
  color: var(--primary-color);
}

.ip-location {
  font-size: 12px;
  color: #86909c;
}
</style>