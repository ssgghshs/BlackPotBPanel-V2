<template>
  <a-card class="containers-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('images') }}</span>
        <div style="display: flex; gap: 10px;">
            <a-button type="outline" @click="showPullModal">{{ t('pullImage') }}</a-button>
            <a-button type="outline" @click="showImportModal">{{ t('importImage') }}</a-button>
            <a-button type="outline" @click="showBuildModal">{{ t('buildImage') }}</a-button>
            <a-button type="outline" @click="showPruneCacheModal">{{ t('pruneImageCache') }}</a-button>
            <a-button type="outline" @click="showPruneImagesModal">{{ t('pruneImages') }}</a-button>
        </div>
      </div>
    </template>

    <!-- 镜像列表表格 -->
    <a-table 
      :columns="columns" 
      :data="images" 
      :loading="loading" 
      :pagination="pagination"
      @page-change="handlePageChange"
      @page-size-change="handlePageSizeChange"
      :scroll="scroll"
      row-key="id"
    >
      <template #id_short="{ record }">
        <a-tooltip :content="record.id" placement="top">
          <span>{{ record.id_short }}</span>
        </a-tooltip>
      </template>
      <template #tags="{ record }">
        <div v-if="record.tags && record.tags.length > 0">
          <a-tag 
            v-for="(tag, index) in record.tags" 
            :key="index" 
            color="blue"
            style="margin-right: 4px; margin-bottom: 4px"
          >
            {{ tag }}
          </a-tag>
        </div>
        <span v-else>-</span>
      </template>
      <template #isUsed="{ record }">
        <a-tag :color="record.isUsed ? 'green' : 'orange'">
          {{ record.isUsed ? t('yes') : t('no') }}
        </a-tag>
      </template>
      <template #size="{ record }">
        {{ formatSize(record.size) }}
      </template>
      <template #createdAt="{ record }">
        {{ formatDate(record.createdAt) }}
      </template>
      <template #operation="{ record }">
          <a-button type="text" size="small" @click="openImageDetail(record)">{{ t('detail') }}</a-button>
          <a-dropdown>
            <a-button type="text" size="small">
              {{ t('more') }}
              <icon-down />
            </a-button>
            <template #content>
              <a-doption key="export" @click="showExportImageModal(record)">
                <icon-download />
                {{ t('export') }}
              </a-doption>
              <!-- 管理标签选项 -->
              <a-doption key="manageTags" @click="showManageTagsModal(record)">
                <icon-tag />
                {{ t('tags') }}
              </a-doption>
              <a-doption key="delete" :disabled="record.isUsed" @click="showDeleteImageModal(record)" danger>
                <icon-delete />
                {{ t('delete') }}
              </a-doption>
            </template>
          </a-dropdown>
        </template>
    </a-table>

    <!-- 镜像详情抽屉 -->
    <images-inspect 
      :visible="isImageDetailVisible"
      :image-info="selectedImage"
      @update:visible="updateImageDetailVisible"
      @close="handleImageDetailClose"
    />
    
    <!-- 删除镜像确认对话框 -->
    <a-modal 
      v-model:visible="deleteImageModalVisible" 
      :title="t('confirmDelete')" 
      @ok="confirmDeleteImage" 
      @cancel="cancelDeleteImage"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
    >
      <p>{{ t('confirmDeleteImage')}}</p>
      <!-- 只对有多个tag的镜像显示强制删除选项 -->
      <div v-if="containerToDelete.tags && containerToDelete.tags.length > 1" style="margin-top: 16px;">
        <a-checkbox v-model="forceDelete">
          {{ t('forceDeleteImage')}}
        </a-checkbox>
      </div>
    </a-modal>
    
    <!-- 构建镜像对话框 -->
    <a-modal 
      v-model:visible="buildModalVisible" 
      :title="t('buildImage')" 
      @ok="confirmBuildImage" 
      @cancel="cancelBuildImage"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
    >
      <a-form layout="vertical" :model="buildForm">
        <a-form-item :label="t('buildPath')">
          <a-input 
            v-model="buildForm.path" 
            :placeholder="t('inputBuildPath')"
          >
            <template #suffix>
              <a-button 
                type="text" 
                size="small" 
                style="margin-right: -10px;"
                @click="showBuildFileManager"
              >
                <folder-outlined style="font-size: 16px;" />
              </a-button>
            </template>
          </a-input>
        </a-form-item>
        <a-form-item :label="t('imageTag')">
          <a-input 
            v-model="buildForm.tag" 
            :placeholder="t('inputImageTag')"
            allow-clear
          />
        </a-form-item>
      </a-form>
    </a-modal>
    
    <!-- 导入镜像对话框 -->
    <a-modal 
      v-model:visible="importModalVisible" 
      :title="t('importImage')" 
      @ok="confirmImportImage" 
      @cancel="cancelImportImage"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
    >
      <a-form layout="vertical" :model="importForm">
        <a-form-item :label="t('filePath')">
          <a-input 
            v-model="importForm.filePath" 
            :placeholder="t('inputFilePath')"
          >
            <template #suffix>
              <a-button 
                type="text" 
                size="small" 
                style="margin-right: -10px;" 
                @click="showFileManager"
              >
                <folder-outlined style="font-size: 16px;" />
              </a-button>
            </template>
          </a-input>
        </a-form-item>
      </a-form>
    </a-modal>
    
    <!-- 日志黑框对话框 -->
    <a-modal 
      v-model:visible="logModalVisible" 
      :title="logModalTitle" 
      @cancel="closeLogModal"
      @close="closeLogModal"
      :mask-closable="false"
      :width="1000"
    >
      <div class="log-container" ref="logContainerRef">
        <pre class="log-content">{{ logContent }}</pre>
      </div>
      <template #footer>
        <a-space>
          <a-button v-if="currentOperation === 'pull'" type="primary" status="danger" @click="cancelPullImageOperation">
            {{ t('cancelPullImage') }}
          </a-button>
          <a-button @click="closeLogModal">{{ t('close') }}</a-button>
        </a-space>
      </template>
    </a-modal>
    
    <!-- 文件管理器组件 -->
    <MiniFileManager
      :visible="fileManagerVisible"
      :initial-path="'/'"
      :select-mode="currentFileManagerType === 'export' ? 'directory' : 'file'"
      @update:visible="fileManagerVisible = $event"
      @select="handleFileSelect"
    />
    
    <!-- 导出镜像对话框 -->
    <a-modal 
      v-model:visible="exportModalVisible" 
      :title="t('exportImage')" 
      @ok="confirmExportImage" 
      @cancel="cancelExportImage"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
    >
      <a-form layout="vertical" :model="exportForm">
        <a-form-item :label="t('imageTag')">
          <a-select 
            v-model="exportForm.tag" 
            :placeholder="t('selectImageTag')"
            allow-clear
          >
            <a-option 
              v-for="(tag, index) in selectedImageToExport.tags || []" 
              :key="index" 
              :value="tag"
            >
              {{ tag }}
            </a-option>
          </a-select>
        </a-form-item>
        
        <a-form-item :label="t('outputPath')">
          <a-input 
            v-model="exportForm.output_path" 
            :placeholder="t('inputOutputPath')"
          >
            <template #suffix>
              <a-button 
                type="text" 
                size="small" 
                style="margin-right: -10px;" 
                @click="showExportFileManager"
              >
                <folder-outlined style="font-size: 16px;" />
              </a-button>
            </template>
          </a-input>
        </a-form-item>
        
        <a-form-item>
          <a-checkbox v-model="exportForm.compress">
            {{ t('compressImage') }}
          </a-checkbox>
        </a-form-item>
      </a-form>
    </a-modal>
    
    <!-- 拉取镜像对话框 -->
    <a-modal 
      v-model:visible="pullModalVisible" 
      :title="t('pullImage')" 
      @ok="confirmPullImage" 
      @cancel="cancelPullImageModal"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
    >
      <a-form layout="inline" :model="pullForm" style="width: 100%;">
        <a-form-item :label="t('imageName')" :style="{ flex: 1 }">
          <a-input 
            v-model="pullForm.name" 
            :placeholder="t('inputImageName')"
            allow-clear
          />
        </a-form-item>
        <a-form-item :label="t('imageTag')" :style="{ flex: 1 }">
          <a-input 
            v-model="pullForm.tag" 
            :placeholder="t('inputImageTag')"
            allow-clear
          />
        </a-form-item>
      </a-form>
    </a-modal>
  
    <!-- 清理镜像确认对话框 -->
    <a-modal 
      v-model:visible="pruneImagesModalVisible" 
      :title="t('pruneImages')" 
      @ok="confirmPruneImages" 
      @cancel="cancelPruneImages"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
    >
      <p>{{ t('confirmPruneImages')}}</p>
      <a-checkbox v-model="onlyPruneDangling">
        {{ t('onlyPruneDanglingImages') }}
      </a-checkbox>
    </a-modal>
    
    <!-- 清理镜像确认对话框 -->
    <a-modal 
      v-model:visible="pruneCacheModalVisible" 
      :title="t('pruneImageCache')" 
      @ok="confirmPruneImageCache" 
      @cancel="cancelPruneImageCache"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
    >
      <p>{{ t('confirmPruneImageCache')}}</p>
      <a-checkbox v-model="clearAllCache">
        {{ t('clearAllImageCache') }}
      </a-checkbox>
    </a-modal>
    
    <!-- 标签管理对话框 -->
    <a-modal 
      v-model:visible="manageTagsModalVisible" 
      :title="t('tags')" 
      @ok="confirmManageTags" 
      @cancel="cancelManageTags"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
    >
      <a-form layout="vertical" :model="tagsForm" :rules="tagsRules" ref="tagsFormRef">
        <a-form-item :label="t('tags')" field="tags">
          <a-input-tag 
            v-model="tagsForm.tags" 
            allow-clear
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </a-card>
</template>

