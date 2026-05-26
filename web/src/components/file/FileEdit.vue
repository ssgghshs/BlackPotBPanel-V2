<template>
  <a-modal
    :visible="visible"
    :title="null"
    :width="isFullscreen ? '100%' : '65%'"
    :footer="false"
    @cancel="closeEditor"
    @close="closeEditor"
    :mask-closable="false"
  >
    <div class="file-editor" :class="{ 'fullscreen': isFullscreen }">
      <!-- 标题栏 -->
      <div class="editor-title-bar">
        <div class="title-left">
          <span class="editor-title">{{ t('editFile') }}</span>
          <!-- 将文件路径显示移到这里 -->
          <div v-if="activeFile" class="file-path-container">
            <icon-home class="path-home-icon" />
            <span class="file-path">{{ getFullFilePath(activeFile) }}</span>
          </div>
        </div>
        <div class="title-right">
          <span v-if="activeFile && activeFile.isModified" class="modified-indicator">{{ t('modified') }}</span>
          <span class="char-count">{{ t('characters') }}: {{ activeFile ? activeFile.characterCount || 0 : 0 }}</span>
          <span class="line-count">{{ t('lines') }}: {{ activeFile ? activeFile.lineCount || 1 : 1 }}</span>
          <span class="current-line-info">{{ t('currentLine') }}: {{ activeFile ? activeFile.currentLine || 1 : 1 }}</span>
          <!-- 将四个按钮移到这里并靠右对齐 -->
          <div class="editor-actions">
            <a-button 
              type="outline" 
              size="small" 
              @click="() => goToParentDirectory(activeFile)" 
              :disabled="!activeFile || isRootPath(activeFile ? activeFile.filePath : '')"
            >
              <icon-left />
              {{ t('goToParentDirectory') }}
            </a-button>
            <a-button 
              type="primary" 
              size="small" 
              @click="() => saveFile(activeFile)"
              :loading="activeFile ? activeFile.saving : false"
              :disabled="!activeFile || !activeFile.isModified"
            >
              <icon-save />
              {{ t('save') }}
            </a-button>
            <a-button 
              size="small" 
              @click="toggleFullscreen"
            >
              <icon-fullscreen v-if="!isFullscreen" />
              <icon-fullscreen-exit v-else />
              {{ isFullscreen ? t('exitFullscreen') : t('fullscreen') }}
            </a-button>
            <a-button 
              size="small" 
              @click="closeEditor"
            >
              <icon-close />
              {{ t('close') }}
            </a-button>
          </div>
        </div>
      </div>

      <!-- 当有打开的文件时显示编辑器 -->
      <div v-if="openFiles.length > 0" class="editor-main">
        <!-- 侧边文件列表 -->
        <div ref="sidebarRef" class="sidebar" :class="{ 'sidebar-collapsed': !showSidebar }">
          <div class="sidebar-header">
            <span class="sidebar-title" v-show="showSidebar">{{ t('fileList') }}</span>
            <a-button size="small" @click="() => refreshFileList(activeFile)" :disabled="!activeFile" v-show="showSidebar">
              <icon-refresh />
            </a-button>
          </div>
          <!-- 添加滚动容器 -->
          <div class="sidebar-content" v-show="showSidebar">
            <!-- 使用 a-tree 组件展示文件树 -->
            <a-tree
              :key="treeDataKey"
              ref="treeRef"
              class="file-tree"
              :data="getFileTreeData()"
              :field-names="{ key: 'key', title: 'title', children: 'children' }"
              :show-line="false"
              :default-expand-all="false"
              v-model:expanded-keys="expandedKeys"
              :load-more="loadMore"
              @select="handleTreeSelect"
            >
              <template #title="nodeData">
                <div class="tree-node">
                  <component 
                    :is="getFileIconComponent(nodeData.filename, nodeData.is_directory)" 
                    class="file-icon"
                    :style="{ color: getFileIconColor(nodeData.filename, nodeData.is_directory) }" 
                  />
                  <span class="file-item-name" :title="nodeData.title || nodeData.filename">{{ nodeData.title || nodeData.filename }}</span>
                </div>
              </template>
            </a-tree>
          </div>
        </div>
        
        <!-- 侧边栏切换按钮 -->
        <div class="sidebar-toggle-wrapper" @click="toggleSidebar">
          <div class="sidebar-toggle-btn">
            <icon-left v-if="showSidebar" />
            <icon-right v-else />
          </div>
        </div>
        
        <!-- 编辑器主体 -->
        <div class="editor-content">
          <!-- 添加标签页组件 -->
          <div v-if="openFiles.length > 0" class="editor-tabs">
            <Tabs 
              v-model:active-key="activeTabKey" 
              type="card" 
              :editable="openFiles.length > 1" 
              @delete="closeTab"
              hide-content
              class="file-tabs"
            >
              <Tabs.TabPane 
                v-for="file in openFiles" 
                :key="file.key" 
                :title="file.fileName"
              >
                <div class="tab-content">
                  <component 
                    :is="getFileIconComponent(file.fileName)" 
                    class="tab-file-icon" 
                    :style="{ color: getFileIconColor(file.fileName) }"
                  />
                  <span class="tab-file-name">{{ file.fileName }}</span>
                  <span v-if="file.isModified" class="tab-modified-indicator"></span>
                </div>
              </Tabs.TabPane>
            </Tabs>
          </div>
          
          <div class="editor-header">
            <div class="file-info">
              <component 
                :is="activeFile ? getFileIconComponent(activeFile.fileName) : IconFile" 
                class="file-icon" 
                :style="{ color: activeFile ? getFileIconColor(activeFile.fileName) : '#409eff' }"
              />
              <span class="file-name">{{ activeFile ? activeFile.fileName : '' }}</span>
            </div>
            <div class="editor-header-right">
              <!-- 移除了这里的文件路径显示和按钮 -->
            </div>
          </div>
          
          <div class="editor-container" ref="editorContainerRef">
            <!-- Monaco Editor -->
            <div class="monaco-editor-container" ref="monacoEditorContainerRef"></div>
          </div>
        </div>
      </div>
      
      <!-- 当没有打开的文件时显示默认界面 -->
      <div v-else class="empty-editor">
        <icon-empty style="font-size: 48px; color: #C9CDD4; margin-bottom: 16px;" />
        <div>{{ t('noFileOpened') }}</div>
      </div>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue';
