<template>
  <!-- 批量压缩文件/目录抽屉 -->
  <a-drawer
    v-model:visible="drawerVisible"
    :title="t('batchCompressFilesOrDirectories')"
    placement="right"
    :width="isMobile ? '90%' : 600"
    @ok="handleBatchCompressSubmit"
    :footer="true"
  >
    <a-spin :loading="formData.loading" style="width: 100%;">
      <a-form :model="formData" layout="vertical">
        <a-form-item :label="t('destinationPath')" required>
          <a-input 
            v-model="formData.destinationPath"
            :placeholder="t('enterDestinationPath')"
            style="width: 100%;"
            :disabled="formData.loading"
          >
            <template #suffix>
              <icon-folder 
                style="cursor: pointer; color: #165DFF;" 
                @click="handleShowMiniFileManager('destinationPath')"
                :disabled="formData.loading"
              />
            </template>
          </a-input>
        </a-form-item>
        
        <a-form-item :label="t('archiveName')" required>
          <a-input 
            v-model="formData.archiveName"
            :placeholder="t('enterArchiveName')"
            style="width: 100%;"
            :disabled="formData.loading"
          >
          </a-input>
          <div style="margin-top: 4px; font-size: 12px; color: #86909c;">
            {{ t('supportedCompressionFormats') }}
          </div>
        </a-form-item>
      </a-form>
    </a-spin>
    
    <template #footer>
      <a-button @click="drawerVisible = false" :disabled="formData.loading">{{ t('cancel') }}</a-button>
      <a-button type="primary" @click="handleBatchCompressSubmit" :loading="formData.loading">{{ t('compress') }}</a-button>
    </template>
  </a-drawer>
</template>

<script setup>
import { reactive, computed, watch } from 'vue';
import { IconFolder } from '@arco-design/web-vue/es/icon';
import { t } from '../../utils/locale';

// 添加导入Message用于显示错误消息
import { Message } from '@arco-design/web-vue';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  sourcePath: {
    type: String,
    default: ''
  },
  sourceNames: {
    type: Array,
    default: () => []
  },
  destinationPath: {
    type: String,
    default: ''
  },
  archiveName: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  },
  isMobile: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:visible', 'update:loading', 'submit', 'show-mini-file-manager']);

// 使用 computed 属性来处理 v-model
const drawerVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
});

const formData = reactive({
  sourcePath: '',
  sourceNames: [],
  destinationPath: '',
  archiveName: '',
  loading: false
});

// 生成友好的压缩文件名
const generateFriendlyArchiveName = (sourceNames) => {
  // 生成随机字符串的辅助函数
  const generateRandomString = () => {
    // 使用更稳定的随机字符串生成方法
    const timestamp = Date.now().toString(36);
    
    // 尝试使用 Crypto API 生成更安全的随机字符串，如果不可用则回退到 Math.random()
    let randomString;
    try {
      // 生成16字节的随机数据
      const array = new Uint8Array(16);
      crypto.getRandomValues(array);
      // 转换为36进制字符串
      randomString = Array.from(array).map(b => b.toString(36).padStart(2, '0')).join('').substring(0, 16);
    } catch (e) {
      // 如果 Crypto API 不可用，使用改进的 Math.random() 方法
      const randomPart1 = Math.random().toString(36).substring(2, 6).padEnd(4, '0');
      const randomPart2 = Math.random().toString(36).substring(2, 6).padEnd(4, '0');
      const randomPart3 = Math.random().toString(36).substring(2, 6).padEnd(4, '0');
      const randomPart4 = Math.random().toString(36).substring(2, 6).padEnd(4, '0');
      randomString = `${randomPart1}${randomPart2}${randomPart3}${randomPart4}`.substring(0, 16);
    }
    
    return `batch_${randomString}_${timestamp}.zip`;
  };
  
  try {
    if (!sourceNames || sourceNames.length === 0) {
      return generateRandomString();
    }
    
    // 获取第一个文件名
    const firstFileName = sourceNames[0];
    let baseFileName = firstFileName;
    if (firstFileName.includes('/')) {
      const lastSlashIndex = firstFileName.lastIndexOf('/');
      baseFileName = firstFileName.substring(lastSlashIndex + 1);
    }
    
    // 如果只选择了一个文件/目录，使用其名称作为压缩文件名
    // 如果选择了多个，使用第一个文件名加上"等N个文件"作为名称
    let archiveName;
    if (sourceNames.length === 1) {
      archiveName = `${baseFileName}.zip`;
    } else {
      // 生成更友好的文件名，例如 "文件名等3个文件.zip"
      const fileCount = sourceNames.length;
      archiveName = `${baseFileName}${t('and')} ${fileCount} ${t('files')}.zip`;
    }
    
    return archiveName;
  } catch (error) {
    console.error('生成压缩文件名失败:', error);
    return generateRandomString();
  }
};

// 监听 props 变化，更新表单数据
watch(() => props.visible, (newVal) => {
  if (newVal) {
    formData.sourcePath = props.sourcePath;
    formData.sourceNames = props.sourceNames;
    formData.destinationPath = props.destinationPath;
    
    // 生成默认的压缩文件名
    // 如果外部提供了archiveName且不为空，则使用外部提供的
    // 否则根据sourceNames生成友好的文件名
    if (props.archiveName && props.archiveName.trim() !== '') {
      formData.archiveName = props.archiveName;
    } else {
      formData.archiveName = generateFriendlyArchiveName(props.sourceNames);
    }
    
    formData.loading = props.loading;
  }
}, { immediate: true });

// 监听 loading prop 变化
watch(() => props.loading, (newVal) => {
  formData.loading = newVal;
});

// 监听目标路径和压缩包名称的变化，实时更新表单数据
watch(() => [props.destinationPath, props.archiveName], ([newDestinationPath, newArchiveName]) => {
  formData.destinationPath = newDestinationPath;
  if (newArchiveName) {
    formData.archiveName = newArchiveName;
  }
});

const handleBatchCompressSubmit = () => {
  emit('submit', {
    sourcePath: formData.sourcePath,
    sourceNames: formData.sourceNames,
    destinationPath: formData.destinationPath,
    archiveName: formData.archiveName
  });
};

const handleShowMiniFileManager = (targetField) => {
  emit('show-mini-file-manager', targetField);
};
</script>

<style scoped>
/* 批量压缩抽屉源文件项样式 */
.source-file-item {
  margin-bottom: 4px;
  width: 100%;
}
</style>