<template>
  <div class="filetran-container">
    <div class="split-panel left-panel">
      <div class="panel-header">
        <span><icon-folder style="margin-right: 6px;" />{{ t('localFile') }}</span>
        <div class="host-select-in-header">
          <a-form-item label="127.0.0.1" style="margin-bottom: 0;">
          </a-form-item>
        </div>
      </div>

      <div class="navigation-bar">
        <a-button type="outline" size="large" @click="goToParentDirectory" :disabled="currentPath === '/'">
          <template #icon><icon-left /></template>
          {{ t('goToParentDirectory') }}
        </a-button>

        <div class="path-container">
          <a-breadcrumb class="path-breadcrumb" separator=">" v-show="!showPathInput" @dblclick="startPathEdit">
            <a-breadcrumb-item>
              <a-link @click="goToRoot"><icon-home /></a-link>
            </a-breadcrumb-item>
            <a-breadcrumb-item v-for="(seg, idx) in pathSegments" :key="idx">
              <a-link @click="navigateToPath(idx)">{{ seg.name }}</a-link>
            </a-breadcrumb-item>
          </a-breadcrumb>

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

      <div class="action-bar">
        <a-dropdown>
          <a-button size="small" type="primary">{{ t('create') }}</a-button>
          <template #content>
            <a-doption @click="handleCreateFolder">{{ t('createFolder') }}</a-doption>
            <a-doption @click="handleCreateFile">{{ t('createFile') }}</a-doption>
          </template>
        </a-dropdown>
        <a-button size="small" type="primary" @click="handleUpload">{{ t('uploadFile') }}</a-button>
        <a-button size="small" @click="refresh"><icon-refresh /> {{ t('refresh') }}</a-button>

        <div class="search-container">
          <a-input-search
            v-model="searchKeyword"
            size="small"
            :placeholder="t('searchFile')"
            style="width: 200px;"
            @search="handleSearch"
          />
        </div>
      </div>

      <div class="file-list-wrapper">
        <a-table
          :columns="columns"
          :data="filteredFileList"
          :loading="loading"
          :pagination="false"
          row-key="filename"
          size="medium"
          :scroll="{ x: 'max-content', y: tableScrollY }"
          sticky-header
          :row-selection="getRowSelection()"
          v-model:selectedKeys="selectedRowKeys"
        >
          <template #filename="{ record }">
            <div class="file-item">
              <component
                :is="getFileIcon(record)"
                :size="16"
                :style="{ color: getFileIconColor(record), marginRight: '8px', fontSize: '16px' }"
              />
              <span @click="handleFileClick(record)" style="cursor: pointer;" class="list-filename">{{ record.filename }}</span>
            </div>
          </template>

          <template #size="{ record }">
            <template v-if="record.is_directory">
              <a-link v-if="!calculatedSizes[keyFor(record)]" size="small" type="text" @click="handleCalculateSize(record)">{{ t('calculate') }}</a-link>
              <span v-else-if="calculatedSizes[keyFor(record)].loading">...</span>
              <span v-else-if="calculatedSizes[keyFor(record)].error">{{ t('failed') }}</span>
              <span v-else>{{ calculatedSizes[keyFor(record)].size_human }}</span>
            </template>
            <span v-else>{{ record.size }}</span>
          </template>

          <template #operations="{ record }">
              <a-space size="mini">
                <a-link @click="handleDeleteFile(record)" status="danger">{{ t('delete') }}</a-link>
                <a-link v-if="!record.is_directory" @click="handleSendToRemote(record)">{{ t('sendToRight') }}</a-link>
              </a-space>
            </template>
        </a-table>
      </div>

      <div class="pagination-bar">
        <div class="pagination-left">
          <a-button
            size="small"
            type="primary"
            :disabled="selectedRowKeys.length === 0 || !selectedHostId"
            @click="handleBatchSendToRemote"
          >{{ t('batchSendToRight') }} ({{ selectedRowKeys.length }})</a-button>
        </div>
        <a-pagination
          :total="total"
          :current="page"
          :page-size="pageSize"
          @change="handlePageChange"
          @page-size-change="handlePageSizeChange"
          show-total
          show-page-size
          show-jumper
          size="small"
        />
      </div>
    </div>

    <div class="split-divider"></div>

    <div class="split-panel right-panel">
      <div class="panel-header">
        <span><icon-computer style="margin-right: 6px;" />{{ t('remoteFile') }}</span>
        <div class="host-select-in-header">
          <a-form-item :label="t('selectHosts')" style="margin-bottom: 0;">
            <a-select
              v-model="selectedHostId"
              :placeholder="t('selectHostsPlaceholder')"
              style="width: 280px;"
              :loading="hostsLoading"
              allow-clear
              @change="handleHostChange"
            >
              <a-option
                v-for="host in hostsData"
                :key="host.id"
                :value="host.id"
                :label="`${host.comment || host.address} (${host.address})`"
                :disabled="host.status === 'offline'"
              >
                <a-space>
                  <a-tag :color="host.status === 'online' ? 'green' : 'red'" size="small">
                    {{ host.status === 'online' ? 'ON' : 'OFF' }}
                  </a-tag>
                  <span>{{ host.comment || host.address }}</span>
                  <span style="color: var(--color-text-3); font-size: 12px;">({{ host.address }})</span>
                </a-space>
              </a-option>
            </a-select>
          </a-form-item>
        </div>
      </div>

      <template v-if="selectedHostId">
        <div class="navigation-bar">
          <a-button type="outline" size="large" @click="goToRemoteParent" :disabled="remotePath === '/'">
            <template #icon><icon-left /></template>
            {{ t('goToParentDirectory') }}
          </a-button>

          <div class="path-container">
            <a-breadcrumb class="path-breadcrumb" separator=">" v-show="!showRemotePathInput" @dblclick="startRemotePathEdit">
              <a-breadcrumb-item>
                <a-link @click="goToRemoteRoot"><icon-home /></a-link>
              </a-breadcrumb-item>
              <a-breadcrumb-item v-for="(seg, idx) in remotePathSegments" :key="idx">
                <a-link @click="navigateToRemotePath(idx)">{{ seg.name }}</a-link>
              </a-breadcrumb-item>
            </a-breadcrumb>

            <div class="path-input-wrapper" v-show="showRemotePathInput">
              <a-input
                v-model="remoteEditablePath"
                size="small"
                :placeholder="t('enterFilePath')"
                @press-enter="handleRemotePathChange"
                @blur="cancelRemotePathEdit"
                ref="remotePathInputRef"
              />
            </div>
          </div>
        </div>

        <div class="action-bar">
          <a-dropdown>
            <a-button size="small" type="primary">{{ t('create') }}</a-button>
            <template #content>
              <a-doption @click="handleRemoteCreateFolder">{{ t('createFolder') }}</a-doption>
              <a-doption @click="handleRemoteCreateFile">{{ t('createFile') }}</a-doption>
            </template>
          </a-dropdown>
          <a-button size="small" type="primary" @click="handleRemoteUpload">{{ t('uploadFile') }}</a-button>
          <a-button size="small" @click="refreshRemote"><icon-refresh /> {{ t('refresh') }}</a-button>

          <div class="search-container">
            <a-input-search
              v-model="remoteSearchKeyword"
              size="small"
              :placeholder="t('searchFile')"
              style="width: 200px;"
              @search="handleRemoteSearch"
            />
          </div>
        </div>

        <div class="file-list-wrapper">
          <a-table
            :columns="remoteColumns"
            :data="remoteFileList"
            :loading="remoteLoading"
            :pagination="false"
            row-key="filename"
            size="medium"
            :scroll="{ x: 'max-content', y: tableScrollY }"
            sticky-header
            :row-selection="getRemoteRowSelection()"
            v-model:selectedKeys="remoteSelectedRowKeys"
          >
            <template #filename="{ record }">
              <div class="file-item">
                <component
                  :is="getFileIcon(record)"
                  :size="16"
                  :style="{ color: getFileIconColor(record), marginRight: '8px', fontSize: '16px' }"
                />
                <span @click="handleRemoteFileClick(record)" style="cursor: pointer;" class="list-filename">{{ record.filename }}</span>
              </div>
            </template>

            <template #size="{ record }">
              <span>{{ record.size }}</span>
            </template>

            <template #operations="{ record }">
              <a-space size="mini">
                <a-link @click="handleRemoteDeleteFile(record)" status="danger">{{ t('delete') }}</a-link>
                <a-link v-if="!record.is_directory" @click="handleRemoteSendToLocal(record)">{{ t('sendToLeft') }}</a-link>
              </a-space>
            </template>
          </a-table>
        </div>

        <div class="pagination-bar">
          <div class="pagination-left">
            <a-button
              size="small"
              type="primary"
              :disabled="remoteSelectedRowKeys.length === 0 || !selectedHostId"
              @click="handleRemoteBatchSendToLocal"
            >{{ t('batchSendToLeft') }} ({{ remoteSelectedRowKeys.length }})</a-button>
          </div>
          <a-pagination
            :total="remoteTotal"
            :current="remotePage"
            :page-size="remotePageSize"
            @change="handleRemotePageChange"
            @page-size-change="handleRemotePageSizeChange"
            show-total
            show-page-size
            show-jumper
            size="small"
          />
        </div>
      </template>

      <div v-else class="no-host-placeholder">
        <icon-computer style="font-size: 48px; color: #C9CDD4; margin-bottom: 16px;" />
        <div class="empty-text">{{ t('selectHosts') }}</div>
      </div>
    </div>

    <FileUpload
      ref="fileUploadRef"
      v-model:visible="uploadModalVisible"
      :current-path="currentPath"
      @upload-success="handleUploadSuccess"
    />

    <FileEdit
      :visible="fileEditor.visible"
      :file-path="fileEditor.path"
      :file-name="fileEditor.name"
      @update:visible="fileEditor.visible = $event"
      @close="handleFileEditorClose"
      @save="handleFileEditorSave"
    />

    <FileRemoteUpload
      ref="remoteFileUploadRef"
      v-model:visible="remoteUploadModalVisible"
      :host-id="selectedHostId"
      :current-path="remotePath"
      @upload-success="handleRemoteUploadSuccess"
    />

    <a-modal
      v-model:visible="showScpConfirm"
      :title="scpDirection === 'download' ? t('sendToLeft') : t('sendToRight')"
      @ok="confirmScpSend"
      @cancel="showScpConfirm = false"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
      width="600px"
    >
      <div>
        <p style="margin-bottom: 16px;">{{ scpDirection === 'download' ? t('scpDownloadConfirmContent') : t('scpConfirmContent') }}</p>
        <div style="max-height: 300px; overflow-y: auto; border: 1px solid var(--color-border-2); border-radius: 4px; padding: 12px;">
          <div
            v-for="f in scpSendingFiles"
            :key="f.filename"
            style="display: flex; align-items: center; gap: 8px; padding: 8px; border-bottom: 1px solid var(--color-border-1);"
          >
            <icon-file style="font-size: 16px; color: var(--color-text-2);" />
            <div style="flex: 1; overflow: hidden;">
              <div style="font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ f.filename }}</div>
              <div style="font-size: 12px; color: var(--color-text-3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ f.path }}</div>
            </div>
          </div>
        </div>
      </div>
    </a-modal>
    <!-- SCP传输进度弹窗 -->
    <a-modal
      v-model:visible="showScpProgress"
      :title="t('scpTransferProgress')"
      :footer="false"
      :closable="false"
      width="500px"
    >
      <div style="padding: 16px 0;">
        <div style="margin-bottom: 12px; display: flex; justify-content: space-between;">
          <span>{{ t('scpCurrentFile') }}: {{ scpProgressData.current_file || '-' }}</span>
          <span>{{ scpProgressData.completed_files }}/{{ scpProgressData.total_files }}</span>
        </div>
        <a-progress
          :percent="scpProgressPercent / 100"
          :status="scpProgressData.status === 'failed' ? 'danger' : (scpProgressData.status === 'completed' ? 'success' : 'active')"
          style="margin-bottom: 12px;"
        >
          <template #text="scope">
            {{ (scope.percent * 100).toFixed(2) }}%
          </template>
        </a-progress>
        <div style="font-size: 13px; color: var(--color-text-3); margin-bottom: 16px; text-align: center;">
          {{ scpProgressData.message || '' }}
        </div>
        <div style="text-align: center;">
          <a-button
            v-if="scpProgressData.status === 'pending' || scpProgressData.status === 'running'"
            status="danger"
            @click="cancelScpSend"
          >{{ t('cancel') }}</a-button>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted, nextTick, watch, h } from 'vue';
