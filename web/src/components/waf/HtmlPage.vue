<template>
  <div class="html-page-container">
    <a-spin :loading="loading">
      <div class="card-grid">
        <a-card
          v-for="page in pages"
          :key="page.name"
          class="html-page-card"
          hoverable
        >
          <template #title>
            <div class="card-title">
              <icon-code />
              <span>{{ page.name }}</span>
            </div>
          </template>
          <template #extra>
            <div class="card-actions">
              <a-button type="text" size="small" @click="handlePreview(page)">
                <template #icon><icon-eye /></template>
                {{ t('preview') }}
              </a-button>
              <a-button type="text" size="small" @click="handleEdit(page)">
                <template #icon><icon-edit /></template>
                {{ t('edit') }}
              </a-button>
            </div>
          </template>
          <div class="card-content">
            <a-tag size="small" class="content-tag">HTML</a-tag>
            <pre class="content-preview">{{ truncateContent(page.content) }}</pre>
          </div>
        </a-card>
      </div>
    </a-spin>

    <a-modal
      v-model:visible="previewVisible"
      :title="t('preview') + ': ' + currentPage?.name"
      width="800px"
      :footer="false"
      render-to-body
    >
      <iframe
        v-if="currentPage"
        :srcdoc="previewContent"
        class="preview-iframe"
        sandbox="allow-same-origin"
      ></iframe>
    </a-modal>

    <a-drawer
      v-model:visible="editVisible"
      :title="t('edit') + ': ' + currentPage?.name"
      :width="700"
      :confirm-loading="saving"
      @ok="handleSave"
      @cancel="handleCancel"
      :ok-text="t('save')"
      :cancel-text="t('cancel')"
      placement="right"
    >
      <div ref="monacoEditorRef" class="html-editor-container"></div>
    </a-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue';
import { Message } from '@arco-design/web-vue';
import { IconCode, IconEye, IconEdit } from '@arco-design/web-vue/es/icon';
import { t } from '../../utils/locale';
import { getHtmlPageList, updateHtmlPageContent } from '../../api/waf';

const loading = ref(false);
const saving = ref(false);
const pages = ref([]);
const previewVisible = ref(false);
const editVisible = ref(false);
const currentPage = ref(null);
const editContent = ref('');

const monacoEditorRef = ref(null);
let monacoEditor = null;

const previewContent = computed(() => {
  if (!currentPage.value) return '';
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{background:#fff;margin:0;padding:16px;box-sizing:border-box;}pre{white-space:pre-wrap;word-break:break-all;margin:0;}</style></head><body>${currentPage.value.content}</body></html>`;
});

const truncateContent = (content) => {
  if (!content) return '';
  return content.length > 150 ? content.substring(0, 150) + '...' : content;
};

const initMonacoEditor = async () => {
  if (monacoEditor) return;
  try {
    const monaco = await import('monaco-editor');
    monacoEditor = monaco.editor.create(monacoEditorRef.value, {
      value: editContent.value,
      language: 'html',
      theme: 'vs-dark',
      automaticLayout: true,
      minimap: { enabled: false },
      fontSize: 14,
      lineNumbers: 'on',
      scrollBeyondLastLine: false,
      wordWrap: 'on',
      tabSize: 2,
      renderLineHighlight: 'line'
    });
  } catch (error) {
    console.error('Failed to initialize Monaco editor:', error);
    Message.error(t('editorInitFailed'));
  }
};

const destroyMonacoEditor = () => {
  if (monacoEditor) {
    monacoEditor.dispose();
    monacoEditor = null;
  }
};

const fetchPages = async () => {
  loading.value = true;
  try {
    const res = await getHtmlPageList();
    if (res && res.pages) {
      pages.value = res.pages;
    }
  } catch (error) {
    Message.error(t.value('fetchFailed'));
  } finally {
    loading.value = false;
  }
};

const handlePreview = (page) => {
  currentPage.value = page;
  previewVisible.value = true;
};

const handleEdit = (page) => {
  currentPage.value = page;
  editContent.value = page.content;
  editVisible.value = true;
  setTimeout(() => {
    initMonacoEditor();
    if (monacoEditor) {
      monacoEditor.setValue(page.content);
    }
  }, 100);
};

const handleSave = async () => {
  if (!currentPage.value) return;

  saving.value = true;
  try {
    const content = monacoEditor ? monacoEditor.getValue() : editContent.value;
    await updateHtmlPageContent(currentPage.value.name, {
      content: content
    });
    Message.success(t.value('saveSuccess'));
    currentPage.value.content = content;
    editVisible.value = false;
    destroyMonacoEditor();
  } catch (error) {
    Message.error(t.value('saveFailed'));
  } finally {
    saving.value = false;
  }
};

const handleCancel = () => {
  editContent.value = '';
  currentPage.value = null;
  destroyMonacoEditor();
};

onMounted(() => {
  fetchPages();
});

onBeforeUnmount(() => {
  destroyMonacoEditor();
});
</script>

<style scoped>
.html-page-container {
  padding: 16px;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

:deep(.arco-spin) {
  display: block;
  width: 100%;
}

:deep(.arco-spin-children) {
  display: block;
  width: 100%;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  width: 100%;
  box-sizing: border-box;
}

.html-page-card {
  min-width: 0;
  width: 100%;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 15px;
}

.card-actions {
  display: flex;
  gap: 8px;
}

.card-actions .arco-btn {
  padding: 4px 10px;
}

.card-content {
  min-height: 100px;
  max-height: 140px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.content-tag {
  width: fit-content;
  background: linear-gradient(135deg, #165dff 0%, #4080ff 100%);
  color: #fff;
  border: none;
  font-weight: 500;
}

.content-preview {
  font-size: 12px;
  color: var(--color-text-2);
  background: var(--color-fill-1);
  padding: 10px 12px;
  border-radius: 6px;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  overflow: hidden;
  line-height: 1.5;
  flex: 1;
  border-left: 3px solid #165dff;
}

.preview-iframe {
  width: 100%;
  height: 500px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #fff;
}

.html-editor-container {
  width: 100%;
  height: 100%;
  min-height: 500px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;
  background: #1e1e1e;
}

:deep(.arco-drawer-body) {
  padding: 16px;
  background: #f7f8fa;
  display: flex;
  flex-direction: column;
}
</style>
