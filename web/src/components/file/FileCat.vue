<template>
  <a-drawer
    :visible="visible"
    :title="t('fileManager')"
    placement="right"
    :width="drawerWidth"
    @cancel="handleClose"
    @close="handleClose"
    unmount-on-close
    :footer="true"
  >
    <div class="file-manager">
      <!-- 路径导航区 -->
      <div class="navigation-bar">
        <a-button type="outline" size="large" @click="goToParentDirectory" :disabled="isAtDefaultRoot">
          <template #icon><icon-left /></template>
          {{ t('goToParentDirectory') }}
        </a-button>

        <!-- 路径导航容器 -->
        <div class="path-container">
          <a-breadcrumb class="path-breadcrumb" separator=">">
            <a-breadcrumb-item>
              <a-link @click="goToRoot">
                <icon-home />
              </a-link>
            </a-breadcrumb-item>
            <a-breadcrumb-item 
              v-for="(path, index) in pathSegments" 
              :key="index"
            >
              <a-link @click="() => navigateToPath(index)">{{ path.name }}</a-link>
            </a-breadcrumb-item>
          </a-breadcrumb>
        </div>
      </div>

      <!-- 操作按钮区 -->
      <div class="action-bar" v-if="fileList.length > 0 || !loading">
        <a-button size="small" @click="refresh"><icon-refresh /> {{ t('refresh') }}</a-button>
        <!-- 搜索框容器 -->
        <div class="search-container">
          <AInputSearch 
            v-model="searchKeyword"
            size="small" 
            :placeholder="t('searchFile')" 
            style="width: 200px;"
            @search="handleSearch"
          />
        </div>
      </div>

      <!-- 文件列表容器 -->
      <div class="file-list-wrapper">
        <!-- 列表视图 -->
        <div class="file-list-container">
          <a-table
            :columns="columns"
            :data="filteredFileList"
            :loading="loading"
            :pagination="false"
            :stripe="true"
            row-key="filename"
            size="medium"
            :scroll="{ x: 'max-content' }"
          >
            <!-- 文件名列：图标 + 名称 -->
            <template #filename="{ record }">
              <div class="file-item">
                <component 
                  :is="getFileIcon(record)" 
                  :size="16"
                  :style="{ 
                    color: getFileIconColor(record), 
                    marginRight: '8px',
                    fontSize: '16px'
                  }" 
                />
                <span @click="() => handleFileClick(record)" style="cursor: pointer;">{{ record.filename }}</span>
              </div>
            </template>

            <!-- 大小列 -->
            <template #size="{ record }">
              {{ record.size }}
            </template>

            <!-- 修改时间列 -->
            <template #modified_time="{ record }">
              {{ formatDate(record.modified_time) }}
            </template>

            <!-- 操作列 -->
            <template #operations="{ record }">
              <a-space size="mini">
                <a-link @click="() => handleShowDetails(record)">{{ t('details') }}</a-link>
                <a-link @click="() => handleDownload(record)">{{ t('download') }}</a-link>
                <a-dropdown>
                  <a-link><icon-more /></a-link>
                  <template #content>
                    <a-doption @click="() => handleOpenImage(record)" v-if="!record.is_directory && isImageFile(record.filename)">
                      <icon-image />
                      {{ t('openImage') }}
                    </a-doption>
                    <a-doption @click="() => handleOpenFile(record)" v-if="!record.is_directory && canOpenFile(record.filename)">
                      <icon-edit />
                      {{ t('open') }}
                    </a-doption>
                    <a-doption @click="() => handleDeleteFile(record)">
                      <icon-delete />
                      {{ t('delete') }}
                    </a-doption>
                  </template>
                </a-dropdown>
              </a-space>
            </template>
          </a-table>
        </div>
      </div>
    </div>
    
    <template #footer>
      <div style="text-align: left;">
        <AButton style="margin-right: 8px;" @click="handleClose">{{ t('cancel') }}</AButton>
        <AButton type="primary" :loading="restartLoading" @click="handleRestart">{{ t('confirm') }}</AButton>
      </div>
    </template>
  </a-drawer>

  <!-- 文件详情弹窗 -->
  <a-modal 
    v-model:visible="detailsModal.visible" 
    :title="t('fileDetails')"
    :footer="false"
    width="500px"
  >
    <div class="file-details" v-if="detailsModal.record">
      <div class="detail-item" style="justify-content: center; margin-bottom: 20px;">
        <component 
          :is="getFileIcon(detailsModal.record)" 
          :size="48"
          :style="{ 
            color: getFileIconColor(detailsModal.record),
            fontSize: '48px'
          }" 
        />
      </div>
      <div class="detail-item">
        <div class="detail-label">{{ t('fileName') }}:</div>
        <div class="detail-value">{{ detailsModal.record.filename }}</div>
      </div>
      <div class="detail-item">
        <div class="detail-label">{{ t('fileType') }}:</div>
        <div class="detail-value">
          {{ detailsModal.record.is_directory ? t('folder') : t('file') }}
        </div>
      </div>
      <div class="detail-item">
        <div class="detail-label">{{ t('size') }}:</div>
        <div class="detail-value">{{ detailsModal.record.size }}</div>
      </div>
      <div class="detail-item">
        <div class="detail-label">{{ t('user') }}:</div>
        <div class="detail-value">{{ detailsModal.record.user || t('unknown') }}</div>
      </div>
      <div class="detail-item">
        <div class="detail-label">{{ t('group') }}:</div>
        <div class="detail-value">{{ detailsModal.record.group || t('unknown') }}</div>
      </div>
      <div class="detail-item">
        <div class="detail-label">{{ t('permissions') }}:</div>
        <div class="detail-value">{{ detailsModal.record.permissions || t('unknown') }}</div>
      </div>
      <div class="detail-item">
        <div class="detail-label">{{ t('modifiedTime') }}:</div>
        <div class="detail-value">{{ formatDate(detailsModal.record.modified_time) }}</div>
      </div>
    </div>
  </a-modal>

  <!-- 文件编辑器弹窗 -->
  <FileEdit
    :visible="fileEditor.visible"
    :file-path="fileEditor.path"
    :file-name="fileEditor.name"
    @update:visible="fileEditor.visible = $event"
    @close="handleFileEditorClose"
    @save="handleFileEditorSave"
    @change-file="handleFileEditorChangeFile"
  />
  
  <!-- 图片监视器弹窗 -->
  <a-modal
    :visible="imageMonitor.visible"
    :title="t('imagePreview')"
    :width="imageModalWidth"
    :footer="false"
    @cancel="handleImageMonitorClose"
    @close="handleImageMonitorClose"
    :mask-closable="false"
  >
    <ImageMonitor 
      :file-path="imageMonitor.path"
      :file-name="imageMonitor.name"
      @image-loaded="handleImageLoaded"
    />
  </a-modal>