import { Message, Modal, Tabs } from '@arco-design/web-vue';
import { 
  IconFile, 
  IconSave, 
  IconClose,
  IconLeft,
  IconRight,
  IconRefresh,
  IconEmpty,
  IconHome,
  IconFullscreen,
  IconFullscreenExit
} from '@arco-design/web-vue/es/icon';
import { getFileContent, saveFileContent, getFileTree } from '../../api/file';
// 引入 Monaco Editor
import * as monaco from 'monaco-editor';
import { t } from '../../utils/locale';
import { getFileIcon as getFileIconFromMapper, getFileIconColor as getFileIconColorFromMapper, getFileLanguage as getFileLanguageFromMapper } from '../../utils/file/fileIconMapper.js';

const props = defineProps({
  filePath: {
    type: String,
    required: true
  },
  fileName: {
    type: String,
    required: true
  },
  visible: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:visible', 'close', 'save', 'change-file']);

// refs
const editorContainerRef = ref(null);
const monacoEditorContainerRef = ref(null);
const treeRef = ref(null);
const sidebarRef = ref(null);
let monacoEditorInstance = null;

// 响应式数据
const activeTabKey = ref('');
const openFiles = ref([]);
const loading = ref(false);
const saving = ref(false);
const showSidebar = ref(true);
const isFullscreen = ref(false);
const modalRef = ref(null);
const expandedKeys = ref([]);
const treeDataKey = ref(0); // 用于强制刷新树组件

// 响应式计算属性：检测屏幕尺寸
const isMobile = computed(() => {
  if (typeof window !== 'undefined') {
    return window.innerWidth <= 768;
  }
  return false;
});

const isTablet = computed(() => {
  if (typeof window !== 'undefined') {
    return window.innerWidth <= 1024 && window.innerWidth > 768;
  }
  return false;
});

// 计算属性：获取当前激活的文件
const activeFile = computed(() => {
  return openFiles.value.find(file => file.key === activeTabKey.value) || null;
});

// 初始化 Monaco Editor
const initMonacoEditor = () => {
  // 使用 nextTick 确保 DOM 更新完成后再初始化编辑器
  nextTick(() => {
    if (!monacoEditorContainerRef.value) {
      // 如果容器不存在，稍后重试
      setTimeout(() => {
        if (monacoEditorContainerRef.value) {
          doInitMonacoEditor();
        }
      }, 100);
      return;
    }
    
    doInitMonacoEditor();
  });
};

// 计算编辑器底部空白区域的高度
const calculateBottomPadding = () => {
  if (!monacoEditorContainerRef.value) return 50;
  
  const containerHeight = monacoEditorContainerRef.value.clientHeight;
  // 根据容器高度动态计算底部空白，至少为容器高度的1/3，最少50px，最多200px
  const dynamicPadding = Math.max(50, Math.min(200, containerHeight / 3));
  return Math.floor(dynamicPadding);
};

// 实际的 Monaco Editor 初始化逻辑
const doInitMonacoEditor = () => {
  if (!monacoEditorContainerRef.value) {
    console.warn('Monaco Editor 容器仍未找到');
    return;
  }
  
  // 销毁之前的实例（如果存在）
  if (monacoEditorInstance) {
    monacoEditorInstance.dispose();
  }
  
  try {
    // 创建新的编辑器实例
    monacoEditorInstance = monaco.editor.create(monacoEditorContainerRef.value, {
      value: activeFile.value ? (activeFile.value.content || '') : '',
      language: activeFile.value ? getFileLanguage(activeFile.value.fileName) : 'plaintext',
      theme: 'vs-dark',  // 固定使用深色主题
      fontSize: 14,  // 稍微增大字体
      fontFamily: "'Consolas', 'Monaco', 'Courier New', 'Fira Code', 'JetBrains Mono', 'Source Code Pro', monospace", // 使用更美观的等宽字体族
      fontWeight: '400', // 正常字重
      lineHeight: 21, // 行高
      scrollBeyondLastLine: true, // 允许滚动到最后一行之后，添加空白区域
      scrollBeyondLastColumn: 10, // 在最后一列之后也添加一些空白
      automaticLayout: true,
      wordWrap: 'on',
      lineNumbers: 'on',
      minimap: {
        enabled: true, // 启用缩略图
        showSlider: 'always'
      },
      smoothScrolling: true, // 平滑滚动
      cursorBlinking: 'smooth', // 光标平滑闪烁
      cursorSmoothCaretAnimation: 'on', // 光标平滑动画
      fontLigatures: true, // 启用字体连字（如果字体支持）
      padding: {
        top: 10, // 顶部内边距
        bottom: calculateBottomPadding() // 动态计算底部内边距，确保最后几行有足够的空白空间
      }
    });
    
    console.log('Monaco Editor 实例已创建', monacoEditorInstance);
    
    // 监听内容变化
    monacoEditorInstance.onDidChangeModelContent(() => {
      if (!activeFile.value) return;
      
      const value = monacoEditorInstance.getValue();
      const file = activeFile.value;
      file.content = value;
      file.isModified = file.content !== file.originalContent;
      file.characterCount = file.content.length;
      file.lineCount = file.content ? file.content.split('\n').length : 1;
    });
  } catch (error) {
    console.error('初始化 Monaco Editor 失败:', error);
    Message.error(t.value('initEditorFailed') + ': ' + (error.message || t.value('unknownError')));
  }
};

// 获取文件语言类型用于语法高亮
const getFileLanguage = (fileName) => {
  return getFileLanguageFromMapper(fileName);
};

// 获取文件图标
const getFileIcon = (fileName, isDirectory = false) => {
  return getFileIconFromMapper({ filename: fileName, is_directory: isDirectory || false });
};

// 获取文件图标颜色
const getFileIconColor = (fileName, isDirectory = false) => {
  return getFileIconColorFromMapper({ filename: fileName, is_directory: isDirectory || false });
};

// 获取文件图标组件
const getFileIconComponent = (fileName, isDirectory = false) => {
  return getFileIcon(fileName, isDirectory);
};

// 获取完整的文件路径（包括文件名）
const getFullFilePath = (file) => {
  if (!file) return '';
  // 如果filePath是根路径，直接返回文件名
  if (file.filePath === '/') {
    return `/${file.fileName}`;
  }
  // 如果filePath为空或未定义，只返回文件名
  if (!file.filePath) {
    return file.fileName;
  }
  // 否则返回完整的路径
  return `${file.filePath}/${file.fileName}`;
};

// 检查文件是否可以打开编辑 - 允许所有文件打开
const canOpenFile = (fileName) => {
  // 检查文件名是否为空或未定义
  if (!fileName || typeof fileName !== 'string') {
    return false;
  }
  
  // 允许所有文件打开编辑
  return true;
};

// 计算属性：是否为根路径
const isRootPath = (filePath) => {
  if (!filePath) return true;
  return filePath === '/' || filePath === '';
};

// 返回上一级目录
const goToParentDirectory = (file) => {
  if (!file) return;
  
  // 如果当前已经是根路径，则不执行任何操作
  if (isRootPath(file.filePath)) {
    return;
  }
  
  // 分割路径并移除最后一个目录
  const paths = file.filePath.split('/').filter(p => p !== '' && p !== '.');
  
  // 如果没有目录了，则返回到根路径
  if (paths.length === 0) {
    // 更新文件路径为根路径
    const updatedFiles = openFiles.value.map(f => {
      if (f.key === file.key) {
        return { ...f, filePath: '/' };
      }
      return f;
    });
    openFiles.value = updatedFiles;
    // 刷新文件列表
    refreshFileList({...file, filePath: '/'});
    return;
  }
  
  // 移除最后一个目录
  paths.pop();
  
  // 重新构建父级路径
  const parentPath = paths.length > 0 ? '/' + paths.join('/') : '/';
  // 更新文件路径
  const updatedFiles = openFiles.value.map(f => {
    if (f.key === file.key) {
      return { ...f, filePath: parentPath };
    }
    return f;
  });
  openFiles.value = updatedFiles;
  // 刷新文件列表
  refreshFileList({...file, filePath: parentPath});
};

// 打开新标签页
const openNewTab = () => {
  // 这里可以实现打开新标签页的逻辑
  // 例如打开一个空白文件或文件选择器
  Message.info(t.value('openNewTabNotImplemented'));
};

// 打开新文件
const openNewFile = async (filePath, fileName) => {
  // 检查参数是否存在
  if (!filePath || !fileName) {
    console.warn('打开文件参数不完整:', { filePath, fileName });
    Message.error(t.value('invalidFileParameters'));
    return;
  }
  
  const fileKey = `${filePath}|${fileName}`;
  
  console.log('尝试打开文件:', { filePath, fileName, fileKey });
  
  // 检查文件是否已经打开
  const existingFile = openFiles.value.find(f => f.key === fileKey);
  if (existingFile) {
    console.log('文件已打开，切换到该文件:', existingFile);
    activeTabKey.value = fileKey;
    // 使用 nextTick 确保 activeFile 已更新后再更新编辑器
    nextTick(() => {
      if (monacoEditorInstance && activeFile.value) {
        console.log('更新编辑器内容:', activeFile.value.content);
        monacoEditorInstance.setValue(activeFile.value.content || '');
        const model = monacoEditorInstance.getModel();
        if (model) {
          monaco.editor.setModelLanguage(model, getFileLanguage(activeFile.value.fileName));
        }
      }
    });
    return;
  }
  
  // 创建新文件对象
  const newFile = {
    key: fileKey,
    filePath: filePath,
    fileName: fileName,
    content: '',
    originalContent: '',
    isModified: false,
    currentLine: 1,
    saving: false,
    loading: true,
    characterCount: 0,
    lineCount: 1,
    fileList: []
  };
  
  console.log('创建新文件对象:', newFile);
  
  // 添加到打开的文件列表
  openFiles.value.push(newFile);
  activeTabKey.value = fileKey;
  
  console.log('设置 activeTabKey:', fileKey);
  
  // 使用 nextTick 确保 activeFile 已更新后再加载内容
  await nextTick();
  
  console.log('activeFile 更新后:', activeFile.value);
  
  // 加载文件内容
  try {
    console.log('开始加载文件内容:', { path: filePath, filename: fileName });
    const response = await getFileContent({
      path: filePath,
      filename: fileName
    });
    
    console.log('文件内容加载完成:', response);
    
    if (response.code === 200) {
      newFile.content = response.data.content || '';
      newFile.originalContent = newFile.content;
      newFile.isModified = false;
      newFile.lineCount = newFile.content ? newFile.content.split('\n').length : 1;
      newFile.characterCount = newFile.content.length;
      
      console.log('文件内容处理完成:', newFile);
      
      // 更新编辑器内容
      if (monacoEditorInstance && activeFile.value && activeFile.value.key === newFile.key) {
        console.log('更新编辑器内容:', newFile.content);
        monacoEditorInstance.setValue(newFile.content || '');
        const model = monacoEditorInstance.getModel();
        if (model) {
          monaco.editor.setModelLanguage(model, getFileLanguage(newFile.fileName));
        }
      }
    } else {
      throw new Error(response.message || t.value('loadFileFailed'));
    }
  } catch (error) {
    console.error('加载文件内容失败:', error);
    // 修改为优先显示后端返回的 detail 信息
    let errorMessage = error.message || t.value('loadFileFailed');
    // 如果错误对象有 response.data.detail，则使用它
    if (error.response && error.response.data && error.response.data.detail) {
      errorMessage = error.response.data.detail;
    }
    Message.error(errorMessage);
  } finally {
    newFile.loading = false;
  }
  
  // 加载文件列表
  refreshFileList(newFile);
};

// 保存文件内容
const saveFile = async (file) => {
  if (!file || !file.isModified) return;
  
  // 从 Monaco Editor 获取最新内容
  if (monacoEditorInstance && activeFile.value && activeFile.value.key === file.key) {
    file.content = monacoEditorInstance.getValue();
  }
  
  file.saving = true;
  try {
    const response = await saveFileContent({
      path: file.filePath,
      filename: file.fileName,
      content: file.content
    });
    
    if (response.code === 200) {
      file.originalContent = file.content;
      file.isModified = false;
      emit('save', {
        filePath: file.filePath,
        fileName: file.fileName,
        content: file.content
      });
    } else {
      throw new Error(response.message || t.value('saveFileFailed'));
    }
  } catch (error) {
    console.error('保存文件失败:', error);
    Message.error(t.value('saveFileFailed') + ': ' + (error.message || t.value('unknownError')));
  } finally {
    file.saving = false;
  }
};

// 关闭标签页
const closeTab = (fileKey) => {
  const file = openFiles.value.find(f => f.key === fileKey);
  
  if (file && file.isModified) {
    // 如果有未保存的修改，提示用户
    Modal.confirm({
      title: t.value('unsavedChanges'),
      content: t.value('unsavedChangesWarning'),
      okText: t.value('save'),
      cancelText: t.value('closeWithoutSaving'),
      closable: true,
      onOk: async () => {
        // 保存文件后关闭标签页
        await saveFile(file);
        removeTab(fileKey);
      },
      onCancel: () => {
        // 不保存直接关闭
        removeTab(fileKey);
      }
    });
  } else {
    removeTab(fileKey);
  }
};

// 移除标签页
const removeTab = (fileKey) => {
  const index = openFiles.value.findIndex(f => f.key === fileKey);
  if (index !== -1) {
    openFiles.value.splice(index, 1);
    
    // 如果关闭的是当前激活的标签页，则激活下一个或上一个标签页
    if (activeTabKey.value === fileKey) {
      if (openFiles.value.length > 0) {
        // 如果有关联的标签页，激活下一个；否则激活上一个
        if (index < openFiles.value.length) {
          activeTabKey.value = openFiles.value[index]?.key || openFiles.value[openFiles.value.length - 1]?.key;
        } else {
          activeTabKey.value = openFiles.value[openFiles.value.length - 1]?.key;
        }
      } else {
        activeTabKey.value = '';
      }
    }
  }
};

// 关闭编辑器
const closeEditor = () => {
  // 检查是否有未保存的文件
  const modifiedFiles = openFiles.value.filter(f => f.isModified);
  
  if (modifiedFiles.length > 0) {
    // 如果有未保存的修改，提示用户
    Modal.confirm({
      title: t.value('unsavedChanges'),
      content: t.value('unsavedChangesWarning'),
      okText: t.value('save'),
      cancelText: t.value('closeWithoutSaving'),
      closable: true,
      onOk: async () => {
        // 保存所有修改过的文件
        for (const file of modifiedFiles) {
          await saveFile(file);
        }
        // 关闭编辑器
        emit('update:visible', false);
        emit('close');
        // 清空打开的文件列表
        openFiles.value = [];
        activeTabKey.value = '';
      },
      onCancel: () => {
        // 不保存直接关闭
        emit('update:visible', false);
        emit('close');
        // 清空打开的文件列表
        openFiles.value = [];
        activeTabKey.value = '';
      }
    });
  } else {
    emit('update:visible', false);
    emit('close');
    // 清空打开的文件列表
    openFiles.value = [];
    activeTabKey.value = '';
  }
};

// 更新当前行号
const updateCurrentLine = (file) => {
  // 使用 Monaco Editor 后不再需要手动更新行号
  // Monaco Editor 会自动处理这些功能
};

// 加载文件列表
const refreshFileList = async (file) => {
  if (!file) return;
  
  // 检查路径是否为空，如果为空则不发送请求
  if (file.filePath === undefined || file.filePath === null) {
    console.warn('文件路径为空，跳过文件列表加载');
    return;
  }
  
  try {
    const response = await getFileTree({ 
      path: file.filePath,
      max_depth: 2 // 设置最大深度为2层
    });
    // 检查响应数据结构
    if (response && response.code === 200 && response.data) {
      // 直接使用后端返回的树形结构数据
      const updatedFiles = openFiles.value.map(f => {
        if (f.key === file.key) {
          // 后端已经返回了完整的树形结构，直接使用
          return { ...f, fileList: [response.data] };
        }
        return f;
      });
      openFiles.value = updatedFiles;
    } else {
      throw new Error(response?.message || t.value('getFileListFailed'));
    }
  } catch (error) {
    console.error('获取文件列表失败:', error);
    // 修改为优先显示后端返回的 detail 信息
    let errorMessage = error.message || t.value('getFileListFailed');
    // 如果错误对象有 response.data.detail，则使用它
    if (error.response && error.response.data && error.response.data.detail) {
      errorMessage = error.response.data.detail;
    }
    Message.error(errorMessage);
  }
};

// 打开文件
const openFile = (currentFile, fileItem) => {
  // 检查参数是否存在
  if (!currentFile || !fileItem) {
    console.warn('打开文件参数不完整:', { currentFile, fileItem });
    return;
  }
  
  // 如果是目录，则不处理
  if (fileItem.is_directory) {
    Message.info(t('directoryCannotBeOpened'));
    return;
  }
  
  // 如果点击的是当前文件，则不处理
  if (fileItem.filename === currentFile.fileName) {
    return;
  }
  
  // 使用文件的完整路径（如果存在），否则使用当前文件的路径
  const filePathToUse = fileItem.full_path ? 
    fileItem.full_path.substring(0, fileItem.full_path.lastIndexOf('/')) : 
    currentFile.filePath;
  
  // 从完整路径中提取文件名
  const fileNameToUse = fileItem.full_path ? 
    fileItem.full_path.substring(fileItem.full_path.lastIndexOf('/') + 1) : 
    fileItem.filename;
  
  // 打开新文件
  openNewFile(filePathToUse, fileNameToUse);
};

// 获取文件树形数据
const getFileTreeData = () => {
  if (!activeFile.value || !activeFile.value.fileList) return [];
  
  // 只显示当前目录的直接子项，不显示根目录本身
  const currentDir = activeFile.value.fileList[0];
  if (!currentDir || !currentDir.children) return [];
  
  // 转换子节点
  const convertTreeNode = (node, parentPath = '') => {
    if (!node) return null;
    
    // 构建文件的完整路径
    const fullPath = parentPath === '/' || parentPath === '' ? 
      `/${node.filename}` : 
      `${parentPath}/${node.filename}`;
    
    // 创建适配后的节点
    const adaptedNode = {
      key: node.filename,
      title: node.filename,
      filename: node.filename,
      full_path: fullPath, // 添加完整路径信息
      is_directory: node.is_directory,
      size: node.size,
      modified_time: node.modified_time,
      permissions: node.permissions,
      user: node.user,
      group: node.group,
      children: [],
      isLeaf: !node.is_directory // 文件是叶子节点，目录不是
    };
    
    // 如果是目录且有子节点，则保留子节点数据
    if (node.children && Array.isArray(node.children) && node.is_directory) {
      // 检查是否已经加载过子节点内容
      if (node.children.length > 0) {
        // 如果已经有子节点数据，则使用这些数据
        adaptedNode.children = node.children.map(child => convertTreeNode(child, fullPath));
      } else {
        // 如果没有子节点数据，保持空数组以保持可展开状态
        adaptedNode.children = [];
      }
    }
    
    return adaptedNode;
  };
  
  // 只转换当前目录的直接子项，而不是显示根目录本身
  // 传递当前文件的路径作为父路径
  const treeData = currentDir.children.map(child => convertTreeNode(child, activeFile.value.filePath));
  
  return treeData;
};

// 动态加载目录内容
const loadMore = async (nodeData) => {
  try {
    // 获取目录的完整路径
    const fullPath = nodeData.full_path || 
      (activeFile.value ? 
        (activeFile.value.filePath === '/' ? `/${nodeData.filename}` : `${activeFile.value.filePath}/${nodeData.filename}`) : 
        `/${nodeData.filename}`);
    
    // 加载目录内容
    const response = await getFileTree({ 
      path: fullPath,
      max_depth: 1 // 只加载一层子目录
    });
    
    if (response && response.code === 200 && response.data && response.data.children) {
      // 返回子节点数据
      const convertTreeNode = (node, parentPath = '') => {
        if (!node) return null;
        
        // 构建文件的完整路径
        const nodeFullPath = parentPath === '/' || parentPath === '' ? 
          `/${node.filename}` : 
          `${parentPath}/${node.filename}`;
        
        // 创建适配后的节点
        const adaptedNode = {
          key: node.filename,
          title: node.filename,
          filename: node.filename,
          full_path: nodeFullPath, // 添加完整路径信息
          is_directory: node.is_directory,
          size: node.size,
          modified_time: node.modified_time,
          permissions: node.permissions,
          user: node.user,
          group: node.group,
          children: [],
          isLeaf: !node.is_directory // 文件是叶子节点，目录不是
        };
        
        // 只有目录才可能有子节点，但我们也只显示一层
        if (node.children && Array.isArray(node.children) && node.is_directory) {
          // 目录节点保留children属性，但不填充具体内容
          // 这样可以保持目录的可展开状态，但不会自动展开
          adaptedNode.children = []; // 不自动填充子节点
        }
        
        return adaptedNode;
      };
      
      // 转换子节点，传递父节点的完整路径
      return response.data.children.map(child => convertTreeNode(child, fullPath));
    }
    
    return [];
  } catch (error) {
    console.error('加载目录内容失败:', error);
    Message.error(t.value('loadFileTreeFailed') + ': ' + (error.message || t.value('unknownError')));
    return [];
  }
};

// 处理树节点点击
const handleTreeNodeClick = async (nodeData) => {
  console.log('点击树节点:', nodeData);
  
  // 检查节点数据是否存在
  if (!nodeData) {
    console.warn('节点数据为空');
    return;
  }
  
  // 验证节点数据是否为对象
  if (typeof nodeData !== 'object') {
    console.warn('节点数据不是有效对象:', nodeData);
    return;
  }
  
  // 验证必要的属性
  if (nodeData.filename === undefined) {
    console.warn('节点数据缺少filename属性:', nodeData);
    return;
  }
  
  // 如果是目录，则展开并加载目录内容
  if (nodeData.is_directory) {
    console.log('点击目录:', nodeData.filename);
    
    // 检查filename是否有效
    if (typeof nodeData.filename !== 'string') {
      console.warn('目录filename不是有效字符串:', nodeData.filename);
      return;
    }
    
    // 管理展开/折叠状态
    const key = nodeData.filename;
    const currentExpandedKeys = [...expandedKeys.value];
    const index = currentExpandedKeys.indexOf(key);
    
    if (index > -1) {
      // 如果已经展开，则折叠
      currentExpandedKeys.splice(index, 1);
    } else {
      // 如果未展开，则展开
      currentExpandedKeys.push(key);
      
      // 如果是第一次展开目录，加载目录内容
      try {
        // 获取目录的完整路径
        // 使用节点的完整路径（如果存在），否则构建路径
        const fullPath = nodeData.full_path || 
          (activeFile.value ? 
            (activeFile.value.filePath === '/' ? `/${nodeData.filename}` : `${activeFile.value.filePath}/${nodeData.filename}`) : 
            `/${nodeData.filename}`);
        
        // 加载目录内容
        const response = await getFileTree({ 
          path: fullPath,
          max_depth: 1 // 只加载一层子目录
        });
        
        if (response && response.code === 200 && response.data) {
          // 更新文件列表，添加目录的子项
          const updatedFiles = openFiles.value.map(f => {
            if (f.key === activeFile.value.key) {
              // 创建新的文件列表，包含原始根目录和新加载的目录内容
              const newFileList = [...f.fileList];
              
              // 找到对应的目录节点并更新其子项
              const updateChildren = (nodes) => {
                return nodes.map(node => {
                  if (node.filename === nodeData.filename) {
                    // 更新该目录的子项
                    return { ...node, children: response.data.children || [] };
                  }
                  if (node.children) {
                    return { ...node, children: updateChildren(node.children) };
                  }
                  return node;
                });
              };
              
              newFileList[0] = updateChildren([newFileList[0]])[0];
              return { ...f, fileList: newFileList };
            }
            return f;
          });
          
          openFiles.value = updatedFiles;
          
          // 通过更新 treeDataKey 来强制刷新树组件
          treeDataKey.value += 1;
        }
      } catch (error) {
        console.error('加载目录内容失败:', error);
        Message.error(t.value('loadFileTreeFailed') + ': ' + (error.message || t.value('unknownError')));
      }
    }
    
    // 更新展开的节点
    expandedKeys.value = currentExpandedKeys;
    console.log('更新后的expandedKeys:', expandedKeys.value);
    return;
  }
  
  // 如果点击的是当前文件，则不处理
  if (activeFile.value && nodeData.filename === activeFile.value.fileName) {
    console.log('点击的是当前文件，不处理');
    return;
  }
  
  // 确保activeFile存在再尝试打开文件
  if (!activeFile.value) {
    console.warn('没有激活的文件，无法打开新文件');
    return;
  }
  
  // 打开文件
  openFile(activeFile.value, nodeData);
};

// 处理树节点选择
const handleTreeSelect = (selectedKeys, event) => {
  // 检查事件对象和节点数据是否存在
  if (!event) {
    console.warn('树节点选择事件对象为空:', { selectedKeys, event });
    return;
  }
  
  // 详细检查事件对象结构
  if (!event.node) {
    console.warn('树节点选择事件缺少node属性:', { selectedKeys, event });
    return;
  }
  
  // 尝试从不同位置获取节点数据
  let nodeData = null;
  
  // 首先尝试从 event.node 获取数据（适配后的数据结构）
  if (event.node) {
    nodeData = {
      filename: event.node.filename,
      full_path: event.node.full_path, // 添加完整路径信息
      is_directory: event.node.is_directory,
      size: event.node.size,
      modified_time: event.node.modified_time,
      permissions: event.node.permissions,
      user: event.node.user,
      group: event.node.group
    };
  }
  
  // 如果仍然没有找到节点数据，则记录警告并返回
  if (!nodeData) {
    console.warn('无法获取树节点数据:', { selectedKeys, event });
    return;
  }
  
  // 验证节点数据是否为有效对象
  if (typeof nodeData !== 'object') {
    console.warn('树节点数据不是有效对象:', { selectedKeys, nodeData, event });
    return;
  }
  
  // 验证必要的属性是否存在
  if (nodeData.filename === undefined) {
    console.warn('树节点缺少filename属性:', { selectedKeys, nodeData, event });
    return;
  }
  
  handleTreeNodeClick(nodeData);
};

// 切换全屏模式
const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value;
  
  // 触发父组件重新计算模态框大小
  nextTick(() => {
    // 如果有Monaco编辑器，重新聚焦并更新布局
    if (monacoEditorInstance) {
      monacoEditorInstance.focus();
      
      // 延迟更新布局和空白区域，确保DOM更新完成
      setTimeout(() => {
        monacoEditorInstance.layout();
        
        // 重新计算并更新底部空白区域
        const newBottomPadding = calculateBottomPadding();
        monacoEditorInstance.updateOptions({
          padding: {
            top: 10,
            bottom: newBottomPadding
          }
        });
      }, 200);
    }
  });
};

// 切换侧边栏显示状态
const toggleSidebar = () => {
  showSidebar.value = !showSidebar.value;
  
  // 侧边栏状态变化后，需要重新布局 Monaco Editor
  nextTick(() => {
    // 立即进行一次布局调整
    forceEditorLayout(50);
    
    // 等待 CSS 过渡动画完成后再次调整
    forceEditorLayout(350);
    
    // 为了确保万无一失，再延迟一次调整
    forceEditorLayout(500);
  });
};

// 切换语法高亮
const toggleSyntaxHighlighting = () => {
  // 使用 Monaco Editor 后不再需要此功能
  Message.info(t.value('monacoEditorAlwaysHighlighting'));
};

// 快捷键处理函数
const handleKeyDown = (event) => {
  // Ctrl+S 保存
  if (event.ctrlKey && event.key === 's') {
    event.preventDefault();
    if (activeFile.value && activeFile.value.isModified) {
      saveFile(activeFile.value);
    }
  }
  
  // ESC 退出全屏
  if (event.key === 'Escape' && isFullscreen.value) {
    isFullscreen.value = false;
  }
  
  // F11 切换全屏
  if (event.key === 'F11') {
    event.preventDefault();
    toggleFullscreen();
  }
};

// 强制重新布局编辑器
const forceEditorLayout = (delay = 100) => {
  if (monacoEditorInstance) {
    setTimeout(() => {
      // 强制重新计算编辑器尺寸
      monacoEditorInstance.layout();
      
      // 重新计算并更新底部空白区域
      const newBottomPadding = calculateBottomPadding();
      monacoEditorInstance.updateOptions({
        padding: {
          top: 10,
          bottom: newBottomPadding
        }
      });
      
      // 如果编辑器仍然有布局问题，再次尝试
      setTimeout(() => {
        monacoEditorInstance.layout();
      }, 50);
    }, delay);
  }
};

// 窗口大小变化处理
const handleResize = () => {
  // 在小屏幕上自动折叠侧边栏
  if (window.innerWidth <= 768 && showSidebar.value) {
    showSidebar.value = false;
  }
  
  // 触发 Monaco Editor 重新布局和更新空白区域
  forceEditorLayout(100);
};

// ResizeObserver 实例
let resizeObserver = null;

// 组件挂载时初始化编辑器
onMounted(() => {
  console.log('FileEdit 组件已挂载');
  // 添加键盘事件监听器
  window.addEventListener('keydown', handleKeyDown);
  // 添加窗口大小变化监听器
  window.addEventListener('resize', handleResize);
  
  // 初始化时检查屏幕尺寸
  if (window.innerWidth <= 768) {
    showSidebar.value = false;
  }
  
  // 初始化 Monaco Editor
  initMonacoEditor();
  
  // 添加一个延时检查，确保容器已正确渲染
  setTimeout(() => {
    if (monacoEditorContainerRef.value) {
      console.log('编辑器容器尺寸:', monacoEditorContainerRef.value.getBoundingClientRect());
      
      // 创建 ResizeObserver 来监听编辑器容器尺寸变化
      if (window.ResizeObserver) {
        resizeObserver = new ResizeObserver((entries) => {
          for (let entry of entries) {
            console.log('编辑器容器尺寸变化:', entry.contentRect);
            // 当容器尺寸变化时，重新布局编辑器
            forceEditorLayout(50);
          }
        });
        
        resizeObserver.observe(monacoEditorContainerRef.value);
      }
    }
  }, 100);
});

// 监听 monacoEditorContainerRef 的变化，确保在 DOM 元素准备好后初始化编辑器
watch(monacoEditorContainerRef, (newVal) => {
  if (newVal) {
    console.log('monacoEditorContainerRef 已准备就绪');
    initMonacoEditor();
  }
});

// 组件卸载时清理资源
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown);
  window.removeEventListener('resize', handleResize);
  
  // 清理 ResizeObserver
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
  
  // 销毁 Monaco Editor 实例
  if (monacoEditorInstance) {
    monacoEditorInstance.dispose();
  }
});