<script setup>
import { reactive, ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { t } from '../../utils/locale';
import { getImages, deleteImage, importImage, exportImage, pruneImages, pullImage, cancelPullImage, buildImage, getOperationLog, pruneImagesCache, manageImageTags } from '../../api/container';
import { Message } from '@arco-design/web-vue';
import { Modal } from '@arco-design/web-vue';
import { Table as ATable, Tag as ATag, Tooltip as ATooltip, Button as AButton, Dropdown as ADropdown, Checkbox as ACheckbox } from '@arco-design/web-vue';
import { IconDown, IconDelete, IconDownload, IconTag } from '@arco-design/web-vue/es/icon';
import { FolderOutlined } from '@ant-design/icons-vue';
import ImagesInspect from '../../components/container/ImagesInspect.vue';
import MiniFileManager from '../../components/file/MiniFileManager.vue';

// 响应式数据
const images = ref([]);
const loading = ref(false);
const selectedHostId = ref(null);
const isImageDetailVisible = ref(false);
const selectedImage = ref({});
const deleteImageModalVisible = ref(false);
const containerToDelete = ref({});
const forceDelete = ref(false);
// 导入镜像相关状态
const importModalVisible = ref(false);
const logModalVisible = ref(false);
const logModalTitle = ref(t.value('importLog'));
const currentOperation = ref('');
// 将导入路径直接存储在importForm对象中，确保表单绑定正常工作
const importForm = reactive({
  filePath: ''
});
// 保留importFilePath作为计算属性，确保向后兼容
const importFilePath = computed({
  get: () => importForm.filePath,
  set: (value) => {
    importForm.filePath = value;
    console.log('通过importFilePath设置的值:', value, 'importForm.filePath:', importForm.filePath);
  }
});
// 导出镜像相关状态
const exportModalVisible = ref(false);
const selectedImageToExport = ref({});
const exportForm = reactive({
  output_path: '',
  tag: '',
  compress: true
});

// 标签管理相关状态
const manageTagsModalVisible = ref(false);
const selectedImageForTags = ref({});
const tagsFormRef = ref(null);
const tagsForm = reactive({
  tags: []
});
const tagsRules = {
  tags: [
    { 
      required: true, 
      message: t.value('tagsRequired'), 
      type: 'array',
      min: 1,
      trigger: 'change'
    }
  ]
};
const operationId = ref('');
const logContent = ref('');
const logTimer = ref(null);
const logContainerRef = ref(null);
const fileManagerVisible = ref(false);
const currentFileManagerType = ref('import'); // 添加响应式变量
const pruneImagesModalVisible = ref(false);
const onlyPruneDangling = ref(true);
const pruneCacheModalVisible = ref(false);
const clearAllCache = ref(false);
const pullModalVisible = ref(false);
const pullForm = reactive({
  name: '',
  tag: ''
});
// 构建镜像相关状态
const buildModalVisible = ref(false);
const buildForm = reactive({
  path: '',
  tag: ''
});
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showTotal: true,
  showJumper: true,
  pageSizeOptions: [10, 20, 50, 100],
  showPageSize: true
});

