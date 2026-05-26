<template>
  <a-tabs type="card" :editable="true" @add="handleAdd" @delete="handleDelete" show-add-button auto-switch v-model:active-key="activeKey">
    <a-tab-pane v-for="(item, index) of data" :key="item.key" :title="getTabTitle(item.key)" :closable="data.length > 1">
      <div class="file-manager" @contextmenu="(e) => handleOperatorRightClick(e, item.key)">
        <!-- 路径导航区 -->
        <div class="navigation-bar">
          <a-button type="outline" size="large" @click="goToParentDirectory(item.key)" :disabled="isAtDefaultRoot(item.key)">
            <template #icon><icon-left /></template>
            {{ t('goToParentDirectory') }}
          </a-button>

          <!-- 路径导航容器 -->
          <div class="path-container">
            <!-- 面包屑导航 - 双击进入编辑模式 -->
            <a-breadcrumb 
              class="path-breadcrumb" 
              separator=">"
              v-show="!showPathInputMap[item.key]"
              @dblclick="() => startPathEdit(item.key)"
              :style="{ cursor: 'text' }"
            >
              <a-breadcrumb-item>
                <a-link @click="() => goToRoot(item.key)">
                  <icon-home />
                </a-link>
              </a-breadcrumb-item>
              <a-breadcrumb-item 
                v-for="(path, index) in getPathSegments(item.key)" 
                :key="index"
              >
                <a-link @click="() => navigateToPath(item.key, index)">{{ path.name }}</a-link>
              </a-breadcrumb-item>
            </a-breadcrumb>
            
            <!-- 路径输入框 -->
            <div class="path-input-wrapper" v-show="showPathInputMap[item.key]">
              <a-input 
                :model-value="editablePathMap[item.key]"
                @update:model-value="(value) => updateEditablePath(item.key, value)"
                size="small" 
                :placeholder="t('enterFilePath')"
                @press-enter="() => handlePathChange(item.key)"
                @blur="() => cancelPathEdit(item.key)"
                :ref="el => pathInputRefs[item.key] = el"
              />
              <a-link @click="() => handlePathChange(item.key)">{{ t('confirm') }}</a-link>
              <a-link @click="() => cancelPathEdit(item.key)">{{ t('cancel') }}</a-link>
            </div>
          </div>
        </div>

        <!-- 操作按钮区 -->
        <div class="action-bar" v-if="getFileListData(item.key).length > 0 || !getLoadingState(item.key)">
          <a-dropdown>
            <a-button size="small" type="primary">{{ t('create') }}</a-button>
            <template #content>
              <a-doption @click="handleCreateFolder">{{ t('createFolder') }}</a-doption>
              <a-doption @click="handleCreateFile">{{ t('createFile') }}</a-doption>
              <a-doption @click="handleCreateLink">{{ t('createLink') }}</a-doption>
            </template>
          </a-dropdown>
          <a-button size="small" type="primary" @click="handleDownloadRemote">{{ t('downloadRemote') }}</a-button>
          <a-button size="small" type="primary" @click="handleUpload">{{ t('uploadFile') }}</a-button>
          <a-button size="small" type="primary" @click="showDownloadTaskList">{{ t('downloadTaskList') }}</a-button>
          <!-- 终端按钮 -->
          <a-button size="small" type="primary" @click="showTerminalModal">{{ t('terminalConnection') }}</a-button>
          <a-button size="small" @click="showRecycleDrawer"><icon-delete /> {{ t('recycle') }}</a-button>          
          <a-button size="small" @click="() => refresh(item.key)"><icon-refresh /> {{ t('refresh') }}</a-button>
          <!-- 视图切换按钮 -->
          <a-button size="small" @click="() => toggleViewMode(item.key)">
            <icon-apps v-if="getViewMode(item.key) === 'list'" />
            <icon-list v-else />
            {{ getViewMode(item.key) === 'list' ? t('iconView') : t('listView') }}
          </a-button>
          <!-- 搜索框容器 -->
          <div class="search-container">
            <a-button size="small" type="outline" @click="handlePaste" v-if="clipboard.hasContent" style="margin-right: 8px;">
              {{ clipboard.operation === 'copy' ? t('paste') : t('paste') }}
            </a-button>
            <!-- 批量按钮 -->
            <a-dropdown v-if="tabStates[item.key]?.selectedKeys?.length > 0">
              <a-button size="small" type="outline">{{ t('more') }}</a-button>
              <template #content>
                <a-doption size="small" @click="handleBatchPermissions(item.key)" style="display: block;">
                  <icon-safe />
                  {{ t('permissions') }}
                </a-doption>
                <a-doption size="small" @click="handleBatchCompress(item.key)" style="display: block;">
                  <icon-edit />                  
                  {{ t('compress') }}
                </a-doption>
                <a-doption size="small" status="danger" @click="handleBatchDelete(item.key)" style="display: block;">
                  <icon-delete />
                  {{ t('delete') }}
                </a-doption>
              </template>
            </a-dropdown>

            <div style="border: 1px solid; border-radius: 4px; padding: 4px 10px; display: inline-flex; align-items: center;">
              <a-checkbox v-model="searchSubdirectoryMap[item.key]">
                <span style="margin-left: 4px;"> {{ t('subdirectory') }}</span>
              </a-checkbox>
            </div>
            <AInputSearch 
              :model-value="searchKeywordMap[item.key]"
              @update:model-value="(value) => updateSearchKeyword(item.key, value)"
              size="small" 
              :placeholder="t('searchFile')" 
              style="width: 200px;"
              @search="(value) => handleSearch(item.key, value)"
            />
          </div>
        </div>

        <!-- 文件列表容器 -->
        <div class="file-list-wrapper" :ref="el => fileListWrapperRefs[item.key] = el">
          <!-- 列表视图 -->
          <div class="file-list-container" v-if="getViewMode(item.key) === 'list'">
            <a-table
              :columns="columns"
              :data="getFilteredFileList(item.key)"
              :loading="getLoadingState(item.key)"
              :pagination="false"
              row-key="filename"
              size="medium"
              :scroll="{ x: 'max-content', minWidth: '100%' }"
              @row-contextmenu="(record, ev) => { ev.preventDefault(); handleRightClick(ev, item.key, record); }"
              :row-selection="getRowSelection(item.key)"
              v-model:selectedKeys="tabStates[item.key].selectedKeys"
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
                  <span @click="() => handleFileClick(item.key, record)" style="cursor: pointer;" class="list-filename">{{ record.filename }}</span>
                </div>
              </template>

              <!-- 大小列 -->
              <template #size="{ record }">
                <template v-if="record.is_directory">
                  <a-link v-if="!calculatedSizes[`${getCurrentPath(activeKey)}/${record.filename}`]" size="small" type="text" @click="() => handleCalculateSize(record)">{{ t('calculate') }}</a-link>
                  <span v-else-if="calculatedSizes[`${getCurrentPath(activeKey)}/${record.filename}`].loading">...</span>
                  <span v-else-if="calculatedSizes[`${getCurrentPath(activeKey)}/${record.filename}`].error">{{ t('failed') }}</span>
                  <span v-else>{{ calculatedSizes[`${getCurrentPath(activeKey)}/${record.filename}`].size_human }}</span>
                </template>
                <span v-else>{{ record.size }}</span>
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
                      <a-doption @click="() => handleOpenImage(item.key, record)" v-if="!record.is_directory && isImageFile(record.filename)">
                        <icon-image />
                        {{ t('openImage') }}
                      </a-doption>
                      <a-doption @click="() => handleOpenFile(item.key, record)" v-if="!record.is_directory && canOpenFile(record.filename)">
                        <icon-edit />
                        {{ t('open') }}
                      </a-doption>
                      <a-doption @click="() => handleRename(item.key, record)">
                        <icon-edit />
                        {{ t('rename') }}
                      </a-doption>
                      <a-doption @click="() => handleMove(item.key, record)">
                        <icon-edit />
                        {{ t('move') }}
                      </a-doption>
                      <a-doption @click="() => handleCopy(item.key, record)">
                        <icon-copy /> 
                        {{ t('copy') }}
                      </a-doption>
                      <a-doption @click="() => handleCompress(item.key, record)">
                        <icon-edit />
                        {{ t('compress') }}
                      </a-doption>
                      <a-doption @click="() => handleDecompress(item.key, record)" v-if="!record.is_directory && isCompressedFile(record.filename)">
                        <icon-edit />
                        {{ t('decompress') }}
                      </a-doption>
                      <a-doption @click="() => handleContextPermissions(item.key, record)">
                        <icon-safe />
                        {{ t('permissions') }}
                      </a-doption>
                      <a-doption @click="() => handleDeleteFile(item.key, record)">
                        <icon-delete />
                        {{ t('delete') }}
                      </a-doption>
                    </template>
                  </a-dropdown>
                </a-space>
              </template>
            </a-table>
          </div>
          
          <!-- 图标视图 -->
          <div class="file-icon-container" v-else @click="(e) => handleIconContainerClick(e, item.key)">
            <div class="file-grid" v-if="getFilteredFileList(item.key).length > 0">
              <a-tooltip 
                v-for="record in getFilteredFileList(item.key)" 
                :key="record.filename"
                position="right"
                :mouse-enter-delay="1000"
                :content-style="{ 
                  maxWidth: '400px', 
                  minWidth: '280px',
                  backgroundColor: 'var(--color-bg-popup)',
                  color: 'var(--color-text-1)',
                  border: '1px solid var(--color-border)'
                }"
              >
                <div 
                  class="file-icon-item"
                  :class="{ 'file-icon-item-selected': isIconItemSelected(item.key, record) }"
                  @dblclick="() => handleFileIconDoubleClick(item.key, record)"
                  @contextmenu="(e) => handleRightClick(e, item.key, record)"
                  @click="(e) => handleIconItemClick(e, item.key, record)"
                >
                  <div class="file-icon" :class="{ 'file-directory': record.is_directory }">
                    <component 
                      :is="getFileIcon(record)" 
                      :size="32"
                      :style="{ 
                        color: getFileIconColor(record),
                        fontSize: '32px'
                      }" 
                    />
                  </div>
                  <div class="file-name" :title="record.filename">{{ record.filename }}</div>
                  <!-- 选中遮罩 -->
                  <div 
                    v-show="isIconItemSelected(item.key, record)" 
                    class="file-icon-item-overlay"
                  ></div>
                </div>
                
                <!-- Tooltip 内容 -->
                <template #content>
                  <div class="tooltip-content">
                    <div class="tooltip-item">
                      <span class="tooltip-label">{{ t('fileName')}}:</span>
                      <span class="tooltip-value">{{ record.filename }}</span>
                    </div>
                    <div class="tooltip-item">
                      <span class="tooltip-label">{{ t('path')}}:</span>
                      <span class="tooltip-value">{{ record.path || getCurrentPath(item.key) }}</span>
                    </div>
                    <div class="tooltip-item" v-if="!record.is_directory">
                      <span class="tooltip-label">{{ t('size')}}:</span>
                      <span class="tooltip-value">{{ record.size }}</span>
                    </div>
                    <div class="tooltip-item">
                      <span class="tooltip-label">{{ t('user')}}:</span>
                      <span class="tooltip-value">{{ record.user || t('unknown') }}</span>
                    </div>
                    <div class="tooltip-item">
                      <span class="tooltip-label">{{ t('group')}}:</span>
                      <span class="tooltip-value">{{ record.group || t('unknown') }}</span>
                    </div>
                    <div class="tooltip-item">
                      <span class="tooltip-label">{{ t('permissions')}}:</span>
                      <span class="tooltip-value">{{ record.permissions || t('unknown') }}</span>
                    </div>
                    <div class="tooltip-item">
                      <span class="tooltip-label">{{ t('modifiedTime') }}:</span>
                      <span class="tooltip-value">{{ formatDate(record.modified_time) }}</span>
                    </div>
                  </div>
                </template>
              </a-tooltip>
            </div>
            <div class="file-grid-empty" v-else>
              <div class="empty-content">
                <icon-empty  style="font-size: 48px; color: #C9CDD4; margin-bottom: 16px;" />
                <div class="empty-text">{{ t('noData') }}</div>
              </div>
            </div>
          </div>
        </div>
        <div style="margin-top: 12px; display: flex; justify-content: flex-end;">
              <a-pagination
                :total="getTotal(item.key)"
                :current="getPage(item.key)"
                :page-size="getPageSize(item.key)"
                @change="(page) => handlePageChange(item.key, page)"
                @pageSizeChange="(size) => handlePageSizeChange(item.key, size)"
                show-total
                show-page-size
                show-jumper 
              />
        </div>
      </div>
    </a-tab-pane>
  </a-tabs>

  <!-- 右键菜单 -->
  <FileRightMenu
    :visible="contextMenu.visible"
    :x="contextMenu.x"
    :y="contextMenu.y"
    :record="contextMenu.record"
    :tab-key="contextMenu.tabKey"
    @close="hideContextMenu"
    @details="handleContextDetails"
    @download="handleContextDownload"
    @open="handleContextOpen"
    @open-image="handleContextOpenImage"
    @rename="handleContextRename"
    @move="handleContextMove"
    @copy="handleContextCopy"
    @compress="handleContextCompress"
    @decompress="handleContextDecompress"
    @permissions="() => handleContextPermissions(contextMenu.tabKey, contextMenu.record)"
    @delete="handleContextDelete"
  />
  
  <!-- 操作右键菜单 -->
  <OperatorMenu
    :visible="operatorMenu.visible"
    :x="operatorMenu.x"
    :y="operatorMenu.y"
    :tab-key="operatorMenu.tabKey"
    @close="hideOperatorMenu"
    @refresh="handleOperatorRefresh"
    @createFolder="handleCreateFolder"
    @createFile="handleCreateFile"
    @createLink="handleCreateLink"
    @downloadRemote="handleDownloadRemote"
    @upload="handleUpload"
    @terminal="showTerminalModal"
  />

  <!-- 文件详情弹窗 -->
  <FileDetails
    :visible="detailsModal.visible"
    :record="detailsModal.record"
    :calculated-sizes="calculatedSizes"
    @update:visible="detailsModal.visible = $event"
    @calculate-size="handleDetailsCalculateSize"
  />

  <!-- 权限修改弹窗 -->
  <FilePermissions
    :visible="permissionsModal.visible"
    :record="permissionsModal.record"
    :permissions="permissionsModal.permissions"
    :user="permissionsModal.user"
    :group="permissionsModal.group"
    @update:visible="permissionsModal.visible = $event"
    @submit="handleChangePermissions"
  />
  
  <!-- 批量权限修改弹窗 -->
  <FileBatchPermissions
    :visible="batchPermissionsModal.visible"
    :selected-count="batchPermissionsModal.selectedCount"
    @update:visible="batchPermissionsModal.visible = $event"
    @submit="handleBatchPermissionsSubmit"
  />

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

  <!-- 移动文件/目录对话框 -->
  <FileMove
    :visible="moveDrawer.visible"
    :source-path="moveDrawer.sourcePath"
    :source-name="moveDrawer.sourceName"
    :destination-path="moveDrawer.destinationPath"
    :destination-name="moveDrawer.destinationName"
    :is-mobile="isMobile"
    @update:visible="moveDrawer.visible = $event"
    @submit="handleMoveSubmit"
    @show-mini-file-manager="handleMoveMiniFileManager"
  />

  <!-- 复制文件/目录对话框 -->
  <FileCopy
    :visible="copyDrawer.visible"
    :source-path="copyDrawer.sourcePath"
    :source-name="copyDrawer.sourceName"
    :destination-path="copyDrawer.destinationPath"
    :destination-name="copyDrawer.destinationName"
    :is-mobile="isMobile"
    @update:visible="copyDrawer.visible = $event"
    @submit="handleCopySubmit"
    @show-mini-file-manager="handleCopyMiniFileManager"
  />

  <!-- 压缩文件/目录抽屉 -->
  <FileCompress
    :visible="compressDrawer.visible"
    :source-path="compressDrawer.sourcePath"
    :source-names="compressDrawer.sourceNames"
    :destination-path="compressDrawer.destinationPath"
    :archive-name="compressDrawer.archiveName"
    :loading="compressDrawer.loading"
    :is-mobile="isMobile"
    @update:visible="compressDrawer.visible = $event"
    @update:loading="compressDrawer.loading = $event"
    @submit="handleCompressSubmit"
    @show-mini-file-manager="handleCompressMiniFileManager"
  />

  <!-- 解压文件抽屉 -->
  <FileDecompress
    :visible="decompressDrawer.visible"
    :source-path="decompressDrawer.sourcePath"
    :source-name="decompressDrawer.sourceName"
    :destination-path="decompressDrawer.destinationPath"
    :loading="decompressDrawer.loading"
    :is-mobile="isMobile"
    @update:visible="decompressDrawer.visible = $event"
    @update:loading="decompressDrawer.loading = $event"
    @submit="handleDecompressSubmit"
    @show-mini-file-manager="handleDecompressMiniFileManager"
  />

  <!-- 批量压缩文件/目录抽屉 -->
  <FileBatchCompress
    :visible="batchCompressDrawer.visible"
    :source-path="batchCompressDrawer.sourcePath"
    :source-names="batchCompressDrawer.sourceNames"
    :destination-path="batchCompressDrawer.destinationPath"
    :archive-name="batchCompressDrawer.archiveName"
    :loading="batchCompressDrawer.loading"
    :is-mobile="isMobile"
    @update:visible="batchCompressDrawer.visible = $event"
    @update:loading="batchCompressDrawer.loading = $event"
    @submit="handleBatchCompressSubmit"
    @show-mini-file-manager="handleBatchCompressMiniFileManager"
  />

  <!-- 创建链接抽屉 -->
  <FileCreateSymlink
    :visible="symlinkDrawer.visible"
    :source-path="symlinkDrawer.sourcePath"
    :source-name="symlinkDrawer.sourceName"
    :destination-path="symlinkDrawer.destinationPath"
    :destination-name="symlinkDrawer.destinationName"
    :link-type="symlinkDrawer.linkType"
    :is-mobile="isMobile"
    @update:visible="symlinkDrawer.visible = $event"
    @submit="handleSymlinkSubmit"
    @show-mini-file-manager="handleSymlinkMiniFileManager"
  />

  <!-- 远程下载抽屉 -->
  <FileDownload
    :visible="remoteDownloadDrawer.visible"
    :url="remoteDownloadDrawer.url"
    :destination-path="remoteDownloadDrawer.destinationPath"
    :filename="remoteDownloadDrawer.filename"
    :verify-ssl="remoteDownloadDrawer.verifySsl"
    :is-downloading="remoteDownloadDrawer.isDownloading"
    :download-progress="remoteDownloadDrawer.downloadProgress"
    :is-mobile="isMobile"
    @update:visible="remoteDownloadDrawer.visible = $event"
    @update:isDownloading="remoteDownloadDrawer.isDownloading = $event"
    @update:downloadProgress="remoteDownloadDrawer.downloadProgress = $event"
    @submit="handleRemoteDownloadSubmit"
    @show-mini-file-manager="handleRemoteDownloadMiniFileManager"
  />

  <!-- 文件上传模态框 -->
  <FileUpload
    ref="fileUploadRef"
    v-model:visible="uploadModal.visible"
    :current-path="getCurrentPath(activeKey)"
    @upload-success="handleUploadSuccess"
  />

  <!-- Mini文件管理器弹窗 -->
  <MiniFileManager
    v-model:visible="miniFileManager.visible"
    :initial-path="miniFileManager.initialPath"
    :select-mode="miniFileManager.selectMode"
    @select="handleMiniFileManagerSelect"
  />
  
  <!-- 下载任务列表模态框 -->
  <DownloadTaskList 
    v-model:visible="downloadTaskListModal.visible"
    @close="downloadTaskListModal.visible = false"
  />
  
  <!-- 终端模态框 -->
  <TerminalModal 
    v-model:visible="terminalModal.visible" 
    :host-info="terminalModal.hostInfo"
    :current-path="terminalModal.currentPath"
    @close="() => terminalModal.visible = false"
  />
  
  <!-- 回收站抽屉 -->
  <RecycleDrawer
    :visible="recycleDrawer.visible"
    :is-mobile="isMobile"
    @update:visible="recycleDrawer.visible = $event"
    @close="handleRecycleDrawerClose"
  />

  <!-- 全局拖拽上传覆盖层 -->
  <div v-if="dragOver" class="file-drop-overlay">
    <div class="file-drop-overlay-content">
      <svg viewBox="0 0 24 24" width="64" height="64" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: middle;">
        <path d="M12 3v12m0-12L8 7m4-4l4 4"/>
        <path d="M3 16v3a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-3"/>
      </svg>
      <p>{{ t('releaseToUpload') }}</p>
    </div>
  </div>