// 初始化时打开传入的文件
watch(() => props.visible, (newVal) => {
  console.log('props.visible 变化:', newVal);
  if (newVal) {
    // 如果有传入的文件路径和文件名，则打开该文件
    if (props.filePath && props.fileName) {
      console.log('props 文件信息:', { filePath: props.filePath, fileName: props.fileName });
      const fileKey = `${props.filePath}|${props.fileName}`;
      const existingFile = openFiles.value.find(f => f.key === fileKey);
      
      if (!existingFile) {
        console.log('打开新文件');
        openNewFile(props.filePath, props.fileName);
      } else {
        console.log('文件已存在，切换到该文件');
        activeTabKey.value = fileKey;
        // 确保编辑器内容更新
        nextTick(() => {
          if (monacoEditorInstance && activeFile.value) {
            console.log('更新现有文件的编辑器内容:', activeFile.value.content);
            monacoEditorInstance.setValue(activeFile.value.content || '');
            const model = monacoEditorInstance.getModel();
            if (model) {
              monaco.editor.setModelLanguage(model, getFileLanguage(activeFile.value.fileName));
            }
          }
        });
      }
    }
  }
}, { immediate: true });

// 监听 activeTabKey 的变化，确保切换文件时更新编辑器
watch(activeTabKey, (newKey) => {
  console.log('activeTabKey 变化:', newKey);
  nextTick(() => {
    if (monacoEditorInstance && activeFile.value) {
      console.log('切换文件时更新编辑器内容:', activeFile.value.content);
      monacoEditorInstance.setValue(activeFile.value.content || '');
      const model = monacoEditorInstance.getModel();
      if (model) {
        monaco.editor.setModelLanguage(model, getFileLanguage(activeFile.value.fileName));
      }
    }
  });
});