</template>

<script setup>
import { ref, computed, onMounted, watch, reactive } from 'vue';
import { Message, Modal } from '@arco-design/web-vue';
import { 
  IconLeft,
  IconRefresh,
  IconHome,
  IconEdit,
  IconDelete,
  IconMore,
  IconImage,
} from '@arco-design/web-vue/es/icon';
import { InputSearch, Input, Button } from '@arco-design/web-vue';
import { 
  getFileList, 
  deleteFile, downloadFile } from '../../api/file';
import { restartComposeProject } from '../../api/container';
import { t } from '../../utils/locale';
import { getFileIcon, getFileIconColor, isImageFile, canOpenFile } from '../../utils/file/fileIconMapper';
import FileEdit from './FileEdit.vue';
import ImageMonitor from './ImageMonitor.vue';

// 注册组件
const AInputSearch = InputSearch;
const AInput = Input;
const AButton = Button;

// Props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  initialPath: {
    type: String,
    default: '/opt/blackpotbpanel-v2/server'
  }
});

// Emits
const emit = defineEmits(['update:visible']);

// 响应式数据
const fileList = ref([]);
const loading = ref(false);
const currentPath = ref(props.initialPath);
const searchKeyword = ref('');
const selectedHostId = ref('');
const restartLoading = ref(false);

// 抽屉宽度
const drawerWidth = computed(() => {
  if (window.innerWidth <= 768) {
    return '95%';
  } else if (window.innerWidth <= 1024) {
    return '80%';
  } else {
    return 1200;
  }
});



// 详情弹窗状态
const detailsModal = reactive({
  visible: false,
  record: null
});

// 文件编辑器状态
const fileEditor = reactive({
  visible: false,
  path: '',
  name: ''
});

// 图片监视器状态
const imageMonitor = reactive({
  visible: false,
  path: '',
  name: ''
});

// 图片模态框宽度
const imageModalWidth = computed(() => {
  if (window.innerWidth <= 480) {
    return '95%';
  } else if (window.innerWidth <= 768) {
    return '90%';
  } else if (window.innerWidth <= 1024) {
    return 700;
  } else if (window.innerWidth <= 1200) {
    return 900;
  } else {
    return 1000;
  }
});

// 路径片段
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

// 是否在根目录
const isAtDefaultRoot = computed(() => {
  return currentPath.value === '/';
});

// 过滤后的文件列表
const filteredFileList = computed(() => {
  let list = [...fileList.value];
  
  // 排序：文件夹在前，文件在后
  list = list.sort((a, b) => {
    if (a.is_directory && !b.is_directory) {
      return -1;
    }
    if (!a.is_directory && b.is_directory) {
      return 1;
    }
    return a.filename.localeCompare(b.filename);
  });
  
  // 搜索过滤
  if (!searchKeyword.value) {
    return list;
  }
  
  const keyword = searchKeyword.value.toLowerCase();
  return list.filter(file => 
    file.filename.toLowerCase().includes(keyword)
  );
});

