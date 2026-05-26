<template>
  <!-- 远程下载抽屉 -->
  <a-drawer
    v-model:visible="drawerVisible"
    :title="t('downloadRemote')"
    placement="right"
    :width="isMobile ? '90%' : 600"
    @ok="handleRemoteDownloadSubmit"
    :footer="true"
  >
    <a-form :model="formData" layout="vertical">
      <a-form-item :label="t('url')" required>
        <a-input 
          v-model="formData.url"
          :placeholder="t('enterUrl')"
          style="width: 100%;"
        />
      </a-form-item>
      
      <a-form-item :label="t('destinationPath')" required>
        <a-input 
          v-model="formData.destinationPath"
          :placeholder="t('enterDestinationPath')"
          style="width: 100%;"
        >
          <template #suffix>
            <icon-folder 
              style="cursor: pointer; color: #165DFF;" 
              @click="handleShowMiniFileManager('destinationPath')"
            />
          </template>
        </a-input>
      </a-form-item>
      
      <a-form-item :label="t('fileName')">
        <a-input 
          v-model="formData.filename"
          :placeholder="t('enterFileName')"
          style="width: 100%;"
        />
      </a-form-item>
      
      <!-- SSL证书验证选项 -->
      <a-form-item :label="t('sslCertificateVerification')">
        <a-switch
          v-model="formData.verifySsl"
          :checked-text="t('enable')"
          :unchecked-text="t('disable')"
        />
        <div class="ssl-verification-hint">{{ t('sslVerificationHint') }}</div>
      </a-form-item>
      
      <!-- 下载进度条 -->
      <a-form-item v-if="formData.isDownloading || formData.downloadProgress > 0">
        <div class="download-progress-container">
          <div class="download-progress-label">{{ t('downloading') }}</div>
          <a-progress 
            :percent="Math.min(100, Math.max(0, formData.downloadProgress))" 
            size="small"
            status="normal"
          />
        </div>
      </a-form-item>
    </a-form>
    
    <template #footer>
      <a-button @click="drawerVisible = false" :disabled="formData.isDownloading">{{ t('cancel') }}</a-button>
      <a-button 
        type="primary" 
        @click="handleRemoteDownloadSubmit" 
        :loading="formData.isDownloading"
        :disabled="formData.isDownloading"
      >
        {{ formData.isDownloading ? t('downloading') : t('download') }}
      </a-button>
    </template>
  </a-drawer>
</template>

<script setup>
import { reactive, computed, watch } from 'vue';
import { IconFolder } from '@arco-design/web-vue/es/icon';
import { t } from '../../utils/locale';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  url: {
    type: String,
    default: ''
  },
  destinationPath: {
    type: String,
    default: ''
  },
  filename: {
    type: String,
    default: ''
  },
  verifySsl: {
    type: Boolean,
    default: true
  },
  isDownloading: {
    type: Boolean,
    default: false
  },
  downloadProgress: {
    type: Number,
    default: 0
  },
  isMobile: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:visible', 'update:isDownloading', 'update:downloadProgress', 'submit', 'show-mini-file-manager']);

// 使用 computed 属性来处理 v-model
const drawerVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
});

const formData = reactive({
  url: '',
  destinationPath: '',
  filename: '',
  verifySsl: true,
  isDownloading: false,
  downloadProgress: 0
});

// 监听 props 变化，更新表单数据
watch(() => props.visible, (newVal) => {
  if (newVal) {
    formData.url = props.url;
    formData.destinationPath = props.destinationPath;
    formData.filename = props.filename;
    formData.verifySsl = props.verifySsl;
    formData.isDownloading = props.isDownloading;
    formData.downloadProgress = props.downloadProgress;
  }
});

// 监听 isDownloading 和 downloadProgress props 变化
watch(() => props.isDownloading, (newVal) => {
  formData.isDownloading = newVal;
});

watch(() => props.downloadProgress, (newVal) => {
  formData.downloadProgress = newVal;
});

// 监听目标路径和文件名的变化，实时更新表单数据
watch(() => [props.destinationPath, props.filename], ([newDestinationPath, newFilename]) => {
  formData.destinationPath = newDestinationPath;
  formData.filename = newFilename;
});

// 监听URL变化，自动提取文件名
watch(() => formData.url, (newUrl) => {
  if (newUrl && !formData.filename) {
    try {
      // 移除查询参数和哈希部分
      const cleanUrl = newUrl.split('?')[0].split('#')[0];
      // 提取URL路径中最后一个斜杠后的部分作为文件名
      const pathParts = cleanUrl.split('/');
      const filename = pathParts[pathParts.length - 1];
      // 确保文件名不为空且包含扩展名
      if (filename && filename.includes('.')) {
        formData.filename = filename;
      }
    } catch (error) {
      // 处理无效URL的情况
      console.warn('Invalid URL format:', error);
    }
  }
});

const handleRemoteDownloadSubmit = () => {
  emit('submit', {
    url: formData.url,
    destinationPath: formData.destinationPath,
    filename: formData.filename,
    verifySsl: formData.verifySsl
  });
};

const handleShowMiniFileManager = (targetField) => {
  emit('show-mini-file-manager', targetField);
};
</script>

<style scoped>
.ssl-verification-hint {
  font-size: 12px;
  color: #86909c;
  margin-top: 4px;
}

/* 下载进度条样式 */
.download-progress-container {
  margin-top: 16px;
}

.download-progress-label {
  margin-bottom: 8px;
  font-size: 14px;
  color: #333;
}
</style>
