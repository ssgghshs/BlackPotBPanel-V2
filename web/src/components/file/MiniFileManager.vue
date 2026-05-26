<template>
  <a-modal
    :visible="visible"
    :title="t('selectDestination')"
    :width="modalWidth"
    :footer="false"
    @cancel="handleCancel"
    @close="handleCancel"
  >
    <div class="mini-file-manager" :class="{ 'mobile': isMobile, 'tablet': isTablet }">
      <!-- 路径导航 -->
      <div class="path-navigation">
        <!-- 新建按钮 -->
        <a-dropdown>
          <a-button type="primary" size="medium">
            <template #icon><icon-plus /></template>
            {{ t('create') }}
          </a-button>
          <template #content>
            <a-doption @click="startCreate('folder')">
              <icon-folder />
              {{ t('createFolder') }}
            </a-doption>
            <a-doption @click="startCreate('file')">
              <icon-file />
              {{ t('createFile') }}
            </a-doption>
          </template>
        </a-dropdown>
        <!-- 上一级目录按钮 -->
        <a-button 
          type="outline" 
          size="medium" 
          @click="goToParent"
          :disabled="currentPath === '/'"
        >
          <template #icon><icon-left /></template>
          {{ t('goToParentDirectory') }}
        </a-button>
        <!-- 路径导航容器 -->
        <div class="path-container">
          <!-- 面包屑导航 - 双击进入编辑模式 -->
          <a-breadcrumb 
            class="path-breadcrumb" 
            separator=">"
            v-show="!showPathInput"
            @dblclick="startPathEdit"
            :style="{ cursor: 'text' }"
          >
            <a-breadcrumb-item>
              <a-link @click="goToRoot">
                <icon-home />
              </a-link>
            </a-breadcrumb-item>
            <a-breadcrumb-item 
              v-for="(segment, index) in pathSegments" 
              :key="index"
            >
              <a-link @click="() => navigateToSegment(index)">{{ segment.name }}</a-link>
            </a-breadcrumb-item>
          </a-breadcrumb>
          
          <!-- 路径输入框 -->
          <div class="path-input-wrapper" v-show="showPathInput">
            <a-input 
              v-model="editablePath"
              size="small" 
              :placeholder="t('enterFilePath')"
              @press-enter="handlePathChange"
              @blur="cancelPathEdit"
              ref="pathInputRef"
            />
          </div>
        </div>      
      </div>
      <!-- 文件列表 -->
      <div class="file-list-container">
        <a-table
          :columns="columns"
          :data="displayFileList"
          :loading="loading"
          :pagination="false"
          row-key="filename"
          :scroll="{ y: '100%' }"
          @row-dblclick="handleRowDblClick"
          @row-click="handleRowClick"
          :style="{ height: '100%', display: 'flex', flexDirection: 'column' }"
        >
          <template #filename="{ record }">
            <div class="file-item">
              <!-- 创建模式下显示输入框 -->
              <template v-if="isCreating && record._isCreating">
                <component 
                  :is="record.is_directory ? IconFolder : IconFile" 
                  :style="{ 
                    color: record.is_directory ? '#FFB300' : '#9E9E9E', 
                    marginRight: '8px',
                    fontSize: '16px'
                  }" 
                />
                <a-input 
                  v-model="creatingName" 
                  size="small" 
                  ref="createInputRef"
                  @press-enter="confirmCreate"
                  style="width: 200px;"
                />
                <a-link @click="confirmCreate" style="margin-left: 8px;">{{ t('save') }}</a-link>
                <a-link @click="cancelCreate" style="margin-left: 8px;">{{ t('cancel') }}</a-link>
              </template>
              <!-- 普通模式下显示文件名 -->
              <template v-else>
                <component 
                  :is="getFileIcon(record)" 
                  :style="{ 
                    color: getFileIconColor(record), 
                    marginRight: '8px',
                    fontSize: '16px'
                  }" 
                />
                <span>{{ record.filename }}</span>
              </template>
            </div>
          </template>
          <template #modified_time="{ record }">
            <!-- 创建模式下不显示时间 -->
            <span v-if="!record._isCreating">{{ formatDate(record.modified_time) }}</span>
          </template>
        </a-table>
      </div>

      <!-- 选中文件/文件夹信息 -->
      <div class="selected-info" v-if="selectedFile">
        <div class="selected-item">
          <component 
            :is="getFileIcon(selectedFile)" 
            :size="16"
            :style="{ 
              color: getFileIconColor(selectedFile), 
              marginRight: '8px'
            }" 
          />
          <span class="selected-name">{{ selectedFile.filename }}</span>
          <a-tag v-if="selectedFile.is_directory" color="blue" size="small">{{ t('folder') }}</a-tag>
          <a-tag v-else color="green" size="small">{{ t('file') }}</a-tag>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="actions">
        <a-button  @click="handleCancel">{{ t('cancel') }}</a-button>
        <a-button type="primary"
          @click="handleSelect"
          :disabled="!selectedFile"
        >
          {{ t('select') }}
        </a-button>
      </div>
    </div>
  </a-modal>


