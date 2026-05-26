<template>
  <a-drawer
    :title="t('createComposeProject')"
    placement="right"
    :width="isMobile ? '100%' : 800"
    :visible="visible"
    :footer="false"
    @update:visible="handleVisibleChange"
  >
    <a-form
      :model="formData"
      :rules="rules"
      ref="formRef"
      layout="vertical"
      :disabled="loading"
    >
      <a-form-item :label="t('projectName')" field="project_name">
        <a-input
          v-model="formData.project_name"
          :placeholder="t('enterProjectName')"
          :maxlength="50"
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
        <a-checkbox v-model="formData.start_on_create">
          {{ t('startOnCreate') }}
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
        {{ t('create') }}
      </a-button>
    </div>

  </a-drawer>
</template>

<script setup>
import { ref, reactive, nextTick, watch, onMounted, onBeforeUnmount } from 'vue';
import { Message } from '@arco-design/web-vue';
import { t } from '../../utils/locale';
import { createComposeProject } from '../../api/container';
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
  }
});

// Emits
const emit = defineEmits(['update:visible', 'created']);

// Form reference
const formRef = ref(null);

// Loading state
const loading = ref(false);

// Form data
const formData = reactive({
    project_name: '',
    compose_content: '',
    env_content: '',
    start_on_create: true
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

// Form validation rules
const rules = reactive({
  project_name: [
    {
      required: true,
      message: t.value('projectNameRequired'),
      trigger: 'blur'
    },
    {
      pattern: /^[a-zA-Z0-9_.-]+$/,
      message: t.value('projectNameInvalid'),
      trigger: 'blur'
    }
  ],
  compose_content: [
    {
      required: true,
      message: t.value('composeContentRequired'),
      trigger: 'blur'
    }
  ]
});

// Handle visible change
const handleVisibleChange = async (value) => {
  if (value) {
    await nextTick();
    await initMonacoEditors();
  } else {
    // Reset form when drawer is closed
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
  Object.assign(formData, {
      project_name: '',
      compose_content: '',
      env_content: '',
      start_on_create: true
    });
  
  // 设置编辑器内容
  setEditorContents();
  
  emit('update:visible', false);
};

// 监听可见性变化，确保抽屉打开时编辑器被正确初始化
watch(() => props.visible, async (newVal) => {
  if (newVal) {
    await nextTick();
    await initMonacoEditors();
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
  
  // 先进行表单验证，参考Login.vue的处理方式
  const errors = await formRef.value.validate().catch(error => {
    // 表单验证失败，直接返回，不执行API调用
    console.log('表单验证失败:', error);
    return false;
  });
  
  // 如果验证失败或者返回了错误，则不继续执行后续逻辑
  if (errors === false || (errors && Object.keys(errors).length > 0)) {
    return;
  }
  
  // 只有表单验证通过后才执行API调用
  loading.value = true;
  
  try {
    // Call API to create compose project - ensure nodeId is string
    // 只发送需要的字段，不包含base_path
    const requestData = {
      project_name: formData.project_name,
      compose_content: formData.compose_content,
      env_content: formData.env_content,
      start_on_create: formData.start_on_create
    };
    await createComposeProject(String(props.nodeId), requestData);
    
    Message.success(t.value('createSuccess'));
    
    // Emit created event to refresh parent component
    emit('created');
    
    // Close drawer
    handleCancel();
  } catch (error) {
    console.error('Create compose project failed:', error);
    Message.error(t.value('createFailed') + (error?.response?.data?.message || ''));
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
