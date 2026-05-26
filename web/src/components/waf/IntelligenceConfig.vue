<template>
  <a-card class="waf-container">
    <div class="table-container">
      <div class="search-filters">
        <div class="flex-grow"></div>
        <a-button type="outline" size="small" :loading="syncing" @click="handleSync">
          {{ t('sync') }}
        </a-button>
        <a-button type="outline" size="small" @click="fetchConfig" :loading="loading">
          {{ t('refresh') }}
        </a-button>
        <a-button type="outline" size="small" @click="showEdit">
          {{ t('edit') }}
        </a-button>
      </div>

      <a-table
        :columns="columns"
        :data="tableData"
        :loading="loading"
        :pagination="false"
        :scroll="scroll"
        row-key="key"
      >
        <template #api_key="{ record }">
          <span class="api-key-text">{{ apiKeyVisible ? record.api_key : '****' }}</span>
          <a-button
            type="text"
            size="mini"
            @click="apiKeyVisible = !apiKeyVisible"
            style="margin-left: 4px"
          >
            <icon-eye v-if="!apiKeyVisible" />
            <icon-eye-invisible v-else />
          </a-button>
        </template>
        <template #enabled="{ record }">
          <a-tag :color="record.enabled ? 'green' : 'red'" size="small">
            {{ record.enabled ? t('enabled') : t('disabled') }}
          </a-tag>
        </template>
        <template #actions>
          <a-link type="text" size="mini" :loading="testing" @click="handleTableTest">
            {{ t('test') }}
          </a-link>
        </template>
      </a-table>

      <div class="sync-status" v-if="config.last_sync_time">
        <span>{{ t('lastSyncTime') }}: {{ formatTime(config.last_sync_time) }}</span>
        <a-divider direction="vertical" />
        <span>{{ t('addedIp') }}: {{ config.synced_ip_count }} 个</span>
      </div>
      <div class="sync-status" v-else>
        <span>{{ t('noSyncedBlacklist') }}</span>
      </div>
    </div>

    <a-drawer
      v-model:visible="editVisible"
      :title="'AbuseIPDB' + ' - ' + t('edit')"
      width="500px"
      @cancel="editVisible = false"
      :footer="false"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="API Key">
          <a-input-password
            v-model="form.api_key"
            :placeholder="t('enterApiKey')"
            allow-clear
          />
        </a-form-item>
        <a-form-item :label="t('enabled')">
          <a-switch v-model="form.enabled" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" :loading="saving" @click="handleSave">
            {{ t('save') }}
          </a-button>
          <a-button style="margin-left: 12px" :loading="testing" @click="handleTest">
            {{ t('test') }}
          </a-button>
          <a-button style="margin-left: 12px" @click="editVisible = false">
            {{ t('cancel') }}
          </a-button>
        </a-form-item>
      </a-form>
    </a-drawer>
  </a-card>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { Message } from '@arco-design/web-vue';
import { IconEye, IconEyeInvisible } from '@arco-design/web-vue/es/icon';
import { t } from '../../utils/locale';
import { getThreatIntelConfig, updateThreatIntelConfig, testThreatIntelApi, syncThreatIntelBlacklist } from '../../api/waf';

const loading = ref(false);
const saving = ref(false);
const testing = ref(false);
const syncing = ref(false);
const editVisible = ref(false);
const apiKeyVisible = ref(false);

const scroll = { x: 600 };

const config = reactive({
  api_key: '',
  enabled: false,
  last_sync_time: null,
  synced_ip_count: 0,
});

const form = reactive({
  api_key: '',
  enabled: true,
});

const columns = computed(() => [
  { title: 'API Key', dataIndex: 'api_key', slotName: 'api_key', width: 280 },
  { title: t.value('status'), dataIndex: 'enabled', slotName: 'enabled', width: 120 },
  { title: t.value('actions'), slotName: 'actions', width: 100 },
]);

const tableData = computed(() => [{
  key: '1',
  api_key: config.api_key,
  enabled: config.enabled,
}]);

const fetchConfig = async () => {
  loading.value = true;
  try {
    const res = await getThreatIntelConfig();
    if (res) {
      config.api_key = res.api_key || '';
      config.enabled = res.enabled !== undefined ? res.enabled : false;
      config.last_sync_time = res.last_sync_time || null;
      config.synced_ip_count = res.synced_ip_count || 0;
    }
  } catch {
    Message.error(t.value('fetchFailed'));
  } finally {
    loading.value = false;
  }
};

const showEdit = () => {
  form.api_key = config.api_key;
  form.enabled = config.enabled;
  editVisible.value = true;
};

const handleSave = async () => {
  saving.value = true;
  try {
    await updateThreatIntelConfig({
      api_key: form.api_key || '',
      enabled: form.enabled,
    });
    Message.success(t.value('saveSuccess'));
    editVisible.value = false;
    await fetchConfig();
  } catch (error) {
    Message.error(error.message || t.value('saveFailed'));
  } finally {
    saving.value = false;
  }
};

const handleTest = async () => {
  if (!form.api_key) {
    Message.warning(t.value('apiKeyRequired'));
    return;
  }
  testing.value = true;
  try {
    const res = await testThreatIntelApi({ api_key: form.api_key });
    if (res && res.success) {
      Message.success(res.message || t.value('testSuccess'));
    } else {
      Message.error(res.message || t.value('testFailed'));
    }
  } catch (error) {
    Message.error(error.message || t.value('testFailed'));
  } finally {
    testing.value = false;
  }
};

const handleTableTest = async () => {
  if (!config.api_key) {
    Message.warning(t.value('apiKeyRequired'));
    return;
  }
  testing.value = true;
  try {
    const res = await testThreatIntelApi({ api_key: config.api_key });
    if (res && res.success) {
      Message.success(res.message || t.value('testSuccess'));
    } else {
      Message.error(res.message || t.value('testFailed'));
    }
  } catch (error) {
    Message.error(error.message || t.value('testFailed'));
  } finally {
    testing.value = false;
  }
};

const handleSync = async () => {
  if (!config.api_key) {
    Message.warning(t.value('apiKeyRequired'));
    return;
  }
  syncing.value = true;
  try {
    const res = await syncThreatIntelBlacklist();
    if (res && res.success) {
      Message.success(res.message || t.value('syncSuccess'));
      if (res.added_count > 0) {
        Message.info(`${res.added_count} ${t.value('addedIp')}`);
      }
    } else {
      Message.warning(res.message || t.value('syncFailed'));
    }
  } catch (error) {
    Message.error(error.message || t.value('syncFailed'));
  } finally {
    syncing.value = false;
    await fetchConfig();
  }
};

onMounted(() => {
  fetchConfig();
});

function formatTime(timeStr) {
  if (!timeStr) return '';
  const d = new Date(timeStr);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}
</script>

<style scoped>
.waf-container {
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 15px;
  font-size: 1.3em;
  padding: 20px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.title {
  font-size: 16px;
  font-weight: 600;
}

.table-container {
  margin-top: 8px;
}

.search-filters {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.flex-grow {
  flex: 1;
}

.api-key-text {
  font-family: 'Courier New', 'Consolas', monospace;
  font-size: 13px;
  color: var(--color-text-3);
}

.sync-status {
  margin-top: 16px;
  padding: 10px 16px;
  background: var(--color-fill-2);
  border-radius: 6px;
  font-size: 13px;
  color: var(--color-text-3);
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