</template>

<script setup>
import { ref, computed, onMounted, watch, reactive, onUnmounted, nextTick } from 'vue';
import { Message, Modal } from '@arco-design/web-vue';
import {
  IconLeft,
  IconPlus,
  IconHome,
  IconFolder,
  IconFile
} from '@arco-design/web-vue/es/icon';
import { getFileList, createDirectory, createFile } from '../../api/file';
import { t } from '../../utils/locale';
import { getFileIcon, getFileIconColor } from '../../utils/file/fileIconMapper';

// 定义 props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  initialPath: {
    type: String,
    default: '/'
  },
  selectMode: {
    type: String,
    default: 'directory' // 'directory' 或 'file'
  }
});

// 定义 emits
const emit = defineEmits(['update:visible', 'select']);

// 响应式数据
const currentPath = ref(props.initialPath);
const fileList = ref([]);
const loading = ref(false);
const selectedFile = ref(null);
const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1200);
const showPathInput = ref(false);
const editablePath = ref(props.initialPath);
const pathInputRef = ref(null);

// 创建状态管理
const isCreating = ref(false);
const creatingType = ref('folder'); // 'folder' 或 'file'
const creatingName = ref('');
const createInputRef = ref(null);

// 计算属性：显示的文件列表（包含创建行）
const displayFileList = computed(() => {
  if (!isCreating.value) {
    return fileList.value;
  }
  
  // 添加创建行到列表开头
  const creatingItem = {
    _isCreating: true,
    filename: creatingName.value,
    is_directory: creatingType.value === 'folder',
    size: 0,
    modified_time: new Date().toISOString()
  };
  
  return [creatingItem, ...fileList.value];
});

// 计算属性：模态框宽度
const modalWidth = computed(() => {
  if (windowWidth.value <= 480) {
    return '95%'; // 超小屏
  } else if (windowWidth.value <= 768) {
    return '90%'; // 小屏（移动端）
  } else if (windowWidth.value <= 1024) {
    return 800;   // 中屏（平板）
  } else if (windowWidth.value <= 1200) {
    return 1000;  // 大屏
  } else {
    return 1200;  // 超大屏
  }
});



// 计算属性：是否为移动端
const isMobile = computed(() => {
  return windowWidth.value <= 768;
});

// 计算属性：是否为平板
const isTablet = computed(() => {
  return windowWidth.value > 768 && windowWidth.value <= 1024;
});

// 计算属性：表格高度 - 自适应剩余空间
const tableHeight = computed(() => {
  return '100%';
});

// 计算属性：路径片段
const pathSegments = computed(() => {
  const segments = [];
  const paths = currentPath.value.split('/').filter(p => p !== '' && p !== '.');
  
  let currentPathSegment = '';
  for (let i = 0; i < paths.length; i++) {
    currentPathSegment += '/' + paths[i];
    segments.push({ name: paths[i], path: currentPathSegment });
  }
  
  return segments;
});

// 表格列定义
const columns = computed(() => {
  const baseColumns = [
    {
      title: t.value('fileName'),
      dataIndex: 'filename',
      slotName: 'filename'
    },
    {
      title: t.value('size'),
      dataIndex: 'size',
      width: isMobile.value ? 80 : 120
    },
    {
      title: t.value('modifiedTime'),
      dataIndex: 'modified_time',
      slotName: 'modified_time',
      width: isMobile.value ? 120 : 240
    }
  ];
  
  // 在移动端隐藏修改时间列以节省空间
  if (isMobile.value) {
    return baseColumns.slice(0, 2);
  }
  
  return baseColumns;
});



// 时间格式化函数
const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleString('zh-CN');
};

// 窗口大小变化处理函数
const handleResize = () => {
  windowWidth.value = window.innerWidth;
};

// 加载文件列表
const loadFileList = async (path) => {
  loading.value = true;
  try {
    const response = await getFileList({ path });
    // 根据选择模式过滤文件
    if (props.selectMode === 'directory') {
      fileList.value = (response.data || []).filter(item => item.is_directory);
    } else {
      fileList.value = response.data || [];
    }
    // 更新当前路径和可编辑路径
    currentPath.value = path;
    editablePath.value = path;
  } catch (error) {
    console.error('获取文件列表失败:', error);
    Message.error(t.value('getFileListFailed') + ': ' + (error.message || t.value('unknownError')));
  } finally {
    loading.value = false;
  }
};

