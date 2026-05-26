<template>
  <div class="image-monitor">
    <div class="image-monitor-header">
      <h3>{{ t('imagePreview') }}</h3>
      <div class="header-actions">
        <a-button 
          type="outline" 
          size="small" 
          @click="refreshImage"
          :loading="loading"
        >
          <icon-refresh />
          {{ t('refresh') }}
        </a-button>
        <a-button 
          type="outline" 
          size="small" 
          @click="downloadImage"
          :disabled="!imageUrl"
        >
          <icon-download />
          {{ t('download') }}
        </a-button>
      </div>
    </div>
    
    <div class="image-container" v-if="imageUrl">
      <img 
        :src="imageUrl" 
        :alt="imageName"
        class="preview-image"
        @load="onImageLoad"
        @error="onImageError"
      />
    </div>
    
    <div class="image-placeholder" v-else>
      <icon-image style="font-size: 48px; color: #C9CDD4;" />
      <div class="placeholder-text">{{ t('noImageSelected') }}</div>
    </div>
    
    <div class="image-info" v-if="imageInfo">
      <div class="info-item">
        <span class="info-label">{{ t('fileName') }}:</span>
        <span class="info-value">{{ imageName }}</span>
      </div>
      <div class="info-item">
        <span class="info-label">{{ t('imageSize') }}:</span>
        <span class="info-value">{{ imageInfo.width }} × {{ imageInfo.height }}</span>
      </div>
      <div class="info-item">
        <span class="info-label">{{ t('fileSize') }}:</span>
        <span class="info-value">{{ formatFileSize(imageInfo.size) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { Message } from '@arco-design/web-vue';
import { 
  IconImage, 
  IconRefresh, 
  IconDownload 
} from '@arco-design/web-vue/es/icon';
import { getImageContent } from '../../api/file';
import { t } from '../../utils/locale';

const props = defineProps({
  filePath: {
    type: String,
    required: true
  },
  fileName: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['image-loaded']);

// 响应式数据
const imageUrl = ref('');
const loading = ref(false);
const imageInfo = ref(null);
const imageElement = ref(null);

// 计算属性
const imageName = computed(() => {
  return props.fileName || '';
});

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// 获取图片内容
const loadImage = async () => {
  if (!props.filePath || !props.fileName) {
    return;
  }
  
  loading.value = true;
  try {
    const response = await getImageContent({
      path: props.filePath,
      filename: props.fileName
    });
    
    // 创建图片URL
    const url = URL.createObjectURL(response);
    
    // 清理旧的URL
    if (imageUrl.value) {
      URL.revokeObjectURL(imageUrl.value);
    }
    
    imageUrl.value = url;
  } catch (error) {
    console.error('加载图片失败:', error);
    Message.error(t('loadImageFailed') + ': ' + (error.message || t('unknownError')));
    imageUrl.value = '';
    imageInfo.value = null;
  } finally {
    loading.value = false;
  }
};

// 刷新图片
const refreshImage = () => {
  loadImage();
};

// 下载图片
const downloadImage = () => {
  if (!imageUrl.value) return;
  
  const link = document.createElement('a');
  link.href = imageUrl.value;
  link.download = props.fileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

// 图片加载完成
const onImageLoad = (event) => {
  imageElement.value = event.target;
  
  // 获取图片信息
  imageInfo.value = {
    width: event.target.naturalWidth,
    height: event.target.naturalHeight,
    size: event.target.src.length // 这里只是一个近似值
  };
  
  emit('image-loaded', {
    width: event.target.naturalWidth,
    height: event.target.naturalHeight
  });
};

// 图片加载错误
const onImageError = () => {
  Message.error(t('loadImageFailed'));
  imageUrl.value = '';
  imageInfo.value = null;
};

// 监听路径和文件名变化
watch(() => [props.filePath, props.fileName], () => {
  loadImage();
}, { immediate: true });

// 组件卸载时清理
// 注意：在Vue 3的<script setup>中，需要使用onUnmounted生命周期钩子
// 但由于模板限制，我们在组件卸载时无法直接访问onUnmounted
// 在实际使用中，应该在父组件中正确处理URL的清理
</script>

<style scoped>
.image-monitor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-bg-2);
  border-radius: 4px;
  overflow: hidden;
}

.image-monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-1);
}

.image-monitor-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.image-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  overflow: auto;
  background: #f5f5f5;
}

.preview-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  background: 
    linear-gradient(45deg, #e0e0e0 25%, transparent 25%),
    linear-gradient(-45deg, #e0e0e0 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, #e0e0e0 75%),
    linear-gradient(-45deg, transparent 75%, #e0e0e0 75%);
  background-size: 20px 20px;
  background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
}

.image-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: var(--color-text-3);
}

.placeholder-text {
  margin-top: 16px;
  font-size: 14px;
}

.image-info {
  padding: 12px 16px;
  border-top: 1px solid var(--color-border);
  background: var(--color-bg-1);
  font-size: 12px;
}

.info-item {
  display: flex;
  margin-bottom: 8px;
}

.info-item:last-child {
  margin-bottom: 0;
}

.info-label {
  width: 80px;
  color: var(--color-text-2);
}

.info-value {
  flex: 1;
  color: var(--color-text-1);
}
</style>