import { Message, Modal, Input } from '@arco-design/web-vue';
const AInput = Input;
import { IconLeft, IconRefresh, IconHome, IconFolder, IconComputer, IconFile } from '@arco-design/web-vue/es/icon';
import { t } from '../../utils/locale.js';
import {
  getFileList,
  createDirectory,
  createFile,
  deleteFile,
  downloadFile,
  getDirectorySize,
  searchFiles,
} from '../../api/file.js';
import { getHosts, getFileTransferHosts, getRemoteFileList, createRemoteFile, uploadFileToRemote, deleteRemoteFile, startSCPTransfer, connectSCPProgress, cancelSCPTransfer } from '../../api/host.js';
import { getFileIcon, getFileIconColor, canOpenFile } from '../../utils/file/fileIconMapper.js';
import FileUpload from '../../components/file/FileUpload.vue';
import FileEdit from '../../components/file/FileEdit.vue';
import FileRemoteUpload from '../../components/hosts/FileRemoteUpload.vue';

const calculatedSizes = ref({});

const keyFor = (record) => `${currentPath.value}/${record.filename}`;

const RECYCLE_DIR_NAME = '.recycle_bp';

const isRecycleDirectory = (filename) => {
  return filename === RECYCLE_DIR_NAME;
};

const fileList = ref([]);
const allFileList = ref([]);
const loading = ref(false);
const currentPath = ref('/opt/blackpotbpanel-v2/server');
const editablePath = ref('/opt/blackpotbpanel-v2/server');
const showPathInput = ref(false);
const searchKeyword = ref('');
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const pathInputRef = ref(null);
const tableScrollY = ref(400);