const scrollLogToBottom = () => {
  const el = logContainerRef.value;
  if (!el) return;
  el.scrollTop = el.scrollHeight;
};

watch(logContent, async () => {
  await nextTick();
  scrollLogToBottom();
});

watch(logModalVisible, async (visible) => {
  if (visible) {
    await nextTick();
    scrollLogToBottom();
  }
});

// 表格滚动配置
const scroll = {
  x: 1300,
  y: 600
};

// 表格列定义
const columns = computed(() => [
  {
    title: t.value('id'),
    dataIndex: 'id_short',
    slotName: 'id_short',
    width: 120
  },
  {
    title: t.value('isUsed'),
    dataIndex: 'isUsed',
    slotName: 'isUsed',
    width: 90
  },
  {
    title: t.value('tags'),
    dataIndex: 'tags',
    slotName: 'tags',
    width: 350
  },
  {
    title: t.value('size'),
    dataIndex: 'size',
    slotName: 'size',
    width: 120
  },
  {    
    title: t.value('createdAt'),    
    dataIndex: 'createdAt',    
    slotName: 'createdAt',    
    width: 130  
  },  
  {    
    title: t.value('action'),    
    dataIndex: 'operation',    
    slotName: 'operation',    
    width: 130,    
    fixed: 'right'  
  }
]);

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '';
  
  try {
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  } catch (error) {
    console.error('日期格式化错误:', error);
    return dateString; // 发生错误时返回原始字符串
  }
};