// 监听 openFiles 的变化，确保当只有一个标签页时默认激活
watch(openFiles, (newFiles) => {
  console.log('openFiles 变化:', newFiles);
  // 如果只有一个文件且当前没有激活的标签页，则激活该文件
  if (newFiles.length === 1 && !activeTabKey.value) {
    activeTabKey.value = newFiles[0].key;
    console.log('设置默认激活标签页:', newFiles[0].key);
  }
  // 如果当前激活的标签页已被关闭，则激活第一个标签页（如果存在）
  else if (newFiles.length > 0 && !newFiles.find(f => f.key === activeTabKey.value)) {
    activeTabKey.value = newFiles[0].key;
    console.log('切换到第一个标签页:', newFiles[0].key);
  }
  // 如果没有文件了，清空激活的标签页
  else if (newFiles.length === 0) {
    activeTabKey.value = '';
    console.log('清空激活标签页');
  }
});

// 监听侧边栏显示状态变化，确保编辑器正确重新布局
watch(showSidebar, (newValue) => {
  console.log('侧边栏状态变化:', newValue);
  nextTick(() => {
    // 多次尝试重新布局，确保编辑器能正确适应新的容器尺寸
    forceEditorLayout(100);
    forceEditorLayout(300);
    forceEditorLayout(500);
  });
});
</script>
<style scoped>
.file-editor {
  display: flex;
  flex-direction: column;
  height: min(80vh, 600px);
  min-height: 400px;
  background: #1e1e1e; /* 固定深色背景，不跟随主题 */
  border-radius: 4px;
  overflow: hidden;
}

