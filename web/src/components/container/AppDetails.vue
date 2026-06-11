<template>
  <a-drawer
    :visible="visible"
    :title="app?.title || app?.name || ''"
    :width="1000"
    @cancel="handleClose"
    :footer="false"
    :closable="true"
  >
    <template v-if="app">
      <!-- 基础信息 -->
      <div class="app-detail-header">
        <div class="app-detail-image">
          <img v-if="app.logo" :src="app.logo" alt="" class="detail-logo" />
          <div v-else class="detail-logo-placeholder">{{ (app.title || app.name)[0] }}</div>
        </div>
        <div class="app-detail-info">
          <div class="detail-title">{{ app.title || app.name }}</div>
          <div class="detail-desc">{{ getAppDescription(app) }}</div>
          <div class="detail-tags">
            <a-tag v-for="(tag, tagIdx) in (app.tags || [])" :key="tagIdx" color="gray" size="small">{{ tag }}</a-tag>
            <a-tag color="arcoblue" size="small">{{ versionKeys.length }}版本</a-tag>
          </div>
        </div>
      </div>

      <!-- 版本选择 -->
      <div class="detail-section">
        <div class="section-label">{{ t('version') }}</div>
        <div class="version-row">
          <a-select v-model="selectedVersion" style="width: 240px;">
            <a-option v-for="ver in versionKeys" :key="ver" :value="ver">{{ ver }}</a-option>
          </a-select>
          <a-button type="primary" @click="handleDeploy" :disabled="!selectedVersion">
            {{ t('deploy') }}
          </a-button>
        </div>
      </div>

      <!-- 环境变量 -->
      <div class="detail-section" v-if="envItems.length > 0">
        <div class="section-label">{{ t('environment') }}</div>
        <a-table
          :columns="envColumns"
          :data="envItems"
          :pagination="false"
          :bordered="false"
          size="small"
          row-key="name"
        />
      </div>

      <!-- 详细介绍 (contents) -->
      <div class="detail-section" v-if="detailContent">
        <div class="section-label">{{ t('detailContent') }}</div>
        <div class="detail-content-box" v-html="detailContent"></div>
      </div>
    </template>

    <!-- 部署对话框 -->
    <StoreDeployDialog
      v-model:visible="deployDialogVisible"
      :app="app"
      :store-name="storeName"
      :selected-version="selectedVersion"
      :store-id="storeId"
      @deploy-success="onDeploySuccess"
    />
  </a-drawer>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue';
import { t, currentLocale } from '../../utils/locale';
import { resolveStoreReadme, renderStoreReadmeHtml } from '../../utils/container/markdownfile';
import request from '../../utils/request';
import StoreDeployDialog from './StoreDeployDialog.vue';
import 'highlight.js/styles/github.css';

const props = defineProps({
  visible: Boolean,
  app: Object,
  storeName: String,
  storeId: Number,
});

const emit = defineEmits(['update:visible']);

const selectedVersion = ref('');
const detailContent = ref('');
const deployDialogVisible = ref(false);

// AbortController 用于取消 pending 请求，防止组件销毁后报错
let contentAbortController = null;

onUnmounted(() => {
  if (contentAbortController) {
    contentAbortController.abort();
    contentAbortController = null;
  }
});

// 版本列表
const versionKeys = computed(() => {
  if (!props.app?.versions) return [];
  return Object.keys(props.app.versions);
});

// 当前选中版本的环境变量
const envItems = computed(() => {
  if (!selectedVersion.value || !props.app?.versions) return [];
  const ver = props.app.versions[selectedVersion.value];
  if (!ver || !ver.environment || ver.environment.length === 0) return [];
  return ver.environment.map(env => ({
    name: env.name || '',
    label: env.label || env.name || '',
    value: env.value || '',
    required: env.required ? '是' : '否',
    type: env.type || 'text',
  }));
});

const envColumns = [
  { title: t.value('name'), dataIndex: 'name', width: 180 },
  { title: t.value('label'), dataIndex: 'label', width: 180 },
  { title: t.value('defaultValue'), dataIndex: 'value', width: 200 },
  { title: t.value('required'), dataIndex: 'required', width: 80 },
  { title: t.value('type'), dataIndex: 'type', width: 100 },
];

// 根据面板语言获取描述
const getAppDescription = (app) => {
  if (!app?.descriptions) return app?.description || '';
  const isZh = currentLocale.value === 'zh-CN';
  if (isZh) return app.descriptions.zh || app.descriptions.zh_cn || app.description || '';
  return app.descriptions.en || app.descriptions.en_us || app.description || '';
};