// 格式化大小
const formatSize = (bytes) => {
  if (!bytes) return '0 B';
  
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = bytes;
  let unitIndex = 0;
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  
  return `${size.toFixed(2)} ${units[unitIndex]}`;
};

// 获取镜像列表
const fetchImages = async (nodeId, page = 1) => {
  if (!nodeId) return;
  
  try {
    loading.value = true;
    console.log('开始请求镜像列表，节点ID:', nodeId);
    const response = await getImages(nodeId, {
      page: page,
      page_size: pagination.pageSize
    });
    
    console.log('获取到镜像列表响应:', response);
    
    // 调整响应结构处理，适配不同可能的后端返回格式
    if (response && response.items && Array.isArray(response.items)) {
      // 后端直接返回items和total的情况
      images.value = response.items;
      pagination.total = response.total || response.items.length;
    } else if (response && response.data && response.data.items && Array.isArray(response.data.items)) {
      // 后端返回嵌套结构的情况
      images.value = response.data.items;
      pagination.total = response.data.total || response.data.items.length;
    } else {
      // 未知格式，尝试作为直接数据处理
      console.warn('响应格式不符合预期，尝试直接处理:', response);
      images.value = Array.isArray(response) ? response : [];
      pagination.total = images.value.length;
    }
    
    console.log('处理后的镜像数据:', images.value);
  } catch (error) {
    console.error('获取镜像列表失败:', error);
    Message.error(t.value('getImagesFailed'));
    images.value = [];
    pagination.total = 0;
  } finally {
    loading.value = false;
  }
};

// 处理分页变化
const handlePageChange = (page) => {
  pagination.current = page;
  fetchImages(selectedHostId.value, page);
};

// 处理分页大小变化
const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize;
  pagination.current = 1; // 重置到第一页
  fetchImages(selectedHostId.value, 1);
};

// 处理容器宿主变化事件
const handleContainerHostChange = (event) => {
  selectedHostId.value = event.detail.hostId;
  pagination.current = 1;
  fetchImages(selectedHostId.value, 1);
};

// 组件挂载时
onMounted(() => {
  // 从localStorage获取已保存的宿主ID
  const savedHostId = localStorage.getItem('selectedContainerHostId');
  if (savedHostId) {
    selectedHostId.value = savedHostId;
    fetchImages(savedHostId, 1);
  }
  
  // 监听宿主变化事件
  window.addEventListener('containerHostChanged', handleContainerHostChange);
});

// 打开镜像详情
const openImageDetail = (image) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  selectedImage.value = image;
  isImageDetailVisible.value = true;
};

// 更新镜像详情抽屉可见性
const updateImageDetailVisible = (value) => {
  isImageDetailVisible.value = value;
};

// 处理镜像详情抽屉关闭
const handleImageDetailClose = () => {
  isImageDetailVisible.value = false;
  selectedImage.value = {};
};

// 显示删除镜像确认对话框
const showDeleteImageModal = (image) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  if (image.isUsed) {
    Message.warning(t.value('imageInUse'));
    return;
  }
  
  containerToDelete.value = image;
  // 对于有多个tag的镜像自动勾选强制删除选项
  forceDelete.value = image.tags && image.tags.length > 1;
  deleteImageModalVisible.value = true;
};

// 取消删除镜像
const cancelDeleteImage = () => {
  deleteImageModalVisible.value = false;
  containerToDelete.value = {};
  forceDelete.value = false;
};

// 显示导入镜像对话框
const showImportModal = () => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  importForm.filePath = '';
  importModalVisible.value = true;
};

// 取消导入镜像
const cancelImportImage = () => {
  importModalVisible.value = false;
  importForm.filePath = '';
};

// 显示导入文件管理器
const showFileManager = () => {
  fileManagerVisible.value = true;
  // 标记当前是为导入功能打开的文件管理器
  currentFileManagerType.value = 'import';
};

// 显示导出文件管理器
const showExportFileManager = () => {
  fileManagerVisible.value = true;
  // 标记当前是为导出功能打开的文件管理器
  currentFileManagerType.value = 'export';
};

