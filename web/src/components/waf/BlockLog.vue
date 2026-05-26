<template>
  <div class="block-log-container">
    <div class="card-header">
      <div class="search-filters">
        <a-input
          v-model="searchFilters.application"
          :placeholder="t('application')"
          size="small"
          allow-clear
          @change="handleSearch"
          class="search-input"
        />
        <a-input
          v-model="searchFilters.request_uri"
          :placeholder="t('requestUri')"
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

    <!-- 拦截日志表格 -->
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
      <template #attack_type="{ record }">
        <a-tag :color="getAttackTypeColor(record.attack_type)">
          {{ getAttackTypeText(record.attack_type) }}
        </a-tag>
      </template>
      <template #operation="{ record }">
        <a-link type="text" size="small" @click="openLogDetail(record)">{{ t('detail') }}</a-link>
        <a-link type="text" size="small" @click="handleAnalyzeIP(record)">{{ t('ipAnalyze') }}</a-link>
        <a-link type="text" size="small" status="danger" @click="handleBlockIP(record)">{{ t('block') }}</a-link>
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
          <a-descriptions-item :label="t('attackType')">
            <a-tag :color="getAttackTypeColor(selectedLog.attack_type)">
              {{ getAttackTypeText(selectedLog.attack_type) }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item :label="t('reason')">
            {{ selectedLog.reason }}
          </a-descriptions-item>
          <a-descriptions-item :label="t('action')">
            <a-tag :color="getActionColor(selectedLog.action)">
              {{ getActionText(selectedLog.action) }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item :label="t('clientIp')">
            {{ selectedLog.client_ip }}
          </a-descriptions-item>
          <a-descriptions-item :label="t('userAgent')" v-if="selectedLog.user_agent">
            <div class="user-agent-content">{{ selectedLog.user_agent }}</div>
          </a-descriptions-item>
          <a-descriptions-item :label="t('requestUri')">
            {{ selectedLog.request_uri }}
          </a-descriptions-item>
          <a-descriptions-item :label="t('requestMethod')">
            {{ selectedLog.request_method }}
          </a-descriptions-item>
          <a-descriptions-item :label="t('application')">            
            {{ selectedLog.application }}          
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
      <p>{{ t('clearBlockLogsConfirmMessage') }}</p>
    </a-modal>

    <!-- 拉黑确认对话框 -->
    <a-modal 
      v-model:visible="blockIPModalVisible" 
      :title="t('blockIPConfirm')" 
      @ok="handleBlockIPSubmit" 
      @cancel="handleBlockIPCancel"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
    >
      <p>{{ t('blockIPConfirmMessage', { ip: blockIPTarget.ip }) }}</p>
    </a-modal>

    <!-- IP分析结果抽屉 -->
    <a-drawer
      v-model:visible="analyzeDrawerVisible"
      :title="'AbuseIPDB 信誉分析 - ' + analysisTargetIp"
      width="620px"
      :footer="false"
      @cancel="analyzeDrawerVisible = false"
    >
      <!-- 加载骨架屏 -->
      <div v-if="analyzing" class="analysis-loading">
        <div class="loading-header">
          <div class="loading-dot"></div>
          <span>{{ t('analyzing') }}</span>
        </div>
        <div class="skeleton-list">
          <div class="skeleton-item">
            <div class="skeleton-line skeleton-line-short"></div>
            <div class="skeleton-line"></div>
            <div class="skeleton-line"></div>
            <div class="skeleton-line skeleton-line-long"></div>
          </div>
        </div>
      </div>

      <div v-else-if="analysisData" class="analysis-results">
        <div class="analysis-platform-block">
          <div class="platform-header">
            <span class="platform-icon"></span>
            <span class="platform-name">AbuseIPDB</span>
            <a-tag color="green" size="small">{{ t('success') }}</a-tag>
          </div>
          <div class="platform-body">
            <a-descriptions :column="1" size="mini" bordered layout="horizontal">
              <a-descriptions-item
                v-for="item in formatAnalysisData"
                :key="item.label"
                :label="item.label"
              >
                <span :class="{ 'risk-high': item.highlight }">{{ item.value }}</span>
              </a-descriptions-item>
            </a-descriptions>
          </div>
        </div>
      </div>
      <div v-else-if="!analyzing && analysisMessage">
        <a-result status="warning" :title="analysisMessage" />
      </div>
      <a-empty v-else :description="t('noAnalyzeResult')" />
    </a-drawer>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue';
import { t } from '../../utils/locale';
import { getBlockLog, cleanBlockLog, blockIP, analyzeThreatIntelIp } from '../../api/waf';
import { Message } from '@arco-design/web-vue';

const logs = ref([]);
const allLogs = ref([]);
const loading = ref(false);
const cleaning = ref(false);
const detailDrawerVisible = ref(false);
const clearLogsModalVisible = ref(false);
const blockIPModalVisible = ref(false);
const selectedLog = ref(null);
const blockIPTarget = ref({ ip: '' });
const analyzeDrawerVisible = ref(false);
const analyzing = ref(false);
const analysisTargetIp = ref('');
const analysisData = ref(null);
const analysisMessage = ref('');
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
  application: '',
  request_uri: '',
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
    dataIndex: 'application',    
    width: 150  
  },
  {
    title: t.value('requestUri'),
    dataIndex: 'request_uri',
    width: 200,
    ellipsis: true,
    tooltip: true
  },
  {
    title: t.value('attackIp'),
    dataIndex: 'client_ip',
    slotName: 'client_ip',
    width: 150
  },

  {
    title: t.value('attackType'),
    dataIndex: 'attack_type',
    slotName: 'attack_type',
    width: 100
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
    'blocked': 'red',
    'record': 'blue'
  };
  return colorMap[action] || 'gray';
};