.file-editor.fullscreen {
  height: 100vh;
  border-radius: 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .file-editor {
    height: 90vh;
    min-height: 300px;
  }
}

.editor-title-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 12px;
  border-bottom: 1px solid #2d2d2d; /* 固定深色边框 */
  background: #1e1e1e; /* 固定深色背景 */
  flex-wrap: wrap;
  gap: 8px;
}

/* 响应式标题栏 */
@media (max-width: 1024px) {
  .editor-title-bar {
    flex-direction: column;
    align-items: stretch;
    padding: 8px 12px;
  }
  
  .title-left,
  .title-right {
    justify-content: space-between;
  }
}

.title-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.editor-title {
  font-weight: 500;
  font-size: 16px;
  color: #cccccc; /* 固定文字颜色 */
}

.title-right {
  display: flex;
  gap: 12px;
  align-items: center;
  font-size: 12px;
  color: #aaaaaa; /* 固定文字颜色 */
  flex-wrap: wrap;
}

/* 小屏幕时隐藏部分信息 */
@media (max-width: 768px) {
  .title-right .char-count,
  .title-right .line-count {
    display: none;
  }
}

.title-right .char-count,
.title-right .line-count,
.title-right .current-line-info {
  color: #aaaaaa; /* 固定文字颜色 */
}