// 显示构建镜像文件管理器
const showBuildFileManager = () => {
  fileManagerVisible.value = true;
  // 标记当前是为构建功能打开的文件管理器
  currentFileManagerType.value = 'build';
  // 强制刷新MiniFileManager以确保选择模式正确
  setTimeout(() => {
    // 通过修改visible状态强制组件重新初始化
    const tempVisible = fileManagerVisible.value;
    fileManagerVisible.value = false;
    setTimeout(() => {
      fileManagerVisible.value = tempVisible;
    }, 0);
  }, 0);
};

// 处理文件选择
const handleFileSelect = (fileInfo) => {
  console.log('接收到文件选择信息:', fileInfo);
  if (fileInfo && fileInfo.path) {
    let fullPath = '';
    
    // 对于导出模式（目录选择），直接使用path
    if (currentFileManagerType.value === 'export') {
      // 当选择目录时，直接使用fileInfo.path作为完整路径
      fullPath = fileInfo.path;
    } else if (fileInfo.name) {
      // 对于导入模式和构建模式（文件选择），使用完整路径
      fullPath = fileInfo.path.endsWith('/') 
        ? `${fileInfo.path}${fileInfo.name}` 
        : `${fileInfo.path}/${fileInfo.name}`;
    } else if (fileInfo.filename) {
      // 兼容MiniFileManager中可能使用filename属性的情况
      fullPath = fileInfo.path.endsWith('/') 
        ? `${fileInfo.path}${fileInfo.filename}` 
        : `${fileInfo.path}/${fileInfo.filename}`;
    } else {
      // 其他情况，使用路径
      fullPath = fileInfo.path;
    }
    
    console.log('准备设置的完整路径:', fullPath);
    
    // 根据当前文件管理器类型设置不同的表单字段
    if (currentFileManagerType.value === 'export') {
      exportForm.output_path = fullPath;
      console.log('设置导出路径:', exportForm.output_path);
    } else if (currentFileManagerType.value === 'build') {
      // 设置构建路径
      buildForm.path = fullPath;
      console.log('设置构建路径:', buildForm.path);
    } else {
      // 默认设置导入路径
      importForm.filePath = fullPath;
      console.log('设置导入路径:', importForm.filePath);
    }
  } else {
    console.error('接收到的文件信息不完整:', fileInfo);
  }
};

// 显示导出镜像对话框
const showExportImageModal = (image) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  selectedImageToExport.value = image;
  // 如果镜像有标签，默认选择第一个标签
  if (image.tags && image.tags.length > 0) {
    exportForm.tag = image.tags[0];
  } else {
    exportForm.tag = '';
  }
  // 重置其他表单字段
  exportForm.output_path = '';
  exportForm.compress = false;
  
  exportModalVisible.value = true;
};

// 显示标签管理对话框
const showManageTagsModal = (image) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  selectedImageForTags.value = image;
  // 复制当前镜像的标签到表单中
  tagsForm.tags = [...(image.tags || [])];
  manageTagsModalVisible.value = true;
};

// 取消管理标签
const cancelManageTags = () => {
  // 清除表单验证状态
  if (tagsFormRef.value) {
    tagsFormRef.value.clearValidate();
  }
  manageTagsModalVisible.value = false;
  selectedImageForTags.value = {};
  tagsForm.tags = [];
};

// 确认管理标签
const confirmManageTags = async () => {
  if (!tagsFormRef.value) return;
  
  // 先进行表单验证
  const errors = await tagsFormRef.value.validate().catch(error => {
    console.log('标签表单验证失败:', error);
    return false;
  });
  
  // 如果验证失败，则不继续执行
  if (errors === false || (errors && Object.keys(errors).length > 0)) {
    // 清除验证状态，避免再次打开对话框时显示旧的验证提示
    tagsFormRef.value.clearValidate();
    return;
  }
  
  try {
    loading.value = true;
    
    // 调用管理标签API
    await manageImageTags(selectedHostId.value, selectedImageForTags.value.id, {
      tags: tagsForm.tags
    });
    
    Message.success(t.value('manageTagsSuccess'));
    
    // 清除表单验证状态
    if (tagsFormRef.value) {
      tagsFormRef.value.clearValidate();
    }
    
    // 关闭对话框
    manageTagsModalVisible.value = false;
    
    // 刷新镜像列表
    setTimeout(() => {
      fetchImages(selectedHostId.value, pagination.current);
    }, 500);
  } catch (error) {
    console.error('管理标签失败:', error);
    const errorMsg = error.response?.data?.detail || error.message || (t.value('manageTagsFailed') || '标签管理失败');
    Message.error(errorMsg);
  } finally {
    loading.value = false;
  }
};

