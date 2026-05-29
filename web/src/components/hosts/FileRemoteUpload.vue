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
</template>

<script setup>
import { ref, reactive, watch, computed, onMounted, onUnmounted } from 'vue';
import { Message } from '@arco-design/web-vue';
import { IconFile, IconLoading } from '@arco-design/web-vue/es/icon';
import { t } from '../../utils/locale';
import { uploadFileToRemote } from '../../api/host';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  hostId: {
    type: [Number, String],
    default: null
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
const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1200);

const modalVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
});

const drawerWidth = computed(() => {
  if (windowWidth.value <= 768) {
    return '100%';
  } else if (windowWidth.value <= 1200) {
    return 500;
  } else {
    return 600;
  }
});

const handleResize = () => {
  windowWidth.value = window.innerWidth;
};

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

const clearFileList = () => {
  fileList.value = [];
};

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const handleCancelUpload = () => {
  if (isUploading.value && abortController.value) {
    abortController.value.abort();
    Message.info(t.value('uploadCancelled'));
  }
  handleCancel();
};

const handleCancel = () => {
  emit('update:visible', false);
  fileList.value = [];
  isProcessing.value = false;
  isUploading.value = false;
  for (const key of Object.keys(uploadProgress)) {
    delete uploadProgress[key];
  }
  abortController.value = null;
};

const handleUploadSubmit = async () => {
  if (fileList.value.length === 0) {
    Message.warning(t.value('noFilesSelected'));
    return;
  }

  Message.info(`${t.value('readyToUpload')} ${fileList.value.length} ${t.value('files')}`);

  isUploading.value = true;
  abortController.value = new AbortController();

  for (const file of fileList.value) {
    if (!isUploading.value) break;

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('path', props.currentPath);
      uploadProgress[file.name] = 0;

      await uploadFileToRemote(props.hostId, formData);

      uploadProgress[file.name] = 100;
      Message.success(`${t.value('fileUploaded')}: ${file.name}`);
    } catch (error) {
      if (error.name === 'AbortError') {
        Message.info(`${t.value('uploadCancelled')}: ${file.name}`);
      } else {
        let errorMessage = `${t.value('uploadFileFailed')}: ${file.name}`;
        if (error.message) {
          errorMessage += ` (${error.message})`;
        }
        Message.error(errorMessage);
      }
      uploadProgress[file.name] = -1;
    }
  }

  emit('upload-success');
  isUploading.value = false;
  abortController.value = null;
  emit('update:visible', false);
  fileList.value = [];
  for (const key of Object.keys(uploadProgress)) {
    delete uploadProgress[key];
  }
};

watch(() => props.visible, (newVal) => {
  if (!newVal) {
    fileList.value = [];
    isDragging.value = false;
    isProcessing.value = false;
    isUploading.value = false;
    for (const key of Object.keys(uploadProgress)) {
      delete uploadProgress[key];
    }
    abortController.value = null;
  }
});

onMounted(() => {
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
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
