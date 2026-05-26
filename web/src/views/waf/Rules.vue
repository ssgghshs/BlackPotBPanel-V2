<template>
  <a-card class="waf-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('protectionRules') }}</span>
      </div>
    </template>

    <a-tabs v-model:active-tab="activeTab" position="left">
      <a-tab-pane key="bot" title="BOT">
        <div class="tab-content">
          <div class="search-filters">
            <div class="flex-grow"></div>
            <a-button type="outline" size="small" @click="fetchRules" :loading="loading">
              {{ t('refresh') }}
            </a-button>
            <a-button type="outline" size="small" @click="handleEdit('bot')">
              {{ t('edit') }}
            </a-button>
          </div>
          <a-table :columns="botColumns" :data="botData" :loading="loading" :pagination="false" row-key="key">
            <template #value="{ record }">
              <div v-if="Array.isArray(record.value)" class="value-list">
                <a-tag v-for="(item, index) in record.value" :key="index" size="small" class="value-tag">
                  {{ item }}
                </a-tag>
              </div>
              <span v-else>{{ record.value }}</span>
            </template>
          </a-table>
        </div>
      </a-tab-pane>

      <a-tab-pane key="cc" :title="t('CCProtection')">
        <div class="tab-content">
          <div class="search-filters">
            <div class="flex-grow"></div>
            <a-button type="outline" size="small" @click="fetchRules" :loading="loading">
              {{ t('refresh') }}
            </a-button>
            <a-button type="outline" size="small" @click="handleEdit('cc')">
              {{ t('edit') }}
            </a-button>
          </div>
          <a-table :columns="ccColumns" :data="ccData" :loading="loading" :pagination="false" row-key="key">
            <template #value="{ record }">
              {{ record.value }}
            </template>
          </a-table>
        </div>
      </a-tab-pane>

      <a-tab-pane key="cmd" :title="t('cmdInjection')">
        <div class="tab-content">
          <div class="search-filters">
            <div class="flex-grow"></div>
            <a-button type="outline" size="small" @click="fetchRules" :loading="loading">
              {{ t('refresh') }}
            </a-button>
            <a-button type="outline" size="small" @click="handleEdit('cmd')">
              {{ t('edit') }}
            </a-button>
          </div>
          <a-table :columns="rulesColumns" :data="cmdData" :loading="loading" :pagination="false" row-key="key">
            <template #value="{ record }">
              <div v-if="Array.isArray(record.value)" class="value-list">
                <a-tag v-for="(item, index) in record.value" :key="index" size="small" class="value-tag">
                  {{ item }}
                </a-tag>
              </div>
              <span v-else>{{ record.value }}</span>
            </template>
          </a-table>
        </div>
      </a-tab-pane>

      <a-tab-pane key="csrf" title="CSRF">
        <div class="tab-content">
          <div class="search-filters">
            <div class="flex-grow"></div>
            <a-button type="outline" size="small" @click="fetchRules" :loading="loading">
              {{ t('refresh') }}
            </a-button>
            <a-button type="outline" size="small" @click="handleEdit('csrf')">
              {{ t('edit') }}
            </a-button>
          </div>
          <a-table :columns="csrfColumns" :data="csrfData" :loading="loading" :pagination="false" row-key="key">
            <template #value="{ record }">
              <div v-if="Array.isArray(record.value)" class="value-list">
                <a-tag v-for="(item, index) in record.value" :key="index" size="small" class="value-tag">
                  {{ item }}
                </a-tag>
              </div>
              <span v-else-if="typeof record.value === 'boolean'">
                <a-tag :color="record.value ? 'green' : 'red'" size="small">
                  {{ record.value ? 'ON' : 'OFF' }}
                </a-tag>
              </span>
              <span v-else>{{ record.value }}</span>
            </template>
          </a-table>
        </div>
      </a-tab-pane>

      <a-tab-pane key="file_inclusion" :title="t('fileInclusion')">
        <div class="tab-content">
          <div class="search-filters">
            <div class="flex-grow"></div>
            <a-button type="outline" size="small" @click="fetchRules" :loading="loading">
              {{ t('refresh') }}
            </a-button>
            <a-button type="outline" size="small" @click="handleEdit('file_inclusion')">
              {{ t('edit') }}
            </a-button>
          </div>
          <a-table :columns="fileInclusionColumns" :data="fileInclusionData" :loading="loading" :pagination="false" row-key="key">
            <template #value="{ record }">
              <div v-if="Array.isArray(record.value)" class="value-list">
                <a-tag v-for="(item, index) in record.value" :key="index" size="small" class="value-tag">
                  {{ item }}
                </a-tag>
              </div>
              <span v-else>{{ record.value }}</span>
            </template>
          </a-table>
        </div>
      </a-tab-pane>

      <a-tab-pane key="file_upload" :title="t('fileUpload')">
        <div class="tab-content">
          <div class="search-filters">
            <div class="flex-grow"></div>
            <a-button type="outline" size="small" @click="fetchRules" :loading="loading">
              {{ t('refresh') }}
            </a-button>
            <a-button type="outline" size="small" @click="handleEdit('file_upload')">
              {{ t('edit') }}
            </a-button>
          </div>
          <a-table :columns="fileUploadColumns" :data="fileUploadData" :loading="loading" :pagination="false" row-key="key">
            <template #value="{ record }">
              <div v-if="Array.isArray(record.value)" class="value-list">
                <a-tag v-for="(item, index) in record.value" :key="index" size="small" class="value-tag">
                  {{ item }}
                </a-tag>
              </div>
              <span v-else-if="typeof record.value === 'boolean'">
                <a-tag :color="record.value ? 'green' : 'red'" size="small">
                  {{ record.value ? 'ON' : 'OFF' }}
                </a-tag>
              </span>
              <span v-else>{{ record.value }}</span>
            </template>
          </a-table>
        </div>
      </a-tab-pane>

      <a-tab-pane key="ldap_injection" :title="t('ldapUpload')">
        <div class="tab-content">
          <div class="search-filters">
            <div class="flex-grow"></div>
            <a-button type="outline" size="small" @click="fetchRules" :loading="loading">
              {{ t('refresh') }}
            </a-button>
            <a-button type="outline" size="small" @click="handleEdit('ldap_injection')">
              {{ t('edit') }}
            </a-button>
          </div>
          <a-table :columns="rulesColumns" :data="ldapData" :loading="loading" :pagination="false" row-key="key">
            <template #value="{ record }">
              <div v-if="Array.isArray(record.value)" class="value-list">
                <a-tag v-for="(item, index) in record.value" :key="index" size="small" class="value-tag">
                  {{ item }}
                </a-tag>
              </div>
              <span v-else>{{ record.value }}</span>
            </template>
          </a-table>
        </div>
      </a-tab-pane>

      <a-tab-pane key="scanner" :title="t('scanner')">
        <div class="tab-content">
          <div class="search-filters">
            <div class="flex-grow"></div>
            <a-button type="outline" size="small" @click="fetchRules" :loading="loading">
              {{ t('refresh') }}
            </a-button>
            <a-button type="outline" size="small" @click="handleEdit('scanner')">
              {{ t('edit') }}
            </a-button>
          </div>
          <a-table :columns="scannerColumns" :data="scannerData" :loading="loading" :pagination="false" row-key="key">
            <template #value="{ record }">
              <div v-if="Array.isArray(record.value)" class="value-list">
                <a-tag v-for="(item, index) in record.value" :key="index" size="small" class="value-tag">
                  {{ item }}
                </a-tag>
              </div>
              <span v-else>{{ record.value }}</span>
            </template>
          </a-table>
        </div>
      </a-tab-pane>

      <a-tab-pane key="sql" :title="t('sqlInjection')">
        <div class="tab-content">
          <div class="search-filters">
            <div class="flex-grow"></div>
            <a-button type="outline" size="small" @click="fetchRules" :loading="loading">
              {{ t('refresh') }}
            </a-button>
            <a-button type="outline" size="small" @click="handleEdit('sql')">
              {{ t('edit') }}
            </a-button>
          </div>
          <a-table :columns="rulesColumns" :data="sqlData" :loading="loading" :pagination="false" row-key="key">
            <template #value="{ record }">
              <div v-if="Array.isArray(record.value)" class="value-list">
                <a-tag v-for="(item, index) in record.value" :key="index" size="small" class="value-tag">
                  {{ item }}
                </a-tag>
              </div>
              <span v-else>{{ record.value }}</span>
            </template>
          </a-table>
        </div>
      </a-tab-pane>

      <a-tab-pane key="ssrf" title="SSRF">
        <div class="tab-content">
          <div class="search-filters">
            <div class="flex-grow"></div>
            <a-button type="outline" size="small" @click="fetchRules" :loading="loading">
              {{ t('refresh') }}
            </a-button>
            <a-button type="outline" size="small" @click="handleEdit('ssrf')">
              {{ t('edit') }}
            </a-button>
          </div>
          <a-table :columns="rulesColumns" :data="ssrfData" :loading="loading" :pagination="false" row-key="key">
            <template #value="{ record }">
              <div v-if="Array.isArray(record.value)" class="value-list">
                <a-tag v-for="(item, index) in record.value" :key="index" size="small" class="value-tag">
                  {{ item }}
                </a-tag>
              </div>
              <span v-else>{{ record.value }}</span>
            </template>
          </a-table>
        </div>
      </a-tab-pane>

      <a-tab-pane key="xss" title="XSS">
        <div class="tab-content">
          <div class="search-filters">
            <div class="flex-grow"></div>
            <a-button type="outline" size="small" @click="fetchRules" :loading="loading">
              {{ t('refresh') }}
            </a-button>
            <a-button type="outline" size="small" @click="handleEdit('xss')">
              {{ t('edit') }}
            </a-button>
          </div>
          <a-table :columns="rulesColumns" :data="xssData" :loading="loading" :pagination="false" row-key="key">
            <template #value="{ record }">
              <div v-if="Array.isArray(record.value)" class="value-list">
                <a-tag v-for="(item, index) in record.value" :key="index" size="small" class="value-tag">
                  {{ item }}
                </a-tag>
              </div>
              <span v-else>{{ record.value }}</span>
            </template>
          </a-table>
        </div>
      </a-tab-pane>
    </a-tabs>

    <a-drawer v-model:visible="editModalVisible" :title="editTitle" width="600px" @close="handleEditCancel" :footer="false">
      <div class="drawer-content">
        <a-form :model="editForm" layout="vertical">
          <template v-if="activeTab === 'bot'">
            <a-form-item label="Whitelist">
              <a-textarea v-model="editForm.whitelist" placeholder="One entry per line" :rows="15" />
            </a-form-item>
          </template>

          <template v-else-if="activeTab === 'cc'">
            <a-form-item label="Max Requests">
              <a-input-number v-model="editForm.max_requests" :min="1" style="width: 100%" />
            </a-form-item>
            <a-form-item label="Time Window (seconds)">
              <a-input-number v-model="editForm.time_window" :min="1" style="width: 100%" />
            </a-form-item>
            <a-form-item label="Block Duration (seconds)">
              <a-input-number v-model="editForm.block_duration" :min="1" style="width: 100%" />
            </a-form-item>
          </template>

          <template v-else-if="activeTab === 'cmd'">
            <a-form-item label="Rules">
              <a-textarea v-model="editForm.rules" placeholder="One rule per line" :rows="15" />
            </a-form-item>
          </template>

          <template v-else-if="activeTab === 'csrf'">
            <a-form-item label="Check Origin">
              <a-switch v-model="editForm.check_origin" />
            </a-form-item>
            <a-form-item label="Check Referer">
              <a-switch v-model="editForm.check_referer" />
            </a-form-item>
            <a-form-item label="Allowed Origins">
              <a-textarea v-model="editForm.allowed_origins" placeholder="One per line" :rows="6" />
            </a-form-item>
            <a-form-item label="Allowed Referers">
              <a-textarea v-model="editForm.allowed_referers" placeholder="One per line" :rows="6" />
            </a-form-item>
            <a-form-item label="Protected Methods">
              <a-textarea v-model="editForm.protected_methods" placeholder="One per line" :rows="6" />
            </a-form-item>
            <a-form-item label="Exclude Paths">
              <a-textarea v-model="editForm.exclude_paths" placeholder="One per line" :rows="6" />
            </a-form-item>
          </template>

          <template v-else-if="activeTab === 'file_inclusion'">
            <a-form-item label="Rules">
              <a-textarea v-model="editForm.rules" placeholder="One rule per line" :rows="15" />
            </a-form-item>
            <a-form-item label="Exclude Paths">
              <a-textarea v-model="editForm.exclude_paths" placeholder="One per line" :rows="6" />
            </a-form-item>
          </template>

          <template v-else-if="activeTab === 'file_upload'">
            <a-form-item label="Max File Size (bytes)">
              <a-input-number v-model="editForm.max_file_size" :min="1" style="width: 100%" />
            </a-form-item>
            <a-form-item label="Check Content">
              <a-switch v-model="editForm.check_content" />
            </a-form-item>
            <a-form-item label="Allowed Extensions">
              <a-textarea v-model="editForm.allowed_extensions" placeholder="One per line" :rows="6" />
            </a-form-item>
            <a-form-item label="Forbidden Extensions">
              <a-textarea v-model="editForm.forbidden_extensions" placeholder="One per line" :rows="6" />
            </a-form-item>
            <a-form-item label="Allowed Types">
              <a-textarea v-model="editForm.allowed_types" placeholder="One per line" :rows="6" />
            </a-form-item>
            <a-form-item label="Forbidden Types">
              <a-textarea v-model="editForm.forbidden_types" placeholder="One per line" :rows="6" />
            </a-form-item>
            <a-form-item label="Forbidden Content">
              <a-textarea v-model="editForm.forbidden_content" placeholder="One per line" :rows="6" />
            </a-form-item>
            <a-form-item label="Exclude Paths">
              <a-textarea v-model="editForm.exclude_paths" placeholder="One per line" :rows="6" />
            </a-form-item>
          </template>

          <template v-else-if="activeTab === 'ldap_injection'">
            <a-form-item label="Rules">
              <a-textarea v-model="editForm.rules" placeholder="One rule per line" :rows="15" />
            </a-form-item>
          </template>

          <template v-else-if="activeTab === 'scanner'">
            <a-form-item label="Scanner User Agents">
              <a-textarea v-model="editForm.scanner_user_agents" placeholder="One per line" :rows="10" />
            </a-form-item>
            <a-form-item label="Scanner Headers">
              <a-textarea v-model="editForm.scanner_headers" placeholder="One per line" :rows="6" />
            </a-form-item>
            <a-form-item label="Scanner Paths">
              <a-textarea v-model="editForm.scanner_paths" placeholder="One per line" :rows="6" />
            </a-form-item>
            <a-form-item label="Exclude Paths">
              <a-textarea v-model="editForm.exclude_paths" placeholder="One per line" :rows="6" />
            </a-form-item>
            <a-form-item label="Allowed Crawlers">
              <a-textarea v-model="editForm.allowed_crawlers" placeholder="One per line" :rows="6" />
            </a-form-item>
          </template>

          <template v-else-if="activeTab === 'sql'">
            <a-form-item label="Rules">
              <a-textarea v-model="editForm.rules" placeholder="One rule per line" :rows="15" />
            </a-form-item>
          </template>

          <template v-else-if="activeTab === 'ssrf'">
            <a-form-item label="Rules">
              <a-textarea v-model="editForm.rules" placeholder="One rule per line" :rows="15" />
            </a-form-item>
          </template>

          <template v-else-if="activeTab === 'xss'">
            <a-form-item label="Rules">
              <a-textarea v-model="editForm.rules" placeholder="One rule per line" :rows="15" />
            </a-form-item>
          </template>

          <div class="drawer-footer">
            <a-button @click="handleEditCancel">{{ t('cancel') }}</a-button>
            <a-button type="primary" @click="handleEditSubmit" :loading="submitLoading">{{ t('confirm') }}</a-button>
          </div>
        </a-form>
      </div>
    </a-drawer>
  </a-card>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue';
