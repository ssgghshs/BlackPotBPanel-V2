<template>
  <!-- 复制文件/目录对话框 -->
  <a-modal
    v-model:visible="modalVisible"
    :title="t('copyFileOrDirectory')"
    :width="isMobile ? '90%' : 600"
    @ok="handleCopySubmit"
  >
    <a-form :model="formData" layout="vertical">
      <a-form-item :label="t('sourceFile')">
        <a-input 
          :model-value="`${formData.sourcePath}/${formData.sourceName}`"
          readonly
          style="background-color: var(--color-fill-2); width: 100%;"
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
      
      <a-form-item :label="t('destinationName')">
        <a-input 
          v-model="formData.destinationName"
          :placeholder="t('enterDestinationName')"
          style="width: 100%;"
        >
        </a-input>
      </a-form-item>
    </a-form>
  </a-modal>
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
  destinationName: {
    type: String,
    default: ''
  },
  isMobile: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:visible', 'submit', 'show-mini-file-manager']);

// 使用 computed 属性来处理 v-model
const modalVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
});

const formData = reactive({
  sourcePath: '',
  sourceName: '',
  destinationPath: '',
  destinationName: ''
});

// 监听 props 变化，更新表单数据
watch(() => props.visible, (newVal) => {
  if (newVal) {
    formData.sourcePath = props.sourcePath;
    formData.sourceName = props.sourceName;
    formData.destinationPath = props.destinationPath;
    formData.destinationName = props.destinationName;
  }
});

// 监听目标路径和目标名称的变化，实时更新表单数据
watch(() => [props.destinationPath, props.destinationName], ([newDestinationPath, newDestinationName]) => {
  formData.destinationPath = newDestinationPath;
  formData.destinationName = newDestinationName;
});

const handleCopySubmit = () => {
  emit('submit', {
    sourcePath: formData.sourcePath,
    sourceName: formData.sourceName,
    destinationPath: formData.destinationPath,
    destinationName: formData.destinationName
  });
};

const handleShowMiniFileManager = (targetField) => {
  emit('show-mini-file-manager', targetField);
};
</script>

<style scoped>
/* 组件特定样式可以在这里添加 */
</style>
