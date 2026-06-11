<template>
  <a-drawer
    :visible="visible"
    :title="deployState === 'form' ? t('deployTitle') : t('deploy')"
    :width="640"
    @cancel="handleClose"
    :mask-closable="false"
    :footer="false"
  >
    <!-- 部署表单 -->
    <template v-if="deployState === 'form'">
      <a-form layout="vertical" :model="formData" :disabled="loading">
        <a-descriptions :title="t('appInfo')" :column="2" size="small" style="margin-bottom: 16px;">
          <a-descriptions-item :label="t('name')">
            {{ app?.title || app?.name || '-' }}
          </a-descriptions-item>
          <a-descriptions-item :label="t('version')">
            {{ selectedVersion }}
          </a-descriptions-item>
          <a-descriptions-item :label="t('storeName')">
            {{ storeName }}
          </a-descriptions-item>
          <a-descriptions-item :label="t('appIdentify')">
            {{ app?.name || '-' }}
          </a-descriptions-item>
        </a-descriptions>

        <a-form-item :label="t('taskName')" field="task_name" required>
          <a-input v-model="formData.task_name" :placeholder="t('enterTaskName')" />
        </a-form-item>

        <template v-if="envFormItems.length > 0">
          <a-divider />
          <div class="section-label">{{ t('environment') }}</div>
          <a-form-item
            v-for="(item, idx) in envFormItems"
            :key="item.name"
            :label="item.label || item.name"
            :field="`env_${idx}`"
          >
            <a-input v-model="item.value" :placeholder="item.defaultValue || item.name" />
          </a-form-item>
        </template>

        <a-divider />
        <div style="margin-bottom:12px;">
          <a-space>
            <span class="section-label">Compose YAML</span>
            <a-button size="mini" @click="showCompose = !showCompose">
              {{ showCompose ? t('collapse') : t('view') }}
            </a-button>
          </a-space>
        </div>
        <div v-show="showCompose">
          <pre v-if="composeContent" class="compose-preview">{{ composeContent }}</pre>
          <a-spin v-else-if="composeLoading" style="display:block;padding:20px;text-align:center;" />
          <span v-else style="font-size:13px;color:var(--color-text-3);">暂无内容</span>
        </div>
      </a-form>

      <!-- 底部按钮 -->
      <div class="drawer-footer">
        <a-button @click="handleClose" :disabled="loading">{{ t('cancel') }}</a-button>
        <a-button type="primary" :loading="loading" @click="handleDeploy">{{ t('deploy') }}</a-button>
      </div>
    </template>

    <!-- 部署状态 + 实时日志 -->
    <template v-else>
      <!-- 顶部状态栏 -->
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--color-border-2);">
        <a-spin v-if="deployState === 'deploying'" :size="24" />
        <icon-check-circle-fill v-else-if="deployState === 'success'" style="font-size:24px;color:rgb(var(--green-5));" />
        <icon-close-circle-fill v-else style="font-size:24px;color:rgb(var(--red-5));" />
        <span style="font-size:16px;font-weight:500;color:var(--color-text-1);">
          <template v-if="deployState === 'deploying'">{{ t('deployRunning') }}</template>
          <template v-else-if="deployState === 'success'">{{ t('deploySuccess') }}</template>
          <template v-else>{{ t('deployFailed') }}</template>
        </span>
        <span v-if="deployMessage" style="font-size:13px;color:var(--color-text-3);margin-left:8px;">{{ deployMessage }}</span>
      </div>

      <!-- 实时日志内容 -->
      <pre ref="deployLogRef" class="log-content" style="max-height:450px;">{{ deployLog || t('noLog') }}</pre>

      <!-- 底部按钮 -->
      <div class="drawer-footer">
        <a-button type="primary" @click="handleClose">{{ t('confirm') }}</a-button>
      </div>
    </template>
  </a-drawer>
</template>