import { t } from '../../utils/locale';
import { getProtectionRules, updateProtectionRule } from '../../api/waf';
import { Message } from '@arco-design/web-vue';

const loading = ref(false);
const submitLoading = ref(false);
const activeTab = ref('bot');
const editModalVisible = ref(false);
const rulesData = ref({});

const editForm = reactive({});

const editTitle = computed(() => {
  const titleMap = {
    'bot': 'BOT',
    'cc': t.value('CCProtection'),
    'cmd': t.value('cmdInjection'),
    'csrf': 'CSRF',
    'file_inclusion': t.value('fileInjection'),
    'file_upload': t.value('fileUpload'),
    'ldap_injection': t.value('ldapUpload'),
    'scanner': t.value('scanner'),
    'sql': t.value('sqlInjection'),
    'ssrf': 'SSRF',
    'xss': 'XSS'
  };
  return t.value('edit') + ' - ' + (titleMap[activeTab.value] || activeTab.value);
});

const rulesColumns = [
  { title: 'Key', dataIndex: 'key', width: 200 },
  { title: 'Value', dataIndex: 'value', slotName: 'value' }
];

const botColumns = [
  { title: 'Key', dataIndex: 'key', width: 200 },
  { title: 'Value', dataIndex: 'value', slotName: 'value' }
];

