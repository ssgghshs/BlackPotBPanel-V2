<template>
  <a-drawer
    v-model:visible="isVisible"
    :title="t('commitContainerToImage')"
    placement="right"
    :width="isMobile ? '90%' : 900"
    :footer="false"
    @close="handleClose"
  >
    <a-form
      :model="formData"
      :rules="formRules"
      ref="formRef"
      :label-col="{ span: 6 }"
      :wrapper-col="{ span: 18 }"
    >
      <!-- 容器信息显示 -->
      <a-card class="container-info-card" :bordered="true">
        <div class="container-info">
          <div class="info-item">
            <span class="info-label">{{ t('containerName') }}:</span>
            <span class="info-value">{{ containerInfo.name || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('containerId') }}:</span>
            <span class="info-value">{{ containerInfo.id || '-' }}</span>
          </div>
        </div>
      </a-card>

      <!-- 镜像提交表单 -->
      <a-form-item :label="t('imageName')" field="image_name">
        <a-input 
          v-model="formData.image_name" 
          :placeholder="t('imageNameFormatHint')" 
          allow-clear 
        />
      </a-form-item>
      
      <a-form-item :label="t('commitMessage')" field="message">
        <a-input 
          v-model="formData.message" 
          :placeholder="t('commitMessageHint')" 
          allow-clear 
        />
      </a-form-item>
      
      <a-form-item :label="t('author')" field="author">
        <a-input 
          v-model="formData.author" 
          :placeholder="t('authorHint')" 
          allow-clear 
        />
      </a-form-item>
      
      <a-form-item :label="t('pauseContainer')">
        <a-checkbox v-model="formData.pause">{{ t('pauseContainerHint') }}</a-checkbox>
      </a-form-item>
      
      <a-form-item :label="t('changes')">
        <div class="changes-container">
          <div class="section-header">
            <a-button type="outline" size="small" @click="addChange">{{ t('add') }}</a-button>
          </div>
          <div v-for="(change, index) in formData.changes" :key="index" class="change-item">
            <a-input 
              v-model="change.value" 
              :placeholder="t('changeFormatHint')" 
              allow-clear 
            />
            <a-button type="outline" danger size="small" @click="removeChange(index)">{{ t('delete') }}</a-button>
          </div>
        </div>
      </a-form-item>
    </a-form>

    <div class="drawer-footer">
      <a-button @click="handleClose" :disabled="isSubmitting" style="margin-right: 8px">{{ t('cancel') }}</a-button>
      <a-button type="primary" @click="handleSubmit" :loading="isSubmitting">{{ t('confirm') }}</a-button>
    </div>
  </a-drawer>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue';
import { t } from '../../utils/locale';
import { Message } from '@arco-design/web-vue';
import { Drawer as ADrawer, Form as AForm, FormItem as AFormItem, Input as AInput, Switch as ASwitch, Button as AButton, Card as ACard } from '@arco-design/web-vue';
import { commitContainer } from '../../api/container';

const props = defineProps({
  visible: { type: Boolean, default: false },
  containerInfo: { 
    type: Object, 
    default: () => ({})
  },
  nodeId: { 
    type: [String, Number], 
    default: ''
  }
});
const emit = defineEmits(['update:visible', 'success', 'close']);

// 响应式数据
const isVisible = ref(false);
const selectedHostId = ref(null);
const isSubmitting = ref(false);
const formRef = ref(null);
const containerInfo = ref({});
const isMobile = ref(false);

// 响应式布局检测
const checkIsMobile = () => {
  isMobile.value = window.innerWidth < 768;
};

// 表单数据
const formData = reactive({
  image_name: '',
  message: '',
  author: '',
  pause: false,
  changes: []
});

// 表单验证规则
const formRules = {
  image_name: [
    { 
      required: true, 
      message: t.value('pleaseInputImageName'), 
      trigger: 'blur' 
    },
    {
      pattern: /^[a-zA-Z0-9_\-./]+(?::[a-zA-Z0-9_\-./]+)?$/, 
      message: t.value('invalidImageNameFormat'), 
      trigger: 'blur'
    }
  ]
};

// 验证变更项
const validateChanges = () => {
  for (let i = 0; i < formData.changes.length; i++) {
    const change = formData.changes[i];
    if (change.value && !change.value.trim()) {
      Message.error(`${t.value('changeItem')} ${i + 1}: ${t.value('cannotBeEmpty')}`);
      return false;
    }
  }
  return true;
};

// 监听props变化
watch(() => props.visible, (nv) => {
  isVisible.value = nv;
  if (nv) {
    resetForm();
    // 组件打开时获取节点ID和容器信息
    getSelectedHostId();
  }
}, { immediate: true });

// 监听容器信息变化
watch(() => props.containerInfo, (newInfo) => {
  if (newInfo && Object.keys(newInfo).length > 0) {
    containerInfo.value = { ...newInfo };
  }
}, { deep: true, immediate: true });

// 监听nodeId变化
watch(() => props.nodeId, (newNodeId) => {
  if (newNodeId) {
    selectedHostId.value = newNodeId;
  }
}, { immediate: true });

// 重置表单
const resetForm = () => {
  try {
    if (formRef.value) formRef.value.resetFields();
    formData.image_name = '';
    formData.message = '';
    formData.author = '';
    formData.pause = true;
    formData.changes = [];
  } catch (e) {
    console.error(e);
  }
};

// 添加变更项
const addChange = () => {
  formData.changes.push({ value: '' });
};

// 移除变更项
const removeChange = (index) => {
  formData.changes.splice(index, 1);
};

