<template>
  <a-card class="waf-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('globalSetting') }}</span>
          <a-tag :color="wafStatus === 'running' || wafStatus === true ? 'green' : 'red'">
          {{ wafStatus === 'running' || wafStatus === true ? (t('running') ) : (t('stopped')) }}
         </a-tag>
         <div class="status-actions">
          <a-link type="text" size="small" :loading="actionLoading.stop" @click="handleAction('stop')" :disabled="wafStatus === 'stopped' || wafStatus === false || actionLoading.stop">
            {{ t('stop') }}
          </a-link>
          <a-link type="text" size="small" :loading="actionLoading.restart" @click="handleAction('restart')" :disabled="wafStatus === 'stopped' || wafStatus === false || actionLoading.restart">
            {{ t('restart') }}
          </a-link>
          <a-link type="text" size="small" :loading="actionLoading.start" @click="handleAction('start')" :disabled="wafStatus === 'running' || wafStatus === true || actionLoading.start">
            {{ t('start')}}
          </a-link>
      </div>
      </div>
    </template>

<!--  内容区域  -->
    <a-tabs position="left">
      <a-tab-pane key="1" :title="t('globalSetting')">
        <div class="tab-content">
          <div class="section-title">{{ t('connectionTuning') }}</div>
          <div class="card-grid">
            <a-card hoverable>
              <div :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }">
                <span :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }">
                  <a-typography-text>{{ t('workerConnections') }}</a-typography-text>
                </span>
                <a-button size="small" type="outline" @click="handleEditNumber('worker_connections', globalConfig.worker_connections)">{{ globalConfig.worker_connections }}</a-button>
              </div>
            </a-card>
            <a-card hoverable>
              <div :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }">
                <span :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }">
                  <a-typography-text>{{ t('keepaliveTimeout') }}</a-typography-text>
                </span>
                <span style="display: flex; align-items: center; gap: 8px;">
                  <a-typography-text>{{ globalConfig.keepalive_timeout }}s</a-typography-text>
                  <a-button size="small" type="outline" @click="handleEditNumber('keepalive_timeout', globalConfig.keepalive_timeout)">{{ t('edit') }}</a-button>
                </span>
              </div>
            </a-card>
            <a-card hoverable>
              <div :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }">
                <span :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }">
                  <a-typography-text>{{ t('multiAccept') }}</a-typography-text>
                </span>
                <a-switch :model-value="globalConfig.multi_accept" @change="(v) => handleBoolChange('multi_accept', v)" />
              </div>
            </a-card>
            <a-card hoverable>
              <div :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }">
                <span :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }">
                  <a-typography-text>{{ t('sendfile') }}</a-typography-text>
                </span>
                <a-switch :model-value="globalConfig.sendfile" @change="(v) => handleBoolChange('sendfile', v)" />
              </div>
            </a-card>
            <a-card hoverable>
              <div :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }">
                <span :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }">
                  <a-typography-text>{{ t('tcpNopush') }}</a-typography-text>
                </span>
                <a-switch :model-value="globalConfig.tcp_nopush" @change="(v) => handleBoolChange('tcp_nopush', v)" />
              </div>
            </a-card>
            <a-card hoverable>
              <div :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }">
                <span :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }">
                  <a-typography-text>{{ t('tcpNodelay') }}</a-typography-text>
                </span>
                <a-switch :model-value="globalConfig.tcp_nodelay" @change="(v) => handleBoolChange('tcp_nodelay', v)" />
              </div>
            </a-card>
          </div>

          <div class="section-title">{{ t('timeoutSetting') }}</div>
          <div class="card-grid">
            <a-card hoverable>
              <div :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }">
                <span :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }">
                  <a-typography-text>{{ t('clientBodyTimeout') }}</a-typography-text>
                </span>
                <span style="display: flex; align-items: center; gap: 8px;">
                  <a-typography-text>{{ globalConfig.client_body_timeout }}s</a-typography-text>
                  <a-button size="small" type="outline" @click="handleEditNumber('client_body_timeout', globalConfig.client_body_timeout)">{{ t('edit') }}</a-button>
                </span>
              </div>
            </a-card>
            <a-card hoverable>
              <div :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }">
                <span :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }">
                  <a-typography-text>{{ t('clientHeaderTimeout') }}</a-typography-text>
                </span>
                <span style="display: flex; align-items: center; gap: 8px;">
                  <a-typography-text>{{ globalConfig.client_header_timeout }}s</a-typography-text>
                  <a-button size="small" type="outline" @click="handleEditNumber('client_header_timeout', globalConfig.client_header_timeout)">{{ t('edit') }}</a-button>
                </span>
              </div>
            </a-card>
            <a-card hoverable>
              <div :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }">
                <span :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }">
                  <a-typography-text>{{ t('sendTimeout') }}</a-typography-text>
                </span>
                <span style="display: flex; align-items: center; gap: 8px;">
                  <a-typography-text>{{ globalConfig.send_timeout }}s</a-typography-text>
                  <a-button size="small" type="outline" @click="handleEditNumber('send_timeout', globalConfig.send_timeout)">{{ t('edit') }}</a-button>
                </span>
              </div>
            </a-card>
          </div>

          <div class="section-title">{{ t('uploadLimit') }}</div>
          <div class="card-grid">
            <a-card hoverable>
              <div :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }">
                <span :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }">
                  <a-typography-text>{{ t('clientMaxBodySize') }}</a-typography-text>
                </span>
                <span style="display: flex; align-items: center; gap: 8px;">
                  <a-typography-text>{{ globalConfig.client_max_body_size }}</a-typography-text>
                  <a-button size="small" type="outline" @click="handleEditSize('client_max_body_size', globalConfig.client_max_body_size)">{{ t('edit') }}</a-button>
                </span>
              </div>
            </a-card>
          </div>

          <div class="section-title">{{ t('gzipSetting') }}</div>
          <div class="card-grid">
            <a-card hoverable>
              <div :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }">
                <span :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }">
                  <a-typography-text>{{ t('gzipEnabled') }}</a-typography-text>
                </span>
                <a-switch :model-value="globalConfig.gzip_enabled" @change="(v) => handleBoolChange('gzip_enabled', v)" />
              </div>
            </a-card>
            <a-card hoverable>
              <div :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }">
                <span :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }">
                  <a-typography-text>{{ t('gzipCompLevel') }}</a-typography-text>
                </span>
                <span style="display: flex; align-items: center; gap: 8px;">
                  <a-typography-text>{{ globalConfig.gzip_comp_level }}</a-typography-text>
                  <a-button size="small" type="outline" @click="handleEditNumber('gzip_comp_level', globalConfig.gzip_comp_level)">{{ t('edit') }}</a-button>
                </span>
              </div>
            </a-card>
            <a-card hoverable>
              <div :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }">
                <span :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }">
                  <a-typography-text>{{ t('gzipMinLength') }}</a-typography-text>
                </span>
                <span style="display: flex; align-items: center; gap: 8px;">
                  <a-typography-text>{{ globalConfig.gzip_min_length }}</a-typography-text>
                  <a-button size="small" type="outline" @click="handleEditSize('gzip_min_length', globalConfig.gzip_min_length)">{{ t('edit') }}</a-button>
                </span>
              </div>
            </a-card>
            <a-card hoverable>
              <div :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }">
                <span :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }">
                  <a-typography-text>{{ t('gzipVary') }}</a-typography-text>
                </span>
                <a-switch :model-value="globalConfig.gzip_vary" @change="(v) => handleBoolChange('gzip_vary', v)" />
              </div>
            </a-card>
            <a-card hoverable>
              <div :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }">
                <span :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }">
                  <a-typography-text>{{ t('gzipDisable') }}</a-typography-text>
                </span>
                <span style="display: flex; align-items: center; gap: 8px; max-width: 280px;">
                  <a-typography-text style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ globalConfig.gzip_disable }}</a-typography-text>
                  <a-button size="small" type="outline" @click="handleEditString('gzip_disable', globalConfig.gzip_disable)">{{ t('edit') }}</a-button>
                </span>
              </div>
            </a-card>
          </div>

          <div class="section-title">{{ t('otherSetting') }}</div>
          <div class="card-grid">
            <a-card hoverable>
              <div :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }">
                <span :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }">
                  <a-typography-text>{{ t('proxyInterceptErrors') }}</a-typography-text>
                </span>
                <a-switch :model-value="globalConfig.proxy_intercept_errors" @change="(v) => handleBoolChange('proxy_intercept_errors', v)" />
              </div>
            </a-card>
            <a-card hoverable>
              <div :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }">
                <span :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }">
                  <a-typography-text>{{ t('luaCodeCache') }}</a-typography-text>
                </span>
                <a-switch :model-value="globalConfig.lua_code_cache" @change="(v) => handleBoolChange('lua_code_cache', v)" />
              </div>
            </a-card>
          </div>
        </div>
      </a-tab-pane>
      <a-tab-pane key="2" :title="t('bigScreenSetting')">
        <ScreenSetting />
      </a-tab-pane>
      <a-tab-pane key="3" :title="t('customHTML')">
        <HtmlPage />
      </a-tab-pane>
      <a-tab-pane key="4" title="AbuseIPDB API key">
        <IntelligenceConfig />
      </a-tab-pane>

    </a-tabs>

    <a-modal
      v-model:visible="editModalVisible"
      :title="editModalTitle"
      @ok="handleEditConfirm"
      @cancel="handleEditCancel"
    >
      <a-form :model="editForm" layout="vertical">
        <a-form-item v-if="editModalType === 'number'" label="Value">
          <a-input-number v-model="editForm.numberValue" :min="1" style="width: 100%" />
        </a-form-item>
        <a-form-item v-if="editModalType === 'size'" :label="t('sizeHint')">
          <a-input v-model="editForm.sizeValue" placeholder="e.g. 100m, 1k" />
        </a-form-item>
        <a-form-item v-if="editModalType === 'string'" label="Value">
          <a-input v-model="editForm.stringValue" placeholder="e.g. MSIE [1-6]\." />
        </a-form-item>
      </a-form>
    </a-modal>

  </a-card>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue';