const ccColumns = [
  { title: 'Key', dataIndex: 'key', width: 200 },
  { title: 'Value', dataIndex: 'value', width: 200 }
];

const csrfColumns = [
  { title: 'Key', dataIndex: 'key', width: 200 },
  { title: 'Value', dataIndex: 'value', slotName: 'value' }
];

const fileInclusionColumns = [
  { title: 'Key', dataIndex: 'key', width: 200 },
  { title: 'Value', dataIndex: 'value', slotName: 'value' }
];

const fileUploadColumns = [
  { title: 'Key', dataIndex: 'key', width: 200 },
  { title: 'Value', dataIndex: 'value', slotName: 'value' }
];

const scannerColumns = [
  { title: 'Key', dataIndex: 'key', width: 200 },
  { title: 'Value', dataIndex: 'value', slotName: 'value' }
];

const configToArray = (config) => {
  if (Array.isArray(config)) return config;
  if (typeof config === 'string') return config.split('\n').filter(item => item.trim());
  return [];
};

const configToTableData = (config) => {
  if (!config) return [];
  return Object.entries(config).map(([key, value]) => ({ key, value }));
};

const botData = computed(() => configToTableData(rulesData.value.bot?.config));
const ccData = computed(() => configToTableData(rulesData.value.cc?.config));
const cmdData = computed(() => configToTableData(rulesData.value.cmd?.config));
const csrfData = computed(() => configToTableData(rulesData.value.csrf?.config));
const fileInclusionData = computed(() => configToTableData(rulesData.value.file_inclusion?.config));
const fileUploadData = computed(() => configToTableData(rulesData.value.file_upload?.config));
const ldapData = computed(() => configToTableData(rulesData.value.ldap_injection?.config));
const scannerData = computed(() => configToTableData(rulesData.value.scanner?.config));
const sqlData = computed(() => configToTableData(rulesData.value.sql?.config));
const ssrfData = computed(() => configToTableData(rulesData.value.ssrf?.config));
const xssData = computed(() => configToTableData(rulesData.value.xss?.config));

