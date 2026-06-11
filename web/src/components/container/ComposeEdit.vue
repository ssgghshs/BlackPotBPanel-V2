<template>
  <a-drawer
    :title="t('editComposeProject')"
    placement="right"
    :width="isMobile ? '100%' : 800"
    :visible="visible"
    :footer="false"
    @update:visible="handleVisibleChange"
  >
    <a-form
      :model="formData"
      ref="formRef"
      layout="vertical"
      :disabled="loading"
    >
      <a-form-item :label="t('projectName')">
        <a-input
          :model-value="projectName"
          disabled
        />
      </a-form-item>

      <a-form-item :label="t('composeFileContent')" field="compose_content">
        <div
          ref="composeEditorRef"
          class="monaco-editor-container"
        ></div>
      </a-form-item>

      <a-form-item :label="t('envFileContent')" field="env_content">
        <div
          ref="envEditorRef"
          class="monaco-editor-container env-editor"
        ></div>
        <div class="form-hint">{{ t('envContentHint') }}</div>
      </a-form-item>

      <a-form-item>
        <a-checkbox v-model="formData.restart_on_edit">
          {{ t('restartOnEdit') }}
        </a-checkbox>
      </a-form-item>
    </a-form>

    <div class="drawer-footer">
      <a-button @click="handleCancel">
        {{ t('cancel') }}
      </a-button>
      <a-button
        type="primary"
        @click="handleSubmit"
        :loading="loading"
      >
        {{ t('save') }}
      </a-button>
    </div>

  </a-drawer>
</template>

<script setup>
import { ref, reactive, nextTick, watch, onMounted, onBeforeUnmount } from 'vue';
import { Message } from '@arco-design/web-vue';
import { t } from '../../utils/locale';
import { updateComposeProjectFile } from '../../api/container';
import * as monaco from 'monaco-editor';

// 响应式布局相关
const isMobile = ref(false);

const checkIsMobile = () => {
  isMobile.value = window.innerWidth < 768;
};

// Props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  nodeId: {
    type: [String, Number, null],
    default: null
  },
  projectName: {
    type: String,
    default: ''
  },
  composeContent: {
    type: String,
    default: ''
  },
  envContent: {
    type: String,
    default: ''
  }
});

// Emits
const emit = defineEmits(['update:visible', 'updated']);

// Form reference
const formRef = ref(null);

// Loading state
const loading = ref(false);

// Form data
const formData = reactive({
  compose_content: '',
  env_content: '',
  restart_on_edit: false
});

// Monaco Editor references
const composeEditorRef = ref(null);
const envEditorRef = ref(null);
let composeEditor = null;
let envEditor = null;

// Editor initialization state
const isEditorsInitializing = ref(false);
const isEditorsDisposing = ref(false);
const editorDisposables = ref([]);

// 初始化Monaco Editor
const initMonacoEditors = async () => {
  // 防止重复初始化
  if (isEditorsInitializing.value || isEditorsDisposing.value) {
    return;
  }

  isEditorsInitializing.value = true;

  try {
    await nextTick();

    // 初始化Compose编辑器
    if (composeEditorRef.value && !composeEditor) {
      composeEditor = monaco.editor.create(composeEditorRef.value, {
        value: formData.compose_content,
        language: 'yaml',
        theme: 'vs-dark',
        automaticLayout: true,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        fontSize: 14,
        lineNumbers: 'on',
        wordWrap: 'on',
        folding: true,
        selectOnLineNumbers: true,
        matchBrackets: 'always'
      });

      // 监听内容变化
      const composeContentChangeDisposable = composeEditor.onDidChangeModelContent(() => {
        if (composeEditor && !isEditorsDisposing.value) {
          formData.compose_content = composeEditor.getValue();
        }
      });

      editorDisposables.value.push(composeContentChangeDisposable);
    }

    // 初始化环境变量编辑器
    if (envEditorRef.value && !envEditor) {
      envEditor = monaco.editor.create(envEditorRef.value, {
        value: formData.env_content,
        language: 'ini',
        theme: 'vs-dark',
        automaticLayout: true,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        fontSize: 14,
        lineNumbers: 'on',
        wordWrap: 'on',
        folding: true,
        selectOnLineNumbers: true
      });

      // 监听内容变化
      const envContentChangeDisposable = envEditor.onDidChangeModelContent(() => {
        if (envEditor && !isEditorsDisposing.value) {
          formData.env_content = envEditor.getValue();
        }
      });

      editorDisposables.value.push(envContentChangeDisposable);
    }
  } catch (error) {
    console.warn('Monaco Editor 初始化警告（可忽略）:', error);
  } finally {
    isEditorsInitializing.value = false;
  }
};