import { t } from '../../utils/locale'
import HtmlPage from '../../components/waf/HtmlPage.vue'
import ScreenSetting from '../../components/waf/ScreenSetting.vue'
import IntelligenceConfig from '../../components/waf/IntelligenceConfig.vue'
import { getWAFContainerStatus, operateWAFContainer, getGlobalConfig, updateGlobalConfig } from '../../api/waf'
import { Message } from '@arco-design/web-vue';

const wafStatus = ref(false);
const actionLoading = reactive({
  stop: false,
  restart: false,
  start: false
});

const globalConfig = ref({});
const configLoading = ref(false);
const editModalVisible = ref(false);
const editModalTitle = ref('');
const editModalType = ref('');
const editModalKey = ref('');
const editForm = reactive({
  numberValue: null,
  sizeValue: '',
  stringValue: ''
});

const fetchWafStatus = async () => {
  try {
    const res = await getWAFContainerStatus();
    if (res) {
      wafStatus.value = res.status === 'running' || res.status === true;
    }
  } catch (error) {
    console.error('获取WAF状态失败:', error);
  }
};

const fetchGlobalConfig = async () => {
  configLoading.value = true;
  try {
    const res = await getGlobalConfig();
    if (res) {
      globalConfig.value = res;
    }
  } catch (error) {
    console.error('获取全局配置失败:', error);
    Message.error(t.value('fetchFailed'));
  } finally {
    configLoading.value = false;
  }
};