const fetchRules = async () => {
  loading.value = true;
  try {
    const response = await getProtectionRules();
    if (response && response.rules) {
      rulesData.value = {};
      for (const rule of response.rules) {
        rulesData.value[rule.rule_key] = rule;
      }
    }
  } catch (error) {
    console.error('Failed to fetch rules:', error);
    Message.error(t.value('fetchFailed') || 'Failed to fetch rules');
  } finally {
    loading.value = false;
  }
};

const initEditForm = (ruleKey) => {
  const config = rulesData.value[ruleKey]?.config || {};

  if (ruleKey === 'bot') {
    editForm.whitelist = (config.whitelist || []).join('\n');
  } else if (ruleKey === 'cc') {
    editForm.max_requests = config.max_requests;
    editForm.time_window = config.time_window;
    editForm.block_duration = config.block_duration;
  } else if (ruleKey === 'cmd') {
    editForm.rules = (config.rules || []).join('\n');
  } else if (ruleKey === 'csrf') {
    editForm.check_origin = config.check_origin;
    editForm.check_referer = config.check_referer;
    editForm.allowed_origins = (config.allowed_origins || []).join('\n');
    editForm.allowed_referers = (config.allowed_referers || []).join('\n');
    editForm.protected_methods = (config.protected_methods || []).join('\n');
    editForm.exclude_paths = (config.exclude_paths || []).join('\n');
  } else if (ruleKey === 'file_inclusion') {
    editForm.rules = (config.rules || []).join('\n');
    editForm.exclude_paths = (config.exclude_paths || []).join('\n');
  } else if (ruleKey === 'file_upload') {
    editForm.max_file_size = config.max_file_size;
    editForm.check_content = config.check_content;
    editForm.allowed_extensions = (config.allowed_extensions || []).join('\n');
    editForm.forbidden_extensions = (config.forbidden_extensions || []).join('\n');
    editForm.allowed_types = (config.allowed_types || []).join('\n');
    editForm.forbidden_types = (config.forbidden_types || []).join('\n');
    editForm.forbidden_content = (config.forbidden_content || []).join('\n');
    editForm.exclude_paths = (config.exclude_paths || []).join('\n');
  } else if (ruleKey === 'ldap_injection') {
    editForm.rules = (config.rules || []).join('\n');
  } else if (ruleKey === 'scanner') {
    editForm.scanner_user_agents = (config.scanner_user_agents || []).join('\n');
    editForm.scanner_headers = (config.scanner_headers || []).join('\n');
    editForm.scanner_paths = (config.scanner_paths || []).join('\n');
    editForm.exclude_paths = (config.exclude_paths || []).join('\n');
    editForm.allowed_crawlers = (config.allowed_crawlers || []).join('\n');
  } else if (ruleKey === 'sql') {
    editForm.rules = (config.rules || []).join('\n');
  } else if (ruleKey === 'ssrf') {
    editForm.rules = (config.rules || []).join('\n');
  } else if (ruleKey === 'xss') {
    editForm.rules = (config.rules || []).join('\n');
  }
};