const updateTableScrollY = () => {
  tableScrollY.value = Math.max(200, window.innerHeight - 370);
};

const columns = computed(() => [
  { title: t.value('fileName'), dataIndex: 'filename', slotName: 'filename', width: 300, minWidth: 150 },
  { title: t.value('size'), dataIndex: 'size', slotName: 'size', width: 150 },
  { title: t.value('actions'), slotName: 'operations', width: 160, fixed: 'right' },
]);

const pathSegments = computed(() => {
  const segs = [];
  const parts = currentPath.value.split('/').filter(p => p);
  let acc = '';
  for (const p of parts) {
    acc += '/' + p;
    segs.push({ name: p, path: acc });
  }
  return segs;
});

const filteredFileList = computed(() => {
  const list = [...fileList.value];
  list.sort((a, b) => {
    if (a.is_directory && !b.is_directory) return -1;
    if (!a.is_directory && b.is_directory) return 1;
    return a.filename.localeCompare(b.filename);
  });
  return list.map(r => ({ ...r, disabled: !!r.is_directory }));
});

const formatDate = (dateString) => {
  if (!dateString) return '-';
  const d = new Date(dateString);
  return d.toLocaleString('zh-CN');
};

const loadFileList = async (path) => {
  const parts = path.split('/').filter(p => p);
  if (parts.some(p => isRecycleDirectory(p))) {
    Message.warning(t.value('cannotAccessRecycleDirectory'));
    return;
  }
  loading.value = true;
  try {
    const skip = (page.value - 1) * pageSize.value;
    const response = await getFileList({ path, skip, limit: pageSize.value });
    const allResponse = await getFileList({ path, skip: 0, limit: 1000 });

    fileList.value = response.data || [];
    allFileList.value = allResponse.data || [];
    total.value = response.total || fileList.value.length;
    currentPath.value = path;
    editablePath.value = path;
    showPathInput.value = false;
  } catch (error) {
    Message.error(t.value('getFileListFailed') + ': ' + (error.message || ''));
  } finally {
    loading.value = false;
  }
};

