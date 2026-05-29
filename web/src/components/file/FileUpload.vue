<!-- 文件上传抽屉 -->
<template>
  <a-drawer 
    v-model:visible="modalVisible" 
    :title="t('uploadFile')"
    :width="drawerWidth"
    :footer="false"
    @cancel="handleCancel"
    placement="right"
  >
    <div class="upload-drawer-content">
      <!-- 拖拽上传区域 -->
      <div 
        class="upload-drop-area"
        :class="{ 'upload-drop-active': isDragging, 'upload-drop-processing': isProcessing }"
        @dragover.prevent="handleDragOver"
        @dragenter.prevent="handleDragEnter"
        @dragleave.prevent="handleDragLeave"
        @drop.prevent="handleDrop"
        @click="triggerFileSelect"
      >
        <template v-if="isProcessing">
          <div class="processing-icon">
            <icon-loading />
          </div>
          <div class="processing-text">{{ t('processingFile') }}</div>
        </template>
        <template v-else>
          <div class="upload-icon">
            <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="#165DFF" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: middle;">
              <path d="M12 3v12m0-12L8 7m4-4l4 4"/>
              <path d="M3 16v3a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-3"/>
            </svg>
          </div>
          <div class="upload-text">
            {{ t('dragFileHere') }}
          </div>
          <div class="upload-hint">
            {{ t('clickOrDragToUpload') }}
          </div>
          <a-button type="primary" size="small" style="margin-top: 16px;">
            {{ t('selectFile') }}
          </a-button>
        </template>
      </div>
      
      <!-- 文件列表 -->
      <div class="upload-file-list" v-if="fileList.length > 0">
        <div class="upload-file-list-header">
          <div>{{ t('selectedFiles') }} ({{ fileList.length }})</div>
          <a-link @click="clearFileList">{{ t('clear') }}</a-link>
        </div>
        <div class="upload-file-item" v-for="(file, index) in fileList" :key="index">
          <div class="upload-file-info">
            <icon-file style="font-size: 16px; color: #666; margin-right: 8px;" />
            <div class="upload-file-name">{{ file.name }}</div>
          </div>
          <div class="upload-file-size">{{ formatFileSize(file.size) }}</div>
        </div>
        
        <!-- 上传百分比显示 -->
        <div class="upload-progress-container" v-if="isUploading">
          <div class="upload-progress-item" v-for="(file, index) in fileList" :key="index">
            <div class="upload-progress-info">
              <span class="upload-progress-name">{{ file.name }}</span>
              <span class="upload-progress-percent">{{ Math.min(100, Math.max(0, uploadProgress[file.name] || 0)) }}%</span>
            </div>
          </div>
        </div>
        
        <div class="upload-actions">
          <a-button @click="handleCancelUpload" style="margin-right: 8px;">{{ t('cancel') }}</a-button>
          <a-button type="primary" @click="handleUploadSubmit" :loading="isUploading">{{ t('upload') }}</a-button>
        </div>
      </div>
    </div>
  </a-drawer>
   <!-- 文件冲突弹窗 -->
  <a-modal
    v-model:visible="showConflictDialog"
    :title="t('fileConflictTitle')"
    @ok="handleConfirmOverwrite"
    @cancel="showConflictDialog = false"
    :ok-loading="conflictUploading"
    :cancel-text="t('cancel')"
    :ok-text="t('overwrite')"
    width="600px"
  >
    <div>
      <p style="color: var(--color-danger-6); margin-bottom: 16px;">
        {{ t('fileConflictDesc') }}
      </p>
      <div style="max-height: 300px; overflow-y: auto; border: 1px solid var(--color-border-2); border-radius: 4px; padding: 12px;">
        <div
          v-for="file in conflictFiles"
          :key="file.name"
          style="display: flex; align-items: center; gap: 8px; padding: 8px; border-bottom: 1px solid var(--color-border-1);"
        >
          <icon-file style="font-size: 16px; color: var(--color-text-2);" />
          <div style="flex: 1; overflow: hidden;">
            <div style="font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              {{ file.name }}
            </div>
            <div style="font-size: 12px; color: var(--color-text-3);">
              {{ formatFileSize(file.size) }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, reactive, watch, computed, onMounted, onUnmounted } from 'vue';