// 表格列定义
const columns = computed(() => [
  {
    title: t.value('fileName'),
    dataIndex: 'filename',
    slotName: 'filename'
  },
  {
    title: t.value('permissions'),
    dataIndex: 'permissions',
    width: 120
  },
  {
    title: t.value('user'),
    dataIndex: 'user',
    width: 120
  },
  {
    title: t.value('group'),
    dataIndex: 'group',
    width: 120
  },
  {
    title: t.value('size'),
    dataIndex: 'size',
    slotName: 'size',
    width: 150
  },
  {
    title: t.value('modifiedTime'),
    dataIndex: 'modified_time',
    slotName: 'modified_time',
    width: 200
  },
  {
    title: t.value('actions'),
    slotName: 'operations',
    width: 200
  }
]);

// 关闭抽屉
const handleClose = () => {
  emit('update:visible', false);
};

// 获取选中的主机ID
const getSelectedHostId = () => {
  // 从localStorage获取选中的主机ID
  const hostId = localStorage.getItem('selectedContainerHostId');
  if (hostId) {
    selectedHostId.value = hostId;
  }
  return hostId;
};

// 处理重启功能
const handleRestart = async () => {
  try {
    restartLoading.value = true;
    // 获取主机ID
    const hostId = getSelectedHostId();
    if (!hostId) {
      Message.error(t.value('pleaseSelectHost') || '请选择容器主机');
      return;
    }
    
    // 从当前路径中提取项目名称（假设路径格式为 /path/to/project/docker-compose.yml）
    // 提取倒数第二级目录作为项目名称
    const pathParts = currentPath.value.split('/').filter(part => part !== '');
    let projectName = pathParts.length > 0 ? pathParts[pathParts.length - 1] : 'default';
    
    // 如果当前目录包含docker-compose.yml文件，可以直接使用当前目录名
    const composeFileExists = fileList.value.some(file => 
      file.filename === 'docker-compose.yml' || file.filename === 'docker-compose.yaml'
    );
    
    if (!composeFileExists && pathParts.length > 1) {
      // 如果当前目录没有compose文件，尝试使用父目录名
      projectName = pathParts[pathParts.length - 2];
    }
    
    // 调用重启方法
    await restartComposeProject(hostId, projectName);
    Message.success(t.value('restartSuccess') || '重启成功');
    // 重启成功后自动关闭弹窗
    handleClose();
  } catch (error) {
    console.error('重启失败:', error);
    Message.error(t.value('restartFailed') || '重启失败');
  } finally {
    restartLoading.value = false;
  }
};

// 加载文件列表
const loadFileList = async (path) => {
  loading.value = true;
  try {
    const response = await getFileList({ path });
    fileList.value = response.data || [];
    currentPath.value = path;
  } catch (error) {
    console.error('获取文件列表失败:', error);
    Message.error(t.value('getFileListFailed') + ': ' + (error.message || t.value('unknownError')));
  } finally {
    loading.value = false;
  }
};

// 刷新
const refresh = () => {
  loadFileList(currentPath.value);
};

// 返回上级目录
const goToParentDirectory = () => {
  if (currentPath.value === '/') {
    return;
  }
  
  const paths = currentPath.value.split('/').filter(p => p !== '');
  
  if (paths.length === 0) {
    loadFileList('/');
    return;
  }
  
  paths.pop();
  const parentPath = paths.length > 0 ? '/' + paths.join('/') : '/';
  loadFileList(parentPath);
};

// 返回根目录
const goToRoot = () => {
  loadFileList('/');
};

// 导航到指定路径
const navigateToPath = (index) => {
  const segments = pathSegments.value;
  if (index === -1) {
    loadFileList('/');
  } else {
    const paths = segments.slice(0, index + 1);
    const targetPath = paths[paths.length - 1].path;
    loadFileList(targetPath);
  }
};

// 处理搜索
const handleSearch = () => {
  // 搜索逻辑已在 computed 中处理
};

// 格式化日期
const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleString('zh-CN');
};

// 文件点击
const handleFileClick = (record) => {
  if (record.is_directory) {
    // 如果是目录，进入目录
    const newPath = currentPath.value === '/' 
      ? `/${record.filename}` 
      : `${currentPath.value}/${record.filename}`;
    loadFileList(newPath);
  } else {
    // 如果是文件，根据文件类型打开
    if (isImageFile(record.filename)) {
      // 图片文件，打开图片预览
      handleOpenImage(record);
    } else if (canOpenFile(record.filename)) {
      // 可编辑文件，打开文件编辑器
      handleOpenFile(record);
    } else {
      // 其他文件，提示无法打开
      Message.info(t.value('fileCannotBeOpened') || '此文件类型无法预览，请使用下载功能');
    }
  }
};