.modified-indicator {
  color: #e6a23c; /* 保持修改指示器的颜色 */
  font-weight: 500;
}

.file-path-container {
  display: flex;
  align-items: center;
  background: #2d2d2d; /* 固定深色背景 */
  border-radius: 4px;
  padding: 4px 12px; /* 增加内边距使路径容器更舒适 */
  font-size: 12px;
  color: #cccccc; /* 固定文字颜色 */
  min-width: 0; /* 允许收缩 */
  flex: 1;
}

/* 小屏幕时隐藏文件路径 */
@media (max-width: 768px) {
  .file-path-container {
    display: none;
  }
}

.path-home-icon {
  margin-right: 4px;
  color: #aaaaaa; /* 固定图标颜色 */
}

.file-path {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 400px;
  color: #cccccc; /* 固定文字颜色 */
}

.editor-actions {
  display: flex;
  gap: 8px; /* 调整按钮间距 */
  margin-left: 12px; /* 与左侧元素保持一定间距 */
  flex-wrap: wrap;
}

/* 小屏幕时调整按钮 */
@media (max-width: 768px) {
  .editor-actions {
    margin-left: 0;
    gap: 4px;
  }
  
  .editor-actions .arco-btn {
    font-size: 12px;
    padding: 4px 8px;
  }
  
  /* 隐藏部分按钮文字，只保留图标 */
  .editor-actions .arco-btn span:not([class*="icon"]) {
    display: none;
  }
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 12px;
  border-bottom: 1px solid #2d2d2d; /* 固定深色边框 */
  background: #1e1e1e; /* 固定深色背景 */
}