// 获取选中的节点ID
const getSelectedHostId = () => {
  // 优先使用props传入的nodeId
  if (props.nodeId) {
    selectedHostId.value = props.nodeId;
    return;
  }
  
  // 其次尝试从localStorage获取
  const saved = localStorage.getItem('selectedContainerHostId');
  if (saved) {
    selectedHostId.value = saved;
    return;
  }
  
  // 最后尝试从事件总线或其他方式获取
  try {
    // 尝试获取当前活跃的容器节点
    const activeNode = window.__activeContainerNode;
    if (activeNode && activeNode.id) {
      selectedHostId.value = activeNode.id;
    }
  } catch (e) {
    console.warn('Failed to get active container node:', e);
  }
};

// 手动设置容器信息
const setContainerInfo = (containerData) => {
  containerInfo.value = { ...containerData };
};

// 手动设置节点ID
const setHostId = (hostId) => {
  selectedHostId.value = hostId;
  // 保存到localStorage以便下次使用
  try {
    localStorage.setItem('selectedContainerHostId', hostId);
  } catch (e) {
    console.warn('Failed to save selected host ID to localStorage:', e);
  }
};

// 验证单个表单字段
const validateField = (fieldName) => {
  if (formRef.value) {
    formRef.value.validateFields([fieldName]);
  }
};

// 导出方法供父组件调用
defineExpose({
  setContainerInfo,
  setHostId,
  validateField
});

// 处理容器宿主变化的事件监听器
const handleContainerHostChange = (event) => {
  if (event && event.detail && event.detail.hostId) {
    selectedHostId.value = event.detail.hostId;
  }
};

// 处理提交
const handleSubmit = async () => {
  if (!containerInfo.value.id) {
    Message.error({
      content: t.value('pleaseSelectContainer'),
      duration: 3000
    });
    return;
  }
  
  if (!selectedHostId.value) {
    Message.error({
      content: t.value('pleaseSelectHost'),
      duration: 3000
    });
    return;
  }
  
  try {
    // 先进行表单验证，参考ContainerCreate.vue的处理方式
    const errors = await formRef.value.validate().catch(error => {
      // 表单验证失败，直接返回，不执行API调用
      console.log('表单验证失败:', error);
      return false;
    });
    
    // 如果验证失败，则不继续执行后续逻辑
    if (errors === false || (errors && Object.keys(errors).length > 0)) {
      return;
    }
    
    // 验证变更项
    if (!validateChanges()) {
      return;
    }
    
    isSubmitting.value = true;
    
    // 构建请求数据
    const requestData = {
      image_name: formData.image_name,
      message: formData.message,
      author: formData.author,
      pause: formData.pause,
      changes: formData.changes
        .map(item => item.value)
        .filter(change => change && change.trim())
    };
    
    // 显示加载提示
    const loadingMessage = Message.loading({
      content: t.value('committingImage'),
      duration: 0, // 持续显示直到手动关闭
      closable: false
    });
    
    // 调用API
    const response = await commitContainer(selectedHostId.value, containerInfo.value.id, requestData);
    
    // 关闭加载提示
    loadingMessage.close();
    
    // 提交成功
    Message.success({
      content: t.value('commitSuccess'),
      duration: 3000,
      onClose: () => {
        // 成功消息关闭后再关闭抽屉，提升用户体验
        emit('success', response);
        handleClose();
      }
    });
  } catch (error) {
    // 处理验证错误
    if (error.code === 'ERR_VALIDATE' || error.name === 'ValidateError') {
      return;
    }
    
    // 处理API错误
    const errorMessage = error.response?.data?.message || error.message || t.value('commitFailed');
    Message.error({
      content: errorMessage,
      duration: 5000, // 错误消息显示时间更长
      closable: true
    });
    console.error('Commit container failed:', error);
  } finally {
    isSubmitting.value = false;
  }
};

// 关闭抽屉
const handleClose = () => {
  // 如果正在提交，阻止关闭
  if (isSubmitting.value) {
    Message.warning({
      content: t.value('submissionInProgress'),
      duration: 3000
    });
    return;
  }
  
  // 重置表单和状态
  resetForm();
  
  // 发送关闭事件
  emit('update:visible', false);
  emit('close');
  
  // 清理状态
  setTimeout(() => {
    containerInfo.value = {};
    // 保留selectedHostId以便下次使用
  }, 300);
};

// 处理ESC键关闭
const handleKeyDown = (event) => {
  if (event.key === 'Escape' && isVisible.value) {
    handleClose();
  }
};

// 生命周期钩子
onMounted(() => {
  window.addEventListener('containerHostChanged', handleContainerHostChange);
  window.addEventListener('resize', checkIsMobile);
  window.addEventListener('keydown', handleKeyDown);
  checkIsMobile();
  getSelectedHostId();
});

onUnmounted(() => {
  window.removeEventListener('containerHostChanged', handleContainerHostChange);
  window.removeEventListener('resize', checkIsMobile);
  window.removeEventListener('keydown', handleKeyDown);
  // 清理任何可能的定时器或事件监听器
  isSubmitting.value = false;
});
</script>

<style scoped>
/* 容器信息卡片样式 */
.container-info-card {
  margin-bottom: 20px;
  background-color: var(--color-bg-1);
}

.container-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.info-item {
  display: flex;
  align-items: center;
}

.info-label {
  font-weight: 500;
  width: 100px;
  color: #666;
}

.info-value {
  flex: 1;
  word-break: break-all;
}

/* 变更项样式 */
.changes-container {
  margin-top: 10px;
}

.change-item {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
}

.change-item .arco-input {
  flex: 1;
}

/* 开关提示样式 */
.switch-hint {
  margin-left: 10px;
  color: #999;
  font-size: 14px;
}

/* 抽屉底部样式 */
.drawer-footer {
  margin-top: 30px;
  display: flex;
  justify-content: flex-end;
  padding: 16px;
  position: sticky;
  bottom: 0;
}
</style>