<script setup>
import { ref, reactive, watch, nextTick } from 'vue';
import { t } from '../../utils/locale';
import { deployStoreApp, getStoreDeployStatus, getStoreDeployLog, getStoreAppVersionDetail } from '../../api/container';
import { IconCheckCircleFill, IconCloseCircleFill } from '@arco-design/web-vue/es/icon';

const props = defineProps({
  visible: Boolean,
  app: Object,
  storeName: String,
  selectedVersion: String,
  storeId: Number,
});

const emit = defineEmits(['update:visible', 'deploy-success']);

const loading = ref(false);
const deployState = ref('form'); // form | deploying | success | error
const deployId = ref(null);
const deployOperationId = ref('');
const deployMessage = ref('');
const deployLog = ref('');
const deployLogRef = ref(null);
let logPollTimer = null;
let pollTimer = null;

const scrollLogToBottom = async () => {
  await nextTick();
  if (deployLogRef.value) {
    deployLogRef.value.scrollTop = deployLogRef.value.scrollHeight;
  }
};

const formData = reactive({
  task_name: '',
  node_id: 0,
});

const envFormItems = ref([]);
const composeContent = ref('');
const composeLoading = ref(false);
const showCompose = ref(false);

const generateTaskName = () => {
  const appName = props.app?.name || 'app';
  const suffix = Math.random().toString(36).substring(2, 8);
  return `${appName.toLowerCase()}-${suffix}`;
};

const getVersionData = (versionName) => {
  const versions = props.app?.versions || {};
  let ver = versions[versionName];
  if (!ver) return null;
  if (ver.ref && versions[ver.ref]) {
    // 递归解析 ref
    const resolveRef = (v, seen = new Set()) => {
      if (!v || !v.ref || seen.has(v.ref)) return v;
      seen.add(v.ref);
      const parent = versions[v.ref];
      if (!parent) return v;
      const resolved = resolveRef(parent, seen);
      // 合并：当前数据覆盖父级
      return { ...resolved, ...v };
    };
    ver = resolveRef(ver);
  }
  return ver;
};

const initEnvForm = () => {
  const items = [];
  if (props.app?.versions && props.selectedVersion) {
    const ver = getVersionData(props.selectedVersion);
    if (ver?.environment && ver.environment.length > 0) {
      for (const env of ver.environment) {
        items.push({
          name: env.name || '',
          label: env.label || env.name || '',
          value: env.value || '',
          defaultValue: env.value || '',
          required: !!env.required,
          type: env.type || 'text',
        });
      }
    }
  }
  envFormItems.value = items;
};

const resetForm = () => {
  formData.task_name = generateTaskName();
  const savedHostId = localStorage.getItem('selectedContainerHostId');
  formData.node_id = savedHostId ? parseInt(savedHostId, 10) : 0;
  initEnvForm();
};

// 获取版本详情（compose YAML）
const fetchVersionDetail = async () => {
  if (!props.storeId || !props.app?.name || !props.selectedVersion) return;
  composeLoading.value = true;
  composeContent.value = '';
  showCompose.value = false;
  try {
    const res = await getStoreAppVersionDetail(props.storeId, props.app.name, props.selectedVersion);
    composeContent.value = res.compose_content || '';
    // 如果接口返回了环境变量，用它补充/覆盖表单
    if (res.environment && res.environment.length > 0) {
      for (const apiEnv of res.environment) {
        const exist = envFormItems.value.find(e => e.name === apiEnv.name);
        if (exist) {
          if (!exist.value && apiEnv.value) exist.value = apiEnv.value;
        } else {
          envFormItems.value.push({
            name: apiEnv.name || '',
            label: apiEnv.label || apiEnv.name || '',
            value: apiEnv.value || '',
            defaultValue: apiEnv.value || '',
            required: !!apiEnv.required,
            type: apiEnv.type || 'text',
          });
        }
      }
    }
  } catch {
    composeContent.value = '';
  } finally {
    composeLoading.value = false;
  }
};