.file-info {
  display: flex;
  align-items: center;
  gap: 6px;
}

.file-icon {
  color: #409eff; /* 保持文件图标颜色 */
}

.file-name {
  font-weight: 500;
  font-size: 14px;
  color: #cccccc; /* 固定文字颜色 */
}

.sidebar {
  width: 200px;
  background-color: #1e1e1e; /* 固定深色背景 */
  border-right: 1px solid #2d2d2d; /* 固定深色边框 */
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  transition: width 0.3s ease;
  min-width: 0; /* 允许收缩 */
}

/* 确保侧边栏过渡期间编辑器容器能正确调整 */
.sidebar:not(.sidebar-collapsed) + .sidebar-toggle-wrapper + .editor-content {
  transition: margin-left 0.3s ease;
}

.sidebar.sidebar-collapsed {
  width: 30px;
}

/* 响应式侧边栏 */
@media (max-width: 1024px) {
  .sidebar {
    width: 160px;
  }
}

@media (max-width: 768px) {
  .sidebar {
    width: 120px;
  }
  
  .sidebar.sidebar-collapsed {
    width: 20px;
  }
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid #2d2d2d; /* 固定深色边框 */
  color: #cccccc; /* 固定文字颜色 */
  background-color: #1e1e1e; /* 固定深色背景 */
  font-weight: 500;
  font-size: 12px;
  flex-shrink: 0; /* 防止头部被压缩 */
}