// 销毁Monaco Editor
const disposeMonacoEditors = () => {
  if (isEditorsDisposing.value) {
    return;
  }

  isEditorsDisposing.value = true;

  try {
    // 首先清理所有事件监听器
    editorDisposables.value.forEach(disposable => {
      try {
        disposable.dispose();
      } catch (error) {
        console.warn('清理编辑器事件监听器警告:', error);
      }
    });
    editorDisposables.value = [];

    // 清理编辑器实例
    if (composeEditor) {
      try {
        const model = composeEditor.getModel();
        if (model) {
          model.dispose();
        }
        composeEditor.dispose();
      } catch (error) {
        console.warn('清理Compose编辑器警告:', error);
      }
      composeEditor = null;
    }

    if (envEditor) {
      try {
        const model = envEditor.getModel();
        if (model) {
          model.dispose();
        }
        envEditor.dispose();
      } catch (error) {
        console.warn('清理环境变量编辑器警告:', error);
      }
      envEditor = null;
    }
  } catch (error) {
    console.warn('Monaco Editor 销毁警告（可忽略）:', error);
  } finally {
    setTimeout(() => {
      isEditorsDisposing.value = false;
    }, 200);
  }
};

// 设置编辑器内容
const setEditorContents = () => {
  if (composeEditor && !isEditorsDisposing.value) {
    try {
      composeEditor.setValue(formData.compose_content || '');
    } catch (error) {
      console.warn('设置Compose编辑器内容警告:', error);
    }
  }

  if (envEditor && !isEditorsDisposing.value) {
    try {
      envEditor.setValue(formData.env_content || '');
    } catch (error) {
      console.warn('设置环境变量编辑器内容警告:', error);
    }
  }
};

// 加载props中的内容到编辑器中
const loadPropsContent = () => {
  formData.compose_content = props.composeContent || '';
  formData.env_content = props.envContent || '';
  formData.restart_on_edit = false;
  setEditorContents();
};

// Handle visible change
const handleVisibleChange = async (value) => {
  if (value) {
    // 加载props中的内容到formData
    loadPropsContent();
    await nextTick();
    await initMonacoEditors();
  } else {
    handleCancel();
  }
  emit('update:visible', value);
};

// Handle cancel
const handleCancel = () => {
  if (formRef.value) {
    formRef.value.resetFields();
  }
  // Reset form data
  formData.compose_content = '';
  formData.env_content = '';
  formData.restart_on_edit = false;

  // 设置编辑器内容
  setEditorContents();

  emit('update:visible', false);
};

// 监听可见性变化，确保抽屉打开时编辑器被正确初始化
watch(() => props.visible, async (newVal) => {
  if (newVal) {
    loadPropsContent();
    await nextTick();
    await initMonacoEditors();
  }
});

// 监听props内容变化（当project切换时更新编辑器）
watch(() => props.composeContent, (newVal) => {
  if (props.visible) {
    formData.compose_content = newVal || '';
    setEditorContents();
  }
});

watch(() => props.envContent, (newVal) => {
  if (props.visible) {
    formData.env_content = newVal || '';
    setEditorContents();
  }
});

// 生命周期钩子
onMounted(() => {
  // 初始化检测窗口大小
  checkIsMobile();
  // 添加窗口大小监听
  window.addEventListener('resize', checkIsMobile);
});

// 组件卸载前清理资源
onBeforeUnmount(() => {
  isEditorsDisposing.value = true;
  disposeMonacoEditors();
  // 移除窗口大小监听
  window.removeEventListener('resize', checkIsMobile);
});

// Handle submit
const handleSubmit = async () => {
  if (!formRef.value) return;

  // Check if nodeId is valid
  if (!props.nodeId) {
    Message.error(t.value('pleaseSelectNode') || 'Please select a node');
    return;
  }

  // 先进行表单验证
  const errors = await formRef.value.validate().catch(error => {
    console.log('表单验证失败:', error);
    return false;
  });

  if (errors === false || (errors && Object.keys(errors).length > 0)) {
    return;
  }

  loading.value = true;

  try {
    const requestData = {
      compose_content: formData.compose_content,
      env_content: formData.env_content,
      restart_on_edit: formData.restart_on_edit
    };
    await updateComposeProjectFile(String(props.nodeId), props.projectName, requestData);

    Message.success(t.value('editSuccess'));

    // Emit updated event to refresh parent component
    emit('updated');

    // Close drawer
    handleCancel();
  } catch (error) {
    console.error('Edit compose project failed:', error);
    Message.error(t.value('editFailed') + (error?.response?.data?.message || ''));
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.form-hint {
  font-size: 12px;
  color: #8c8c8c;
  margin-top: 4px;
}

.drawer-footer {
  display: flex;
  justify-content: flex-start;
  gap: 12px;
  padding: 16px 24px 16px 0;
}

/* Monaco Editor 容器样式 */
.monaco-editor-container {
  width: 100%;
  height: 400px;
  border: 2px solid var(--arco-color-border);
  border-radius: 6px;
  overflow: hidden;
}

.monaco-editor-container:hover {
  border-color: #40a9ff;
}

.monaco-editor-container:focus-within {
  border-color: #40a9ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

/* 环境变量编辑器较小高度 */
.monaco-editor-container.env-editor {
  height: 150px;
}
</style>