const goToRoot = () => loadFileList('/');

const goToParentDirectory = () => {
  if (currentPath.value === '/') return;
  const parent = currentPath.value.split('/').slice(0, -1).join('/') || '/';
  loadFileList(parent);
};

const navigateToPath = (index) => {
  const seg = pathSegments.value[index];
  if (seg) loadFileList(seg.path);
};

const startPathEdit = () => {
  showPathInput.value = true;
  nextTick(() => pathInputRef.value?.focus());
};

const cancelPathEdit = () => {
  showPathInput.value = false;
  editablePath.value = currentPath.value;
};

const handlePathChange = () => {
  if (editablePath.value.trim()) loadFileList(editablePath.value.trim());
  showPathInput.value = false;
};

const handleFileClick = (record) => {
  if (!record.is_directory) return;
  if (isRecycleDirectory(record.filename)) {
    Message.warning(t.value('cannotAccessRecycleDirectory'));
    return;
  }
  const name = record.filename.includes(' -> ') ? record.filename.split(' -> ')[0].trim() : record.filename;
  const newPath = currentPath.value === '/' ? `/${name}` : `${currentPath.value}/${name}`;
  loadFileList(newPath);
};

const handleSearch = async (value) => {
  searchKeyword.value = value;
  if (!value.trim()) {
    loadFileList(currentPath.value);
    return;
  }
  loading.value = true;
  try {
    const response = await searchFiles(
      { skip: (page.value - 1) * pageSize.value, limit: pageSize.value },
      { path: currentPath.value, keyword: value }
    );
    fileList.value = response.data || [];
    total.value = response.total || fileList.value.length;
  } catch (error) {
    Message.error(t.value('searchFailed'));
  } finally {
    loading.value = false;
  }
};

const refresh = () => loadFileList(currentPath.value);

const handlePageChange = (p) => { page.value = p; loadFileList(currentPath.value); };
const handlePageSizeChange = (s) => { pageSize.value = s; page.value = 1; loadFileList(currentPath.value); };

const selectedRowKeys = ref([]);

const getRowSelection = () => {
  return {
    type: 'checkbox',
    showCheckedAll: true,
    fixed: true,
  };
};

const showScpConfirm = ref(false);
const scpSendingFiles = ref([]);
const scpDirection = ref('upload');
const showScpProgress = ref(false);
const scpProgressData = ref({});
const scpWsRef = ref(null);
const scpTaskId = ref('');

const scpProgressPercent = computed(() => {
  return Number((scpProgressData.value.progress || 0));
});

const handleSendToRemote = (record) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  const path = currentPath.value === '/' ? `/${record.filename}` : `${currentPath.value}/${record.filename}`;
  scpDirection.value = 'upload';
  scpSendingFiles.value = [{ filename: record.filename, path }];
  showScpConfirm.value = true;
};

const handleBatchSendToRemote = () => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  const selected = filteredFileList.value.filter(r => selectedRowKeys.value.includes(r.filename));
  if (selected.length === 0) {
    Message.warning(t.value('pleaseSelectFiles'));
    return;
  }
  scpDirection.value = 'upload';
  scpSendingFiles.value = selected.map(r => ({
    filename: r.filename,
    path: currentPath.value === '/' ? `/${r.filename}` : `${currentPath.value}/${r.filename}`,
  }));
  showScpConfirm.value = true;
};