.sidebar-content {
  flex: 1;
  overflow-y: auto; /* 添加垂直滚动条 */
  overflow-x: hidden; /* 隐藏水平滚动条 */
}

.sidebar-toggle-wrapper {
  position: relative;
  width: 0;
  height: 100%;
}

.sidebar-toggle-btn {
  position: absolute;
  left: -12px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 10;
  background: #2d2d2d;
  border: 1px solid #3d3d3d;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
}

.sidebar-toggle-btn:hover {
  background: #3d3d3d;
}

.sidebar-content::-webkit-scrollbar {
  width: 8px;
}

.sidebar-content::-webkit-scrollbar-thumb {
  background-color: #555; /* 滚动条颜色 */
  border-radius: 4px;
}

.sidebar-content::-webkit-scrollbar-track {
  background-color: #2d2d2d; /* 滚动条轨道颜色 */
}

.file-tree {
  background-color: #1e1e1e; /* 固定深色背景 */
  color: #cccccc; /* 固定文字颜色 */
  min-height: 100%; /* 确保树组件占据整个容器高度 */
}

.file-tree :deep(.arco-tree-node) {
  padding: 2px 0;
}

.file-tree :deep(.arco-tree-node-selected) {
  background-color: #37373d; /* 固定选中背景色 */
}

.file-tree :deep(.arco-tree-node-title) {
  color: #cccccc; /* 固定文字颜色 */
}

.tree-node {
  display: flex;
  align-items: center;
  width: 100%;
  max-width: 180px; /* 限制树节点最大宽度 */
  overflow: hidden;
}

.file-item-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 160px; /* 限制最大宽度 */
  color: #cccccc; /* 固定文字颜色 */
}

/* 响应式文件树 */
@media (max-width: 1024px) {
  .tree-node {
    max-width: 140px;
  }
  
  .file-item-name {
    max-width: 120px;
  }
}

@media (max-width: 768px) {
  .tree-node {
    max-width: 100px;
  }
  
  .file-item-name {
    max-width: 80px;
    font-size: 12px;
  }
}

.editor-main {
  display: flex;
  flex: 1;
  overflow: hidden;
  height: calc(100% - 40px); /* 确保主编辑区域占据剩余空间 */
}

.editor-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #040000; /* 固定深色背景 */
  min-width: 0; /* 确保能够收缩 */
  transition: all 0.3s ease; /* 添加过渡动画 */
}

.editor-header-right {
  display: flex;
  align-items: center;
  gap: 16px; /* 增加文件路径和按钮组之间的间距 */
}

.editor-container {
  position: relative;
  flex: 1;
  overflow: hidden;
  background-color: #1e1e1e; /* 固定深色背景，不跟随主题 */
  display: flex;
  overflow-y: auto;
  overflow-x: auto;
  min-height: 200px; /* 确保最小高度 */
}

.editor-container::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.editor-container::-webkit-scrollbar-thumb {
  background-color: #555; /* 调整滚动条颜色以适应深色主题 */
  border-radius: 4px;
}

.editor-container::-webkit-scrollbar-track {
  background-color: #2d2d2d; /* 调整滚动条轨道颜色 */
}

.monaco-editor-container {
  flex: 1;
  height: 100%;
  min-height: 400px; /* 添加最小高度确保容器可见 */
  padding-bottom: 20px; /* 为编辑器底部添加额外的空白空间 */
  position: relative; /* 确保定位正确 */
  overflow: hidden; /* 防止内容溢出 */
}

/* 确保 Monaco Editor 内部有足够的滚动空间 */
.monaco-editor-container :deep(.monaco-editor) {
  padding-bottom: 30px;
  width: 100% !important; /* 强制宽度为100% */
  height: 100% !important; /* 强制高度为100% */
}

.monaco-editor-container :deep(.monaco-editor .overflow-guard) {
  padding-bottom: 20px;
}

/* 确保 Monaco Editor 的滚动条不会溢出 */
.monaco-editor-container :deep(.monaco-scrollable-element) {
  width: 100% !important;
  height: 100% !important;
}

.monaco-editor-container :deep(.monaco-editor .monaco-scrollable-element > .scrollbar) {
  z-index: 10;
}

.empty-editor {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  min-height: 400px;
  color: #cccccc; /* 固定文字颜色 */
  background: #1e1e1e; /* 固定深色背景 */
}

.editor-tabs {
  background: #1e1e1e;
  border-bottom: 1px solid #2d2d2d;
}

.file-tabs {
  background: #1e1e1e;
}

.file-tabs :deep(.arco-tabs-nav) {
  background: #1e1e1e;
  border-bottom: 1px solid #2d2d2d;
}

.file-tabs :deep(.arco-tabs-tab) {
  background: #2d2d2d;
  border: 1px solid #3d3d3d;
  border-bottom: none;
  color: #cccccc;
  margin-right: 2px;
  padding: 8px 16px;
}

.file-tabs :deep(.arco-tabs-tab:hover) {
  background: #3d3d3d;
}

.file-tabs :deep(.arco-tabs-tab-active) {
  background: #1e1e1e;
  border-bottom: 1px solid #1e1e1e;
  color: #409eff;
}

.tab-content {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tab-file-icon {
  font-size: 14px;
}

.tab-file-name {
  font-size: 14px;
}

.tab-modified-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #e6a23c;
}

/* 额外的响应式优化 */
@media (max-width: 480px) {
  .file-editor {
    height: 95vh;
    min-height: 250px;
  }
  
  .editor-title-bar {
    padding: 4px 8px;
  }
  
  .editor-title {
    font-size: 14px;
  }
  
  .sidebar {
    width: 100px;
  }
  
  .sidebar.sidebar-collapsed {
    width: 15px;
  }
  
  .editor-actions .arco-btn {
    padding: 2px 4px;
    font-size: 11px;
  }
  
  .file-tabs :deep(.arco-tabs-tab) {
    padding: 4px 8px;
    font-size: 12px;
  }
  
  .tab-file-name {
    font-size: 12px;
  }
  
  /* 小屏幕时减少编辑器底部空白 */
  .monaco-editor-container {
    padding-bottom: 10px;
  }
}

/* 确保编辑器在所有屏幕尺寸下都能正常显示 */
@media (max-height: 600px) {
  .file-editor {
    height: 95vh;
    min-height: 200px;
  }
  
  .editor-container {
    min-height: 150px;
  }
}
</style>
