<template>
  <a-modal 
    :visible="visible" 
    :title="t('fileDetails')"
    :footer="false"
    width="700px"
    @update:visible="handleVisibleChange"
    @cancel="handleVisibleChange(false)"
  >
    <div class="file-details" v-if="record">
      <div class="detail-item" style="justify-content: center; margin-bottom: 20px;">
        <component 
          :is="getFileIcon(record)" 
          :size="48"
          :style="{ 
            color: getFileIconColor(record),
            fontSize: '48px'
          }" 
        />
      </div>
      <div class="detail-item">
        <div class="detail-label">{{ t('fileName') }}:</div>
        <div class="detail-value">{{ record.filename }}</div>
      </div>
      <div class="detail-item">
        <div class="detail-label">{{ t('path') }}:</div>
        <div class="detail-value" style="display: flex; align-items: center; gap: 8px;">
          {{ record.path || '-' }}
          <IconCopy 
            v-if="record.path"
            style="cursor: pointer; color: #165DFF; font-size: 16px;"
            @click="handleCopyPath(record.path)"
          />
        </div>
      </div>
      <div class="detail-item">
        <div class="detail-label">{{ t('fileType') }}:</div>
        <div class="detail-value">
          {{ record.is_directory ? t('folder') : t('file') }}
        </div>
      </div>
      <div class="detail-item">
        <div class="detail-label">{{ t('size') }}:</div>
        <div class="detail-value">
          <template v-if="record.is_directory">
            <a-link v-if="!calculatedSizes[`${record.path}/${record.filename}`]" size="small" type="text" @click="() => handleCalculateSize(record)">{{ t('calculate') }}</a-link>
            <span v-else-if="calculatedSizes[`${record.path}/${record.filename}`].loading">...</span>
            <span v-else-if="calculatedSizes[`${record.path}/${record.filename}`].error">{{ t('failed') }}</span>
            <span v-else>{{ calculatedSizes[`${record.path}/${record.filename}`].size_human }}</span>
          </template>
          <span v-else>{{ record.size }}</span>
        </div>
      </div>
      <div class="detail-item">
        <div class="detail-label">{{ t('user') }}:</div>
        <div class="detail-value">{{ record.user || t('unknown') }}</div>
      </div>
      <div class="detail-item">
        <div class="detail-label">{{ t('group') }}:</div>
        <div class="detail-value">{{ record.group || t('unknown') }}</div>
      </div>
      <div class="detail-item">
        <div class="detail-label">{{ t('permissions') }}:</div>
        <div class="detail-value">{{ record.permissions || t('unknown') }}</div>
      </div>
      <div class="detail-item">
        <div class="detail-label">{{ t('modifiedTime') }}:</div>
        <div class="detail-value">{{ formatDate(record.modified_time) }}</div>
      </div>
    </div>
  </a-modal>
</template>

<script setup>
import { ref } from 'vue';
import { Message } from '@arco-design/web-vue';
import { IconCopy } from '@arco-design/web-vue/es/icon';
import { t } from '../../utils/locale';
import { getFileIcon, getFileIconColor } from '../../utils/file/fileIconMapper';
import { getDirectorySize } from '../../api/file';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  record: {
    type: Object,
    default: null
  },
  calculatedSizes: {
    type: Object,
    default: () => ({})
  }
});

const emit = defineEmits(['update:visible', 'calculate-size']);

const handleVisibleChange = (value) => {
  emit('update:visible', value);
};

// 处理路径复制功能
const handleCopyPath = (path) => {
  try {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      navigator.clipboard.writeText(path).then(() => {
        Message.success('Copy Path Success');
      }).catch(() => {
        fallbackCopyTextToClipboard(path);
      });
    } else {
      fallbackCopyTextToClipboard(path);
    }
  } catch (err) {
    console.error('复制失败:', err);
    Message.error('Copy Path Failed');
  }
};

// 备用复制方法
const fallbackCopyTextToClipboard = (text) => {
  const textArea = document.createElement('textarea');
  textArea.value = text;
  
  textArea.style.position = 'fixed';
  textArea.style.left = '-999999px';
  textArea.style.top = '-999999px';
  
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();
  
  try {
    const successful = document.execCommand('copy');
    if (successful) {
      Message.success('Copy Path Success');
    } else {
      throw new Error('Copy Command Failed');
    }
  } catch (err) {
    console.error('Fallback Copy Method Failed:', err);
    Message.error('Copy Path Failed');
  } finally {
    document.body.removeChild(textArea);
  }
};

// 处理计算大小
const handleCalculateSize = (record) => {
  emit('calculate-size', record);
};

// 格式化日期
const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleString('zh-CN');
};
</script>

<style scoped>
/* 文件详情样式 */
.file-details {
  padding: 12px;
}

.detail-item {
  display: flex;
  margin-bottom: 12px;
  line-height: 1.5;
}

.detail-label {
  width: 120px;
  font-weight: bold;
  color: var(--color-text-2);
}

.detail-value {
  flex: 1;
  color: var(--color-text-1);
}
</style>