const handleAction = async (action) => {
  actionLoading[action] = true;
  try {
    await operateWAFContainer(action);
    Message.success(t.value('operationSuccess') || '操作成功');
    await fetchWafStatus();
  } catch (error) {
    Message.error(t.value('operationFailed') || '操作失败');
    console.error('WAF容器操作失败:', error);
  } finally {
    actionLoading[action] = false;
  }
};

const handleBoolChange = async (key, value) => {
  try {
    await updateGlobalConfig({ [key]: value });
    Message.success(t.value('updateSuccess'));
    await fetchGlobalConfig();
  } catch (error) {
    console.error('更新配置失败:', error);
    Message.error(t.value('updateFailed'));
  }
};

const handleEditNumber = (key, currentValue) => {
  editModalTitle.value = key;
  editModalType.value = 'number';
  editModalKey.value = key;
  editForm.numberValue = currentValue;
  editModalVisible.value = true;
};

const handleEditSize = (key, currentValue) => {
  editModalTitle.value = key;
  editModalType.value = 'size';
  editModalKey.value = key;
  editForm.sizeValue = currentValue;
  editModalVisible.value = true;
};

const handleEditString = (key, currentValue) => {
  editModalTitle.value = key;
  editModalType.value = 'string';
  editModalKey.value = key;
  editForm.stringValue = currentValue;
  editModalVisible.value = true;
};

const handleEditConfirm = async () => {
  try {
    let updateData = {};
    if (editModalType.value === 'number') {
      updateData = { [editModalKey.value]: Number(editForm.numberValue) };
    } else if (editModalType.value === 'size') {
      updateData = { [editModalKey.value]: editForm.sizeValue };
    } else if (editModalType.value === 'string') {
      updateData = { [editModalKey.value]: editForm.stringValue };
    }
    await updateGlobalConfig(updateData);
    Message.success(t.value('updateSuccess'));
    editModalVisible.value = false;
    await fetchGlobalConfig();
  } catch (error) {
    console.error('更新配置失败:', error);
    Message.error(t.value('updateFailed'));
  }
};

const handleEditCancel = () => {
  editModalVisible.value = false;
};

onMounted(() => {
  fetchWafStatus();
  fetchGlobalConfig();
});
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
  margin: 0;
  padding: 0;
}

.desc {
  margin-top: 4px;
  color: #8c8c8c;
  font-size: 12px;
}

.waf-status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: var(--color-fill-light);
  border-radius: 4px;
  margin-bottom: 16px;
}

.status-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-label {
  font-size: 14px;
  color: var(--color-text-1);
}

.status-actions {
  display: flex;
  gap: 8px;
}

.tab-content {
  padding: 15px;
}

.section-title {
  font-size: 1.1em;
  font-weight: 500;
  margin-bottom: 15px;
  margin-top: 20px;
  color: var(--color-text-1);
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border-2);
}

.section-title:first-child {
  margin-top: 0;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  margin-bottom: 10px;
}
</style>