const getActionText = (action) => {
  const textMap = {
    'blocked': t.value('blocked'),
    'record': t.value('record')
  };
  return textMap[action] || action;
};

const getAttackTypeColor = (attackType) => {
  const colorMap = {
    'cc': 'blue',
    'sql': 'red',
    'xss': 'orange',
    'ssrf': 'purple',
    'cmd_injection': 'red'
  };
  return colorMap[attackType] || 'gray';
};

const getAttackTypeText = (attackType) => {
  const textMap = {
    'bot': 'BOT',
    'cc': 'CC',
    'sql': 'SQL',
    'xss': 'XSS',
    'ssrf': 'SSRF',
    'cmd_injection': 'CMD injection'
  };
  return textMap[attackType] || attackType.toUpperCase();
};

const fetchLogs = async (page = 1) => {
  loading.value = true;
  try {
    const response = await getBlockLog({
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
    console.error('获取拦截日志失败:', error);
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

  if (searchFilters.application) {
    const appFilter = searchFilters.application.toLowerCase();
    filtered = filtered.filter(log =>
      log.application && log.application.toLowerCase().includes(appFilter)
    );
  }

  if (searchFilters.request_uri) {
    const uriFilter = searchFilters.request_uri.toLowerCase();
    filtered = filtered.filter(log =>
      log.request_uri && log.request_uri.toLowerCase().includes(uriFilter)
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
    const response = await cleanBlockLog({});
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

const handleBlockIP = (record) => {
  blockIPTarget.value.ip = record.client_ip;
  blockIPModalVisible.value = true;
};

const handleBlockIPSubmit = async () => {
  try {
    const response = await blockIP({ ip: blockIPTarget.value.ip });
    if (response && response.message) {
      Message.success('IP blocked successfully');
    }
  } catch (error) {
    console.error('Block IP failed:', error);
    Message.error('Block IP failed');
  } finally {
    blockIPModalVisible.value = false;
    blockIPTarget.value.ip = '';
  }
};

const handleBlockIPCancel = () => {
  blockIPModalVisible.value = false;
  blockIPTarget.value.ip = '';
};

const handleAnalyzeIP = async (record) => {
  analysisTargetIp.value = record.client_ip;
  analyzeDrawerVisible.value = true;
  analyzing.value = true;
  analysisData.value = null;
  analysisMessage.value = '';
  try {
    const res = await analyzeThreatIntelIp({ ip: record.client_ip });
    if (res && res.data) {
      analysisData.value = res.data;
      analysisMessage.value = '';
    } else {
      analysisData.value = null;
      analysisMessage.value = res.message || '查询失败';
    }
  } catch (error) {
    analysisMessage.value = error.message || 'IP 分析请求失败';
  } finally {
    analyzing.value = false;
  }
};

const formatAnalysisData = computed(() => {
  const data = analysisData.value;
  if (!data) return [];
  const items = [];
  const score = data.abuseConfidenceScore;
  items.push({ label: '滥用置信度', value: score != null ? score + '%' : '未知', highlight: score > 50 });
  items.push({ label: 'IP 地址', value: data.ipAddress || '未知' });
  items.push({ label: '国家/地区', value: data.countryName || data.countryCode || '未知' });
  items.push({ label: 'ISP', value: data.isp || '未知' });
  items.push({ label: '域名', value: data.domain || '无' });
  items.push({ label: '使用类型', value: data.usageType || '未知' });
  items.push({ label: '总举报次数', value: data.totalReports != null ? String(data.totalReports) : '0' });
  items.push({ label: '最近举报', value: data.lastReportedAt || '无' });
  items.push({ label: '是否 Tor 节点', value: data.isTor ? '是' : '否', highlight: data.isTor });
  items.push({ label: '是否在白名单', value: data.isWhitelisted ? '是' : '否' });
  return items;
});

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

.analysis-results {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.analysis-platform-block {
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 0;
  overflow: hidden;
}

.platform-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: var(--color-fill-2);
  border-bottom: 1px solid var(--color-border);
}

.platform-icon {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
  background: #f77234;
  box-shadow: 0 0 6px rgba(247, 114, 52, 0.5);
}

.platform-name {
  font-weight: 600;
  font-size: 14px;
  flex: 1;
}

.platform-body {
  padding: 12px 18px 18px;
}

.platform-body :deep(.arco-descriptions-item-label) {
  color: var(--color-text-3);
  font-size: 12px;
  width: 110px;
  white-space: nowrap;
}

.platform-body :deep(.arco-descriptions-item-value) {
  font-size: 13px;
}

.risk-high {
  color: rgb(var(--danger-6));
  font-weight: 600;
}

.platform-error {
  margin: 16px 18px;
  font-size: 13px;
  color: rgb(var(--danger-6));
}

/* 加载骨架屏 */
.analysis-loading {
  padding: 10px 0;
}

.loading-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  font-size: 15px;
  font-weight: 500;
  color: var(--color-text-2);
}

.loading-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #165dff;
  animation: pulse-dot 1.2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 0.3; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}

.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 0 18px;
}

.skeleton-item {
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-line {
  height: 14px;
  border-radius: 6px;
  background: linear-gradient(90deg, var(--color-fill-2) 25%, var(--color-fill-3) 50%, var(--color-fill-2) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

.skeleton-line-short {
  width: 40%;
}

.skeleton-line-long {
  width: 80%;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