const confirmScpSend = async () => {
  showScpConfirm.value = false;
  try {
    const sourcePaths = scpSendingFiles.value.map(f => f.path);
    const remoteDir = scpDirection.value === 'download' ? currentPath.value : remotePath.value;
    const { task_id } = await startSCPTransfer(selectedHostId.value, {
      direction: scpDirection.value,
      source_paths: sourcePaths,
      remote_dir: remoteDir,
    });
    scpTaskId.value = task_id;
    showScpProgress.value = true;
    scpProgressData.value = { progress: 0, status: 'pending', message: '等待开始传输...', current_file: '', total_files: sourcePaths.length, completed_files: 0 };
    wsConnectProgress(task_id);
  } catch (error) {
    Message.error(t.value('scpStartFailed') + ': ' + (error.message || ''));
  }
};

const wsConnectProgress = (taskId) => {
  const ws = connectSCPProgress(taskId);
  scpWsRef.value = ws;
  ws.onmessage = (e) => {
    const data = JSON.parse(e.data);
    scpProgressData.value = { ...scpProgressData.value, ...data };
    if (data.status === 'completed') {
      Message.success(t.value('scpCompleted'));
      if (scpDirection.value === 'download') {
        setTimeout(() => { showScpProgress.value = false; loadFileList(currentPath.value); }, 1000);
      } else {
        setTimeout(() => { showScpProgress.value = false; loadRemoteFileList(); }, 1000);
      }
    } else if (data.status === 'failed') {
      Message.error(t.value('scpFailed') + ': ' + (data.message || ''));
      setTimeout(() => { showScpProgress.value = false; }, 2000);
    } else if (data.status === 'cancelled') {
      Message.info(t.value('scpCancelled'));
      showScpProgress.value = false;
    }
  };
  ws.onerror = () => {
    Message.error(t.value('scpProgressConnectFailed'));
  };
  ws.onclose = () => {
    if (scpProgressData.value.status !== 'completed' && scpProgressData.value.status !== 'failed' && scpProgressData.value.status !== 'cancelled') {
      showScpProgress.value = false;
    }
  };
};

const cancelScpSend = () => {
  if (scpWsRef.value) {
    scpWsRef.value.close();
    scpWsRef.value = null;
  }
  if (scpTaskId.value) {
    cancelSCPTransfer(scpTaskId.value).catch(() => {});
  }
  showScpProgress.value = false;
};

const handleCalculateSize = async (record) => {
  if (isRecycleDirectory(record.filename)) {
    Message.warning(t.value('cannotOperateRecycleDirectory'));
    return;
  }
  try {
    const fullPath = record.path || `${currentPath.value}/${record.filename}`;
    const key = keyFor(record);
    calculatedSizes.value[key] = { loading: true };
    const response = await getDirectorySize({ path: fullPath });
    calculatedSizes.value[key] = { loading: false, size_human: response.data.size_human };
  } catch (error) {
    Message.error(t.value('calculateSizeFailed'));
    calculatedSizes.value[keyFor(record)] = { loading: false, error: true };
  }
};

const uploadModalVisible = ref(false);
const fileUploadRef = ref(null);

const handleUpload = () => { uploadModalVisible.value = true; };
const handleUploadSuccess = () => { loadFileList(currentPath.value); };

const fileEditor = reactive({ visible: false, path: '', name: '' });

const handleOpenFile = (record) => {
  if (isRecycleDirectory(record.filename)) {
    Message.warning(t.value('cannotOperateRecycleDirectory'));
    return;
  }
  if (!canOpenFile(record.filename)) {
    Message.warning(t.value('cannotOpenFile'));
    return;
  }
  fileEditor.path = currentPath.value;
  fileEditor.name = record.filename.includes(' -> ') ? record.filename.split(' -> ')[0].trim() : record.filename;
  fileEditor.visible = true;
};

const handleFileEditorClose = () => { fileEditor.visible = false; };
const handleFileEditorSave = () => { loadFileList(currentPath.value); };