// 取消导出镜像
const cancelExportImage = () => {
  exportModalVisible.value = false;
  selectedImageToExport.value = {};
};

// 确认导出镜像
const confirmExportImage = async () => {
  if (!exportForm.tag) {
    Message.warning(t.value('selectImageTag'));
    return;
  }
  
  if (!exportForm.output_path.trim()) {
    Message.warning(t.value('inputOutputPath'));
    return;
  }
  
  try {
    loading.value = true;
    
    // 显示导出开始提示
    Message.info(t.value('exportImageStarted'));
    
    // 调用导出镜像API
    const response = await exportImage(selectedHostId.value, exportForm);
    
    console.log('导出镜像响应:', response);
    
    // 关闭导出对话框
    exportModalVisible.value = false;
    
    // 从响应中获取更多信息用于显示
    const outputFile = response.output_file_path || response.data?.output_file_path;
    const successMessage = outputFile 
      ? `${t.value('exportImageSuccess')}: ${outputFile}`
      : t.value('exportImageSuccess');
    
    // 显示成功消息
    Message.success(successMessage);
  } catch (error) {
    console.error('导出镜像失败:', error);
    // 更详细的错误处理
    let errorMsg = '';
    if (error.response) {
      // 服务器返回错误
      if (error.response.data?.detail) {
        errorMsg = error.response.data.detail;
      } else if (error.response.status === 404) {
        errorMsg = t.value('imageNotFound');
      } else if (error.response.status === 403) {
        errorMsg = t.value('noPermission');
      } else if (error.response.status === 400) {
        errorMsg = t.value('invalidParameter');
      } else {
        errorMsg = t.value('exportImageFailed');
      }
    } else if (error.request) {
      // 请求发出但未收到响应
      errorMsg = t.value('networkError');
    } else {
      // 其他错误
      errorMsg = error.message || t.value('exportImageFailed');
    }
    Message.error(errorMsg);
  } finally {
    loading.value = false;
  }
};

// 确认导入镜像
const confirmImportImage = async () => {
  if (!importForm.filePath.trim()) {
    Message.warning(t.value('inputFilePath'));
    return;
  }
  
  try {
    // 调用导入镜像API - 使用正确的字段名image_path
    const response = await importImage(selectedHostId.value, { image_path: importForm.filePath });
    operationId.value = response.operation_id || response.data?.operation_id;
    logContent.value = '';
    
    // 关闭导入对话框，打开日志对话框
    importModalVisible.value = false;
    logModalTitle.value = t.value('importLog');
    currentOperation.value = 'import';
    logModalVisible.value = true;
    
    // 开始定期获取日志
    startLogTimer();
    
    Message.success(t.value('importImageStarted'));
  } catch (error) {
    console.error('导入镜像失败:', error);
    const errorMsg = error.response?.data?.detail || error.message || t.value('importImageFailed');
    Message.error(errorMsg);
  }
};

const showPullModal = () => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  pullForm.name = '';
  pullForm.tag = '';
  pullModalVisible.value = true;
};

const showBuildModal = () => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  buildForm.path = '';
  buildForm.tag = '';
  buildModalVisible.value = true;
};

const cancelBuildImage = () => {
  buildModalVisible.value = false;
  buildForm.path = '';
  buildForm.tag = '';
};

const confirmBuildImage = async () => {
  if (!buildForm.path.trim()) {
    Message.warning(t.value('inputBuildPath'));
    return;
  }
  try {
    const payload = { path: buildForm.path, tag: buildForm.tag };
    const response = await buildImage(selectedHostId.value, payload);
    operationId.value = response.operation_id || response.data?.operation_id;
    logContent.value = '';
    buildModalVisible.value = false;
    logModalTitle.value = t.value('buildLog');
    currentOperation.value = 'build';
    logModalVisible.value = true;
    startLogTimer();
    Message.success(t.value('buildImageStarted'));
  } catch (error) {
    console.error('构建镜像失败:', error);
    const errorMsg = error.response?.data?.detail || error.message || t.value('buildImageFailed');
    Message.error(errorMsg);
  }
};

const cancelPullImageModal = () => {
  pullModalVisible.value = false;
  pullForm.name = '';
  pullForm.tag = '';
};