// 处理双击行
const handleRowDblClick = (record) => {
  if (record.is_directory) {
    const newPath = currentPath.value === '/' 
      ? `/${record.filename}` 
      : `${currentPath.value}/${record.filename}`;
    loadFileList(newPath);
  } else if (props.selectMode === 'file') {
    // 如果是文件且选择模式为文件，则选中并关闭
    selectedFile.value = record;
    handleSelect();
  }
};

// 处理单击行
const handleRowClick = (record) => {
  selectedFile.value = record;
};

// 返回上级目录
const goToParent = () => {
  if (currentPath.value === '/') {
    return;
  }
  
  const paths = currentPath.value.split('/').filter(p => p !== '');
  paths.pop();
  const parentPath = paths.length > 0 ? '/' + paths.join('/') : '/';
  loadFileList(parentPath);
};

// 返回根目录
const goToRoot = () => {
  loadFileList('/');
};

// 导航到指定路径片段
const navigateToSegment = (index) => {
  const segments = pathSegments.value;
  if (index >= 0 && index < segments.length) {
    const targetPath = segments[index].path;
    loadFileList(targetPath);
  }
};

// 开始路径编辑
const startPathEdit = () => {
  showPathInput.value = true;
  nextTick(() => {
    if (pathInputRef.value) {
      pathInputRef.value.focus();
    }
  });
};

// 取消路径编辑
const cancelPathEdit = () => {
  showPathInput.value = false;
  editablePath.value = currentPath.value;
};

// 处理路径变更
const handlePathChange = () => {
  if (editablePath.value.trim() !== '') {
    loadFileList(editablePath.value);
  }
  showPathInput.value = false;
};

// 开始创建文件/文件夹
const startCreate = (type) => {
  isCreating.value = true;
  creatingType.value = type;
  creatingName.value = type === 'folder' ? t.value('unnamedFolder') : t.value('unnamedFile');
  
  // 等待DOM更新后聚焦输入框
  nextTick(() => {
    if (createInputRef.value) {
      createInputRef.value.focus();
      // 选中输入框内容 - 访问原生input元素
      if (createInputRef.value.input) {
        createInputRef.value.input.select();
      } else if (createInputRef.value.$el) {
        const inputEl = createInputRef.value.$el.querySelector('input');
        if (inputEl) {
          inputEl.select();
        }
      }
    }
  });
};

// 确认创建
const confirmCreate = async () => {
  const name = creatingName.value.trim();
  if (!name) {
    Message.error(creatingType.value === 'folder' ? t.value('folderNameCannotBeEmpty') : t.value('fileNameCannotBeEmpty'));
    return;
  }
  
  try {
    if (creatingType.value === 'folder') {
      await createDirectory({
        path: currentPath.value,
        dir_name: name
      });
      Message.success(`${t.value('folderCreated')}: ${name}`);
    } else {
      await createFile({
        path: currentPath.value,
        file_name: name
      });
      Message.success(`${t.value('fileCreated')}: ${name}`);
    }
    
    // 重置创建状态
    isCreating.value = false;
    creatingName.value = '';
    
    // 重新加载文件列表
    loadFileList(currentPath.value);
  } catch (error) {
    console.error(`创建${creatingType.value}失败:`, error);
    Message.error((creatingType.value === 'folder' ? t.value('createFolderFailed') : t.value('createFileFailed')) + ': ' + (error.message || t.value('unknownError')));
  }
};

// 取消创建
const cancelCreate = () => {
  isCreating.value = false;
  creatingName.value = '';
};

// 处理取消
const handleCancel = () => {
  emit('update:visible', false);
};

// 处理选择
const handleSelect = () => {
  if (selectedFile.value) {
    if (props.selectMode === 'directory' && !selectedFile.value.is_directory) {
      // 如果选择模式是目录但选中的是文件，则使用当前路径
      emit('select', {
        path: currentPath.value
      });
    } else {
      emit('select', {
        path: currentPath.value,
        name: selectedFile.value.filename
      });
    }
  } else {
    // 如果没有选择文件，则返回当前路径
    emit('select', {
      path: currentPath.value
    });
  }
  emit('update:visible', false);
};

// 监听可见性变化
onMounted(() => {
  // 添加窗口大小变化监听器
  window.addEventListener('resize', handleResize);
  
  if (props.visible) {
    loadFileList(currentPath.value);
  }
});