const handleEdit = (ruleKey) => {
  activeTab.value = ruleKey;
  initEditForm(ruleKey);
  editModalVisible.value = true;
};

const handleEditSubmit = async () => {
  submitLoading.value = true;
  try {
    let config = {};

    if (activeTab.value === 'bot') {
      config = { whitelist: configToArray(editForm.whitelist) };
    } else if (activeTab.value === 'cc') {
      config = {
        max_requests: editForm.max_requests,
        time_window: editForm.time_window,
        block_duration: editForm.block_duration
      };
    } else if (['cmd', 'ldap_injection', 'sql', 'ssrf', 'xss'].includes(activeTab.value)) {
      config = { rules: configToArray(editForm.rules) };
    } else if (activeTab.value === 'csrf') {
      config = {
        check_origin: editForm.check_origin,
        check_referer: editForm.check_referer,
        allowed_origins: configToArray(editForm.allowed_origins),
        allowed_referers: configToArray(editForm.allowed_referers),
        protected_methods: configToArray(editForm.protected_methods),
        exclude_paths: configToArray(editForm.exclude_paths)
      };
    } else if (activeTab.value === 'file_inclusion') {
      config = {
        rules: configToArray(editForm.rules),
        exclude_paths: configToArray(editForm.exclude_paths)
      };
    } else if (activeTab.value === 'file_upload') {
      config = {
        max_file_size: editForm.max_file_size,
        check_content: editForm.check_content,
        allowed_extensions: configToArray(editForm.allowed_extensions),
        forbidden_extensions: configToArray(editForm.forbidden_extensions),
        allowed_types: configToArray(editForm.allowed_types),
        forbidden_types: configToArray(editForm.forbidden_types),
        forbidden_content: configToArray(editForm.forbidden_content),
        exclude_paths: configToArray(editForm.exclude_paths)
      };
    } else if (activeTab.value === 'scanner') {
      config = {
        scanner_user_agents: configToArray(editForm.scanner_user_agents),
        scanner_headers: configToArray(editForm.scanner_headers),
        scanner_paths: configToArray(editForm.scanner_paths),
        exclude_paths: configToArray(editForm.exclude_paths),
        allowed_crawlers: configToArray(editForm.allowed_crawlers)
      };
    }

    await updateProtectionRule(activeTab.value, { config });
    Message.success(t.value('updateSuccess') || 'Update successful');
    editModalVisible.value = false;
    await fetchRules();
  } catch (error) {
    console.error('Failed to update rules:', error);
    Message.error(t.value('updateFailed') || 'Update failed');
  } finally {
    submitLoading.value = false;
  }
};

const handleEditCancel = () => {
  editModalVisible.value = false;
  Object.keys(editForm).forEach(key => delete editForm[key]);
};

onMounted(() => {
  fetchRules();
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

.tab-content {
  padding: 15px;
}

.search-filters {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 15px;
}

.flex-grow {
  flex-grow: 1;
}

.value-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-height: 150px;
  overflow-y: auto;
}

.value-tag {
  margin-bottom: 4px;
}

.drawer-content {
  padding: 20px;
}

.drawer-footer {
  margin-top: 30px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>