import { Message } from '@arco-design/web-vue';
import { IconFile, IconLoading } from '@arco-design/web-vue/es/icon';
import { t } from '../../utils/locale';
import { uploadFile, getFileList } from '../../api/file';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  currentPath: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['update:visible', 'upload-success']);

const fileList = ref([]);
const isDragging = ref(false);
const isProcessing = ref(false);
const isUploading = ref(false);
const uploadProgress = reactive({});
const abortController = ref(null);
const showConflictDialog = ref(false);
const conflictFiles = ref([]);
const conflictUploading = ref(false);
const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1200);

// 使用 computed 处理 v-model
const modalVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
});

// 响应式抽屉宽度
const drawerWidth = computed(() => {
  if (windowWidth.value <= 768) {
    return '100%'; // 移动端全屏
  } else if (windowWidth.value <= 1200) {
    return 500; // 平板和小屏桌面
  } else {
    return 600; // 大屏桌面
  }
});

// 窗口大小变化处理函数
const handleResize = () => {
  windowWidth.value = window.innerWidth;
};

// 触发文件选择
const triggerFileSelect = () => {
  const input = document.createElement('input');
  input.type = 'file';
  input.multiple = true;
  input.onchange = (e) => {
    const files = Array.from(e.target.files);
    fileList.value = [...fileList.value, ...files];
    isProcessing.value = false;
  };
  isProcessing.value = true;
  input.click();
};

// 拖拽事件处理
const handleDragOver = () => {
  isDragging.value = true;
};

const handleDragEnter = () => {
  isDragging.value = true;
};

const handleDragLeave = () => {
  isDragging.value = false;
};

const handleDrop = (e) => {
  isDragging.value = false;
  const files = Array.from(e.dataTransfer.files);
  fileList.value = [...fileList.value, ...files];
};

// 清空文件列表
const clearFileList = () => {
  fileList.value = [];
};

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// 取消上传
const handleCancelUpload = () => {
  if (isUploading.value && abortController.value) {
    abortController.value.abort();
    Message.info(t.value('uploadCancelled'));
  }
  handleCancel();
};

// 关闭模态框
const handleCancel = () => {
  emit('update:visible', false);
  fileList.value = [];
  isProcessing.value = false;
  isUploading.value = false;
  uploadProgress.value = {};
  abortController.value = null;
};

const doUpload = async (overwrite) => {
  isUploading.value = true;
  abortController.value = new AbortController();
  
  for (const file of fileList.value) {
    if (!isUploading.value) {
      break;
    }
    
    try {
      const formData = new FormData();
      formData.append('path', props.currentPath);
      formData.append('file', file);
      if (overwrite) {
        formData.append('overwrite', 'true');
      }
      
      uploadProgress[file.name] = 0;
      
      await uploadFile(formData, {
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const progress = Math.min(100, Math.max(0, Math.round((progressEvent.loaded * 100) / progressEvent.total)));
            uploadProgress[file.name] = progress;
          }
        },
        signal: abortController.value.signal
      });
      
      uploadProgress[file.name] = 100;
      Message.success(`${t.value('fileUploaded')}: ${file.name}`);
    } catch (error) {
      if (error.name === 'AbortError') {
        console.log('上传已取消:', file.name);
        Message.info(`${t.value('uploadCancelled')}: ${file.name}`);
      } else {
        console.error('上传文件失败:', error);
        let errorMessage = `${t.value('uploadFileFailed')}: ${file.name}`;
        if (error.code === 'ECONNABORTED') {
          errorMessage = `${t.value('uploadFileTimeout')}: ${file.name} (${t.value('pleaseTryAgainOrUploadSmallerFile')})`;
        } else if (error.message) {
          errorMessage = `${t.value('uploadFileFailed')}: ${file.name} (${error.message})`;
        }
        Message.error(errorMessage);
      }
      uploadProgress[file.name] = -1;
    }
  }
  
  emit('upload-success');
  isUploading.value = false;
  conflictUploading.value = false;
  emit('update:visible', false);
  fileList.value = [];
  abortController.value = null;
};