// 监听 props.visible 的变化
watch(() => props.visible, (newVal) => {
  if (newVal) {
    // 当visible变为true时，重置选中状态并使用最新的initialPath
    selectedFile.value = null;
    isCreating.value = false;
    creatingName.value = '';
    currentPath.value = props.initialPath;
    loadFileList(currentPath.value);
  }
});

// 监听 props.initialPath 的变化
watch(() => props.initialPath, (newVal) => {
  if (props.visible) {
    // 如果组件是可见的，更新currentPath并重新加载文件列表
    currentPath.value = newVal;
    editablePath.value = newVal;
    loadFileList(currentPath.value);
  }
});

// 组件卸载时移除事件监听器
onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
});

</script>

<style scoped>
.mini-file-manager {
  padding: 16px;
  height: 550px;
  display: flex;
  flex-direction: column;
}

.mini-file-manager.mobile {
  padding: 12px;
  height: 550px;
}

.mini-file-manager.tablet {
  padding: 14px;
  height: 600px;
}

.path-navigation {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border);
  flex-wrap: nowrap;
}

.path-navigation.mobile {
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
}

/* 确保所有按钮和路径容器在同一行垂直对齐 */
.path-navigation > * {
  align-self: center;
}

.path-navigation.tablet {
  gap: 10px;
}

/* 路径容器样式 */
.path-container {
  flex: 1;
  background: var(--color-fill-2);
  border-radius: 4px;
  border: 1px solid var(--color-border);
  position: relative;
  height: 32px;
  display: flex;
  align-items: center;
  padding: 0 12px;
  margin-bottom: 0;
}

.path-breadcrumb {
  flex: 1;
  user-select: none;
}

/* 路径输入框容器 */
.path-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.path-input-wrapper :deep(.arco-input-wrapper) {
  flex: 1;
}

.file-list-container {
  margin-bottom: 16px;
  flex: 1;
  overflow: auto;
  min-height: 0;
}

.file-list-container.mobile {
  margin-bottom: 12px;
}

.file-list-container.tablet {
  margin-bottom: 14px;
}

.file-item {
  display: flex;
  align-items: center;
}

.selected-info {
  padding: 12px;
  background: var(--color-fill-2);
  border-radius: 4px;
  border: 1px solid var(--color-border);
  margin-bottom: 12px;
}

.selected-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.selected-name {
  font-weight: 500;
  color: var(--color-text-1);
}

.selected-path {
  font-size: 12px;
  color: var(--color-text-3);
  margin-left: auto;
  word-break: break-all;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.actions.mobile {
  flex-direction: column;
}

.actions.mobile :deep(.arco-btn) {
  width: 100%;
  margin-bottom: 8px;
}

.actions.tablet {
  gap: 10px;
}

/* 响应式断点 */
@media (max-width: 1200px) {
  .path-navigation {
    gap: 10px;
  }
  
  .actions {
    gap: 10px;
  }
}

@media (max-width: 1024px) {
  .path-navigation {
    gap: 10px;
  }
  
  .actions {
    gap: 10px;
  }
  
  :deep(.arco-table-th) {
    font-size: 13px;
    padding: 10px 6px;
  }
  
  :deep(.arco-table-td) {
    font-size: 13px;
    padding: 10px 6px;
  }
}

@media (max-width: 768px) {
  .mini-file-manager {
    padding: 12px;
  }
  
  .path-navigation {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }
  
  .path-container {
    min-height: 40px;
    flex-direction: column;
    align-items: stretch;
    padding: 8px 12px;
  }
  
  .path-input-wrapper {
    margin-top: 8px;
  }
  
  .file-list-container {
    margin-bottom: 12px;
  }
  
  .actions {
    flex-direction: column;
  }
  
  .actions :deep(.arco-btn) {
    width: 100%;
    margin-bottom: 8px;
  }
  
  /* 表格在移动端的优化 */
  :deep(.arco-table-th) {
    font-size: 12px;
    padding: 8px 4px;
  }
  
  :deep(.arco-table-td) {
    font-size: 12px;
    padding: 8px 4px;
  }
  
  :deep(.arco-table-tr) {
    min-height: 36px;
  }
}

@media (max-width: 480px) {
  .mini-file-manager {
    padding: 10px;
  }
  
  .path-navigation {
    gap: 6px;
  }
  
  :deep(.arco-table-th) {
    font-size: 11px;
    padding: 6px 2px;
  }
  
  :deep(.arco-table-td) {
    font-size: 11px;
    padding: 6px 2px;
  }
  
  :deep(.file-item) {
    font-size: 12px;
  }
  
  :deep(.file-item span) {
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  :deep(.arco-btn) {
    font-size: 12px;
    padding: 0 12px;
  }
}
</style>