// 加载详细介绍内容
const loadDetailContent = async () => {
  const app = props.app;
  if (!app?.contents) return;
  
  // 取消上一次 pending 请求
  if (contentAbortController) {
    contentAbortController.abort();
    contentAbortController = null;
  }
  contentAbortController = new AbortController();
  const signal = contentAbortController.signal;

  const isZh = currentLocale.value === 'zh-CN';
  const raw = isZh ? (app.contents.zh || app.contents.en || '') : (app.contents.en || app.contents.zh || '');
  if (!raw) return;

  const resolved = resolveStoreReadme(raw, props.storeName || '');
  if (!resolved) return;

  let text = '';
  // 如果是 markdown-file:// 转成的 URL，需要 fetch
  if (resolved.startsWith(request.defaults.baseURL)) {
    try {
      // 去掉 baseURL 前缀，避免 axios 重复拼接
      const relativePath = resolved.replace(request.defaults.baseURL, '');
      const resp = await request.get(relativePath, { signal });
      text = typeof resp === 'string' ? resp : (resp.data || '');
    } catch (err) {
      if (err?.name === 'CanceledError' || err?.code === 'ERR_CANCELED') return;
      text = t.value('loadContentFailed');
    }
  } else {
    // 内联 markdown 文本
    text = resolved;
  }

  // 渲染为 HTML
  detailContent.value = renderStoreReadmeHtml(text);
};

// 默认选中第一个版本
watch(() => props.app, (app) => {
  if (app?.versions) {
    const keys = Object.keys(app.versions);
    selectedVersion.value = keys.length > 0 ? keys[0] : '';
  }
  detailContent.value = '';
  loadDetailContent();
}, { immediate: true });

// 语言切换时重新加载
watch(currentLocale, () => {
  loadDetailContent();
});

const handleClose = () => {
  emit('update:visible', false);
};

// 部署
const handleDeploy = () => {
  deployDialogVisible.value = true;
};

// 部署成功
const onDeploySuccess = (taskName) => {
  handleClose();
};
</script>

<style scoped>
.app-detail-header {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border);
}

.app-detail-image {
  flex-shrink: 0;
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.detail-logo {
  width: 64px;
  height: 64px;
  object-fit: contain;
  border-radius: 4px;
}

.detail-logo-placeholder {
  width: 64px;
  height: 64px;
  border-radius: 4px;
  background: var(--color-fill-3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 600;
  color: var(--color-text-3);
}

.app-detail-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-1);
}

.detail-desc {
  font-size: 14px;
  color: var(--color-text-3);
  line-height: 1.5;
}

.detail-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.detail-section {
  margin-bottom: 20px;
}

.version-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-1);
  margin-bottom: 8px;
}

.detail-desc-text {
  font-size: 14px;
  color: var(--color-text-2);
  line-height: 1.6;
}

.detail-content-box {
  background: var(--color-fill-2);
  border-radius: 4px;
  padding: 16px;
  max-height: 500px;
  overflow-y: auto;
  font-size: 14px;
  line-height: 1.7;
  color: var(--color-text-2);
}

.detail-content-box :deep(h1),
.detail-content-box :deep(h2),
.detail-content-box :deep(h3),
.detail-content-box :deep(h4) {
  margin: 16px 0 8px;
  color: var(--color-text-1);
}

.detail-content-box :deep(h1) { font-size: 20px; }
.detail-content-box :deep(h2) { font-size: 18px; }
.detail-content-box :deep(h3) { font-size: 16px; }

.detail-content-box :deep(p) {
  margin: 8px 0;
}

.detail-content-box :deep(ul),
.detail-content-box :deep(ol) {
  padding-left: 24px;
  margin: 8px 0;
}

.detail-content-box :deep(li) {
  margin: 4px 0;
}

.detail-content-box :deep(code) {
  background: var(--color-fill-3);
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 13px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}

.detail-content-box :deep(pre) {
  background: var(--color-fill-4);
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  margin: 8px 0;
}

.detail-content-box :deep(pre code) {
  background: none;
  padding: 0;
}

.detail-content-box :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 8px 0;
  font-size: 13px;
}

.detail-content-box :deep(th),
.detail-content-box :deep(td) {
  border: 1px solid var(--color-border);
  padding: 6px 10px;
  text-align: left;
}

.detail-content-box :deep(th) {
  background: var(--color-fill-3);
  font-weight: 600;
}

.detail-content-box :deep(blockquote) {
  border-left: 3px solid rgb(var(--arcoblue-5));
  padding: 4px 12px;
  margin: 8px 0;
  background: var(--color-fill-3);
  border-radius: 0 4px 4px 0;
}

.detail-content-box :deep(hr) {
  border: none;
  border-top: 1px solid var(--color-border);
  margin: 16px 0;
}

.detail-content-box :deep(a) {
  color: rgb(var(--arcoblue-5));
  text-decoration: none;
}

.detail-content-box :deep(a:hover) {
  text-decoration: underline;
}

.detail-content-box :deep(img) {
  max-width: 100%;
  border-radius: 4px;
  margin: 8px 0;
}

.detail-content-box :deep(del) {
  opacity: 0.6;
}

.detail-content-box :deep(strong) {
  font-weight: 600;
  color: var(--color-text-1);
}
</style>