// 停止轮询
const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  if (logPollTimer) {
    clearInterval(logPollTimer);
    logPollTimer = null;
  }
};

// 开始轮询日志
const startLogPolling = () => {
  if (logPollTimer) clearInterval(logPollTimer);
  logPollTimer = setInterval(async () => {
    if (!deployOperationId.value) return;
    try {
      const res = await getStoreDeployLog(deployOperationId.value);
      if (res.log_content) {
        deployLog.value = res.log_content;
        scrollLogToBottom();
      }
    } catch {
      // 静默失败
    }
  }, 3000);
};

// 开始轮询状态
const startPolling = (id) => {
  stopPolling();
  // 立即拉取一次日志
  fetchLog();
  // 启动日志实时刷新
  startLogPolling();
  pollTimer = setInterval(async () => {
    try {
      const res = await getStoreDeployStatus(id);
      if (res.status === 'running') {
        deployState.value = 'success';
        stopPolling();
        emit('deploy-success', formData.task_name);
      } else if (res.status === 'error') {
        deployState.value = 'error';
        deployMessage.value = res.message || '';
        stopPolling();
      }
      // status === 'deploying' — 继续轮询
    } catch {
      stopPolling();
    }
  }, 3000);
};

// 拉取日志
const fetchLog = async () => {
  if (!deployOperationId.value) return;
  try {
    const res = await getStoreDeployLog(deployOperationId.value);
    deployLog.value = res.log_content || '';
    scrollLogToBottom();
  } catch {
    deployLog.value = '';
  }
};

const handleDeploy = async () => {
  if (!formData.task_name) return;
  loading.value = true;
  try {
    const envList = envFormItems.value
      .filter((item) => item.value)
      .map((item) => ({ name: item.name, value: item.value }));

    const res = await deployStoreApp({
      store_id: props.storeId,
      app_name: props.app?.name || '',
      app_title: props.app?.title || props.app?.name || '',
      version_name: props.selectedVersion,
      task_name: formData.task_name,
      environment: envList,
      node_id: formData.node_id || 0,
    });

    deployId.value = res.id;
    deployOperationId.value = res.operation_id || `deploy_${res.id}`;
    deployState.value = 'deploying';
    deployMessage.value = '';
    loading.value = false;
    startPolling(res.id);
  } catch (e) {
    deployMessage.value = e?.message || String(e);
    loading.value = false;
  }
};

const handleClose = () => {
  stopPolling();
  deployState.value = 'form';
  deployId.value = null;
  deployOperationId.value = '';
  deployMessage.value = '';
  deployLog.value = '';
  showCompose.value = false;
  composeContent.value = '';
  emit('update:visible', false);
};

watch(() => props.selectedVersion, () => {
  if (props.selectedVersion) {
    initEnvForm();
    fetchVersionDetail();
  }
});

watch(() => props.visible, (val) => {
  if (val) {
    deployState.value = 'form';
    deployId.value = null;
    deployOperationId.value = '';
    deployMessage.value = '';
    resetForm();
    // 等待 props 全部就绪后获取版本详情
    nextTick(() => fetchVersionDetail());
  } else {
    stopPolling();
    showCompose.value = false;
    composeContent.value = '';
  }
});
</script>

<style scoped>
.section-label {
  font-weight: 500;
  margin-bottom: 8px;
  color: var(--color-text-1);
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border-2);
}

.log-content {
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

body[arco-theme="dark"] .log-content {
  background: #0d0d0d;
  color: #cccccc;
}

.compose-preview {
  background: #1e1e1e;
  color: #d4d4d4;
  font-size: 11px;
  line-height: 1.5;
  padding: 12px;
  border-radius: 4px;
  max-height: 350px;
  overflow: auto;
  white-space: pre;
  font-family: 'Consolas', 'Courier New', monospace;
}

body[arco-theme="dark"] .compose-preview {
  background: #0d0d0d;
  color: #cccccc;
}
</style>