</template>


<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick, h, reactive } from 'vue';
import { Message, Modal} from '@arco-design/web-vue';
import { IconLeft,IconRefresh,IconHome,IconEdit,IconApps,
  IconList,IconEmpty, IconDelete, IconMore,IconSafe,IconImage, IconCopy
} from '@arco-design/web-vue/es/icon';
import { InputSearch, Input } from '@arco-design/web-vue';
import { 
  getFileList, createDirectory, createFile, deleteFile, deleteFilesBatch,
   downloadFile, renameFile, changePermissions, moveFileOrDirectory, copyFileOrDirectory, compressFiles, decompressFile, 
   createSymlink, downloadRemoteFile, getDirectorySize, searchFiles, compressFilesBatch, changePermissionsBatch, getRecycleConfig  } from '../../api/file';
import { t } from '../../utils/locale';
import FileEdit from '../../components/file/FileEdit.vue';
import ImageMonitor from '../../components/file/ImageMonitor.vue';
import MiniFileManager from '../../components/file/MiniFileManager.vue';
import DownloadTaskList from '../../components/file/DownloadTaskList.vue';
import FilePermissions from '../../components/file/FilePermissions.vue';
import FileMove from '../../components/file/FileMove.vue';
import FileCopy from '../../components/file/FileCopy.vue';
import FileCompress from '../../components/file/FileCompress.vue';
import FileBatchCompress from '../../components/file/FileBatchCompress.vue';
import FileDecompress from '../../components/file/FileDecompress.vue';
import FileCreateSymlink from '../../components/file/FileCreateSymlink.vue';
import FileDownload from '../../components/file/FileDownload.vue';
import FileUpload from '../../components/file/FileUpload.vue';
import TerminalModal from '../../components/hosts/TerminalModal.vue';
import FileDetails from '../../components/file/FileDetails.vue';
import FileRightMenu from '../../components/file/FileRightMenu.vue';
import FileBatchPermissions from '../../components/file/FileBatchPermissions.vue';
import OperatorMenu from '../../components/file/OperatorMenu.vue';
import RecycleDrawer from '../../components/file/RecycleDrawer.vue';
// 引入文件图标映射工具函数
import { getFileIcon, getFileIconColor, isImageFile, isCompressedFile, canOpenFile } from '../../utils/file/fileIconMapper';

// 注册组件
const AInputSearch = InputSearch;
const AInput = Input;

// 回收站目录名称
const RECYCLE_DIR_NAME = '.recycle_bp';

// 检查是否为回收站目录
const isRecycleDirectory = (filename) => {
  return filename === RECYCLE_DIR_NAME;
};

// 存储计算后的大小信息
const calculatedSizes = ref({});

// 回收站配置状态
const recycleEnabled = ref(false);

// 获取回收站配置
const getRecycleConfigData = async () => {
  try {
    const response = await getRecycleConfig();
    recycleEnabled.value = response.RECYCLE === "True";
  } catch (error) {
    console.error('获取回收站配置失败:', error);
    recycleEnabled.value = false;
  }
};

// 处理回收站抽屉关闭事件
const handleRecycleDrawerClose = () => {
  // 当回收站抽屉关闭时，重新获取回收站配置
  getRecycleConfigData();
};

// 处理详情弹窗中的计算大小
const handleDetailsCalculateSize = async (record) => {
  try {
    // 直接使用record.path作为完整路径，因为它可能已经包含了filename部分
    const fullPath = record.path || '';
    const key = `${record.path}/${record.filename}`;
    
    // 设置为计算中状态
    calculatedSizes.value[key] = { loading: true };
    
    // 调用API获取大小 - 简化参数传递
    const response = await getDirectorySize({ 
      path: fullPath
    });
    
    // 更新计算结果
    calculatedSizes.value[key] = {
      loading: false,
      size_human: response.data.size_human
    };
  } catch (error) {
    console.error('计算大小失败:', error);
    Message.error('Calculate Size Failed');
    
    // 设置错误状态
    const key = `${record.path}/${record.filename}`;
    calculatedSizes.value[key] = {
      loading: false,
      error: true
    };
  }
};

// 计算文件或目录大小
const handleCalculateSize = async (record) => {
  try {
    // 获取当前路径
    const currentPath = getCurrentPath(activeKey.value);
    // 处理符号链接：提取实际文件名（忽略 " -> 目标路径" 部分）
    let actualFilename = record.filename;
    if (actualFilename.includes(' -> ')) {
      actualFilename = actualFilename.split(' -> ')[0].trim();
    }
    // 构建完整路径
    const fullPath = record.is_directory 
      ? `${currentPath}/${actualFilename}` 
      : currentPath;
    
    // 生成唯一键
    const key = `${currentPath}/${actualFilename}`;
    
    // 设置为计算中状态
    calculatedSizes.value[key] = { loading: true };
    
    // 调用API获取大小
    const response = await getDirectorySize({ 
      path: fullPath,
      filename: record.is_directory ? undefined : actualFilename
    });
    
    // 更新计算结果
    calculatedSizes.value[key] = {
      loading: false,
      size_human: response.data.size_human
    };
  } catch (error) {
    console.error('计算大小失败:', error);
    Message.error(t('calculateSizeFailed'));
    
    // 设置错误状态
    // 处理符号链接：提取实际文件名（忽略 " -> 目标路径" 部分）
    let actualFilename = record.filename;
    if (actualFilename.includes(' -> ')) {
      actualFilename = actualFilename.split(' -> ')[0].trim();
    }
    const key = `${getCurrentPath(activeKey.value)}/${actualFilename}`;
    calculatedSizes.value[key] = {
      loading: false,
      error: true
    };
  }
};

let count = 2;

// 标签页数据
const data = ref([
  {
    key: '1',
    title: '文件管理'  // 使用默认值，避免在初始化时调用t()
  }
]);

// 子目录搜索复选框状态管理
const searchSubdirectoryMap = ref({});

// 初始化默认标签页的子目录搜索状态
searchSubdirectoryMap.value['1'] = false;

// 当前激活的标签页key
const activeKey = ref('1');

// 为每个标签页维护独立的状态
const tabStates = ref({
  '1': {
    fileList: [],
    loading: false,
    currentPath: '/opt/blackpotbpanel-v2/server',
    editablePath: '/opt/blackpotbpanel-v2/server',
    showPathInput: false,
    searchKeyword: '',
    viewMode: 'list', // 'list' 或 'icon'
    total: 0,
    page: 1,
    pageSize: 20,
    selectedKeys: [],
    iconSelectedKeys: []  // 图标视图选中状态
  }
});

// 引用集合
const pathInputRefs = {};
const fileListWrapperRefs = {};