const handleCreateFolder = () => {
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

const createFolderForm = reactive({ name: '' });

const handleCreateFolderSubmit = async () => {
  if (!createFolderForm.name.trim()) {
    Message.error(t.value('fileNameCannotBeEmpty'));
    return false;
  }
  try {
    await createDirectory({ path: currentPath.value, dir_name: createFolderForm.name.trim() });
    Message.success(t.value('createFolderSuccess'));
    loadFileList(currentPath.value);
  } catch (e) {
    Message.error(t.value('createFolderFailed') + ': ' + (e.message || ''));
  }
};

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

const createFileForm = reactive({ name: '' });

const handleCreateFileSubmit = async () => {
  if (!createFileForm.name.trim()) {
    Message.error(t.value('fileNameCannotBeEmpty'));
    return false;
  }
  try {
    await createFile({ path: currentPath.value, file_name: createFileForm.name.trim(), content: '' });
    Message.success(t.value('createFileSuccess'));
    loadFileList(currentPath.value);
  } catch (e) {
    Message.error(t.value('createFileFailed') + ': ' + (e.message || ''));
  }
};

const handleDeleteFile = (record) => {
  if (isRecycleDirectory(record.filename)) {
    Message.warning(t.value('cannotOperateRecycleDirectory'));
    return;
  }
  const name = record.filename.includes(' -> ') ? record.filename.split(' -> ')[0].trim() : record.filename;
  Modal.warning({
    title: t.value('confirmDelete'),
    content: t.value('confirmDeleteFile').replace('{filename}', record.filename),
    okText: t.value('confirm'),
    cancelText: t.value('cancel'),
    onOk: async () => {
      try {
        await deleteFile({ path: currentPath.value, filename: name });
        Message.success(t.value('fileDeleted') + ': ' + record.filename);
        loadFileList(currentPath.value);
      } catch (e) {
        Message.error(t.value('deleteFileFailed') + ': ' + (e.message || ''));
      }
    }
  });
};

const handleDownload = (record) => {
  if (isRecycleDirectory(record.filename)) {
    Message.warning(t.value('cannotOperateRecycleDirectory'));
    return;
  }
  const name = record.filename.includes(' -> ') ? record.filename.split(' -> ')[0].trim() : record.filename;
  downloadFile({ path: currentPath.value, filename: name });
};

// ==================== 右侧远程文件 ====================

const hostsData = ref([]);
const hostsLoading = ref(false);
const selectedHostId = ref(null);
const remoteFileList = ref([]);
const remoteLoading = ref(false);
const remotePath = ref('/');
const remoteEditablePath = ref('/');
const showRemotePathInput = ref(false);
const remotePathInputRef = ref(null);
const remoteTotal = ref(0);
const remotePage = ref(1);
const remotePageSize = ref(20);

const remoteColumns = computed(() => [
  { title: t.value('fileName'), dataIndex: 'filename', slotName: 'filename', width: 300, minWidth: 150 },
  { title: t.value('size'), dataIndex: 'size', slotName: 'size', width: 150 },
  { title: t.value('actions'), slotName: 'operations', width: 180, fixed: 'right' },
]);

const remoteSelectedRowKeys = ref([]);

const getRemoteRowSelection = () => {
  return {
    type: 'checkbox',
    showCheckedAll: true,
    fixed: true,
  };
};

const remotePathSegments = computed(() => {
  const segs = [];
  const parts = remotePath.value.split('/').filter(p => p);
  let acc = '';
  for (const p of parts) {
    acc += '/' + p;
    segs.push({ name: p, path: acc });
  }
  return segs;
});

const loadHosts = async () => {
  hostsLoading.value = true;
  try {
    const hosts = await getFileTransferHosts();
    hostsData.value = (hosts || []).filter(h => h.address !== '127.0.0.1');
  } catch (error) {
    Message.error(t.value('getHostListFailed'));
  } finally {
    hostsLoading.value = false;
  }
};

const handleHostChange = (hostId) => {
  if (hostId) {
    remotePath.value = '/';
    remotePage.value = 1;
    loadRemoteFileList();
  } else {
    remoteFileList.value = [];
  }
};

const loadRemoteFileList = async () => {
  if (!selectedHostId.value) return;
  remoteLoading.value = true;
  try {
    const skip = (remotePage.value - 1) * remotePageSize.value;
    const response = await getRemoteFileList(selectedHostId.value, {
      path: remotePath.value,
      skip,
      limit: remotePageSize.value,
    });
    remoteFileList.value = response.data || [];
    remoteTotal.value = response.total || remoteFileList.value.length;
    remoteFileList.value = remoteFileList.value.map(r => ({ ...r, disabled: !!r.is_directory }));
    remoteEditablePath.value = remotePath.value;
    showRemotePathInput.value = false;
    remoteAllFileList.value = [];
    remoteSearchKeyword.value = '';
  } catch (error) {
    Message.error(t.value('getRemoteFileListFailed') + ': ' + (error.message || ''));
  } finally {
    remoteLoading.value = false;
  }
};

const goToRemoteRoot = () => { remotePath.value = '/'; remotePage.value = 1; loadRemoteFileList(); };
const goToRemoteParent = () => {
  if (remotePath.value === '/') return;
  remotePath.value = remotePath.value.split('/').slice(0, -1).join('/') || '/';
  remotePage.value = 1;
  loadRemoteFileList();
};
const navigateToRemotePath = (index) => {
  const seg = remotePathSegments.value[index];
  if (seg) { remotePath.value = seg.path; remotePage.value = 1; loadRemoteFileList(); }
};
const handleRemoteFileClick = (record) => {
  if (!record.is_directory) return;
  const name = record.filename.includes(' -> ') ? record.filename.split(' -> ')[0].trim() : record.filename;
  remotePath.value = remotePath.value === '/' ? `/${name}` : `${remotePath.value}/${name}`;
  remotePage.value = 1;
  loadRemoteFileList();
};
const refreshRemote = () => loadRemoteFileList();

const handleRemoteSendToLocal = (record) => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  const fullPath = remotePath.value === '/' ? `/${record.filename}` : `${remotePath.value}/${record.filename}`;
  scpDirection.value = 'download';
  scpSendingFiles.value = [{ filename: record.filename, path: fullPath }];
  showScpConfirm.value = true;
};