const confirmPullImage = async () => {
  if (!pullForm.name.trim()) {
    Message.warning(t.value('inputImageName'));
    return;
  }
  try {
    const payload = { name: pullForm.name, tag: pullForm.tag };
    const response = await pullImage(selectedHostId.value, payload);
    operationId.value = response.operation_id || response.data?.operation_id;
    logContent.value = '';
    pullModalVisible.value = false;
    logModalTitle.value = t.value('pullLog');
    currentOperation.value = 'pull';
    logModalVisible.value = true;
    startLogTimer();
    Message.success(t.value('pullImageStarted'));
  } catch (error) {
    console.error('拉取镜像失败:', error);
    const errorMsg = error.response?.data?.detail || error.message || t.value('pullImageFailed');
    Message.error(errorMsg);
  }
};

// 开始定期获取日志
const startLogTimer = () => {
  // 清除可能存在的旧定时器
  if (logTimer.value) {
    clearInterval(logTimer.value);
  }
  
  // 立即获取一次日志
  fetchLog();
  
  // 设置定时器，每3秒获取一次日志
  logTimer.value = setInterval(fetchLog, 3000);
};

// 获取日志内容
const fetchLog = async () => {
  if (!operationId.value) return;
  
  try {
    const response = await getOperationLog(operationId.value);
    console.log('日志API响应:', response);
    // 尝试从不同可能的响应格式中获取日志内容
    logContent.value = 
      response.log_content || // 直接字段
      response.data?.log_content || // 嵌套data对象
      response.log || // 保持兼容性
      response.data?.log || 
      '';
    console.log('设置的日志内容:', logContent.value);
    
    // 检查是否完成，如果完成则自动关闭对话框并刷新镜像列表
    const isComplete = response.is_complete || response.data?.is_complete;
    if (isComplete && logModalVisible.value) {
      console.log('操作已完成，自动关闭日志对话框并刷新镜像列表');
      // 调用closeLogModal函数，使用延迟关闭功能
      closeLogModal();
      // 延迟刷新镜像列表，确保操作完全完成
      setTimeout(() => {
        fetchImages(selectedHostId.value, pagination.current);
        if (currentOperation.value === 'pull') {
          Message.success(t.value('pullImageSuccess'));
        } else if (currentOperation.value === 'build') {
          Message.success(t.value('buildImageSuccess'));
        } else if (currentOperation.value === 'pruneCache') {
          Message.success(t.value('pruneImageCacheSuccess'));
        } else {
          Message.success(t.value('importImageSuccess'));
        }
      }, 500);
    }
  } catch (error) {
    console.error('获取日志失败:', error);
  }
};

// 关闭日志对话框
const closeLogModal = () => {
  // 清除定时器（立即执行，避免内存泄漏）
  if (logTimer.value) {
    clearInterval(logTimer.value);
    logTimer.value = null;
  }
  
  // 添加3秒延迟后关闭对话框
  setTimeout(() => {
    logModalVisible.value = false;
  }, 3000);
};

// 取消拉取镜像
const cancelPullImageOperation = () => {
  Modal.confirm({
    title: t.value('confirmCancelPull'),
    content: t.value('confirmCancelPullContent'),
    okText: t.value('confirm'),
    cancelText: t.value('cancel'),
    okType: 'danger',
    async onOk() {
      try {
        await cancelPullImage(selectedHostId.value, { operation_id: operationId.value });
        Message.success(t.value('cancelPullImageSuccess'));
        if (logTimer.value) {
          clearInterval(logTimer.value);
          logTimer.value = null;
        }
        logModalVisible.value = false;
      } catch (error) {
        const errMsg = error?.response?.data?.detail || error.message || t.value('cancelPullImageFailed');
        Message.error(errMsg);
      }
    }
  });
};

// 确认删除镜像
const confirmDeleteImage = async () => {
  try {
    loading.value = true;
    // 调用删除镜像API，传递用户选择的force值
    await deleteImage(selectedHostId.value, containerToDelete.value.id, { force: forceDelete.value });
    Message.success(t.value('deleteImageSuccess'));
    // 使用setTimeout延迟重新获取镜像列表
    setTimeout(() => {
      fetchImages(selectedHostId.value);
    }, 500);
  } catch (error) {
    console.error('删除镜像失败:', error);
    // 处理API返回的错误信息
    const errorMsg = error.response?.data?.detail || error.message || t.value('deleteImageFailed');
    Message.error(errorMsg);
  } finally {
    loading.value = false;
    deleteImageModalVisible.value = false;
    containerToDelete.value = {};
    forceDelete.value = false;
  }
};

