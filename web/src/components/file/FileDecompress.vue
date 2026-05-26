<template>
  <!-- 解压文件抽屉 -->
  <a-drawer
    v-model:visible="drawerVisible"
    :title="t('decompressFile')"
    placement="right"
    :width="isMobile ? '90%' : 600"
    @ok="handleDecompressSubmit"
    :footer="true"
  >
    <a-spin :loading="formData.loading" style="width: 100%;">
      <a-form :model="formData" layout="vertical">
        <a-form-item :label="t('sourceFile')">
          <a-input 
            :model-value="`${formData.sourcePath}/${formData.sourceName}`"
            readonly
            style="background-color: var(--color-fill-2); width: 100%;"
          />
          <div style="margin-top: 4px; font-size: 12px; color: #86909c;">
            {{ t('supportedFormats') }}
          </div>
        </a-form-item>
        
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
      </a-form>
    </a-spin>
    
    <template #footer>
      <a-button @click="drawerVisible = false" :disabled="formData.loading">{{ t('cancel') }}</a-button>
      <a-button type="primary" @click="handleDecompressSubmit" :loading="formData.loading">{{ t('decompress') }}</a-button>
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
  sourcePath: {
    type: String,
    default: ''
  },
  sourceName: {
    type: String,
    default: ''
  },
  destinationPath: {
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
  sourceName: '',
  destinationPath: '',
  loading: false
});

// 监听 props 变化，更新表单数据
watch(() => props.visible, (newVal) => {
  if (newVal) {
    formData.sourcePath = props.sourcePath;
    formData.sourceName = props.sourceName;
    formData.destinationPath = props.destinationPath;
    formData.loading = props.loading;
  }
});

// 监听 loading prop 变化
watch(() => props.loading, (newVal) => {
  formData.loading = newVal;
});

// 监听目标路径的变化，实时更新表单数据
watch(() => props.destinationPath, (newDestinationPath) => {
  formData.destinationPath = newDestinationPath;
});

const handleDecompressSubmit = () => {
  emit('submit', {
    sourcePath: formData.sourcePath,
    sourceName: formData.sourceName,
    destinationPath: formData.destinationPath
  });
};

const handleShowMiniFileManager = (targetField) => {
  emit('show-mini-file-manager', targetField);
};
</script>

<style scoped>
/* 解压抽屉样式 */
</style>