const handleRemoteBatchSendToLocal = () => {
  if (!selectedHostId.value) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  const selected = remoteFileList.value.filter(r => remoteSelectedRowKeys.value.includes(r.filename));
  if (selected.length === 0) {
    Message.warning(t.value('pleaseSelectFiles'));
    return;
  }
  scpDirection.value = 'download';
  scpSendingFiles.value = selected.map(r => ({
    filename: r.filename,
    path: remotePath.value === '/' ? `/${r.filename}` : `${remotePath.value}/${r.filename}`,
  }));
  showScpConfirm.value = true;
};
const handleRemotePageChange = (p) => { remotePage.value = p; loadRemoteFileList(); };
const handleRemotePageSizeChange = (s) => { remotePageSize.value = s; remotePage.value = 1; loadRemoteFileList(); };

const startRemotePathEdit = () => {
  showRemotePathInput.value = true;
  nextTick(() => remotePathInputRef.value?.focus());
};

const cancelRemotePathEdit = () => {
  showRemotePathInput.value = false;
  remoteEditablePath.value = remotePath.value;
};

const handleRemotePathChange = () => {
  if (remoteEditablePath.value.trim()) {
    remotePath.value = remoteEditablePath.value.trim();
    remotePage.value = 1;
    loadRemoteFileList();
  }
  showRemotePathInput.value = false;
};

const remoteFileInputRef = ref(null);
const remoteUploadModalVisible = ref(false);
const remoteFileUploadRef = ref(null);

const handleRemoteUpload = () => {
  if (!remotePath.value || remotePath.value === '/') {
    Message.warning(t.value('cannotUploadToRoot'));
    return;
  }
  remoteUploadModalVisible.value = true;
};

const handleRemoteUploadSuccess = () => {
  loadRemoteFileList();
};

const remoteSearchKeyword = ref('');
const remoteAllFileList = ref([]);

const STORAGE_KEY = 'fileTransferState';

const saveStateToLocalStorage = () => {
  try {
    const state = {
      currentPath: currentPath.value,
      page: page.value,
      pageSize: pageSize.value,
      selectedHostId: selectedHostId.value,
      remotePath: remotePath.value,
      remotePage: remotePage.value,
      remotePageSize: remotePageSize.value,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (error) {
  }
};

const restoreStateFromLocalStorage = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const state = JSON.parse(saved);
      if (state.currentPath) currentPath.value = state.currentPath;
      if (state.page) page.value = state.page;
      if (state.pageSize) pageSize.value = state.pageSize;
      if (state.selectedHostId) selectedHostId.value = state.selectedHostId;
      if (state.remotePath) remotePath.value = state.remotePath;
      if (state.remotePage) remotePage.value = state.remotePage;
      if (state.remotePageSize) remotePageSize.value = state.remotePageSize;
      return true;
    }
  } catch (error) {
    localStorage.removeItem(STORAGE_KEY);
  }
  return false;
};

watch([currentPath, page, pageSize, selectedHostId, remotePath, remotePage, remotePageSize], saveStateToLocalStorage, { deep: true });

const handleRemoteSearch = async (value) => {
  remoteSearchKeyword.value = value;
  if (!value.trim()) {
    loadRemoteFileList();
    return;
  }
  remoteLoading.value = true;
  try {
    let allFiles = remoteAllFileList.value;
    if (allFiles.length === 0) {
      const response = await getRemoteFileList(selectedHostId.value, { path: remotePath.value, skip: 0, limit: 10000 });
      allFiles = response.data || [];
      remoteAllFileList.value = allFiles;
    }
    const keyword = value.toLowerCase();
    remoteFileList.value = allFiles.filter(f => f.filename.toLowerCase().includes(keyword));
    remoteTotal.value = remoteFileList.value.length;
  } catch (error) {
    Message.error(t.value('searchFailed'));
  } finally {
    remoteLoading.value = false;
  }
};

const remoteCreateFolderForm = reactive({ name: '' });