// 处理上传提交
const handleUploadSubmit = async () => {
  if (fileList.value.length === 0) {
    Message.warning(t.value('noFilesSelected'));
    return;
  }

  Message.info(`${t.value('readyToUpload')} ${fileList.value.length} ${t.value('files')}`);

  isProcessing.value = true;

  try {
    const res = await getFileList({ path: props.currentPath, skip: 0, limit: 10000 });
    isProcessing.value = false;
    const existingFiles = res?.data || [];
    const existingNames = new Set(existingFiles.map(f => f.filename));

    const conflicts = fileList.value.filter(f => existingNames.has(f.name));
    if (conflicts.length > 0) {
      conflictFiles.value = conflicts;
      showConflictDialog.value = true;
      return;
    }
  } catch (error) {
    isProcessing.value = false;
    console.error('检测文件冲突失败，将直接上传:', error);
  }

  await doUpload(false);
};

const handleConfirmOverwrite = async () => {
  conflictUploading.value = true;
  showConflictDialog.value = false;
  conflictFiles.value = [];
  await doUpload(true);
};

// 监听 visible 变化，重置状态
watch(() => props.visible, (newVal) => {
  if (!newVal) {
    fileList.value = [];
    isDragging.value = false;
    isProcessing.value = false;
    isUploading.value = false;
    uploadProgress.value = {};
    abortController.value = null;
    showConflictDialog.value = false;
    conflictFiles.value = [];
    conflictUploading.value = false;
  }
});

// 组件挂载时添加窗口大小变化监听器
onMounted(() => {
  window.addEventListener('resize', handleResize);
});

// 组件卸载时移除窗口大小变化监听器
onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
});

defineExpose({
  setFileList(files) {
    fileList.value = files;
  }
});
</script>

<style scoped>
.upload-drawer-content {
  padding: 20px 0;
}

.upload-drop-area {
  border: 2px dashed #e5e5e5;
  border-radius: 4px;
  padding: 30px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  background-color: #fafafa;
  margin-bottom: 20px;
}

.upload-drop-area:hover,
.upload-drop-active {
  border-color: #165DFF;
  background-color: #f0f8ff;
}

.upload-drop-processing {
  border-color: #165DFF;
  background-color: #f0f8ff;
  cursor: default;
  pointer-events: none;
}

.processing-icon {
  margin-bottom: 16px;
  color: #165DFF;
  animation: processing-spin 1s linear infinite;
}

@keyframes processing-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.processing-text {
  font-size: 16px;
  font-weight: 500;
  color: #165DFF;
}

.upload-icon {
  margin-bottom: 16px;
}

.upload-text {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 8px;
  color: #333;
}

.upload-hint {
  font-size: 14px;
  color: #999;
  margin-bottom: 16px;
}

.upload-file-list {
  border-top: 1px solid #e5e5e5;
  padding-top: 16px;
}

.upload-file-list-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  font-weight: 500;
}

.upload-file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.upload-file-info {
  display: flex;
  align-items: center;
  flex: 1;
  overflow: hidden;
}

.upload-file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-file-size {
  color: #999;
  font-size: 12px;
  margin-left: 12px;
  flex-shrink: 0;
}

.upload-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.upload-progress-container {
  margin: 16px 0;
  max-height: 300px;
  overflow-y: auto;
}

.upload-progress-item {
  margin-bottom: 12px;
}

.upload-progress-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
  font-size: 12px;
}

.upload-progress-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 80%;
}

.upload-progress-percent {
  color: #666;
  flex-shrink: 0;
}
</style>