// 右键菜单状态
const contextMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  tabKey: '',
  record: null
});

// 操作右键菜单状态
const operatorMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  tabKey: ''
});

// 详情弹窗状态
const detailsModal = reactive({
  visible: false,
  record: null
});

// 权限弹窗状态
const permissionsModal = reactive({
  visible: false,
  record: null,
  permissions: '755',
  user: '',
  group: ''
});

// 批量权限弹窗状态
const batchPermissionsModal = reactive({
  visible: false,
  selectedCount: 0
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

// 终端模态框状态
const terminalModal = reactive({
  visible: false,
  hostInfo: {},
  currentPath: '/opt/blackpotbpanel-v2/server'  // 添加当前路径属性
});

// 回收站抽屉状态
const recycleDrawer = reactive({
  visible: false
});

// 在响应式数据部分添加移动端检测
const isMobile = ref(false);

// 在响应式数据定义之后添加以下函数

// 保存标签页状态到本地存储
const saveTabStatesToLocalStorage = () => {
  try {
    const stateToSave = {
      data: data.value,
      activeKey: activeKey.value,
      tabStates: tabStates.value
    };
    localStorage.setItem('fileManagerTabStates', JSON.stringify(stateToSave));
  } catch (error) {
    console.error('保存标签页状态到本地存储失败:', error);
  }
};

// 从本地存储恢复标签页状态
const restoreTabStatesFromLocalStorage = () => {
  try {
    const savedState = localStorage.getItem('fileManagerTabStates');
  if (savedState) {
      const parsedState = JSON.parse(savedState);
      data.value = parsedState.data || data.value;
      activeKey.value = parsedState.activeKey || activeKey.value;
      
      // 更新count变量，确保新创建的标签页不会与恢复的标签页产生key冲突
      const maxKey = Math.max(...data.value.map(item => parseInt(item.key, 10)), 1);
      count = maxKey + 1;
      
      // 恢复每个标签页的状态
      if (parsedState.tabStates) {
        Object.keys(parsedState.tabStates).forEach(key => {
          if (!tabStates.value[key]) {
            tabStates.value[key] = {
              fileList: [],
              loading: false,
              currentPath: '/opt/blackpotbpanel-v2/server',
              editablePath: '/opt/blackpotbpanel-v2/server',
              showPathInput: false,
              searchKeyword: '',
              viewMode: 'list',
              total: 0,
              page: 1,
              pageSize: 20,
              selectedKeys: [], // 添加这一行
              iconSelectedKeys: []  // 图标视图选中状态
            };
          }
          
          // 只恢复必要的状态，避免恢复过期的文件列表
          const savedTabState = parsedState.tabStates[key];
          tabStates.value[key].currentPath = savedTabState.currentPath || '/opt/blackpotbpanel-v2/server';
          tabStates.value[key].editablePath = savedTabState.editablePath || '/opt/blackpotbpanel-v2/server';
          tabStates.value[key].searchKeyword = savedTabState.searchKeyword || '';
          tabStates.value[key].viewMode = savedTabState.viewMode || 'list';
          tabStates.value[key].total = savedTabState.total || 0;
          tabStates.value[key].page = savedTabState.page || 1;
          tabStates.value[key].pageSize = savedTabState.pageSize || 20;
          tabStates.value[key].selectedKeys = savedTabState.selectedKeys || []; // 添加这一行
          tabStates.value[key].iconSelectedKeys = savedTabState.iconSelectedKeys || [];  // 图标视图选中状态
        });
      }
      
      return true;
    }
  } catch (error) {
    console.error('从本地存储恢复标签页状态失败:', error);
    // 清除可能损坏的存储数据
    localStorage.removeItem('fileManagerTabStates');
  }
  return false;
};

// ========== 标签页操作 ==========
const handleAdd = () => {
  // 生成唯一的标签页key，避免与现有key冲突
  let newKey;
  do {
    newKey = `${count++}`;
  } while (data.value.some(item => item.key === newKey));
  
  const key = newKey;
  data.value.push({
    key,
    title: t.value('fileManager')  // 在函数调用时使用t.value()
  });
  
  // 初始化新标签页的状态
  tabStates.value[key] = {
    fileList: [],
    allFileList: [], // 保存完整文件列表用于普通搜索
    loading: false,
    currentPath: '/opt/blackpotbpanel-v2/server',
    editablePath: '/opt/blackpotbpanel-v2/server',
    showPathInput: false,
    searchKeyword: '',
    isSearching: false, // 标记是否正在进行搜索
    viewMode: 'list', // 'list' 或 'icon'
    total: 0,
    page: 1,
    pageSize: 20,
    selectedKeys: [], // 添加这一行
    iconSelectedKeys: []  // 图标视图选中状态
  };
  
  // 初始化子目录搜索状态
  searchSubdirectoryMap.value[key] = false;
  
  // 设置为当前激活的标签页
  activeKey.value = key;
  
  // 加载文件列表
  loadFileList(key, '/opt/blackpotbpanel-v2/server');
};

const handleDelete = (key) => {
  if (data.value.length <= 1) {
    Message.warning(t.value('atLeastOneTabRequired'));  // 使用t.value()
    return;
  }
  
  const currentIndex = data.value.findIndex(item => item.key === key);
  data.value = data.value.filter(item => item.key !== key);
  
  // 删除标签页状态
  delete tabStates.value[key];
  // 删除子目录搜索状态
  delete searchSubdirectoryMap.value[key];
  
  // 如果删除的是当前激活的标签页，则激活下一个或上一个标签页
  if (activeKey.value === key) {
    if (data.value.length > 0) {
      // 如果有下一个标签页，激活下一个；否则激活上一个
      if (currentIndex < data.value.length) {
        activeKey.value = data.value[currentIndex]?.key || data.value[data.value.length - 1]?.key;
      } else {
        activeKey.value = data.value[data.value.length - 1]?.key;
      }
    }
  }
};

// 监听标签页变化，如果只剩一个标签页，则自动选择它
watch(data, (newData) => {
  if (newData.length === 1) {
    activeKey.value = newData[0].key;
  }
});

// ========== 状态获取方法 ==========
const getFileListData = (key) => {
  return tabStates.value[key]?.fileList || [];
};

const getLoadingState = (key) => {
  return tabStates.value[key]?.loading || false;
};

const getCurrentPath = (key) => {
  return tabStates.value[key]?.currentPath || '/opt/blackpotbpanel-v2/server';
};

const getTabTitle = (key) => {
  const currentPath = getCurrentPath(key);
  if (!currentPath || currentPath === '/') return '/';
  const parts = currentPath.split('/').filter(p => p !== '');
  return parts.length > 0 ? parts[parts.length - 1] : '/';
};

// 检查图标项是否被选中
const isIconItemSelected = (key, record) => {
  const iconSelectedKeys = tabStates.value[key]?.iconSelectedKeys || [];
  // 使用文件名作为唯一标识符
  return iconSelectedKeys.includes(record.filename);
};

// 获取行选择配置
const getRowSelection = (key) => {
  return {
    type: 'checkbox',
    showCheckedAll: true,
    fixed: true,
    selectedRowKeys: tabStates.value[key]?.selectedKeys || [],
    onChange: (selectedRowKeys) => {
      if (tabStates.value[key]) {
        tabStates.value[key].selectedKeys = selectedRowKeys;
      }
    }
  };
};

// 更新可编辑路径
const updateEditablePath = (key, value) => {
  if (tabStates.value[key]) {
    tabStates.value[key].editablePath = value;
  }
};

// 更新搜索关键词
const updateSearchKeyword = (key, value) => {
  if (tabStates.value[key]) {
    tabStates.value[key].searchKeyword = value;
  }
};

// 视图模式相关函数
const getViewMode = (key) => {
  return tabStates.value[key]?.viewMode || 'list';
};

const getTotal = (key) => {
  return tabStates.value[key]?.total || 0;
};

const getPage = (key) => {
  return tabStates.value[key]?.page || 1;
};

const getPageSize = (key) => {
  return tabStates.value[key]?.pageSize || 20;
};

const toggleViewMode = (key) => {
  if (tabStates.value[key]) {
    const oldViewMode = tabStates.value[key].viewMode;
    tabStates.value[key].viewMode = tabStates.value[key].viewMode === 'list' ? 'icon' : 'list';
    
    // 切换视图时同步选中状态
    if (oldViewMode === 'list' && tabStates.value[key].viewMode === 'icon') {
      // 从列表视图切换到图标视图：同步selectedKeys到iconSelectedKeys
      tabStates.value[key].iconSelectedKeys = [...tabStates.value[key].selectedKeys];
    } else if (oldViewMode === 'icon' && tabStates.value[key].viewMode === 'list') {
      // 从图标视图切换到列表视图：同步iconSelectedKeys到selectedKeys
      tabStates.value[key].selectedKeys = [...tabStates.value[key].iconSelectedKeys];
    }
  }
};

// ========== 路径与面包屑 ==========
const isAtDefaultRoot = (key) => {
  const currentPath = getCurrentPath(key);
  return currentPath === '/';
};

const getPathSegments = (key) => {
  const currentPath = getCurrentPath(key);
  const segments = [];
  const paths = currentPath.split('/').filter(p => p !== '' && p !== '.');
  
  let currentPathSegment = '';
  for (let i = 0; i < paths.length; i++) {
    currentPathSegment += '/' + paths[i];
    segments.push({ name: paths[i], path: currentPathSegment });
  }
  
  return segments;
};

// 路径导航
const navigateToPath = (key, index) => {
  const pathSegments = getPathSegments(key);
  if (index === -1) {
    // 根目录
    loadFileList(key, '/');
  } else {
    // 构建路径
    const paths = pathSegments.slice(0, index + 1);
    const targetPath = paths[paths.length - 1].path;
    loadFileList(key, targetPath);
  }
};

// ========== 路径编辑功能 ==========
const showPathInputMap = computed(() => {
  const map = {};
  Object.keys(tabStates.value).forEach(key => {
    map[key] = tabStates.value[key].showPathInput;
  });
  return map;
});

const editablePathMap = computed(() => {
  const map = {};
  Object.keys(tabStates.value).forEach(key => {
    map[key] = tabStates.value[key].editablePath;
  });
  return map;
});

const searchKeywordMap = computed(() => {
  const map = {};
  Object.keys(tabStates.value).forEach(key => {
    map[key] = tabStates.value[key].searchKeyword;
  });
  return map;
});

const startPathEdit = (key) => {
  tabStates.value[key].showPathInput = true;
  nextTick(() => {
    if (pathInputRefs[key]) {
      pathInputRefs[key].focus();
    }
  });
};

const cancelPathEdit = (key) => {
  tabStates.value[key].showPathInput = false;
  tabStates.value[key].editablePath = tabStates.value[key].currentPath;
};

const handlePathChange = (key) => {
  const editablePath = tabStates.value[key].editablePath;
  if (editablePath.trim() !== '') {
    loadFileList(key, editablePath);
  }
  tabStates.value[key].showPathInput = false;
};

// ========== 搜索功能 ==========
const handleSearch = async (key, value) => {
  tabStates.value[key].searchKeyword = value;
  tabStates.value[key].isSearching = true;
  
  // 如果没有关键词，不执行操作
  if (!value.trim()) {
    // 重置为当前路径的文件列表
    tabStates.value[key].isSearching = false;
    loadFileList(key, getCurrentPath(key));
    return;
  }
  
  // 检查是否勾选了子目录搜索
  if (searchSubdirectoryMap.value[key]) {
    // 执行子目录搜索
    tabStates.value[key].loading = true;
    try {
      const skip = ((tabStates.value[key].page || 1) - 1) * (tabStates.value[key].pageSize || 20);
      const limit = tabStates.value[key].pageSize || 20;
      
      // 调用searchFiles API
      const response = await searchFiles(
        { skip, limit },  // Query参数
        { 
          path: getCurrentPath(key), 
          keyword: value 
        }  // Body参数
      );
      
      // 更新文件列表
      tabStates.value[key].fileList = response.data || [];
      tabStates.value[key].total = response.total || (response.data ? response.data.length : 0);
    } catch (error) {
      console.error('搜索文件失败:', error);
      Message.error(t.value('searchFailed'));
      // 搜索失败时不改变当前文件列表
    } finally {
      tabStates.value[key].loading = false;
    }
  } else {
    // 执行普通搜索：在当前目录文件中过滤
    tabStates.value[key].loading = true;
    try {
      // 使用保存的完整文件列表进行过滤
      let allFiles = tabStates.value[key].allFileList || [];
      
      // 如果没有完整文件列表，则先获取
      if (allFiles.length === 0) {
        const skip = 0;
        const limit = 1000; // 设置一个较大的值以获取足够的文件进行过滤
        const response = await getFileList({ 
          path: getCurrentPath(key), 
          skip, 
          limit 
        });
        allFiles = response.data || [];
        tabStates.value[key].allFileList = allFiles;
      }
      
      const keyword = value.toLowerCase();
      // 应用过滤
      const filteredFiles = allFiles.filter(file => 
        file.filename.toLowerCase().includes(keyword)
      );
      
      // 计算分页
      const page = tabStates.value[key].page || 1;
      const pageSize = tabStates.value[key].pageSize || 20;
      const start = (page - 1) * pageSize;
      const end = start + pageSize;
      
      // 更新文件列表和总数
      tabStates.value[key].fileList = filteredFiles.slice(start, end);
      tabStates.value[key].total = filteredFiles.length;
    } catch (error) {
      console.error('搜索文件失败:', error);
      Message.error(t.value('searchFailed') || '搜索文件失败');
    } finally {
      tabStates.value[key].loading = false;
    }
  }
};

const getFilteredFileList = (key) => {
  let fileList = getFileListData(key);
  
  // 首先按类型排序：文件夹在前，文件在后
  fileList = fileList.sort((a, b) => {
    // 如果一个是目录，一个不是目录，则目录排在前面
    if (a.is_directory && !b.is_directory) {
      return -1;
    }
    if (!a.is_directory && b.is_directory) {
      return 1;
    }
    // 如果两个都是目录或两个都是文件，则按文件名字母顺序排序
    return a.filename.localeCompare(b.filename);
  });
  
  return fileList;
};

// ========== 文件操作 ==========
const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleString('zh-CN');
};

const loadFileList = async (key, path = '/opt/blackpotbpanel-v2/server') => {
  if (!tabStates.value[key]) return;
  
  tabStates.value[key].loading = true;
  try {
    const skip = ((tabStates.value[key].page || 1) - 1) * (tabStates.value[key].pageSize || 20);
    const limit = tabStates.value[key].pageSize || 20;
    const response = await getFileList({ path, skip, limit });
    
    // 获取完整文件列表用于普通搜索
    const allResponse = await getFileList({ path, skip: 0, limit: 1000 });
    
    tabStates.value[key].fileList = response.data || [];
    tabStates.value[key].allFileList = allResponse.data || [];
    tabStates.value[key].total = response.total || (response.data ? response.data.length : 0);
    tabStates.value[key].currentPath = path;
    tabStates.value[key].editablePath = path;
    tabStates.value[key].isSearching = false; // 重置搜索状态
    
    // 清空复选框选择状态
    tabStates.value[key].selectedKeys = [];
    // 清空图标视图选中状态
    if (tabStates.value[key].iconSelectedKeys) {
      tabStates.value[key].iconSelectedKeys = [];
    }
  } catch (error) {
    console.error('获取文件列表失败:', error);
    // 确保t是一个函数后再调用
    const errorMessage = typeof t === 'function' ? t.value('getFileListFailed') : '获取文件列表失败';
    const unknownError = typeof t === 'function' ? t.value('unknownError') : '未知错误';
    Message.error(errorMessage + ': ' + (error.message || unknownError));
  } finally {
    tabStates.value[key].loading = false;
  }
};

const handleFileClick = (key, record) => {
  if (record.is_directory) {
    // 禁止进入回收站目录
    if (isRecycleDirectory(record.filename)) {
      Message.warning(t.value('cannotAccessRecycleDirectory'));
      return;
    }
    const currentPath = getCurrentPath(key);
    // 处理符号链接：提取实际目录名（忽略 " -> 目标路径" 部分）
    let actualFilename = record.filename;
    if (actualFilename.includes(' -> ')) {
      actualFilename = actualFilename.split(' -> ')[0].trim();
    }
    const newPath = currentPath === '/' 
      ? `/${actualFilename}` 
      : `${currentPath}/${actualFilename}`;
    loadFileList(key, newPath);
  } else {
    // 如果是图片文件，直接打开图片预览
    if (isImageFile(record.filename)) {
      handleOpenImage(key, record);
    } else {
      handleOpenFile(key, record);
    }
  }
};

// 处理图标视图中文件的双击事件
const handleFileIconDoubleClick = (key, record) => {
  if (record.is_directory) {
    // 禁止进入回收站目录
    if (isRecycleDirectory(record.filename)) {
      Message.warning(t.value('cannotAccessRecycleDirectory'));
      return;
    }
    // 如果是目录，则进入目录
    const currentPath = getCurrentPath(key);
    // 处理符号链接：提取实际目录名（忽略 " -> 目标路径" 部分）
    let actualFilename = record.filename;
    if (actualFilename.includes(' -> ')) {
      actualFilename = actualFilename.split(' -> ')[0].trim();
    }
    const newPath = currentPath === '/' 
      ? `/${actualFilename}` 
      : `${currentPath}/${actualFilename}`;
    loadFileList(key, newPath);
  } else {
    // 如果是图片文件，直接打开图片预览
    if (isImageFile(record.filename)) {
      handleOpenImage(key, record);
    } else {
      handleOpenFile(key, record);
    }
  }
};

const goToParentDirectory = (key) => {
  const currentPath = getCurrentPath(key);
  // 如果当前已经是文件系统根目录，则不执行任何操作
  if (currentPath === '/') {
    return;
  }
  
  // 分割路径并移除最后一个目录
  const paths = currentPath.split('/').filter(p => p !== '');
  
  // 如果没有目录了，则返回到文件系统根目录
  if (paths.length === 0) {
    loadFileList(key, '/');
    return;
  }
  
  // 移除最后一个目录
  paths.pop();
  
  // 重新构建父级路径
  const parentPath = paths.length > 0 ? '/' + paths.join('/') : '/';
  loadFileList(key, parentPath);
};

const goToRoot = (key) => {
  loadFileList(key, '/');
};

const refresh = (key) => {
  const currentPath = getCurrentPath(key);
  loadFileList(key, currentPath);
};

// ========== 右键菜单操作 ==========
const handleRightClick = (event, tabKey, record) => {
  event.preventDefault();
  contextMenu.visible = true;
  contextMenu.x = event.clientX;
  contextMenu.y = event.clientY;
  contextMenu.tabKey = tabKey;
  contextMenu.record = record;
};

// 操作右键菜单处理函数
const handleOperatorRightClick = (event, tabKey) => {
  event.preventDefault();
  
  // 检查点击的目标元素是否是文件项或其后代
  // 对于列表视图，文件项是 .arco-table-tr 元素
  // 对于图标视图，文件项是 .file-icon-item 元素
  const isClickOnFileItem = event.target.closest('.arco-table-tr') || 
                           event.target.closest('.file-icon-item') ||
                           event.target.closest('.file-item');
  
  // 如果不是点击在文件项上，则显示操作右键菜单
  if (!isClickOnFileItem) {
    operatorMenu.visible = true;
    operatorMenu.x = event.clientX;
    operatorMenu.y = event.clientY;
    operatorMenu.tabKey = tabKey;
  }
};

// 隐藏操作右键菜单
const hideOperatorMenu = () => {
  operatorMenu.visible = false;
};

// 操作右键菜单刷新
const handleOperatorRefresh = () => {
  refresh(operatorMenu.tabKey);
  hideOperatorMenu();
};

// 处理图标项点击事件
const handleIconItemClick = (event, tabKey, record) => {
  // 阻止右键点击触发选中
  if (event.button === 2) return;
  
  const tabState = tabStates.value[tabKey];
  if (!tabState) return;
  
  // 初始化iconSelectedKeys如果不存在
  if (!tabState.iconSelectedKeys) {
    tabState.iconSelectedKeys = [];
  }
  
  // 检查是否按下了Ctrl键（多选）
  const isCtrlPressed = event.ctrlKey || event.metaKey;
  // 检查是否按下了Shift键（连续选择）
  const isShiftPressed = event.shiftKey;
  
  const filename = record.filename;
  const iconSelectedKeys = [...tabState.iconSelectedKeys];
  const isSelected = iconSelectedKeys.includes(filename);
  
  if (isCtrlPressed) {
    // Ctrl键：切换选中状态
    if (isSelected) {
      // 如果已选中，则取消选中
      const index = iconSelectedKeys.indexOf(filename);
      iconSelectedKeys.splice(index, 1);
    } else {
      // 如果未选中，则添加选中
      iconSelectedKeys.push(filename);
    }
  } else if (isShiftPressed) {
    // Shift键：连续选择
    if (iconSelectedKeys.length > 0) {
      // 获取当前文件列表
      const fileList = getFilteredFileList(tabKey);
      // 获取当前点击项的索引
      const currentIndex = fileList.findIndex(item => item.filename === filename);
      // 获取上一次选中项的索引
      const lastSelectedFilename = iconSelectedKeys[iconSelectedKeys.length - 1];
      const lastIndex = fileList.findIndex(item => item.filename === lastSelectedFilename);
      
      if (currentIndex !== -1 && lastIndex !== -1) {
        // 清空现有选中项
        iconSelectedKeys.length = 0;
        
        // 确定范围
        const startIndex = Math.min(currentIndex, lastIndex);
        const endIndex = Math.max(currentIndex, lastIndex);
        
        // 选择范围内的所有项
        for (let i = startIndex; i <= endIndex; i++) {
          iconSelectedKeys.push(fileList[i].filename);
        }
      } else {
        // 如果找不到索引，直接添加当前项
        iconSelectedKeys.push(filename);
      }
    } else {
      // 如果没有已选中项，直接添加当前项
      iconSelectedKeys.push(filename);
    }
  } else {
    // 普通点击：清空其他选中项，只选中当前项
    iconSelectedKeys.length = 0;
    iconSelectedKeys.push(filename);
  }
  
  // 更新选中状态
  tabState.iconSelectedKeys = iconSelectedKeys;
  
  // 同步到列表视图的selectedKeys，以便批量操作按钮能正确显示
  if (tabState.viewMode === 'icon') {
    tabState.selectedKeys = [...iconSelectedKeys];
  }
};

// 处理图标容器点击事件（点击空白区域取消选中）
const handleIconContainerClick = (event, tabKey) => {
  // 检查点击的目标元素是否为容器本身而不是其子元素
  // 通过检查事件目标是否是容器元素本身来确定是否点击了空白区域
  const container = event.currentTarget;
  const target = event.target;
  
  // 如果点击的是容器本身（而不是子元素），则取消选中
  if (target === container) {
    const tabState = tabStates.value[tabKey];
    if (!tabState) return;
    
    // 清空图标视图选中状态
    tabState.iconSelectedKeys = [];
    
    // 同步到列表视图的selectedKeys
    if (tabState.viewMode === 'icon') {
      tabState.selectedKeys = [];
    }
  }
};

const handlePageChange = (key, page) => {
  if (!tabStates.value[key]) return;
  tabStates.value[key].page = page;
  
  // 如果正在进行搜索且有关键词，重新执行搜索
  const searchKeyword = tabStates.value[key].searchKeyword;
  if (tabStates.value[key].isSearching && searchKeyword) {
    handleSearch(key, searchKeyword);
  } else {
    // 否则加载文件列表
    loadFileList(key, getCurrentPath(key));
  }
};

const handlePageSizeChange = (key, size) => {
  if (!tabStates.value[key]) return;
  tabStates.value[key].pageSize = size;
  tabStates.value[key].page = 1;
  
  // 如果正在进行子目录搜索且有搜索关键词，重新执行搜索
  const searchKeyword = tabStates.value[key].searchKeyword;
  if (searchSubdirectoryMap.value[key] && searchKeyword) {
    handleSearch(key, searchKeyword);
  } else {
    // 否则加载文件列表
    loadFileList(key, getCurrentPath(key));
  }
};

const hideContextMenu = () => {
  contextMenu.visible = false;
  contextMenu.x = 0;
  contextMenu.y = 0;
  contextMenu.tabKey = '';
  contextMenu.record = null;
};

const handleContextDownload = () => {
  if (contextMenu.record) {
    handleDownload(contextMenu.record);
  }
  hideContextMenu();
};

const handleContextDelete = () => {
  if (contextMenu.record && contextMenu.tabKey) {
    handleDeleteFile(contextMenu.tabKey, contextMenu.record);
  }
  hideContextMenu();
};

// 批量删除文件
const handleBatchDelete = async (tabKey) => {
  const tabState = tabStates.value[tabKey];
  if (!tabState || tabState.selectedKeys.length === 0) {
    return;
  }
  
  // 检查是否包含回收站目录
  const containsRecycleDir = tabState.selectedKeys.some(filename => isRecycleDirectory(filename));
  if (containsRecycleDir) {
    Message.warning(t.value('cannotOperateRecycleDirectory'));
    return;
  }
  
  try {
    // 根据回收站配置显示不同的确认消息
    const confirmTitle = recycleEnabled.value ? t.value('confirmBatchMoveToRecycle') : t.value('batchDeleteConfirm');
    const confirmContent = recycleEnabled.value 
      ? t.value('confirmBatchMoveToRecycleContent', { count: tabState.selectedKeys.length })
      : t.value('batchDeleteConfirmContent', { count: tabState.selectedKeys.length });
    
    // 弹出确认对话框
    await new Promise((resolve, reject) => {
      Modal.confirm({
        title: confirmTitle,
        content: confirmContent,
        okText: t.value('confirm'),
        cancelText: t.value('cancel'),
        onOk: () => resolve(true),
        onCancel: () => reject(new Error('cancel'))
      });
    });
    
    // 调用批量删除API
    await deleteFilesBatch({
      path: tabState.currentPath,
      filenames: tabState.selectedKeys
    });
    
    // 显示成功消息
    const successMessage = recycleEnabled.value 
      ? t.value('batchMoveToRecycleSuccess')
      : t.value('batchDeleteSuccess');
    Message.success(successMessage);
    
    // 刷新文件列表
    await loadFileList(tabKey, tabState.currentPath);
    
    // 清空选中项
    tabState.selectedKeys = [];
    // 清空图标视图选中项
    if (tabState.iconSelectedKeys) {
      tabState.iconSelectedKeys = [];
    }
  } catch (error) {
    // 如果是用户取消了确认对话框，不显示错误消息
    if (error.message === 'cancel') {
      return;
    }
    
    console.error('批量删除失败:', error);
    Message.error(t.value('batchDeleteFailed'));
  }
};

// 批量权限修改
const handleBatchPermissions = (tabKey) => {
  const tabState = tabStates.value[tabKey];
  if (!tabState || tabState.selectedKeys.length === 0) {
    return;
  }
  
  // 检查是否包含回收站目录
  const containsRecycleDir = tabState.selectedKeys.some(filename => isRecycleDirectory(filename));
  if (containsRecycleDir) {
    Message.warning(t.value('cannotOperateRecycleDirectory'));
    return;
  }
  
  // 设置批量权限弹窗数据
  batchPermissionsModal.selectedCount = tabState.selectedKeys.length;
  batchPermissionsModal.visible = true;
};

// 显示回收站抽屉
const showRecycleDrawer = () => {
  recycleDrawer.visible = true;
};

// 处理批量权限提交
const handleBatchPermissionsSubmit = async (data) => {
  const tabKey = activeKey.value;
  const tabState = tabStates.value[tabKey];
  
  if (!tabState || tabState.selectedKeys.length === 0) {
    return;
  }
  
  try {
    // 调用批量权限修改API
    await changePermissionsBatch({
      path: tabState.currentPath,
      filenames: tabState.selectedKeys,
      permissions: data.permissions,
      user: data.user,
      group: data.group,
      recursive: data.recursive
    });
    
    // 显示成功消息
    Message.success(t.value('batchPermissionsSuccess'));
    
    // 关闭弹窗
    batchPermissionsModal.visible = false;
    
    // 刷新文件列表
    await loadFileList(tabKey, tabState.currentPath);
    
    // 清空选中项
    tabState.selectedKeys = [];
    // 清空图标视图选中项
    if (tabState.iconSelectedKeys) {
      tabState.iconSelectedKeys = [];
    }
  } catch (error) {
    console.error('批量权限修改失败:', error);
    Message.error(t.value('batchPermissionsFailed'));
  }
};

// 批量压缩文件
const handleBatchCompress = async (tabKey) => {
  const tabState = tabStates.value[tabKey];
  if (!tabState || tabState.selectedKeys.length === 0) {
    return;
  }
  
  // 检查是否包含回收站目录
  const containsRecycleDir = tabState.selectedKeys.some(filename => isRecycleDirectory(filename));
  if (containsRecycleDir) {
    Message.warning(t.value('cannotOperateRecycleDirectory'));
    return;
  }
  
  try {
    // 设置批量压缩抽屉数据
    const currentPath = getCurrentPath(tabKey);
    batchCompressDrawer.sourcePath = currentPath;
    batchCompressDrawer.sourceNames = tabState.selectedKeys;
    // 清空图标视图选中项
    if (tabState.iconSelectedKeys) {
      tabState.iconSelectedKeys = [];
    }
    batchCompressDrawer.destinationPath = currentPath;
    
    // 不再在File.vue中生成文件名，让FileBatchCompress.vue组件自己处理
    // 清空archiveName，让组件生成默认文件名
    batchCompressDrawer.archiveName = '';
    batchCompressDrawer.visible = true;
  } catch (error) {
    console.error('批量压缩准备失败:', error);
    Message.error(t.value('batchCompressFailed'));
  }
};


const handleContextRename = () => {
  if (contextMenu.record && contextMenu.tabKey) {
    handleRename(contextMenu.tabKey, contextMenu.record);
  }
  hideContextMenu();
};

const handleContextPermissions = (tabKey, record) => {
  // 如果没有提供tabKey和record参数，则从contextMenu获取
  const currentTabKey = tabKey || contextMenu.tabKey;
  const currentRecord = record || contextMenu.record;
  
  if (currentRecord && currentTabKey) {
    // 禁止操作回收站目录
    if (isRecycleDirectory(currentRecord.filename)) {
      Message.warning(t.value('cannotOperateRecycleDirectory'));
      hideContextMenu();
      return;
    }
    // 直接使用与操作列相同的逻辑
    permissionsModal.record = currentRecord;
    permissionsModal.permissions = currentRecord.permissions || '755';
    permissionsModal.user = currentRecord.user || '';
    permissionsModal.group = currentRecord.group || '';
    permissionsModal.visible = true;
  }
  hideContextMenu();
};



const handleChangePermissions = async (data) => {
  try {
    const { record, permissions, user, group, recursive } = data;
    const tabKey = contextMenu.tabKey || activeKey.value;
    
    // 验证权限格式（仅当提供了权限参数时验证）
    if (permissions && !/^[0-7]{3}$/.test(permissions)) {
      throw new Error(t.value('invalidPermissionsFormat'));
    }
    
    const response = await changePermissions({
      path: getCurrentPath(tabKey),
      filename: record.filename,
      permissions: permissions || undefined,
      user: user || undefined,
      group: group || undefined,
      recursive
    });
    
    if (response.code === 200) {
      Message.success(t.value('permissionsChanged'));
      permissionsModal.visible = false;
      refresh(tabKey);
    }
  } catch (error) {
    console.error('修改权限失败:', error);
    Message.error(t.value('changePermissionsFailed') + ': ' + (error.message || t.value('unknownError')));
  }
};

const handleContextDetails = () => {
  if (contextMenu.record) {
    handleShowDetails(contextMenu.record);
  }
  hideContextMenu();
};

const handleContextOpen = () => {
  if (contextMenu.record && contextMenu.tabKey) {
    handleOpenFile(contextMenu.tabKey, contextMenu.record);
  }
  hideContextMenu();
};

const handleContextOpenImage = () => {
  if (contextMenu.record && contextMenu.tabKey) {
    handleOpenImage(contextMenu.tabKey, contextMenu.record);
  }
  hideContextMenu();
};

// ========== 文件编辑器操作 ==========
const handleOpenFile = (tabKey, record) => {
  if (record && !record.is_directory) {
    const currentPath = getCurrentPath(tabKey);
    
    // 处理符号链接：提取实际文件名（忽略 " -> 目标路径" 部分）
    let actualFilename = record.filename;
    if (actualFilename.includes(' -> ')) {
      actualFilename = actualFilename.split(' -> ')[0].trim();
    }
    
    // 处理文件名中可能包含的路径部分
    if (actualFilename.includes('/')) {
      const parts = actualFilename.split('/');
      const fileName = parts.pop();
      const subPath = parts.join('/');
      fileEditor.path = currentPath === '/' ? `/${subPath}` : `${currentPath}/${subPath}`;
      fileEditor.name = fileName;
    } else {
      fileEditor.path = currentPath;
      fileEditor.name = actualFilename;
    }
    
    fileEditor.visible = true;
  }
};

// 处理文件编辑器中切换文件
const handleFileEditorChangeFile = (fileInfo) => {
  fileEditor.path = fileInfo.path;
  fileEditor.name = fileInfo.fileName;
  // 重新加载文件内容会在 FileEdit 组件中自动处理
};

const handleFileEditorClose = () => {
  fileEditor.visible = false;
  fileEditor.path = '';
  fileEditor.name = '';
};

const handleFileEditorSave = () => {
  // 文件保存后的处理逻辑
  Message.success(t.value('fileSaved'));
};

// 图片监视器操作
const handleOpenImage = (tabKey, record) => {
  if (record && !record.is_directory) {
    // 检查文件是否为图片格式
    if (!isImageFile(record.filename)) {
      Message.warning(t.value('fileCannotBeOpenedAsImage'));
      return;
    }
    
    const currentPath = getCurrentPath(tabKey);
    
    // 处理符号链接：提取实际文件名（忽略 " -> 目标路径" 部分）
    let actualFilename = record.filename;
    if (actualFilename.includes(' -> ')) {
      actualFilename = actualFilename.split(' -> ')[0].trim();
    }
    
    // 处理文件名中可能包含的路径部分
    if (actualFilename.includes('/')) {
      const parts = actualFilename.split('/');
      const fileName = parts.pop();
      const subPath = parts.join('/');
      imageMonitor.path = currentPath === '/' ? `/${subPath}` : `${currentPath}/${subPath}`;
      imageMonitor.name = fileName;
    } else {
      imageMonitor.path = currentPath;
      imageMonitor.name = actualFilename;
    }
    
    imageMonitor.visible = true;
  }
}

const handleImageMonitorClose = () => {
  imageMonitor.visible = false;
  imageMonitor.path = '';
  imageMonitor.name = '';
};

const handleImageLoaded = (info) => {
  // 图片加载完成后的处理逻辑
  console.log('图片加载完成:', info);
};

// ========== 操作按钮 ==========
const handleCreateFolder = () => {
  showCreateFolderModal();
};

// 创建文件夹表单数据
const createFolderForm = reactive({
  name: ''
});

// 创建文件夹模态框引用
const createFolderModalRef = ref(null);

// 显示创建文件夹模态框
const showCreateFolderModal = () => {
  createFolderForm.name = '';
  Modal.open({
    title: t.value('createFolder'),
    content: () => h('div', [
      h('label', { style: { display: 'block', marginBottom: '8px' } }, t.value('enterFolderName')),
      h(AInput, {
        placeholder: t.value('enterFolderName'),
        modelValue: createFolderForm.name,
        'onUpdate:modelValue': (value) => {
          createFolderForm.name = value;
        },
        style: { width: '100%' }
      })
    ]),
    okText: t.value('create'),
    cancelText: t.value('cancel'),
    onOk: handleCreateFolderSubmit,
    onCancel: () => {
      createFolderForm.name = '';
    }
  });
};

// 处理创建文件夹提交
const handleCreateFolderSubmit = async () => {
  if (!createFolderForm.name.trim()) {
    Message.error(t.value('folderNameCannotBeEmpty'));
    return false; // 阻止关闭模态框
  }
  
  try {
    const currentPath = getCurrentPath(activeKey.value);
    await createDirectory({
      path: currentPath,
      dir_name: createFolderForm.name
    });
    Message.success(`${t.value('folderCreated')}: ${createFolderForm.name}`);
    // 刷新文件列表
    refresh(activeKey.value);
    createFolderForm.name = ''; // 清空表单
  } catch (error) {
    console.error('创建文件夹失败:', error);
    Message.error(t.value('createFolderFailed') || '创建文件夹失败');
    return false; // 阻止关闭模态框
  }
};

// 创建文件表单数据
const createFileForm = reactive({
  name: ''
});

const handleCreateFile = () => {
  createFileForm.name = '';
  Modal.open({
    title: t.value('createFile'),
    content: () => h('div', [
      h('label', { style: { display: 'block', marginBottom: '8px' } }, t.value('enterFileName')),
      h(AInput, {
        placeholder: t.value('enterFileName'),
        modelValue: createFileForm.name,
        'onUpdate:modelValue': (value) => {
          createFileForm.name = value;
        },
        style: { width: '100%' }
      })
    ]),
    okText: t.value('create'),
    cancelText: t.value('cancel'),
    onOk: handleCreateFileSubmit,
    onCancel: () => {
      createFileForm.name = '';
    }
  });
};

// 处理创建文件提交
const handleCreateFileSubmit = async () => {
  if (!createFileForm.name.trim()) {
    Message.error(t.value('fileNameCannotBeEmpty'));
    return false; // 阻止关闭模态框
  }
  
  try {
    const currentPath = getCurrentPath(activeKey.value);
    await createFile({
      path: currentPath,
      file_name: createFileForm.name
    });
    Message.success(`${t.value('fileCreated')}: ${createFileForm.name}`);
    // 刷新文件列表
    refresh(activeKey.value);
    createFileForm.name = ''; // 清空表单
  } catch (error) {
    console.error('创建文件失败:', error);
    Message.error(t.value('createFileFailed') || '创建文件失败');
    return false; // 阻止关闭模态框
  }
};

const handleCreateLink = () => {
  // 使用现有的符号链接抽屉来创建链接文件
  // 设置默认值
  const currentPath = getCurrentPath(activeKey.value);
  symlinkDrawer.sourcePath = currentPath;
  symlinkDrawer.sourceName = ''; // 保持为空，让用户可以输入或选择源文件
  symlinkDrawer.destinationPath = currentPath;
  symlinkDrawer.destinationName = '';
  symlinkDrawer.linkType = 'symlink'; // 设置默认链接类型
  symlinkDrawer.visible = true;
  
  // 添加一个提示，告诉用户可以点击文件夹图标来选择源文件
  Message.info(t.value('selectSourceFileOrEnterManually'));
};

const handleDownloadRemote = () => {
  // 设置默认值
  const currentPath = getCurrentPath(activeKey.value);
  remoteDownloadDrawer.url = '';
  remoteDownloadDrawer.destinationPath = currentPath;
  remoteDownloadDrawer.filename = '';
  remoteDownloadDrawer.visible = true;
};

const handleDownload = async (record) => {
  // 检查是否为文件夹，文件夹不允许下载
  if (record.is_directory) {
    Message.warning(t.value('folderCannotBeDownloaded'));
    return;
  }
  
  try {
    const currentPath = getCurrentPath(activeKey.value);
    
    // 处理符号链接：提取实际文件名（忽略 " -> 目标路径" 部分）
    let actualFilename = record.filename;
    if (actualFilename.includes(' -> ')) {
      actualFilename = actualFilename.split(' -> ')[0].trim();
    }
    
    // 处理包含子目录路径的文件下载
    if (actualFilename.includes('/')) {
      const lastSlashIndex = actualFilename.lastIndexOf('/');
      // 确保currentPath末尾有斜杠，避免路径拼接错误
      const normalizedPath = currentPath.endsWith('/') ? currentPath : currentPath + '/';
      const filePath = normalizedPath + actualFilename.substring(0, lastSlashIndex);
      const fileName = actualFilename.substring(lastSlashIndex + 1);
      
      await downloadFile({
        path: filePath,
        filename: fileName
      });
    } else {
      // 原有逻辑，处理普通文件下载
      await downloadFile({
        path: currentPath,
        filename: actualFilename
      });
    }
    
    // 显示开始下载的提示信息，增强用户体验
    Message.success(`${t.value('downloadStarted')}: ${actualFilename}`);
    console.log(`开始下载文件: ${actualFilename}`);
    
  } catch (error) {
    console.error('下载文件失败:', error);
    Message.error(`${t.value('downloadFileFailed')}: ${actualFilename}`);
  }
};

// 显示上传模态框
const handleUpload = () => {
  uploadModal.visible = true;
};

// 处理上传成功
const handleUploadSuccess = () => {
  refresh(activeKey.value);
};

const handleDeleteFile = (key, record) => {
  // 禁止操作回收站目录
  if (isRecycleDirectory(record.filename)) {
    Message.warning(t.value('cannotOperateRecycleDirectory'));
    return;
  }
  
  // 处理符号链接：提取实际文件名（忽略 " -> 目标路径" 部分）
  let actualFilename = record.filename;
  if (actualFilename.includes(' -> ')) {
    actualFilename = actualFilename.split(' -> ')[0].trim();
  }
  
  // 根据回收站配置显示不同的确认消息
  const confirmTitle = recycleEnabled.value ? t.value('confirmMoveToRecycle') : t.value('confirmDelete');
  const confirmContent = recycleEnabled.value 
    ? t.value('confirmMoveToRecycleContent').replace('{filename}', record.filename)
    : t.value('confirmDeleteFile').replace('{filename}', record.filename);
  
  Modal.warning({
    title: confirmTitle,
    content: confirmContent,
    okText: t.value('confirm'),
    cancelText: t.value('cancel'),
    onOk: async () => {
      try {
        const currentPath = getCurrentPath(key);
        await deleteFile({
          path: currentPath,
          filename: actualFilename
        });
        const successMessage = recycleEnabled.value 
          ? `${t.value('fileMovedToRecycle')}: ${record.filename}`
          : `${t.value('fileDeleted')}: ${record.filename}`;
        Message.success(successMessage);
        refresh(key);
      } catch (error) {
        console.error('删除文件失败:', error);
        Message.error(`${t.value('deleteFileFailed')}: ${record.filename}`);
      }
    }
  });
};

// 重命名表单数据
const renameForm = reactive({
  name: ''
});

// 移动表单数据
const moveForm = reactive({
  destinationPath: '',
  destinationName: ''
});

// 剪贴板状态管理
const clipboard = reactive({
  hasContent: false,
  operation: '', // 'copy' 或 'move'
  sourcePath: '',
  sourceName: '',
  sourceKey: '' // 添加这一行，用于保存源标签页key
});

// 移动抽屉数据
const moveDrawer = reactive({
  visible: false,
  sourcePath: '',
  sourceName: '',
  destinationPath: '',
  destinationName: ''
});

// 复制抽屉数据
const copyDrawer = reactive({
  visible: false,
  sourcePath: '',
  sourceName: '',
  destinationPath: '',
  destinationName: ''
});

// 压缩抽屉数据
const compressDrawer = reactive({
  visible: false,
  sourcePath: '',
  sourceNames: [],
  destinationPath: '',
  archiveName: '',
  loading: false // 添加加载状态
});

// 批量压缩抽屉数据
const batchCompressDrawer = reactive({
  visible: false,
  sourcePath: '',
  sourceNames: [],
  destinationPath: '',
  archiveName: '',
  loading: false // 添加加载状态
});

// 解压抽屉数据
const decompressDrawer = reactive({
  visible: false,
  sourcePath: '',
  sourceName: '',
  destinationPath: '',
  loading: false // 添加加载状态
});

// Mini文件管理器数据
const miniFileManager = reactive({
  visible: false,
  initialPath: '/',
  targetField: '', // 记录目标字段（destinationPath 或 destinationName 或 archiveName）
  selectMode: 'directory' // 选择模式：'directory' 或 'file'
});

// 符号链接抽屉数据
const symlinkDrawer = reactive({
  visible: false,
  sourcePath: '',
  sourceName: '',
  destinationPath: '',
  destinationName: '',
  linkType: 'symlink' // 添加链接类型，默认为符号链接
});

// 远程下载抽屉数据
const remoteDownloadDrawer = reactive({
  visible: false,
  url: '',
  destinationPath: '',
  filename: '',
  verifySsl: true, // 添加SSL证书验证选项，默认启用
  isDownloading: false, // 添加下载状态
  downloadProgress: 0   // 添加下载进度
});

// 文件上传模态框数据
const uploadModal = reactive({
  visible: false
});

const fileUploadRef = ref(null);
const dragOver = ref(false);

// 全局拖拽上传事件处理
let dragCounter = 0;

const handleGlobalDragEnter = (e) => {
  e.preventDefault();
  if (e.dataTransfer.types.includes('Files')) {
    dragCounter++;
    dragOver.value = true;
  }
};

const handleGlobalDragOver = (e) => {
  e.preventDefault();
  if (e.dataTransfer.types.includes('Files')) {
    dragOver.value = true;
  }
};

const handleGlobalDragLeave = (e) => {
  e.preventDefault();
  if (e.dataTransfer.types.includes('Files')) {
    dragCounter--;
    if (dragCounter <= 0) {
      dragCounter = 0;
      dragOver.value = false;
    }
  }
};

const handleGlobalDrop = (e) => {
  e.preventDefault();
  dragCounter = 0;
  dragOver.value = false;
  const files = Array.from(e.dataTransfer.files);
  if (files.length === 0) return;
  fileUploadRef.value?.setFileList(files);
  uploadModal.visible = true;
};

// 下载任务列表模态框数据
const downloadTaskListModal = reactive({
  visible: false
});


const handleRename = (key, record) => {
  // 禁止操作回收站目录
  if (isRecycleDirectory(record.filename)) {
    Message.warning(t.value('cannotOperateRecycleDirectory'));
    return;
  }
  
  // 处理符号链接：提取实际文件名（忽略 " -> 目标路径" 部分）
  let actualFilename = record.filename;
  if (actualFilename.includes(' -> ')) {
    actualFilename = actualFilename.split(' -> ')[0].trim();
  }
  
  renameForm.name = actualFilename;
  Modal.open({
    title: t.value('renameFile'),
    content: () => h('div', [
      h('label', { style: { display: 'block', marginBottom: '8px' } }, t.value('enterNewName')),
      h(AInput, {
        placeholder: t.value('enterNewName'),
        modelValue: renameForm.name,
        'onUpdate:modelValue': (value) => {
          renameForm.name = value;
        },
        style: { width: '100%' }
      })
    ]),
    okText: t.value('confirm'),
    cancelText: t.value('cancel'),
    onOk: () => handleRenameSubmit(key, record),
    onCancel: () => {
      renameForm.name = actualFilename;
    }
  });
};

// 处理重命名提交
const handleShowDetails = (record) => {
  detailsModal.record = record;
  detailsModal.visible = true;
};

const handleRenameSubmit = async (key, record) => {
  if (!renameForm.name.trim()) {
    Message.error(t.value('nameCannotBeEmpty'));
    return false; // 阻止关闭模态框
  }
  
  // 处理符号链接：提取实际文件名（忽略 " -> 目标路径" 部分）
  let actualFilename = record.filename;
  if (actualFilename.includes(' -> ')) {
    actualFilename = actualFilename.split(' -> ')[0].trim();
  }
  
  if (renameForm.name === actualFilename) {
    // 名称未改变，直接关闭模态框
    return true;
  }
  
  try {
    const currentPath = getCurrentPath(key);
    await renameFile({
      path: currentPath,
      old_name: actualFilename,
      new_name: renameForm.name
    });
    Message.success(`${t.value('fileRenamed')}: ${actualFilename} -> ${renameForm.name}`);
    refresh(key);
    renameForm.name = actualFilename; // 重置表单
  } catch (error) {
    console.error('重命名失败:', error);
    Message.error(t.value('renameFailed'));
    return false; // 阻止关闭模态框
  }
};

// 处理移动文件/文件夹
const handleMove = (key, record) => {
  // 禁止操作回收站目录
  if (isRecycleDirectory(record.filename)) {
    Message.warning(t.value('cannotOperateRecycleDirectory'));
    return;
  }
  
  // 处理符号链接：提取实际文件名（忽略 " -> 目标路径" 部分）
  let actualFilename = record.filename;
  if (actualFilename.includes(' -> ')) {
    actualFilename = actualFilename.split(' -> ')[0].trim();
  }
  
  // 设置抽屉数据，但不显示对话框
  moveDrawer.sourcePath = getCurrentPath(key);
  moveDrawer.sourceName = actualFilename;
  moveDrawer.destinationPath = getCurrentPath(key);
  
  // 处理文件名中包含子目录路径的情况，提取实际文件名
  let targetFileName = actualFilename;
  if (actualFilename.includes('/')) {
    const lastSlashIndex = actualFilename.lastIndexOf('/');
    targetFileName = actualFilename.substring(lastSlashIndex + 1);
  }
  
  moveDrawer.destinationName = targetFileName;
  
  // 更新剪贴板状态，标记为移动操作
  clipboard.hasContent = true;
  clipboard.operation = 'move';
  
  // 显示移动成功的提示
  Message.success(`${t.value('fileReadyToMove')}: ${actualFilename}`);
};

// 处理粘贴操作
const handlePaste = async () => {
  if (!clipboard.hasContent) return;
  
  // 设置目标路径为当前路径
  const currentPath = getCurrentPath(activeKey.value);
  const sourcePath = clipboard.sourcePath || copyDrawer.sourcePath || moveDrawer.sourcePath; // 优先使用剪贴板中的源路径
  
  if (clipboard.operation === 'move') {
    // 判断是否在同一目录下
    if (currentPath === sourcePath) {
      // 在同一目录下，显示移动对话框，并添加-backup后缀
      moveDrawer.destinationPath = currentPath;
      
      // 为同一目录下的移动添加-backup后缀
      let targetFileName = moveDrawer.destinationName;
      const fileNameParts = targetFileName.split('.');
      if (fileNameParts.length > 1) {
        // 如果文件有扩展名，将-backup插入到文件名和扩展名之间
        const extension = fileNameParts.pop();
        const fileNameWithoutExtension = fileNameParts.join('.');
        moveDrawer.destinationName = `${fileNameWithoutExtension}-backup.${extension}`;
      } else {
        // 如果文件没有扩展名，直接加上-backup后缀
        moveDrawer.destinationName = `${targetFileName}-backup`;
      }
      
      moveDrawer.visible = true;
    } else {
      // 不在同一目录下，直接移动文件，保持原文件名
      try {
        await moveFileOrDirectory({
          source_path: moveDrawer.sourcePath,
          source_name: moveDrawer.sourceName,
          destination_path: currentPath,
          destination_name: moveDrawer.destinationName
        });
        
        Message.success(`${t.value('fileMoved')}: ${moveDrawer.sourceName} -> ${currentPath}/${moveDrawer.destinationName}`);
        refresh(activeKey.value);
        
        // 清空剪贴板状态
        clipboard.hasContent = false;
        clipboard.operation = null;
      } catch (error) {
        console.error('移动失败:', error);
        Message.error(t.value('moveFailed'));
      }
    }
  } else if (clipboard.operation === 'copy') {
    // 判断是否在同一目录下
    if (currentPath === sourcePath) {
      // 在同一目录下，显示复制对话框，并添加-backup后缀
      copyDrawer.destinationPath = currentPath;
      
      // 为同一目录下的复制添加-backup后缀
      let targetFileName = copyDrawer.destinationName;
      const fileNameParts = targetFileName.split('.');
      if (fileNameParts.length > 1) {
        // 如果文件有扩展名，将-backup插入到文件名和扩展名之间
        const extension = fileNameParts.pop();
        const fileNameWithoutExtension = fileNameParts.join('.');
        copyDrawer.destinationName = `${fileNameWithoutExtension}-backup.${extension}`;
      } else {
        // 如果文件没有扩展名，直接加上-backup后缀
        copyDrawer.destinationName = `${targetFileName}-backup`;
      }
      
      copyDrawer.visible = true;
    } else {
      // 不在同一目录下，直接复制文件，保持原文件名
      try {
        await copyFileOrDirectory({
          source_path: copyDrawer.sourcePath,
          source_name: copyDrawer.sourceName,
          destination_path: currentPath,
          destination_name: copyDrawer.destinationName // 保持原文件名
        });
        
        Message.success(`${t.value('fileCopied')}: ${copyDrawer.sourceName} -> ${currentPath}/${copyDrawer.destinationName}`);
        refresh(activeKey.value);
        
        // 清空剪贴板状态
        clipboard.hasContent = false;
        clipboard.operation = null;
        clipboard.sourceKey = null;
      } catch (error) {
        console.error('复制失败:', error);
        Message.error(t.value('copyFailed'));
      }
    }
  }
};

// 处理移动提交
const handleMoveSubmit = async (data) => {
  if (!data.destinationPath.trim()) {
    Message.error(t.value('destinationPathCannotBeEmpty'));
    return false;
  }
  
  try {
    await moveFileOrDirectory({
      source_path: data.sourcePath,
      source_name: data.sourceName,
      destination_path: data.destinationPath,
      destination_name: data.destinationName
    });
    
    Message.success(`${t.value('fileMoved')}: ${data.sourceName} -> ${data.destinationPath}/${data.destinationName}`);
    moveDrawer.visible = false;
    
    // 更新 moveDrawer 的值以便下次使用
    moveDrawer.destinationPath = data.destinationPath;
    moveDrawer.destinationName = data.destinationName;
    
    refresh(activeKey.value);
    
    // 清空剪贴板状态
    clipboard.hasContent = false;
    clipboard.operation = null;
  } catch (error) {
    console.error('移动失败:', error);
    Message.error(t.value('moveFailed'));
    return false;
  }
};

// 处理移动对话框中的 Mini 文件管理器显示
const handleMoveMiniFileManager = (targetField) => {
  showMiniFileManager(targetField, false);
};

// 处理右键菜单中的移动操作
const handleContextMove = () => {
  if (contextMenu.record && contextMenu.tabKey) {
    handleMove(contextMenu.tabKey, contextMenu.record);
  }
  hideContextMenu();
};

// 处理复制文件/文件夹
const handleCopy = (key, record) => {
  // 禁止操作回收站目录
  if (isRecycleDirectory(record.filename)) {
    Message.warning(t.value('cannotOperateRecycleDirectory'));
    return;
  }
  
  // 处理符号链接：提取实际文件名（忽略 " -> 目标路径" 部分）
  let actualFilename = record.filename;
  if (actualFilename.includes(' -> ')) {
    actualFilename = actualFilename.split(' -> ')[0].trim();
  }
  
  // 设置抽屉数据，但不显示对话框
  copyDrawer.sourcePath = getCurrentPath(key);
  copyDrawer.sourceName = actualFilename;
  copyDrawer.destinationPath = getCurrentPath(key);
  
  // 处理文件名中包含子目录路径的情况，提取实际文件名
  let targetFileName = actualFilename;
  if (actualFilename.includes('/')) {
    const lastSlashIndex = actualFilename.lastIndexOf('/');
    targetFileName = actualFilename.substring(lastSlashIndex + 1);
  }
  
  // 注意：这里不再默认添加-backup后缀，而是保持原始文件名
  // 后缀只在粘贴时判断是否需要添加
  copyDrawer.destinationName = targetFileName;
  
  // 更新剪贴板状态，标记为复制操作
  clipboard.hasContent = true;
  clipboard.operation = 'copy';
  clipboard.sourceKey = key; // 保存源标签页key，用于判断是否在同一目录
  clipboard.sourcePath = getCurrentPath(key); // 保存源路径，用于判断是否在同一目录

  // 显示复制成功的提示
  Message.success(`${t.value('fileCopiedToClipboard')}: ${actualFilename}`);
};

// 处理复制提交
const handleCopySubmit = async (data) => {
  if (!data.destinationPath.trim()) {
    Message.error(t.value('destinationPathCannotBeEmpty'));
    return false;
  }
  
  try {
    await copyFileOrDirectory({
      source_path: data.sourcePath,
      source_name: data.sourceName,
      destination_path: data.destinationPath,
      destination_name: data.destinationName
    });
    
    Message.success(`${t.value('fileCopied')}: ${data.sourceName} -> ${data.destinationPath}/${data.destinationName}`);
    copyDrawer.visible = false;
    
    // 更新 copyDrawer 的值以便下次使用
    copyDrawer.destinationPath = data.destinationPath;
    copyDrawer.destinationName = data.destinationName;
    
    // 刷新文件列表
    refresh(activeKey.value);
    
    // 清空剪贴板状态
    clipboard.hasContent = false;
    clipboard.operation = null;
    clipboard.sourceKey = null;
  } catch (error) {
    console.error('复制失败:', error);
    Message.error(t.value('copyFailed'));
    return false;
  }
};

// 处理复制对话框中的 Mini 文件管理器显示
const handleCopyMiniFileManager = (targetField) => {
  showMiniFileManager(targetField, true);
};

// 处理右键菜单中的复制操作
const handleContextCopy = () => {
  if (contextMenu.record && contextMenu.tabKey) {
    handleCopy(contextMenu.tabKey, contextMenu.record);
  }
  hideContextMenu();
};

// 处理压缩文件/目录
const handleCompress = (key, record) => {
  // 禁止操作回收站目录
  if (isRecycleDirectory(record.filename)) {
    Message.warning(t.value('cannotOperateRecycleDirectory'));
    return;
  }
  
  // 处理符号链接：提取实际文件名（忽略 " -> 目标路径" 部分）
  let actualFilename = record.filename;
  if (actualFilename.includes(' -> ')) {
    actualFilename = actualFilename.split(' -> ')[0].trim();
  }
  
  // 设置抽屉数据
  compressDrawer.sourcePath = getCurrentPath(key);
  compressDrawer.sourceNames = [actualFilename];
  compressDrawer.destinationPath = getCurrentPath(key);
  
  // 处理文件名中包含子目录路径的情况，提取实际文件名
  let baseFileName = actualFilename;
  if (actualFilename.includes('/')) {
    const lastSlashIndex = actualFilename.lastIndexOf('/');
    baseFileName = actualFilename.substring(lastSlashIndex + 1);
  }
  
  compressDrawer.archiveName = `${baseFileName}.zip`;
  compressDrawer.visible = true;
};

// 处理解压文件
const handleDecompress = (key, record) => {
  // 处理符号链接：提取实际文件名（忽略 " -> 目标路径" 部分）
  let actualFilename = record.filename;
  if (actualFilename.includes(' -> ')) {
    actualFilename = actualFilename.split(' -> ')[0].trim();
  }
  
  // 设置抽屉数据
  decompressDrawer.sourcePath = getCurrentPath(key);
  decompressDrawer.sourceName = actualFilename;
  decompressDrawer.destinationPath = getCurrentPath(key);
  decompressDrawer.visible = true;
};

// 处理压缩提交
const handleCompressSubmit = async () => {
  if (!compressDrawer.destinationPath.trim()) {
    Message.error(t.value('destinationPathCannotBeEmpty'));
    return false;
  }
  
  if (!compressDrawer.archiveName.trim()) {
    Message.error(t.value('archiveNameCannotBeEmpty'));
    return false;
  }
  
  try {
    // 设置加载状态
    compressDrawer.loading = true;

    await compressFiles({
      source_path: compressDrawer.sourcePath,
      source_names: compressDrawer.sourceNames,
      destination_path: compressDrawer.destinationPath,
      archive_name: compressDrawer.archiveName
    });

    Message.success(`${t.value('fileCompressed')}: ${compressDrawer.sourceNames.join(', ')} -> ${compressDrawer.destinationPath}/${compressDrawer.archiveName}`);
    compressDrawer.visible = false;
    refresh(activeKey.value);
  } catch (error) {
    console.error('压缩失败:', error);
    Message.error(t.value('compressFailed'));
    return false;
  } finally {
    compressDrawer.loading = false;
  }
};

// 处理压缩对话框中的 Mini 文件管理器显示
const handleCompressMiniFileManager = (targetField) => {
  showMiniFileManager(targetField, false);
};

// 处理批量压缩提交
const handleBatchCompressSubmit = async (data) => {
  if (!data.destinationPath.trim()) {
    Message.error(t.value('destinationPathCannotBeEmpty'));
    return false;
  }
  
  if (!data.archiveName.trim()) {
    Message.error(t.value('archiveNameCannotBeEmpty'));
    return false;
  }
  
  try {
    // 设置加载状态
    batchCompressDrawer.loading = true;

    await compressFilesBatch({
      source_path: data.sourcePath,
      source_names: data.sourceNames,
      destination_path: data.destinationPath,
      archive_name: data.archiveName
    });

    Message.success(`${t.value('filesCompressed')}: ${data.sourceNames.join(', ')} -> ${data.destinationPath}/${data.archiveName}`);
    batchCompressDrawer.visible = false;
    refresh(activeKey.value);
  } catch (error) {
    console.error('批量压缩失败:', error);
    Message.error(t.value('compressFailed'));
    return false;
  } finally {
    batchCompressDrawer.loading = false;
  }
};

// 处理批量压缩对话框中的 Mini 文件管理器显示
const handleBatchCompressMiniFileManager = (targetField) => {
  showMiniFileManager(targetField, false);
};

// 处理解压提交
const handleDecompressSubmit = async (data) => {
  if (!data.destinationPath.trim()) {
    Message.error(t.value('destinationPathCannotBeEmpty'));
    return false;
  }
  
  try {
    // 设置加载状态
    decompressDrawer.loading = true;

    await decompressFile({
      source_path: data.sourcePath,
      source_name: data.sourceName,
      destination_path: data.destinationPath
    });

    Message.success(`${t.value('fileDecompressed')}: ${data.sourceName} -> ${data.destinationPath}`);
    decompressDrawer.visible = false;
    
    // 更新 decompressDrawer 的值以便下次使用
    decompressDrawer.destinationPath = data.destinationPath;
    
    refresh(activeKey.value);
  } catch (error) {
    console.error('解压失败:', error);
    Message.error(t.value('decompressFailed'));
    return false;
  } finally {
    decompressDrawer.loading = false;
  }
};

// 处理解压对话框中的 Mini 文件管理器显示
const handleDecompressMiniFileManager = (targetField) => {
  showMiniFileManager(targetField, false);
};

// 处理右键菜单中的解压操作
const handleContextDecompress = () => {
  if (contextMenu.record && contextMenu.tabKey) {
    handleDecompress(contextMenu.tabKey, contextMenu.record);
  }
  hideContextMenu();
};

// 处理右键菜单中的压缩操作
const handleContextCompress = () => {
  if (contextMenu.record && contextMenu.tabKey) {
    handleCompress(contextMenu.tabKey, contextMenu.record);
  }
  hideContextMenu();
};



// 处理符号链接提交
const handleSymlinkSubmit = async (data) => {
  if (!data.destinationPath.trim()) {
    Message.error(t.value('destinationPathCannotBeEmpty'));
    return false;
  }
  
  if (!data.sourceName.trim()) {
    Message.error(t.value('sourceFileNameCannotBeEmpty'));
    return false;
  }
  
  try {
    await createSymlink({
      source_path: data.sourcePath,
      source_name: data.sourceName,
      destination_path: data.destinationPath,
      destination_name: data.destinationName,
      link_type: data.linkType
    });
    
    const linkTypeText = data.linkType === 'symlink' ? t.value('softlink') : t.value('hardlink');
    Message.success(`${linkTypeText} ${t.value('created')}: ${data.sourceName} -> ${data.destinationPath}/${data.destinationName}`);
    symlinkDrawer.visible = false;
    
    // 更新 symlinkDrawer 的值以便下次使用
    symlinkDrawer.sourcePath = data.sourcePath;
    symlinkDrawer.sourceName = data.sourceName;
    symlinkDrawer.destinationPath = data.destinationPath;
    symlinkDrawer.destinationName = data.destinationName;
    symlinkDrawer.linkType = data.linkType;
    
    refresh(activeKey.value);
  } catch (error) {
    console.error('创建符号链接失败:', error);
    Message.error(t.value('createSymlinkFailed'));
    return false;
  }
};

// 处理符号链接对话框中的 Mini 文件管理器显示
const handleSymlinkMiniFileManager = (targetField) => {
  showMiniFileManager(targetField, false);
};

// 处理远程下载提交
const handleRemoteDownloadSubmit = async (data) => {
  if (!data.url.trim()) {
    Message.error(t.value('urlCannotBeEmpty'));
    return false;
  }
  
  if (!data.destinationPath.trim()) {
    Message.error(t.value('destinationPathCannotBeEmpty'));
    return false;
  }
  
  try {
    // 设置下载状态和初始进度
    remoteDownloadDrawer.isDownloading = true;
    remoteDownloadDrawer.downloadProgress = 0;
    
    // 开始下载并获取下载ID，传递SSL证书验证参数
    const response = await downloadRemoteFile({
      url: data.url,
      destination_path: data.destinationPath,
      filename: data.filename || undefined,
      verify_ssl: data.verifySsl // 传递SSL证书验证选项
    });
    
    // 获取下载ID
    const downloadId = response.data.download_id;
    
    // 显示任务已启动的消息
    Message.success(t.value('downloadTaskStarted'));
    
    // 关闭抽屉
    remoteDownloadDrawer.visible = false;
    remoteDownloadDrawer.isDownloading = false;
    
    // 更新 remoteDownloadDrawer 的值以便下次使用
    remoteDownloadDrawer.url = data.url;
    remoteDownloadDrawer.destinationPath = data.destinationPath;
    remoteDownloadDrawer.filename = data.filename;
    remoteDownloadDrawer.verifySsl = data.verifySsl;
    
    // 可选：刷新文件列表
    refresh(activeKey.value);
    
  } catch (error) {
    console.error('远程下载失败:', error);
    // 提供更具体的错误信息
    let errorMessage = t.value('downloadRemoteFailed');
    
    // 特别处理超时错误
    if (error.code === 'ECONNABORTED' || (error.message && error.message.includes('timeout'))) {
      errorMessage = `${t.value('downloadRemoteTimeout') || '下载超时'} (${t.value('pleaseTryAgainOrDownloadSmallerFile')})`;
    } else if (error.response && error.response.data && error.response.data.detail) {
      // 如果后端返回了具体的错误信息，使用它
      errorMessage = error.response.data.detail;
    } else if (error.message) {
      // 如果有错误消息，使用它
      errorMessage = error.message;
    }
    
    // 根据错误类型提供更具体的提示
    if (error.response) {
      switch (error.response.status) {
        case 403:
          errorMessage = t.value('downloadRemoteForbidden') || errorMessage;
          break;
        case 404:
          errorMessage = t.value('downloadRemoteNotFound') || errorMessage;
          break;
        case 408:
          errorMessage = t.value('downloadRemoteTimeout') || errorMessage;
          break;
      }
    }
    
    Message.error(errorMessage);
    // 确保下载状态被重置
    remoteDownloadDrawer.isDownloading = false;
    return false;
  }
};

// 处理远程下载对话框中的 Mini 文件管理器显示
const handleRemoteDownloadMiniFileManager = (targetField) => {
  showMiniFileManager(targetField, false);
};

// 显示下载任务列表
const showDownloadTaskList = () => {
  downloadTaskListModal.visible = true;
};

// 显示终端模态框
const showTerminalModal = () => {
  // 获取当前激活标签页的路径
  const currentPath = getCurrentPath(activeKey.value);
  terminalModal.currentPath = currentPath;
  terminalModal.visible = true;
};


// 显示Mini文件管理器
const showMiniFileManager = (targetField, isCopy = false) => {
  // 处理对象类型的targetField
  if (typeof targetField === 'object' && targetField !== null) {
    miniFileManager.targetField = targetField.field || targetField;
    
    // 如果对象中包含selectMode，则使用传递的selectMode
    if (targetField.selectMode) {
      miniFileManager.selectMode = targetField.selectMode;
    }
    
    // 如果对象中包含initialPath，则使用传递的initialPath
    if (targetField.initialPath) {
      miniFileManager.initialPath = targetField.initialPath;
    } else {
      // 否则根据field设置默认的初始路径
      const field = targetField.field || targetField;
      if (symlinkDrawer.visible && (field === 'sourcePath' || field === 'sourceName')) {
        miniFileManager.initialPath = symlinkDrawer.sourcePath || getCurrentPath(activeKey.value);
      } else if (symlinkDrawer.visible && (field === 'destinationPath' || field === 'destinationName')) {
        miniFileManager.initialPath = symlinkDrawer.destinationPath || getCurrentPath(activeKey.value);
      } else {
        miniFileManager.initialPath = getCurrentPath(activeKey.value);
      }
    }
  } else {
    // 处理字符串类型的targetField
    miniFileManager.targetField = targetField;
    
    // 根据操作类型设置初始路径和选择模式
    if (targetField === 'destinationPath') {
      // 目标路径选择 - 只能选择目录
      miniFileManager.selectMode = 'directory';
      if (isCopy) {
        miniFileManager.initialPath = copyDrawer.destinationPath || getCurrentPath(activeKey.value);
      } else if (compressDrawer.visible) {
        miniFileManager.initialPath = compressDrawer.destinationPath || getCurrentPath(activeKey.value);
      } else if (batchCompressDrawer.visible) {
        miniFileManager.initialPath = batchCompressDrawer.destinationPath || getCurrentPath(activeKey.value);
      } else if (decompressDrawer.visible) {
        miniFileManager.initialPath = decompressDrawer.destinationPath || getCurrentPath(activeKey.value);
      } else if (symlinkDrawer.visible) {
        miniFileManager.initialPath = symlinkDrawer.destinationPath || getCurrentPath(activeKey.value);
      } else {
        miniFileManager.initialPath = moveDrawer.destinationPath || getCurrentPath(activeKey.value);
      }
    } else if (targetField === 'destinationName') {
      // 目标名称选择 - 可以选择文件或目录
      miniFileManager.selectMode = 'file';
      if (isCopy) {
        miniFileManager.initialPath = copyDrawer.destinationPath || getCurrentPath(activeKey.value);
      } else if (symlinkDrawer.visible) {
        miniFileManager.initialPath = symlinkDrawer.destinationPath || getCurrentPath(activeKey.value);
      } else {
        miniFileManager.initialPath = moveDrawer.destinationPath || getCurrentPath(activeKey.value);
      }
    } else if (targetField === 'archiveName') {
      // 压缩文件名选择 - 只能选择目录
      miniFileManager.selectMode = 'directory';
      if (compressDrawer.visible) {
        miniFileManager.initialPath = compressDrawer.destinationPath || getCurrentPath(activeKey.value);
      } else if (batchCompressDrawer.visible) {
        miniFileManager.initialPath = batchCompressDrawer.destinationPath || getCurrentPath(activeKey.value);
      } else {
        miniFileManager.initialPath = getCurrentPath(activeKey.value);
      }
    } else if (targetField === 'sourceName') {
      // 源文件名选择 - 可以选择文件或目录
      miniFileManager.selectMode = 'file';
      if (symlinkDrawer.visible) {
        miniFileManager.initialPath = symlinkDrawer.sourcePath || getCurrentPath(activeKey.value);
      } else {
        miniFileManager.initialPath = getCurrentPath(activeKey.value);
      }
    } else if (targetField === 'sourcePath') {
      // 源文件路径选择 - 根据需求可以选择文件或目录
      // 默认为'directory'，但可以被对象参数覆盖
      miniFileManager.selectMode = 'directory';
      if (symlinkDrawer.visible) {
        miniFileManager.initialPath = symlinkDrawer.sourcePath || getCurrentPath(activeKey.value);
      } else {
        miniFileManager.initialPath = getCurrentPath(activeKey.value);
      }
    }
  }
  
  miniFileManager.visible = true;
};

// 处理Mini文件管理器选择
const handleMiniFileManagerSelect = (selected) => {
  // 判断当前是哪种操作
  if (moveDrawer.visible) {
    // 移动操作
    if (miniFileManager.targetField === 'destinationPath') {
      moveDrawer.destinationPath = selected.path;
    } else if (miniFileManager.targetField === 'destinationName') {
      moveDrawer.destinationName = selected.name || selected.path.split('/').pop();
    }
  } else if (copyDrawer.visible) {
    // 复制操作
    if (miniFileManager.targetField === 'destinationPath') {
      copyDrawer.destinationPath = selected.path;
    } else if (miniFileManager.targetField === 'destinationName') {
      copyDrawer.destinationName = selected.name || selected.path.split('/').pop();
    }
  } else if (compressDrawer.visible) {
    // 压缩操作
    if (miniFileManager.targetField === 'destinationPath') {
      compressDrawer.destinationPath = selected.path;
    } else if (miniFileManager.targetField === 'archiveName') {
      // 对于压缩文件名，我们只更新路径，文件名由用户输入
      compressDrawer.destinationPath = selected.path;
    }
  } else if (batchCompressDrawer.visible) {
    // 批量压缩操作
    if (miniFileManager.targetField === 'destinationPath') {
      batchCompressDrawer.destinationPath = selected.path;
    } else if (miniFileManager.targetField === 'archiveName') {
      // 对于压缩文件名，我们只更新路径，文件名由用户输入
      batchCompressDrawer.destinationPath = selected.path;
    }
  } else if (decompressDrawer.visible) {
    // 解压操作
    if (miniFileManager.targetField === 'destinationPath') {
      decompressDrawer.destinationPath = selected.path;
    }
  } else if (symlinkDrawer.visible) {
    // 符号链接操作
    if (miniFileManager.targetField === 'sourcePath') {
      symlinkDrawer.sourcePath = selected.path;
    } else if (miniFileManager.targetField === 'sourceName') {
      // 对于源文件名，我们只使用文件名部分，不包含路径
      symlinkDrawer.sourceName = selected.name || selected.path.split('/').pop();
    } else if (miniFileManager.targetField === 'destinationPath') {
      symlinkDrawer.destinationPath = selected.path;
    } else if (miniFileManager.targetField === 'destinationName') {
      symlinkDrawer.destinationName = selected.name || selected.path.split('/').pop();
    }
  } else if (remoteDownloadDrawer.visible) {
    // 远程下载操作
    if (miniFileManager.targetField === 'destinationPath') {
      remoteDownloadDrawer.destinationPath = selected.path;
    }
  }
};

// 页面加载
onMounted(() => {
  // 尝试从本地存储恢复标签页状态
  const restored = restoreTabStatesFromLocalStorage();
  
  if (restored) {
    // 如果成功恢复状态，为每个标签页重新加载文件列表
    Object.keys(tabStates.value).forEach(key => {
      loadFileList(key, tabStates.value[key].currentPath);
    });
  } else {
    // 如果没有恢复状态，使用默认初始化
    loadFileList('1', '/opt/blackpotbpanel-v2/server');
  }
  
  // 获取回收站配置
  getRecycleConfigData();
  
  // 添加全局点击事件监听器，用于关闭右键菜单
  document.addEventListener('click', hideContextMenu);
  
  
  // 检测是否为移动端
  checkIsMobile();
  window.addEventListener('resize', checkIsMobile);
  
  // 全局拖拽上传监听
  document.addEventListener('dragenter', handleGlobalDragEnter);
  document.addEventListener('dragover', handleGlobalDragOver);
  document.addEventListener('dragleave', handleGlobalDragLeave);
  document.addEventListener('drop', handleGlobalDrop);
});

// 监听标签页数据变化并保存到本地存储
watch([data, activeKey, tabStates], () => {
  saveTabStatesToLocalStorage();
}, { deep: true });

// 组件卸载时移除事件监听器
onUnmounted(() => {
  document.removeEventListener('click', hideContextMenu);
  window.removeEventListener('resize', checkIsMobile);
});

// 表格列定义
const columns = computed(() => {
  const isMobileView = window.innerWidth <= 768;

  const baseColumns = [
    {
      title: t.value('fileName'),
      dataIndex: 'filename',
      slotName: 'filename',
      width: 250,
      minWidth: 150,
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
      width: 150
    }
  ];
  
  // 在移动端隐藏部分列
  if (isMobileView) {
    return baseColumns.filter(col => 
      !['permissions', 'user', 'group'].includes(col.dataIndex)
    );
  }
  
  return baseColumns;
});
  


// 添加图片模态框宽度计算属性
const imageModalWidth = computed(() => {
  if (window.innerWidth <= 480) {
    return '95%'; // 超小屏
  } else if (window.innerWidth <= 768) {
    return '90%'; // 小屏（移动端）
  } else if (window.innerWidth <= 1024) {
    return 700;   // 中屏（平板）
  } else if (window.innerWidth <= 1200) {
    return 900;   // 大屏
  } else {
    return 1000;  // 超大屏
  }
});

// 添加移动端检测函数
const checkIsMobile = () => {
  isMobile.value = window.innerWidth <= 768;
};

// 在表格列定义之前添加 watch 监听器
// 监听窗口大小变化
watch(() => window.innerWidth, () => {
  checkIsMobile();
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

/* 路径容器样式 */
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
  user-select: none;
}

/* 路径输入框容器 */
.path-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.path-input-wrapper .arco-input-wrapper {
  flex: 1;
}

.action-bar {
  margin: 8px 0 16px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

/* 批量操作菜单样式 */
.batch-operation-menu {
  padding: 8px;
  min-width: 80px;
}

.batch-operation-menu a-link {
  display: block;
  padding: 4px 0;
  text-decoration: none;
}

.batch-operation-menu a-link:hover {
  opacity: 0.8;
}

/* 搜索框右对齐 */
.search-container {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-list-wrapper {
  min-height: 600px;
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

/* 图标视图样式 */
.file-icon-container {
  padding: 16px;
  background: var(--color-bg-2);
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  border: 1px solid var(--color-border);
  min-height: 300px; /* 增加容器最小高度 */
}

.file-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 16px;
}

.file-icon-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px;
  border-radius: 4px;
  cursor: pointer;
  position: relative;
  transition: all 0.2s;
  /* 添加这个属性来创建一个新的层叠上下文 */
  transform: translateZ(0);
}

.file-icon-item:hover {
  background-color: var(--color-fill-2);
}

/* 图标视图选中状态样式 */
.file-icon-item-selected {
  background-color: var(--color-primary-light-1);
  border: 2px solid var(--color-primary);
  padding: 6px;
}

.file-icon-item-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(24, 144, 255, 0.2);
  border: 2px solid var(--color-primary);
  border-radius: 4px;
  pointer-events: none; /* 遮罩不拦截事件 */
  z-index: 1;
}

/* Tooltip 内容样式 */
.tooltip-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 4px 0;
}

.tooltip-item {
  display: flex;
  gap: 8px;
  font-size: 12px;
  line-height: 1.5;
}

.tooltip-label {
  font-weight: 600;
  color: var(--color-text-2);
  white-space: nowrap;
  min-width: 70px;
}

.tooltip-value {
  color: var(--color-text-1);
  word-break: break-all;
  flex: 1;
}

/* Tooltip 主题色适配 - 箭头颜色跟随主题 */
:deep(.arco-tooltip-content) {
  background-color: var(--color-bg-popup);
  color: var(--color-text-1);
  border: 1px solid var(--color-border) !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

:deep(.arco-tooltip-content::before) {
  background-color: var(--color-bg-popup);
  border: 1px solid var(--color-border);
}


.file-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  margin-bottom: 8px;
  color: #9E9E9E;
}

.file-icon.file-directory {
  color: #FFB300;
}

.file-name {
  font-size: 12px;
  text-align: center;
  word-break: break-all;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  line-height: 1.4;
  max-height: 3.2em;
}

/* 列表视图文件名样式 */
.list-filename {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
  display: inline-block;
}

/* 图标视图无数据样式 */
.file-grid-empty {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

.empty-content {
  text-align: center;
  color: #C9CDD4;
}

.empty-text {
  font-size: 14px;
}

/* 表格表头加粗样式 */
:deep(.arco-table-th) {
  font-weight: bold;
}

/* 表格行右键菜单样式 */
:deep(.arco-table-tr) {
  cursor: context-menu;
}

:deep(.arco-table-tr:hover) {
  background-color: var(--color-fill-1) !important;
}

/* 响应式优化 */
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
  
  /* 移动端路径容器样式调整 */
  .path-container {
    min-height: 40px;
    flex-direction: column;
    align-items: stretch;
    padding: 8px 12px;
  }
  
  .path-input-wrapper {
    margin-top: 8px;
  }
  
  /* 移动端搜索框调整 */
  .search-container {
    margin-left: 0;
    margin-top: 8px;
  }
  
  /* 移动端表格适配 */
  :deep(.arco-table-cell),
  :deep(.arco-table-th) {
    padding: 6px 4px !important;
    font-size: 13px;
  }
  
  :deep(.arco-table-tr) {
    min-height: 36px;
  }
}

/* 全局拖拽上传覆盖层 */
.file-drop-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(22, 93, 255, 0.85);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.file-drop-overlay-content {
  text-align: center;
  color: #fff;
}

.file-drop-overlay-content p {
  font-size: 24px;
  margin-top: 16px;
  color: #fff;
}
</style>