// 组件卸载时
onUnmounted(() => {
  window.removeEventListener('containerHostChanged', handleContainerHostChange);
  // 确保组件卸载时清除日志定时器
  if (logTimer.value) {
    clearInterval(logTimer.value);
    logTimer.value = null;
  }
  
  // 重置文件管理器类型
  currentFileManagerType.value = 'import';
});

  // 显示清除镜像缓存对话框
  const showPruneCacheModal = () => {
    if (!selectedHostId.value) {
      Message.warning(t.value('pleaseSelectHost'));
      return;
    }
    clearAllCache.value = false; // 默认不清除所有缓存
    pruneCacheModalVisible.value = true;
  };
  
  // 取消清除镜像缓存
  const cancelPruneImageCache = () => {
    pruneCacheModalVisible.value = false;
    clearAllCache.value = false; // 重置选项
  };
  
  // 确认清除镜像缓存
  const confirmPruneImageCache = async () => {
    try {
      // 构建请求参数
      const pruneRequest = { all: clearAllCache.value };
      
      // 调用清除镜像缓存API
      const response = await pruneImagesCache(selectedHostId.value, pruneRequest);
      
      console.log('清除镜像缓存响应:', response);
      
      // 获取操作ID并显示日志对话框
      operationId.value = response.operation_id || response.data?.operation_id;
      logContent.value = '';
      
      // 关闭缓存清除对话框，打开日志对话框
      pruneCacheModalVisible.value = false;
      logModalTitle.value = t.value('pruneImageCacheLog');
      currentOperation.value = 'pruneCache';
      logModalVisible.value = true;
      
      // 开始定期获取日志
      startLogTimer();
      
      Message.success(t.value('pruneImageCacheStarted'));
    } catch (error) {
      console.error('清除镜像缓存失败:', error);
      const errorMsg = error.response?.data?.detail || error.message || t.value('pruneImageCacheFailed');
      Message.error(errorMsg);
    } finally {
      clearAllCache.value = false; // 重置选项
    }
  };

  // 显示清理镜像对话框
  const showPruneImagesModal = () => {
    if (!selectedHostId.value) {
      Message.warning(t.value('pleaseSelectHost'));
      return;
    }
    onlyPruneDangling.value = true; // 默认只清理悬空镜像
    pruneImagesModalVisible.value = true;
  };
  
  // 取消清理镜像
  const cancelPruneImages = () => {
    pruneImagesModalVisible.value = false;
    onlyPruneDangling.value = true; // 重置选项
  };
  
  // 确认清理镜像
  const confirmPruneImages = async () => {
    try {
      loading.value = true;
      
      // 构建请求参数 - 使用dangling参数而不是filters
      const pruneRequest = { dangling: onlyPruneDangling.value };
      
      // 调用清理镜像API
      const response = await pruneImages(selectedHostId.value, pruneRequest);
      
      console.log('清理镜像响应:', response);
      
      // 关闭对话框
      pruneImagesModalVisible.value = false;
      
      // 从响应中获取更多信息用于显示
      const deletedImages = response.deleted_images || response.data?.deleted_images || [];
      const spaceReclaimed = response.space_reclaimed || response.data?.space_reclaimed || 0;
      
      // 显示成功消息
      let successMessage = t.value('pruneImagesSuccess');
      if (deletedImages.length > 0) {
        successMessage += ` ${t.value('deletedCount')}: ${deletedImages.length}`;
      }
      if (spaceReclaimed > 0) {
        successMessage += `, ${t.value('spaceReclaimed')}: ${formatSize(spaceReclaimed)}`;
      }
      
      Message.success(successMessage);
      
      // 刷新镜像列表
      fetchImages(selectedHostId.value, pagination.current);
    } catch (error) {
      console.error('清理镜像失败:', error);
      // 更详细的错误处理
      let errorMsg = '';
      if (error.response) {
        // 服务器返回错误
        if (error.response.data?.detail) {
          errorMsg = error.response.data.detail;
        } else if (error.response.status === 403) {
          errorMsg = t.value('noPermission');
        } else {
          errorMsg = t.value('pruneImagesFailed');
        }
      } else {
        // 其他错误
        errorMsg = error.message || t.value('pruneImagesFailed');
      }
      Message.error(errorMsg);
    } finally {
      loading.value = false;
      onlyPruneDangling.value = true; // 重置选项
    }
  };
</script>

<style>
/* 日志区域字体样式 */
.log-content {
  font-family: Consolas, "Courier New", "SFMono-Regular", "Menlo", "Monaco", "Roboto Mono", "Ubuntu Mono", monospace !important;
}
</style>

<style scoped>
.containers-container {
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 15px;
  font-size: 1.3em;
  padding: 20px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.title {
  margin: 0;
  padding: 0;
}

.desc {
  margin-top: 4px;
  color: #8c8c8c;
  font-size: 12px;
}

.log-container {
  height: 500px;
  overflow: auto;
  background-color: #000000;
  border-radius: 4px;
  position: relative;
}

.log-content {
  padding: 12px;
  margin: 0;
  background-color: #000000;
  color: #ffffff;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