// 显示详情
const handleShowDetails = (record) => {
  detailsModal.record = record;
  detailsModal.visible = true;
};

// 下载文件
const handleDownload = async (record) => {
  if (record.is_directory) {
    Message.warning(t.value('folderCannotBeDownloaded'));
    return;
  }
  
  try {
    await downloadFile({
      path: currentPath.value,
      filename: record.filename
    });
    
    Message.success(`${t.value('downloadStarted')}: ${record.filename}`);
  } catch (error) {
    console.error('下载文件失败:', error);
    Message.error(`${t.value('downloadFileFailed')}: ${record.filename}`);
  }
};

// 打开图片
const handleOpenImage = (record) => {
  if (record && !record.is_directory) {
    if (!isImageFile(record.filename)) {
      Message.warning(t.value('fileCannotBeOpenedAsImage'));
      return;
    }
    
    imageMonitor.path = currentPath.value;
    imageMonitor.name = record.filename;
    imageMonitor.visible = true;
  }
};

// 打开文件
const handleOpenFile = (record) => {
  if (record && !record.is_directory) {
    if (!canOpenFile(record.filename)) {
      Message.warning(t.value('fileCannotBeOpened'));
      return;
    }
    
    fileEditor.path = currentPath.value;
    fileEditor.name = record.filename;
    fileEditor.visible = true;
  }
};

// 删除文件
const handleDeleteFile = (record) => {
  Modal.warning({
    title: t.value('confirmDelete'),
    content: t.value('confirmDeleteFile').replace('{filename}', record.filename),
    okText: t.value('confirm'),
    cancelText: t.value('cancel'),
    onOk: async () => {
      try {
        await deleteFile({
          path: currentPath.value,
          filename: record.filename
        });
        Message.success(`${t.value('fileDeleted')}: ${record.filename}`);
        refresh();
      } catch (error) {
        console.error('删除文件失败:', error);
        Message.error(`${t.value('deleteFileFailed')}: ${record.filename}`);
      }
    }
  });
};

// 文件编辑器关闭
const handleFileEditorClose = () => {
  fileEditor.visible = false;
  fileEditor.path = '';
  fileEditor.name = '';
};

// 文件编辑器保存
const handleFileEditorSave = () => {
  Message.success(t.value('fileSaved'));
};

// 文件编辑器切换文件
const handleFileEditorChangeFile = (fileInfo) => {
  fileEditor.path = fileInfo.path;
  fileEditor.name = fileInfo.fileName;
};

// 图片监视器关闭
const handleImageMonitorClose = () => {
  imageMonitor.visible = false;
  imageMonitor.path = '';
  imageMonitor.name = '';
};

// 图片加载完成
const handleImageLoaded = (info) => {
  console.log('图片加载完成:', info);
};

// 监听 visible 变化
watch(() => props.visible, (newVal) => {
  if (newVal) {
    loadFileList(props.initialPath);
  }
});

// 监听 initialPath 变化
watch(() => props.initialPath, (newVal) => {
  if (props.visible && newVal) {
    loadFileList(newVal);
  }
});

// 组件挂载
onMounted(() => {
  // 获取选中的主机ID
  getSelectedHostId();
  
  // 监听容器宿主变化事件
  window.addEventListener('containerHostChanged', (event) => {
    selectedHostId.value = event.detail.hostId;
  });
  
  if (props.visible) {
    loadFileList(props.initialPath);
  }
});
</script>

<style scoped>
.file-manager {
  padding: 16px;
  font-size: 14px;
}

.navigation-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.path-container {
  flex: 1;
  background: var(--color-fill-2);
  border-radius: 4px;
  border: 1px solid var(--color-border);
  position: relative;
  min-height: 36px;
  display: flex;
  align-items: center;
  padding: 0 12px;
}

.path-breadcrumb {
  flex: 1;
}

.action-bar {
  margin: 8px 0 16px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.search-container {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-list-wrapper {
  min-height: 400px;
}

.file-list-container {
  background: var(--color-bg-2);
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  border: 1px solid var(--color-border);
}

.file-item {
  display: flex;
  align-items: center;
}

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

@media (max-width: 768px) {
  .file-manager {
    padding: 8px;
  }
  
  .navigation-bar, .action-bar {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }
  
  .action-bar {
    flex-direction: row;
  }
  
  .path-container {
    min-height: 40px;
    flex-direction: column;
    align-items: stretch;
    padding: 8px 12px;
  }
  
  .search-container {
    margin-left: 0;
    margin-top: 8px;
  }
}
</style>
