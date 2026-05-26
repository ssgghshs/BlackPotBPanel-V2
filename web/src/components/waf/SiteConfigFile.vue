<template>
  <div class="config-file-container">
    <div class="config-actions">
      <a-button type="primary" @click="fetchConfigFileContent" :loading="configFileLoading">
        {{ t('refresh') }}
      </a-button>
      <a-button :loading="savingConfig" @click="saveConfig">
        {{ t('save') }}
      </a-button>
    </div>
    <a-alert type="warning">
      {{ t('warningConfigFile') }}
    </a-alert>
    <div ref="monacoEditorRef" class="monaco-editor-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue';
import { t } from '../../utils/locale';
import { getSiteConfig, updateSiteConfig } from '../../api/waf';
import { Message } from '@arco-design/web-vue';

const props = defineProps({
  siteName: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['refresh']);

// 配置文件相关状态
const configFileLoading = ref(false);
const savingConfig = ref(false);
const configFileContent = ref('');
const monacoEditorRef = ref(null);
let monacoEditor = null;

// 获取配置文件内容
const fetchConfigFileContent = async () => {
  if (!props.siteName) {
    Message.error(t.value('siteNameRequired'))
    return;
  }
  
  configFileLoading.value = true;
  try {
    const res = await getSiteConfig(props.siteName);
    if (res && res.content) {
      configFileContent.value = res.content;
      if (monacoEditor) {
        monacoEditor.setValue(res.content);
      }
    } else if (res && res.message && res.message.includes('not found')) {
      Message.error(res.message);
    }
  } catch (error) {
    Message.error(error.msg || `${t.value('fetch')} ${t.value('config')} ${t.value('failed')}`);
  } finally {
    configFileLoading.value = false;
  }
};

// 保存配置文件内容
const saveConfig = async () => {
  if (!monacoEditor) {
    Message.error(`${t.value('editor')} ${t.value('not')} ${t.value('initialized')}`);
    return;
  }
  
  if (!props.siteName) {
    Message.error(t.value('siteNameRequired'))
    return;
  }
  
  savingConfig.value = true;
  try {
    // 从编辑器获取内容
    const content = monacoEditor.getValue();
    
    // 调用updateSiteConfig方法保存配置
    await updateSiteConfig(props.siteName, { content });
    
    // 保存成功，显示成功消息
    Message.success(t.value('saveSuccess'));
    
    // 触发刷新事件
    emit('refresh');
  } catch (error) {
    // 显示错误信息
    Message.error(error.message || error.msg || t.value('saveFailed'));
  } finally {
    savingConfig.value = false;
  }
};

// 初始化Monaco编辑器
const initMonacoEditor = async () => {
  try {
    // 动态导入monaco-editor
    const monaco = await import('monaco-editor');
    
    // 初始化编辑器
    monacoEditor = monaco.editor.create(monacoEditorRef.value, {
      value: configFileContent.value,
      language: 'nginx',
      theme: 'vs-dark',
      automaticLayout: true,
      minimap: { enabled: false },
      fontSize: 14,
      lineNumbers: 'on',
      scrollBeyondLastLine: false,
      wordWrap: 'on',
      tabSize: 2
    });
  } catch (error) {
    console.error('Failed to initialize Monaco editor:', error);
    Message.error(`${t.value('editor')} ${t.value('initialize')} ${t.value('failed')}`);
  }
};

// 销毁Monaco编辑器
const destroyMonacoEditor = () => {
  if (monacoEditor) {
    monacoEditor.dispose();
    monacoEditor = null;
  }
};

// 监听siteName变化，重新获取配置文件内容
watch(() => props.siteName, (newVal) => {
  if (newVal) {
    fetchConfigFileContent();
  }
}, { immediate: false });

// 组件挂载时初始化编辑器
onMounted(() => {
  // 延迟初始化编辑器，确保DOM已渲染
  setTimeout(() => {
    initMonacoEditor();
    // 如果siteName存在，获取配置文件内容
    if (props.siteName) {
      fetchConfigFileContent();
    }
  }, 100);
});

// 组件卸载时销毁编辑器
onBeforeUnmount(() => {
  destroyMonacoEditor();
});
</script>

<style scoped>
.config-file-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.config-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.monaco-editor-container {
  flex: 1;
  min-height: 600px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  overflow: hidden;
}
</style>