const handleRemoteCreateFolder = () => {
  remoteCreateFolderForm.name = '';
  Modal.open({
    title: t.value('createFolder'),
    content: () => h('div', [
      h('label', { style: { display: 'block', marginBottom: '8px' } }, t.value('enterFolderName')),
      h(AInput, {
        placeholder: t.value('enterFolderName'),
        modelValue: remoteCreateFolderForm.name,
        'onUpdate:modelValue': (value) => { remoteCreateFolderForm.name = value; },
        style: { width: '100%' }
      })
    ]),
    okText: t.value('create'),
    cancelText: t.value('cancel'),
    onOk: handleRemoteCreateFolderSubmit,
    onCancel: () => { remoteCreateFolderForm.name = ''; }
  });
};

const handleRemoteCreateFolderSubmit = async () => {
  if (!remoteCreateFolderForm.name.trim()) {
    Message.error(t.value('fileNameCannotBeEmpty'));
    return false;
  }
  try {
    await createRemoteFile(selectedHostId.value, {
      path: remotePath.value,
      name: remoteCreateFolderForm.name.trim(),
      type: 'directory'
    });
    Message.success(t.value('createFolderSuccess'));
    loadRemoteFileList();
  } catch (e) {
    Message.error(t.value('createFolderFailed') + ': ' + (e.message || ''));
  }
};

const remoteCreateFileForm = reactive({ name: '' });

const handleRemoteCreateFile = () => {
  remoteCreateFileForm.name = '';
  Modal.open({
    title: t.value('createFile'),
    content: () => h('div', [
      h('label', { style: { display: 'block', marginBottom: '8px' } }, t.value('enterFileName')),
      h(AInput, {
        placeholder: t.value('enterFileName'),
        modelValue: remoteCreateFileForm.name,
        'onUpdate:modelValue': (value) => { remoteCreateFileForm.name = value; },
        style: { width: '100%' }
      })
    ]),
    okText: t.value('create'),
    cancelText: t.value('cancel'),
    onOk: handleRemoteCreateFileSubmit,
    onCancel: () => { remoteCreateFileForm.name = ''; }
  });
};

const handleRemoteCreateFileSubmit = async () => {
  if (!remoteCreateFileForm.name.trim()) {
    Message.error(t.value('fileNameCannotBeEmpty'));
    return false;
  }
  try {
    await createRemoteFile(selectedHostId.value, {
      path: remotePath.value,
      name: remoteCreateFileForm.name.trim(),
      type: 'file'
    });
    Message.success(t.value('createFileSuccess'));
    loadRemoteFileList();
  } catch (e) {
    Message.error(t.value('createFileFailed') + ': ' + (e.message || ''));
  }
};

const handleRemoteDeleteFile = (record) => {
  const name = record.filename.includes(' -> ') ? record.filename.split(' -> ')[0].trim() : record.filename;
  Modal.warning({
    title: t.value('confirmDelete'),
    content: t.value('confirmDeleteFile').replace('{filename}', record.filename),
    okText: t.value('confirm'),
    cancelText: t.value('cancel'),
    onOk: async () => {
      try {
        const fullPath = `${remotePath.value === '/' ? '' : remotePath.value}/${name}`;
        await deleteRemoteFile(selectedHostId.value, {
          path: fullPath,
          type: record.is_directory ? 'directory' : 'file'
        });
        Message.success(t.value('fileDeleted') + ': ' + record.filename);
        loadRemoteFileList();
      } catch (e) {
        Message.error(t.value('deleteFileFailed') + ': ' + (e.message || ''));
      }
    }
  });
};

onMounted(() => {
  updateTableScrollY();
  window.addEventListener('resize', updateTableScrollY);
  const restored = restoreStateFromLocalStorage();
  loadFileList(currentPath.value);
  loadHosts();
  if (restored && selectedHostId.value) {
    nextTick(() => loadRemoteFileList());
  }
});
</script>

<style scoped>
.filetran-container {
  display: flex;
  height: calc(100vh - 140px);
  gap: 0;
  background: var(--color-bg-1);
  border-radius: 4px;
  overflow: hidden;
}

.split-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px;
  min-width: 0;
}

.split-divider {
  width: 1px;
  background: var(--color-border);
  flex-shrink: 0;
}

.panel-header {
  display: flex;
  align-items: center;
  font-size: 16px;
  font-weight: 600;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 12px;
  color: var(--color-text-1);
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
  user-select: none;
}

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
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.search-container {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-list-wrapper {
  flex: 1;
  overflow: auto;
}

.file-item {
  display: flex;
  align-items: center;
}

.list-filename {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pagination-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
  margin-top: 12px;
}

.pagination-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.host-select-in-header {
  margin-left: auto;
  display: flex;
  align-items: center;
}

.host-select-in-header .arco-form-item {
  margin-bottom: 0;
}

.no-host-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--color-text-3);
}

.empty-text {
  color: var(--color-text-3);
  font-size: 14px;
}

:deep(.arco-table-th) {
  font-weight: 600;
}

:deep(.arco-table-td) {
  font-size: 13px;
}
</style>
