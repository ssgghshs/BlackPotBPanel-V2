<template>
  <!-- 创建链接抽屉 -->
  <a-drawer
    v-model:visible="drawerVisible"
    :title="t('createSymlink')"
    placement="right"
    :width="isMobile ? '90%' : 600"
    @ok="handleSymlinkSubmit"
    :footer="true"
  >
    <a-form :model="formData" layout="vertical">
     <a-form-item :label="t('name')">
        <a-input 
          v-model="formData.destinationName"
          :placeholder="t('enterDestinationName')"
          style="width: 100%;"
        >
        </a-input>
      </a-form-item>

      <a-form-item :label="t('path')" required>
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
      <a-form-item :label="t('linkPath')" required>
        <a-input 
          v-model="formData.mergedSourcePath"
          :placeholder="t('enterFullLinkPath')"
          style="width: 100%;"
        >
          <template #suffix>
            <icon-folder 
              style="cursor: pointer; color: #165DFF;" 
              @click="handleShowMiniFileManager('mergedSourcePath')"
            />
          </template>
        </a-input>
        <div class="ssl-verification-hint">
          {{ t('selectOrEnterFullLinkPath') }}
        </div>
      </a-form-item>
      
      <a-form-item :label="t('linkType')">
        <a-radio-group v-model="formData.linkType" style="width: 100%;">
          <a-radio value="symlink">{{ t('softLink') }}</a-radio>
          <a-radio value="hardlink">{{ t('hardLink') }}</a-radio>
        </a-radio-group>
      </a-form-item>
    </a-form>
    
    <template #footer>
      <a-button @click="drawerVisible = false">{{ t('cancel') }}</a-button>
      <a-button type="primary" @click="handleSymlinkSubmit">{{ t('create') }}</a-button>
    </template>
  </a-drawer>
  
  <!-- 直接集成MiniFileManager组件 -->
  <MiniFileManager
    v-model:visible="miniFileManagerVisible"
    :initial-path="miniFileManagerInitialPath"
    :select-mode="miniFileManagerSelectMode"
    @select="handleMiniFileSelect"
  />
</template>

<script setup>
import { reactive, computed, watch, ref } from 'vue';
import { IconFolder } from '@arco-design/web-vue/es/icon';
import { t } from '../../utils/locale';
import MiniFileManager from './MiniFileManager.vue';

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
  linkType: {
    type: String,
    default: 'symlink'
  },
  isMobile: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:visible', 'submit', 'showMiniFileManager']);

// 使用 computed 属性来处理 v-model
const drawerVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
});

const formData = reactive({
  mergedSourcePath: '',
  destinationPath: '',
  destinationName: '',
  linkType: 'symlink'
});

// MiniFileManager组件的状态管理
const miniFileManagerVisible = ref(false);
const miniFileManagerInitialPath = ref('/');
const miniFileManagerSelectMode = ref('file');
const currentTargetField = ref('');

// 处理MiniFileManager选择结果
const handleMiniFileSelect = (selection) => {
  const { path, name } = selection;
  
  // 根据当前目标字段更新相应的表单数据
  if (currentTargetField.value === 'mergedSourcePath') {
    // 对于源路径，我们需要完整的路径和文件名
    formData.mergedSourcePath = name ? `${path}/${name}` : path;
  } else if (currentTargetField.value === 'destinationPath') {
    // 对于目标路径，只需要目录路径
    formData.destinationPath = path;
  }
  
  // 关闭文件管理器
  miniFileManagerVisible.value = false;
};

// 移除对已不存在的handleFileSelect函数的引用

// 工具函数：将路径和文件名合并成完整路径
const mergePathAndName = (path, name) => {
  if (!path && !name) return '';
  if (!path) return name;
  if (!name) return path;
  // 确保路径以斜杠结尾
  const normalizedPath = path.endsWith('/') ? path : `${path}/`;
  return normalizedPath + name;
};

// 工具函数：将完整路径拆分为路径和文件名
const splitPath = (fullPath) => {
  if (!fullPath) return { path: '', name: '' };
  
  // 处理文件管理器返回的路径格式
  if (fullPath.includes('|')) {
    const [path, name] = fullPath.split('|');
    return { path: path || '', name: name || '' };
  }
  
  // 常规路径拆分
  const lastSlashIndex = fullPath.lastIndexOf('/');
  if (lastSlashIndex === -1) {
    return { path: '', name: fullPath };
  } else if (lastSlashIndex === fullPath.length - 1) {
    return { path: fullPath, name: '' };
  } else {
    return {
      path: fullPath.substring(0, lastSlashIndex + 1),
      name: fullPath.substring(lastSlashIndex + 1)
    };
  }
};

// 监听 props 变化，更新表单数据
watch(() => props.visible, (newVal) => {
  if (newVal) {
    // 保持mergedSourcePath为空，不自动填充
    formData.mergedSourcePath = '';
    formData.destinationPath = props.destinationPath;
    formData.destinationName = props.destinationName;
    formData.linkType = props.linkType;
  }
});

// 监听路径变化，实时更新表单数据
watch(() => [props.destinationPath, props.destinationName], 
  ([newDestinationPath, newDestinationName]) => {
    formData.destinationPath = newDestinationPath;
    formData.destinationName = newDestinationName;
  }
);

// 移除对未定义props的监听


const handleSymlinkSubmit = () => {
  const { path: sourcePath, name: sourceName } = splitPath(formData.mergedSourcePath);
  emit('submit', {
    sourcePath: sourcePath,
    sourceName: sourceName,
    destinationPath: formData.destinationPath,
    destinationName: formData.destinationName,
    linkType: formData.linkType
  });
};

const handleShowMiniFileManager = (targetField) => {
  // 设置当前目标字段
  currentTargetField.value = targetField;
  
  // 根据目标字段设置选择模式
  if (targetField === 'mergedSourcePath') {
    // 对于源路径，我们需要选择文件
    miniFileManagerSelectMode.value = 'file';
    
    // 尝试从当前路径中提取初始路径
    const currentPath = formData.mergedSourcePath;
    if (currentPath) {
      const pathParts = splitPath(currentPath);
      miniFileManagerInitialPath.value = pathParts.path || '/';
    } else {
      miniFileManagerInitialPath.value = '/';
    }
  } else if (targetField === 'destinationPath') {
    // 对于目标路径，我们需要选择目录
    miniFileManagerSelectMode.value = 'directory';
    miniFileManagerInitialPath.value = formData.destinationPath || '/';
  }
  
  // 显示文件管理器
  miniFileManagerVisible.value = true;
};
</script>

<style scoped>
.ssl-verification-hint {
  font-size: 12px;
  color: #86909c;
  margin-top: 4px;
}
</style>