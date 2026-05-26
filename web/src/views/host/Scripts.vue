<template>
  <a-card class="host-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('scripts') }}</span>
        <!-- 新增脚本按钮 -->
        <a-button type="outline" size="small" @click="openCreateScriptDrawer" style="margin-left: auto;">
          {{ t('createScript') }}
        </a-button>
        <!-- 将脚本类型管理按钮移到标题同一排 -->
        <a-button type="outline" size="small" @click="openScriptTypeDrawer" >
          {{ t('manageScriptTypes') }}
        </a-button>
      </div>
    </template>

    <a-table 
      :columns="columns" 
      :data="scriptData" 
      :loading="loading" 
      :pagination="pagination" 
      @page-change="handlePageChange"
      @page-size-change="handlePageSizeChange"
      :scroll="scroll"
    >
      <template #script_type="{ record }">
        <a-tag>
          {{ record.script_type || '-' }}
        </a-tag>
      </template>
      <template #created_at="{ record }">
        {{ formatDate(record.created_at) }}
      </template>
      <template #actions="{ record }">
        <a-link @click="openEditScriptDrawer(record)">{{ t('edit') }}</a-link>
        <!-- 修改这里，使用实时执行脚本功能 -->
        <a-link  @click="openRealTimeExecuteModal(record)">{{ t('execute') }}</a-link>
        <a-link status="danger" @click="confirmDeleteScript(record)">
          {{ t('delete') }}
        </a-link>
      </template>
    </a-table>
  </a-card>

  <!-- 脚本类型管理抽屉 -->
  <a-drawer 
    :visible="scriptTypeDrawerVisible" 
    @ok="closeScriptTypeDrawer" 
    @cancel="closeScriptTypeDrawer"
    :width="isMobile ? '90%' : 800"
    :footer="false"
  >
    <template #title>
      {{ t('scriptTypeManagement') }}
    </template>
    
    <!-- 脚本类型列表 -->
    <a-table 
      :columns="scriptTypeColumns" 
      :data="scriptTypeData" 
      :loading="scriptTypeLoading" 
      :pagination="false"
      :scroll="scriptTypeScroll"
    >
      <template #actions="{ record }">
        <a-button type="text" size="small" @click="editScriptType(record)">
          {{ t('edit') }}
        </a-button>
        <a-popconfirm 
          :content="t('confirmDeleteScriptType')" 
          @ok="deleteScriptType(record.id)"
        >
          <a-button type="text" size="small" status="danger">
            {{ t('delete') }}
          </a-button>
        </a-popconfirm>
      </template>
    </a-table>
    
    <!-- 添加/编辑脚本类型表单 -->
    <div class="script-type-form-container">
      <a-form 
        :model="scriptTypeForm" 
        :rules="scriptTypeRules"
        ref="scriptTypeFormRef"
        @submit="saveScriptType"
        layout="vertical"
      >
        <a-form-item field="type_name" :label="t('typeName')">
          <a-input 
            v-model="scriptTypeForm.type_name" 
            :placeholder="t('typeNamePlaceholder')"
          />
        </a-form-item>
        
        <a-form-item field="interpreter_path" :label="t('interpreterPath')">
          <a-input 
            v-model="scriptTypeForm.interpreter_path" 
            :placeholder="t('interpreterPathPlaceholder')"
          />
        </a-form-item>
        
        <a-form-item field="description" :label="t('description')">
          <a-textarea 
            v-model="scriptTypeForm.description" 
            :placeholder="t('descriptionPlaceholder')"
            :auto-size="{ minRows: 3 }"
          />
        </a-form-item>
        
        <a-form-item class="form-buttons">
          <a-space>
            <a-button type="primary" html-type="submit">
              {{ scriptTypeForm.id ? t('update') : t('create') }}
            </a-button>
            <a-button @click="resetScriptTypeForm">
              {{ t('reset') }}
            </a-button>
          </a-space>
        </a-form-item>
      </a-form>
    </div>
  </a-drawer>
  
  <!-- 脚本新增/编辑抽屉 -->
  <a-drawer 
    :visible="scriptDrawerVisible" 
    @ok="closeScriptDrawer" 
    @cancel="closeScriptDrawer"
    :width="isMobile ? '100%' : 800"
    :footer="false"
  >
    <template #title>
      {{ scriptForm.id ? t('editScript') : t('createScript') }}
    </template>
    
    <div class="script-form-container">
      <a-form 
        :model="scriptForm" 
        :rules="scriptRules"
        ref="scriptFormRef"
        @submit="saveScript"
        layout="vertical"
      >
        <a-form-item field="name" :label="t('scriptName')">
          <a-input 
            v-model="scriptForm.name" 
            :placeholder="t('scriptNamePlaceholder')"
          />
        </a-form-item>
        
        <a-form-item field="script_type_id" :label="t('scriptType')">
          <a-select 
            v-model="scriptForm.script_type_id" 
            :placeholder="t('selectScriptType')"
            :loading="scriptTypeLoading"
          >
            <a-option
              v-for="type in scriptTypeData"
              :key="type.id"
              :value="type.id"
              :label="type.type_name"
            />
          </a-select>
        </a-form-item>
        
        <a-form-item field="description" :label="t('description')">
          <a-textarea 
            v-model="scriptForm.description" 
            :placeholder="t('descriptionPlaceholder')"
            :auto-size="{ minRows: 3 }"
          />
        </a-form-item>
        
        <a-form-item field="requires_params" :label="t('requiresParams')">
          <a-switch v-model="scriptForm.requires_params" />
        </a-form-item>
        
        <a-form-item 
          field="params_description" 
          :label="t('paramsDescription')"
          v-if="scriptForm.requires_params"
        >
          <a-textarea 
            v-model="scriptForm.params_description" 
            :placeholder="t('paramsDescriptionPlaceholder')" 
            :auto-size="{ minRows: 2 }"
          />
        </a-form-item>
        
        <!-- 将脚本内容改为Monaco Editor -->
        <a-form-item field="script_context" :label="t('scriptContent')">
          <div 
            ref="monacoEditorRef" 
            class="monaco-editor-container"
          ></div>
        </a-form-item>
        
        <a-form-item class="form-buttons">
          <a-space>
            <a-button type="primary" html-type="submit">
              {{ scriptForm.id ? t('update') : t('create') }}
            </a-button>
            <a-button @click="resetScriptForm">
              {{ t('reset') }}
            </a-button>
          </a-space>
        </a-form-item>
      </a-form>
    </div>
  </a-drawer>
  
  <!-- 删除确认对话框 -->
  <a-modal 
    :visible="deleteModalVisible" 
    @ok="handleDeleteScript" 
    @cancel="cancelDeleteScript" 
    :ok-text="t('confirm')" 
    :cancel-text="t('cancel')"
  >
    <template #title>
      {{ t('delete') }}
    </template>
    <div>
      <p>{{ t('confirmDeleteScript') }} {{ deleteScriptTarget.name }}?</p>
    </div>
  </a-modal>
  
  <!-- 实时脚本执行对话框 - 改为响应式抽屉 -->
  <a-drawer 
      :visible="realTimeExecuteModalVisible" 
      @cancel="cancelRealTimeExecute" 
      :footer="false"
      :width="isMobile ? '100%' : 900"
      :mask-closable="false"
    >
      <template #title>
        {{ t('executeScript') }} - {{ realTimeExecuteTarget.name }}
      </template>
      <div>
        <a-alert type="info" style="margin-bottom: 16px;">
          {{ t('realTimeExecuteScriptInfo') }}
        </a-alert>
        
        <!-- 执行参数配置区域 -->
        <div>
          <!-- 主机选择 - 始终显示 -->
          <a-form-item :label="t('selectHosts')">
            <a-select 
              v-model="realTimeSelectedHostIds" 
              :placeholder="t('selectHostsPlaceholder')"
              multiple
              :loading="hostsLoading"
              :disabled="false"
            >
              <a-option
                v-for="host in hostsData"
                :key="host.id"
                :value="host.id"
                :label="`${host.comment} (${host.address})`"
              />
            </a-select>
          </a-form-item>
          
          <a-form-item 
            v-if="realTimeExecuteTarget.requires_params"
            field="script_parameters" 
            :label="t('scriptParameters')"
          >
            <a-input 
              v-model="scriptParameters" 
              :placeholder="realTimeExecuteTarget.params_description || t('scriptParametersPlaceholder')"
              :disabled="false"
            />
            <div v-if="realTimeExecuteTarget.params_description" class="params-hint">
              {{ t('paramsDescription') }}: {{ realTimeExecuteTarget.params_description }}
            </div>
          </a-form-item>
          
          <a-form-item 
            v-else
            field="script_parameters_disabled" 
            :label="t('scriptParameters')"
          >
            <a-input 
              :placeholder="t('noParametersRequired')"
              disabled
            />
          </a-form-item>
          
          <!-- 执行按钮 -->
          <a-button 
            type="primary" 
            @click="handleExecutionButtonClick" 
            :disabled="realTimeSelectedHostIds.length === 0"
            style="margin-bottom: 16px;"
          >
            {{ terminalTabs.length === 0 ? t('startExecute') : t('newExecute') }}
          </a-button>
          
          <!-- 实时输出 - 标签页模式 -->
          <div :class="['execution-output', { 'fullscreen-terminal': isTerminalFullscreen }]">
            <!-- 终端头部 -->
            <div class="terminal-header">
              <div class="terminal-title">{{ t('realTimeExecuteScriptInfo') }}</div>
              <div class="terminal-actions">
                <a-button 
                  type="text" 
                  size="small" 
                  @click="toggleTerminalFullscreen"
                  :title="isTerminalFullscreen ? t('exitFullscreen') : t('enterFullscreen')"
                  class="fullscreen-btn"
                >
                  <template #icon>
                    <IconFullscreenExit v-if="isTerminalFullscreen" />
                    <IconFullscreen v-else />
                  </template>
                </a-button>
                <a-button size="small" @click="scrollToBottom" :disabled="terminalTabs.length === 0" :title="'滚动到底部'">
                  <template #icon>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>
                    </svg>
                  </template>
                </a-button>
                <a-button size="small" @click="clearActiveTabOutput" :disabled="terminalTabs.length === 0">{{ t('clear') }}</a-button>
                <a-button size="small" @click="clearAllTabs" :disabled="terminalTabs.length === 0">{{ t('clearAllTabs') }}</a-button>
              </div>
            </div>
            
            <!-- 标签页区域 -->
            <div class="terminal-tabs-container">
              <!-- 当有标签页时显示标签页 -->
              <a-tabs 
                v-if="terminalTabs.length > 0"
                v-model:active-key="activeTabKey" 
                type="card" 
                size="small"
                @tab-click="handleTabClick"
                class="terminal-tabs"
              >
                <a-tab-pane 
                  v-for="tab in terminalTabs" 
                  :key="tab.id" 
                  :title="tab.title"
                  :closable="true"
                  @close="closeTab(tab.id)"
                >
                  <template #title>
                    <div class="tab-title">
                      <span class="tab-name">{{ tab.title }}</span>
                      <span 
                        :class="['tab-status', `status-${tab.status}`]"
                        :title="getStatusText(tab.status)"
                      ></span>
                      <IconClose 
                        class="tab-close-icon" 
                        @click.stop="closeTab(tab.id)"
                        :title="'关闭标签页'"
                      />
                    </div>
                  </template>
                  
                  <!-- 终端内容区域 -->
                  <div class="output-content">
                    <!-- 终端容器 -->
                    <div 
                      :ref="el => setTerminalRef(el, tab.id)" 
                      class="terminal-container"
                      :class="{ 'terminal-hidden': activeTabKey !== tab.id }"
                    ></div>
                  </div>
                </a-tab-pane>
              </a-tabs>
              
              <!-- 当没有标签页时显示提示信息 -->
              <div v-else class="empty-terminal-placeholder">
                <div class="placeholder-content">
                  <div class="placeholder-icon">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M4 6C4 4.89543 4.89543 4 6 4H18C19.1046 4 20 4.89543 20 6V18C20 19.1046 19.1046 20 18 20H6C4.89543 20 4 19.1046 4 18V6Z" stroke="#666" stroke-width="2"/>
                      <path d="M8 10L10 12L8 14" stroke="#666" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                      <path d="M12 14H16" stroke="#666" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </a-drawer>
  </template>

<script setup>
import { reactive, ref, computed, onMounted, nextTick, watch, onBeforeUnmount } from 'vue';
import { t } from '../../utils/locale';
import { 
  getScriptList, 
  getScriptTypeList, 
  createScriptType, 
  updateScriptType, 
  deleteScriptType as apiDeleteScriptType,
  createScript,
  updateScript,
  deleteScript as apiDeleteScript,
  connectScriptExecutionWebSocket
} from '../../api/script';

import { getHosts } from '../../api/host';

import { Message, Modal } from '@arco-design/web-vue';
import { IconFullscreen, IconFullscreenExit, IconClose } from '@arco-design/web-vue/es/icon';
// 引入 Monaco Editor
import * as monaco from 'monaco-editor';
// 引入 xterm.js 终端库
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';

// 表格相关数据
const scriptData = ref([]);
const loading = ref(false);
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showTotal: true,
  showJumper: true,
  pageSizeOptions: [10, 20, 50, 100],
  showPageSize: true
});

// 表格滚动配置
const scroll = reactive({
  x: 1300,
  y: 400
});

// 国际化文本计算属性
const idText = computed(() => t.value('id'));
const nameText = computed(() => t.value('name'));
const scriptTypeText = computed(() => t.value('scriptType'));
const descriptionText = computed(() => t.value('description'));
const createdAtText = computed(() => t.value('createdAt'));
const actionsText = computed(() => t.value('actions'));

// 表格列定义
const columns = computed(() => reactive([
  {
    title: idText.value,
    dataIndex: 'script_id',
    width: 80
  },
  {
    title: nameText.value,
    dataIndex: 'name',
    width: 150
  },
  {
    title: scriptTypeText.value,
    dataIndex: 'script_type',
    slotName: 'script_type',
    width: 140
  },
  {
    title: descriptionText.value,
    dataIndex: 'description',
    width: 250
  },
  {
    title: createdAtText.value,
    dataIndex: 'created_at',
    slotName: 'created_at',
    width: 200
  },
  {
    title: actionsText.value,
    slotName: 'actions',
    width: 150
  }
]));


// 响应式布局相关
const isMobile = ref(false);

const checkIsMobile = () => {
  isMobile.value = window.innerWidth < 768;
};

// 脚本类型相关数据
const scriptTypeDrawerVisible = ref(false);
const scriptTypeData = ref([]);
const scriptTypeLoading = ref(false);
const scriptTypeFormRef = ref();
// 脚本类型表格滚动配置
const scriptTypeScroll = reactive({
  y: 300
});

// 脚本类型表单
const scriptTypeForm = reactive({
  id: undefined,
  type_name: '',
  interpreter_path: '',
  description: ''
});

// 脚本类型表单验证规则
const scriptTypeRules = computed(() => reactive({
  type_name: [
    { required: true, message: typeNameRequiredText.value }
  ],
  interpreter_path: [
    { required: true, message: interpreterPathRequiredText.value }
  ]
}));

// 脚本类型国际化文本计算属性
const typeNameText = computed(() => t.value('typeName'));
const interpreterPathText = computed(() => t.value('interpreterPath'));
const typeNameRequiredText = computed(() => t.value('typeNameRequired'));
const interpreterPathRequiredText = computed(() => t.value('interpreterPathRequired'));
const scriptNameRequiredText = computed(() => t.value('scriptNameRequired'));
const scriptTypeRequiredText = computed(() => t.value('scriptTypeRequired'));
const scriptContentRequiredText = computed(() => t.value('scriptContentRequired'));

// 消息文本计算属性
const getScriptListFailedText = computed(() => t.value('getScriptListFailed'));
const getScriptTypeListFailedText = computed(() => t.value('getScriptTypeListFailed'));
const updateScriptTypeSuccessText = computed(() => t.value('updateScriptTypeSuccess'));
const createScriptTypeSuccessText = computed(() => t.value('createScriptTypeSuccess'));
const updateScriptTypeFailedText = computed(() => t.value('updateScriptTypeFailed'));
const createScriptTypeFailedText = computed(() => t.value('createScriptTypeFailed'));
const deleteScriptTypeSuccessText = computed(() => t.value('deleteScriptTypeSuccess'));
const deleteScriptTypeFailedText = computed(() => t.value('deleteScriptTypeFailed'));
const updateScriptSuccessText = computed(() => t.value('updateScriptSuccess'));
const createScriptSuccessText = computed(() => t.value('createScriptSuccess'));
const updateScriptFailedText = computed(() => t.value('updateScriptFailed'));
const createScriptFailedText = computed(() => t.value('createScriptFailed'));
const deleteScriptSuccessText = computed(() => t.value('deleteScriptSuccess'));
const deleteScriptFailedText = computed(() => t.value('deleteScriptFailed'));
const getHostListFailedText = computed(() => t.value('getHostListFailed'));
const pleaseSelectHostText = computed(() => t.value('pleaseSelectHost'));
const executeScriptSuccessText = computed(() => t.value('executeScriptSuccess'));
const executeScriptFailedText = computed(() => t.value('executeScriptFailed'));
const waitingForExecutionText = computed(() => t.value('waitingForExecution') || '等待执行...');
const executeAgainText = computed(() => t.value('executeAgain') || '重新执行');
const startExecutionText = computed(() => t.value('startExecution') || '开始执行');
const executingText = computed(() => t.value('executing') || '执行中...');

// 脚本类型表格列定义
const scriptTypeColumns = computed(() => reactive([
  {
    title: idText.value,
    dataIndex: 'id',
    width: 80
  },
  {
    title: typeNameText.value,
    dataIndex: 'type_name',
    width: 150
  },
  {
    title: interpreterPathText.value,
    dataIndex: 'interpreter_path',
    width: 200
  },
  {
    title: descriptionText.value,
    dataIndex: 'description',
    ellipsis: true
  },
  {
    title: actionsText.value,
    slotName: 'actions',
    width: 120
  }
]));

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleString();
};

// 生命周期钩子
onMounted(() => {
  // 初始化检测窗口大小
  checkIsMobile();
  // 添加窗口大小监听
  window.addEventListener('resize', checkIsMobile);
});

onBeforeUnmount(() => {
  // 移除窗口大小监听
  window.removeEventListener('resize', checkIsMobile);
});

// 获取脚本列表
const fetchScriptList = async (page = 1) => {
  try {
    loading.value = true;
    const response = await getScriptList(reactive({
      skip: (page - 1) * pagination.pageSize,
      limit: pagination.pageSize
    }));
    
    console.log('脚本API响应数据:', response);
    
    // 处理响应数据
    let scripts = [];
    let total = 0;
    
    if (response && response.items && Array.isArray(response.items)) {
      scripts = response.items;
      total = response.total || response.items.length;
    } else if (response && response.data && response.data.items && Array.isArray(response.data.items)) {
      scripts = response.data.items;
      total = response.data.total || response.data.items.length;
    } else if (response && Array.isArray(response)) {
      scripts = response;
      total = response.length;
    } else {
      scripts = [];
      total = 0;
    }
    
    scriptData.value = scripts;
    pagination.total = total;
  } catch (error) {
    console.error('获取脚本列表失败:', error);
    Message.error(getScriptListFailedText.value);
    scriptData.value = [];
    pagination.total = 0;
  } finally {
    loading.value = false;
  }
};

// 获取脚本类型列表
const fetchScriptTypeList = async () => {
  try {
    scriptTypeLoading.value = true;
    const response = await getScriptTypeList(reactive({}));
    
    // 处理响应数据
    let scriptTypes = [];
    
    if (response && response.items && Array.isArray(response.items)) {
      scriptTypes = response.items;
    } else if (response && response.data && response.data.items && Array.isArray(response.data.items)) {
      scriptTypes = response.data.items;
    } else if (response && Array.isArray(response)) {
      scriptTypes = response;
    } else {
      scriptTypes = [];
    }
    
    scriptTypeData.value = scriptTypes;
  } catch (error) {
    console.error('获取脚本类型列表失败:', error);
    Message.error(getScriptTypeListFailedText.value);
    scriptTypeData.value = [];
  } finally {
    scriptTypeLoading.value = false;
  }
};

// 打开脚本类型抽屉
const openScriptTypeDrawer = async () => {
  scriptTypeDrawerVisible.value = true;
  await fetchScriptTypeList();
};

// 关闭脚本类型抽屉
const closeScriptTypeDrawer = () => {
  scriptTypeDrawerVisible.value = false;
  resetScriptTypeForm();
};

// 重置脚本类型表单
const resetScriptTypeForm = () => {
  // 使用Object.assign确保响应式更新
  Object.assign(scriptTypeForm, {
    id: undefined,
    type_name: '',
    interpreter_path: '',
    description: ''
  });
  
  // 清除表单验证状态
  if (scriptTypeFormRef.value) {
    scriptTypeFormRef.value.clearValidate();
  }
};

// 编辑脚本类型
const editScriptType = (record) => {
  // 使用Object.assign确保响应式更新
  Object.assign(scriptTypeForm, {
    id: record.id,
    type_name: record.type_name,
    interpreter_path: record.interpreter_path,
    description: record.description
  });
};

// 保存脚本类型
const saveScriptType = async ({ values, errors }) => {
  if (errors) return;
  
  try {
    if (scriptTypeForm.id) {
      // 更新脚本类型
      await updateScriptType(scriptTypeForm.id, reactive({
        type_name: scriptTypeForm.type_name,
        interpreter_path: scriptTypeForm.interpreter_path,
        description: scriptTypeForm.description
      }));
      Message.success(updateScriptTypeSuccessText.value);
    } else {
      // 创建脚本类型
      // 创建脚本类型
      await createScriptType(reactive({
        type_name: scriptTypeForm.type_name,
        interpreter_path: scriptTypeForm.interpreter_path,
        description: scriptTypeForm.description
      }));
      Message.success(createScriptTypeSuccessText.value);
    }
    
    // 重置表单并刷新列表
    resetScriptTypeForm();
    await fetchScriptTypeList();
  } catch (error) {
    console.error('保存脚本类型失败:', error);
    Message.error(scriptTypeForm.id ? updateScriptTypeFailedText.value : createScriptTypeFailedText.value);
  }
};

// 删除脚本类型
const deleteScriptType = async (id) => {
  try {
    await apiDeleteScriptType(id);
    Message.success(t.value('deleteScriptTypeSuccess'));
    await fetchScriptTypeList();
  } catch (error) {
    console.error('删除脚本类型失败:', error);
    Message.error(t.value('deleteScriptTypeFailed'));
  }
};

// 处理分页变化
const handlePageChange = (page) => {
  pagination.current = page;
  fetchScriptList(page);
};

// 处理分页大小变化
const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize;
  pagination.current = 1; // 重置到第一页
  fetchScriptList(1);
};

// 脚本相关数据
const scriptDrawerVisible = ref(false);
const scriptFormRef = ref();
const monacoEditorRef = ref();
let monacoEditor = null;

// 脚本表单
const scriptForm = reactive({
  id: undefined,
  name: '',
  script_type_id: undefined,
  description: '',
  script_context: '',
  requires_params: false,
  params_description: ''
});

// 脚本表单验证规则
const scriptRules = computed(() => reactive({
  name: [
    { required: true, message: scriptNameRequiredText.value }
  ],
  script_type_id: [
    { required: true, message: scriptTypeRequiredText.value }
  ],
  script_context: [
    { required: true, message: scriptContentRequiredText.value }
  ]
}));

// Monaco Editor 相关状态
const isEditorInitializing = ref(false);
const isEditorDisposing = ref(false);
const editorDisposables = ref([]);

// 初始化Monaco Editor
const initMonacoEditor = async () => {
  // 防止重复初始化
  if (isEditorInitializing.value || monacoEditor) {
    return;
  }
  
  isEditorInitializing.value = true;
  
  try {
    await nextTick();
    
    // 再次检查，确保组件还存在且没有其他编辑器实例
    if (!monacoEditorRef.value || monacoEditor || isEditorDisposing.value) {
      return;
    }

    monacoEditor = monaco.editor.create(monacoEditorRef.value, reactive({
      value: scriptForm.script_context,
      language: 'shell', // 默认语言，可以根据脚本类型动态切换
      theme: 'vs-dark',
      automaticLayout: true,
      minimap: reactive({ enabled: false }),
      scrollBeyondLastLine: false,
      fontSize: 14,
      lineNumbers: 'on',
      wordWrap: 'on',
      folding: true,
      selectOnLineNumbers: true,
      matchBrackets: 'always',
      // 禁用一些可能导致异步问题的功能
      wordHighlighter: false,
      occurrencesHighlight: false,
      selectionHighlight: false
    }));

    // 监听内容变化并保存到disposables中
    const contentChangeDisposable = monacoEditor.onDidChangeModelContent(() => {
      if (monacoEditor && !isEditorDisposing.value) {
        scriptForm.script_context = monacoEditor.getValue();
      }
    });
    
    editorDisposables.value.push(contentChangeDisposable);
  } catch (error) {
    console.warn('Monaco Editor 初始化警告（可忽略）:', error);
  } finally {
    isEditorInitializing.value = false;
  }
};

// 销毁Monaco Editor
const disposeMonacoEditor = () => {
  if (isEditorDisposing.value) {
    return;
  }
  
  isEditorDisposing.value = true;
  
  try {
    // 首先清理所有事件监听器
    editorDisposables.value.forEach(disposable => {
      try {
        disposable.dispose();
      } catch (error) {
        console.warn('清理编辑器事件监听器警告:', error);
      }
    });
    editorDisposables.value = [];
    
    if (monacoEditor) {
      // 获取并清理模型
      const model = monacoEditor.getModel();
      if (model) {
        // 停止所有模型相关的服务
        try {
          model.dispose();
        } catch (error) {
          console.warn('清理编辑器模型警告:', error);
        }
      }
      
      // 清理编辑器实例
      try {
        monacoEditor.dispose();
      } catch (error) {
        console.warn('清理编辑器实例警告:', error);
      }
      
      monacoEditor = null;
    }
  } catch (error) {
    console.warn('Monaco Editor 销毁警告（可忽略）:', error);
  } finally {
    // 延迟重置标志，确保所有清理操作完成
    setTimeout(() => {
      isEditorDisposing.value = false;
    }, 200);
  }
};

// 根据脚本类型设置编辑器语言
const setEditorLanguage = (scriptTypeId) => {
  if (!monacoEditor || isEditorDisposing.value || isEditorInitializing.value) return;
  
  const scriptType = scriptTypeData.value.find(type => type.id === scriptTypeId);
  if (scriptType) {
    let language = 'shell'; // 默认
    
    // 根据解释器路径判断语言类型
    const interpreterPath = scriptType.interpreter_path.toLowerCase();
    if (interpreterPath.includes('python')) {
      language = 'python';
    } else if (interpreterPath.includes('node') || interpreterPath.includes('npm')) {
      language = 'javascript';
    } else if (interpreterPath.includes('bash') || interpreterPath.includes('sh')) {
      language = 'shell';
    } else if (interpreterPath.includes('powershell') || interpreterPath.includes('pwsh')) {
      language = 'powershell';
    }
    
    try {
      const model = monacoEditor.getModel();
      if (model && !isEditorDisposing.value && !model.isDisposed()) {
        monaco.editor.setModelLanguage(model, language);
      }
    } catch (error) {
      console.warn('设置编辑器语言警告（可忽略）:', error);
    }
  }
};

// 打开脚本抽屉（新增）
const openCreateScriptDrawer = async () => {
  // 使用Object.assign确保响应式更新
  Object.assign(scriptForm, {
    id: undefined,
    name: '',
    script_type_id: undefined,
    description: '',
    script_context: '',
    requires_params: false,
    params_description: ''
  });
  
  scriptDrawerVisible.value = true;
  
  // 如果脚本类型数据为空，获取一次
  if (scriptTypeData.value.length === 0) {
    await fetchScriptTypeList();
  }
  
  // 初始化Monaco Editor
  await initMonacoEditor();
};

// 打开脚本抽屉（编辑）
const openEditScriptDrawer = async (record) => {
  // 使用Object.assign确保响应式更新
  Object.assign(scriptForm, {
    id: record.script_id,
    name: record.name,
    script_type_id: record.script_type_id,
    description: record.description,
    script_context: record.script_context,
    requires_params: record.requires_params || false,
    params_description: record.params_description || ''
  });
  
  scriptDrawerVisible.value = true;
  
  // 如果脚本类型数据为空，获取一次
  if (scriptTypeData.value.length === 0) {
    await fetchScriptTypeList();
  }
  
  // 初始化Monaco Editor并设置内容
  await initMonacoEditor();
  
  // 等待编辑器完全初始化后再设置内容
  await nextTick();
  if (monacoEditor && !isEditorDisposing.value) {
    try {
      monacoEditor.setValue(record.script_context || '');
      // 延迟设置语言，确保内容已设置
      setTimeout(() => {
        if (monacoEditor && !isEditorDisposing.value) {
          setEditorLanguage(record.script_type_id);
        }
      }, 50);
    } catch (error) {
      console.warn('设置编辑器内容警告（可忽略）:', error);
    }
  }
};

// 关闭脚本抽屉
const closeScriptDrawer = () => {
  // 先设置抽屉不可见
  scriptDrawerVisible.value = false;
  
  // 延迟清理编辑器，确保DOM已经隐藏
  nextTick(() => {
    disposeMonacoEditor();
    resetScriptForm();
  });
};

// 重置脚本表单
const resetScriptForm = () => {
  // 使用Object.assign确保响应式更新
  Object.assign(scriptForm, {
    id: undefined,
    name: '',
    script_type_id: undefined,
    description: '',
    script_context: '',
    requires_params: false,
    params_description: ''
  });
  
  // 清空Monaco Editor内容
  if (monacoEditor && !isEditorDisposing.value && !isEditorInitializing.value) {
    try {
      const model = monacoEditor.getModel();
      if (model && !model.isDisposed()) {
        monacoEditor.setValue('');
      }
    } catch (error) {
      console.warn('清空编辑器内容警告（可忽略）:', error);
    }
  }
  
  // 清除表单验证状态
  if (scriptFormRef.value) {
    scriptFormRef.value.clearValidate();
  }
};

// 监听脚本类型变化，动态设置编辑器语言
watch(() => scriptForm.script_type_id, (newTypeId) => {
  if (newTypeId && monacoEditor && !isEditorDisposing.value && !isEditorInitializing.value) {
    // 延迟执行，避免在快速切换时出现问题
    setTimeout(() => {
      if (monacoEditor && !isEditorDisposing.value && !isEditorInitializing.value) {
        setEditorLanguage(newTypeId);
      }
    }, 150);
  }
});

// 保存脚本
const saveScript = async ({ values, errors }) => {
  if (errors) return;
  
  try {
    if (scriptForm.id) {
      // 更新脚本
      await updateScript(scriptForm.id, reactive({
        name: scriptForm.name,
        script_type_id: scriptForm.script_type_id,
        description: scriptForm.description,
        script_context: scriptForm.script_context,
        requires_params: scriptForm.requires_params,
        params_description: scriptForm.params_description
      }));
      Message.success(t.value('updateScriptSuccess'));
    } else {
      // 创建脚本
      await createScript(reactive({
        name: scriptForm.name,
        script_type_id: scriptForm.script_type_id,
        description: scriptForm.description,
        script_context: scriptForm.script_context,
        requires_params: scriptForm.requires_params,
        params_description: scriptForm.params_description
      }));
      Message.success(t.value('createScriptSuccess'));
    }
    
    // 重置表单并刷新列表
    resetScriptForm();
    closeScriptDrawer();
    await fetchScriptList();
  } catch (error) {
    console.error('保存脚本失败:', error);
    Message.error(scriptForm.id ? t.value('updateScriptFailed') : t.value('createScriptFailed'));
  }
};

// 删除脚本相关
const deleteModalVisible = ref(false);
const deleteScriptTarget = reactive({
  script_id: 0,
  name: ''
});

// 显示删除脚本确认对话框
const confirmDeleteScript = (record) => {
  deleteScriptTarget.script_id = record.script_id;
  deleteScriptTarget.name = record.name;
  deleteModalVisible.value = true;
};

// 处理删除脚本
const handleDeleteScript = async () => {
  try {
    await apiDeleteScript(deleteScriptTarget.script_id);
    Message.success(t.value('deleteScriptSuccess'));
    deleteModalVisible.value = false;
    
    // 重新获取脚本列表
    await fetchScriptList();
  } catch (error) {
    console.error('删除脚本失败:', error);
    Message.error(t.value('deleteScriptFailed'));
    deleteModalVisible.value = false;
  }
};

// 取消删除脚本
const cancelDeleteScript = () => {
  deleteModalVisible.value = false;
};

// 删除脚本（保留原来的函数，但不再直接调用）
const deleteScript = async (scriptId) => {
  try {
    await apiDeleteScript(scriptId);
    Message.success(t.value('deleteScriptSuccess'));
    // 刷新脚本列表
    await fetchScriptList();
  } catch (error) {
    console.error('删除脚本失败:', error);
    Message.error(t.value('deleteScriptFailed'));
  }
};

// 实时执行脚本相关数据
const realTimeExecuteModalVisible = ref(false);
const realTimeExecuteTarget = reactive({
  script_id: 0,
  name: '',
  requires_params: false,
  params_description: ''
});
const realTimeSelectedHostIds = ref([]);
const scriptParameters = ref('');
const hostsData = ref([]);
const hostsLoading = ref(false);

// 标签页相关状态
const activeTabKey = ref('');
const terminalTabs = ref([]);
let tabCounter = 0;

// 终端相关状态 - 改为支持多个终端实例
const isTerminalFullscreen = ref(false);


// 获取主机列表
const fetchHostList = async () => {
  try {
    hostsLoading.value = true;
    const response = await getHosts();
    
    // 处理响应数据
    let hosts = [];
    
    if (response && response.items && Array.isArray(response.items)) {
      hosts = response.items;
    } else if (response && response.data && response.data.items && Array.isArray(response.data.items)) {
      hosts = response.data.items;
    } else if (response && Array.isArray(response)) {
      hosts = response;
    } else {
      hosts = [];
    }
    
    hostsData.value = hosts;
  } catch (error) {
    console.error('获取主机列表失败:', error);
    Message.error(t.value('getHostListFailed'));
    hostsData.value = [];
  } finally {
    hostsLoading.value = false;
  }
};

// 显示实时执行脚本对话框
const openRealTimeExecuteModal = async (record) => {
  // 使用Object.assign确保响应式更新
  Object.assign(realTimeExecuteTarget, {
    script_id: record.script_id,
    name: record.name,
    requires_params: record.requires_params || false,
    params_description: record.params_description || ''
  });
  realTimeSelectedHostIds.value = [];
  scriptParameters.value = '';
  realTimeExecuteModalVisible.value = true;
  
  // 获取主机列表
  await fetchHostList();
};

// 执行脚本的通用逻辑（支持多主机并发执行）
const executeScript = async () => {
  if (realTimeSelectedHostIds.value.length === 0) {
    Message.warning(t.value('pleaseSelectHost'));
    return;
  }
  
  // 为每个选中的主机创建独立的标签页和WebSocket连接
  const createdTabs = [];
  
  for (const hostId of realTimeSelectedHostIds.value) {
    const hostInfo = hostsData.value.find(h => h.id === hostId);
    const tabTitle = `${realTimeExecuteTarget.name} - ${hostInfo?.comment || hostInfo?.address || '未知主机'}`;
    const newTab = createNewTab(tabTitle);
    
    // 将主机ID绑定到标签页，用于后续识别
    newTab.hostId = hostId;
    createdTabs.push(newTab);
    
    try {
      // 更新当前标签页状态
      updateTabStatus(newTab.id, 'connecting');
      
      // 生成唯一的执行ID
      const executionId = 'execution_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9) + '_' + hostId;
      
      // 创建WebSocket连接（使用API方法）
      const websocket = connectScriptExecutionWebSocket(executionId);
      
      // 将websocket绑定到标签页
      newTab.websocket = websocket;
      
      // 设置WebSocket事件处理
      websocket.onopen = () => {
        console.log(`WebSocket连接已建立 - 主机 ${hostId}`);
        updateTabStatus(newTab.id, 'executing');
        
        const currentTab = getTabById(newTab.id);
        if (currentTab && currentTab.terminal) {
          currentTab.terminal.write(`\r\n\x1b[1;34m连接已建立，开始在主机 ${hostInfo?.comment || hostInfo?.address} 上执行脚本...\x1b[0m\r\n`);
        }
        
        // 发送执行参数 - 只发送当前主机ID
        websocket.send(JSON.stringify(reactive({
          script_id: realTimeExecuteTarget.script_id,
          host_ids: [hostId], // 只发送当前主机ID
          script_parameters: scriptParameters.value
        })));
      };
      
      websocket.onmessage = (event) => {
        const currentTab = getTabById(newTab.id);
        if (currentTab && currentTab.terminal) {
          try {
            const data = JSON.parse(event.data);
            // 只处理对象类型的消息
            if (data && typeof data === 'object') {
              if (data.error) {
                currentTab.terminal.write(`\r\n\x1b[1;31m*** 错误: ${data.error} ***\x1b[0m\r\n`);
                updateTabStatus(newTab.id, 'error');
                return;
              }
              // 处理结构化消息
              if (data.type) {
                handleExecutionMessage(data, newTab.id);
                return;
              }
            }
          } catch {
            // JSON 解析失败，说明是普通文本
          }
          // 所有非错误、非结构化消息都写入终端
          try {
            currentTab.terminal.write(event.data);
          } catch (e) {
            console.warn('Terminal write error:', e);
          }
        }
      };
      
      websocket.onerror = (error) => {
        console.error(`WebSocket错误 - 主机 ${hostId}:`, error);
        const currentTab = getTabById(newTab.id);
        if (currentTab && currentTab.terminal) {
          currentTab.terminal.write(`\r\n\x1b[1;31mWebSocket连接错误: ${error.message || '未知错误'}\x1b[0m\r\n`);
        }
        updateTabStatus(newTab.id, 'error');
      };
      
      websocket.onclose = () => {
        console.log(`WebSocket连接已关闭 - 主机 ${hostId}`);
        const currentTab = getTabById(newTab.id);
        if (currentTab && currentTab.terminal && currentTab.status !== 'completed' && currentTab.status !== 'error') {
          currentTab.terminal.write('\r\n\x1b[1;33m连接已关闭\x1b[0m\r\n');
        }
        // 确保状态被设置为完成
        if (currentTab && (currentTab.status === 'executing' || currentTab.status === 'connecting')) {
          updateTabStatus(newTab.id, 'completed');
        }
      };
      
    } catch (error) {
      console.error(`启动实时执行失败 - 主机 ${hostId}:`, error);
      Message.error(`主机 ${hostInfo?.comment || hostInfo?.address} 执行失败: ${error.message}`);
      updateTabStatus(newTab.id, 'error');
    }
  }
  
  // 如果创建了多个标签页，切换到第一个
  if (createdTabs.length > 0) {
    activeTabKey.value = createdTabs[0].id;
  }
  
  // 显示执行开始的消息
  if (createdTabs.length > 1) {
    Message.success(`已为 ${createdTabs.length} 个主机创建执行任务`);
  }
};

// 开始实时执行
const startRealTimeExecution = async () => {
  await executeScript();
};



// 处理执行按钮点击
const handleExecutionButtonClick = () => {
  // 直接执行，每次执行都会创建新的标签页
  startRealTimeExecution();
};



// 标签页管理函数
const createNewTab = (title) => {
  tabCounter++;
  const newTab = reactive({
    id: `tab_${tabCounter}`,
    title: title || `终端 ${tabCounter}`,
    status: 'idle', // idle, connecting, executing, completed, error
    terminal: null,
    fitAddon: null,
    websocket: null,
    containerRef: null,
    hostId: null // 添加主机ID字段，用于标识该标签页对应的主机
  });
  
  terminalTabs.value.push(newTab);
  // 不自动切换到新标签页，让调用者决定
  
  return newTab;
};

const closeTab = (tabId) => {
  const tabIndex = terminalTabs.value.findIndex(tab => tab.id === tabId);
  if (tabIndex === -1) return;
  
  const tab = terminalTabs.value[tabIndex];
  
  // 清理资源
  if (tab.websocket) {
    try {
      tab.websocket.close();
    } catch (e) {
      console.warn('关闭WebSocket警告:', e);
    }
  }
  
  if (tab.terminal) {
    try {
      // 检查fitAddon是否已经被加载到终端中
      if (tab.fitAddon && tab.terminal.loadedAddons && tab.terminal.loadedAddons.has(tab.fitAddon)) {
        try {
          tab.fitAddon.dispose();
        } catch (addonError) {
          // 忽略fitAddon销毁错误
          console.warn('FitAddon销毁警告（可忽略）:', addonError.message);
        }
      }
      tab.terminal.dispose();
    } catch (e) {
      // 只在非预期错误时输出警告
      if (!e.message.includes('Could not dispose an addon that has not been loaded')) {
        console.warn('清理标签页终端资源警告:', e);
      }
    }
  }
  
  // 清理引用
  tab.terminal = null;
  tab.fitAddon = null;
  tab.websocket = null;
  tab.containerRef = null;
  
  // 移除标签页
  terminalTabs.value.splice(tabIndex, 1);
  
  // 如果关闭的是当前活动标签页，切换到其他标签页
  if (activeTabKey.value === tabId && terminalTabs.value.length > 0) {
    activeTabKey.value = terminalTabs.value[Math.max(0, tabIndex - 1)].id;
  }
  
  // 如果没有标签页了，不需要创建默认标签页
};

const handleTabClick = (tabId) => {
  activeTabKey.value = tabId;
  // 切换标签页时调整终端大小
  nextTick(() => {
    // 延迟一点时间，确保CSS变化和DOM更新完成
    setTimeout(() => {
      const tab = getTabById(tabId);
      if (tab && tab.fitAddon && tab.terminal) {
        try {
          // 确保容器可见后再调整大小
          if (tab.containerRef && tab.containerRef.offsetWidth > 0 && tab.containerRef.offsetHeight > 0) {
            tab.fitAddon.fit();
          }
        } catch (e) {
          console.warn('切换标签页时调整终端大小警告:', e);
        }
      }
    }, 150); // 增加延迟时间
  });
};

const getTabById = (tabId) => {
  return terminalTabs.value.find(tab => tab.id === tabId);
};

const updateTabStatus = (tabId, status) => {
  const tab = getTabById(tabId);
  if (tab) {
    tab.status = status;
  }
};

const getStatusText = (status) => {
  const statusMap = {
    idle: '空闲',
    connecting: '连接中',
    executing: '执行中',
    completed: '已完成',
    error: '错误'
  };
  return statusMap[status] || status;
};

const clearActiveTabOutput = () => {
  const activeTab = getTabById(activeTabKey.value);
  if (activeTab && activeTab.terminal) {
    activeTab.terminal.clear();
  }
};

const clearAllTabs = () => {
  terminalTabs.value.forEach(tab => {
    if (tab.terminal) {
      tab.terminal.clear();
    }
  });
};

// 滚动到底部
const scrollToBottom = () => {
  const activeTab = getTabById(activeTabKey.value);
  if (activeTab && activeTab.terminal) {
    // 滚动到终端底部
    activeTab.terminal.scrollToBottom();
  }
};

// 设置终端容器引用
const setTerminalRef = (el, tabId) => {
  const tab = getTabById(tabId);
  if (tab && el) {
    tab.containerRef = el;
    // 为所有标签页初始化终端，不仅仅是活动标签页
    if (!tab.terminal) {
      nextTick(() => {
        initializeTerminalForTab(tabId);
      });
    }
  }
};

// 为特定标签页初始化终端
const initializeTerminalForTab = (tabId) => {
  const tab = getTabById(tabId);
  if (!tab || !tab.containerRef || tab.terminal) {
    return;
  }

  try {
    // 创建新终端实例，优化滚动和显示
    tab.terminal = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Consolas, "Courier New", "SFMono-Regular", "Menlo", "Monaco", "Roboto Mono", "Ubuntu Mono", monospace',
      // 不设置固定的 cols 和 rows，让 FitAddon 自动计算
      theme: {
        background: '#000000',
        foreground: '#ffffff',
        cursor: '#ffffff',
        selectionBackground: '#264f78',
        selectionForeground: '#ffffff',
        cursorAccent: '#000000',
        black: '#000000',
        red: '#cd3131',
        green: '#0dbc79',
        yellow: '#e5e510',
        blue: '#2472c8',
        magenta: '#bc3fbc',
        cyan: '#11a8cd',
        white: '#e5e5e5',
        brightBlack: '#666666',
        brightRed: '#f14c4c',
        brightGreen: '#23d18b',
        brightYellow: '#f5f543',
        brightBlue: '#3b8eea',
        brightMagenta: '#d670d6',
        brightCyan: '#29b8db',
        brightWhite: '#e5e5e5',
      },
      allowTransparency: false,
      scrollback: 10000, // 增加滚动缓冲区
      fontWeight: 'normal',
      fontWeightBold: 'bold',
      lineHeight: 1.2,
      letterSpacing: 0,
      convertEol: true, // 启用换行转换
      disableStdin: false,
      // 优化滚动行为
      scrollOnUserInput: true,
      fastScrollModifier: 'alt',
      fastScrollSensitivity: 5,
      scrollSensitivity: 1,
    });

    // 打开终端
    tab.terminal.open(tab.containerRef);

    // 创建并加载fit插件（在终端打开后）
    try {
      tab.fitAddon = new FitAddon();
      tab.terminal.loadAddon(tab.fitAddon);
      // 验证addon是否成功加载
      if (!tab.terminal.loadedAddons || !tab.terminal.loadedAddons.has(tab.fitAddon)) {
        tab.fitAddon = null;
      }
    } catch (e) {
      console.warn('加载FitAddon失败:', e);
      tab.fitAddon = null;
    }

    // 添加事件监听器
    tab.terminal.onData((data) => {
      // 确保只向该标签页对应的WebSocket发送数据
      if (tab.websocket && tab.websocket.readyState === WebSocket.OPEN) {
        tab.websocket.send(JSON.stringify(reactive({ type: 'input', data: data })));
      }
    });

    tab.terminal.onResize((size) => {
      // 确保只向该标签页对应的WebSocket发送大小调整信息
      if (tab.websocket && tab.websocket.readyState === WebSocket.OPEN) {
        tab.websocket.send(JSON.stringify(reactive({ type: 'resize', data: size })));
      }
    });

    // 特殊按键处理
    tab.terminal.attachCustomKeyEventHandler((event) => {
      if (event.ctrlKey && event.key === 'c' && event.type === 'keydown') {
        // 确保只向该标签页对应的WebSocket发送中断信号
        if (tab.websocket && tab.websocket.readyState === WebSocket.OPEN) {
          const message = JSON.stringify(reactive({ type: 'input', data: '\x03' }));
          tab.websocket.send(message);
          event.preventDefault();
          return false;
        }
      }
      return true;
    });

    // 设置ResizeObserver来自动调整终端大小（节流处理）
    let resizeTimeout = null;
    const resizeObserver = new ResizeObserver(() => {
      if (resizeTimeout) {
        clearTimeout(resizeTimeout);
      }
      resizeTimeout = setTimeout(() => {
        // 只在标签页可见且是活动标签页时调整大小
        if (tab.fitAddon && tab.terminal && activeTabKey.value === tabId) {
          try {
            // 确保容器真正可见
            if (tab.containerRef && tab.containerRef.offsetWidth > 0 && tab.containerRef.offsetHeight > 0) {
              tab.fitAddon.fit();
            }
          } catch (e) {
            console.warn('Fit addon error:', e);
          }
        }
      }, 100); // 100ms 节流
    });

    if (tab.containerRef?.parentElement) {
      resizeObserver.observe(tab.containerRef.parentElement);
    }

    // 初始大小调整
    if (tab.fitAddon) {
      // 延迟调整，确保DOM完全渲染
      setTimeout(() => {
        if (tab.fitAddon && tab.terminal) {
          try {
            // 如果是当前活动标签页，立即调整
            if (activeTabKey.value === tabId) {
              tab.fitAddon.fit();
              // 确保滚动到底部显示最新内容
              setTimeout(() => {
                if (tab.terminal) {
                  tab.terminal.scrollToBottom();
                }
              }, 100);
              console.log(`活动标签页 ${tabId} 终端大小已调整`);
            } else {
              // 如果不是活动标签页，先设置一个默认大小
              // 当标签页变为活动时会重新调整
              console.log(`非活动标签页 ${tabId} 终端已初始化，等待激活时调整大小`);
            }
          } catch (e) {
            console.warn('初始终端大小调整警告:', e);
          }
        }
      }, 200);
    }

    console.log(`标签页 ${tabId} 终端初始化成功`);
  } catch (error) {
    console.error(`标签页 ${tabId} 终端初始化失败:`, error);
  }
};

// 切换终端全屏
const toggleTerminalFullscreen = () => {
  isTerminalFullscreen.value = !isTerminalFullscreen.value;
  // 在下一个tick中调整当前活动终端大小
  nextTick(() => {
    setTimeout(() => {
      const activeTab = getTabById(activeTabKey.value);
      if (activeTab && activeTab.fitAddon && activeTab.terminal) {
        try {
          // 确保容器尺寸已经更新
          if (activeTab.containerRef && activeTab.containerRef.offsetWidth > 0) {
            activeTab.fitAddon.fit();
          }
        } catch (e) {
          console.warn('终端全屏调整警告:', e);
        }
      }
    }, 300); // 给全屏动画更多时间
  });
};

// 处理执行消息
const handleExecutionMessage = (data, tabId) => {
  const tab = getTabById(tabId);
  if (!tab || !tab.terminal) return;
  
  const timestamp = new Date().toLocaleTimeString();
  const timestampStr = `[${timestamp}]`;
  
  switch (data.type) {
    case 'start':
      tab.terminal.write(`\r\n\x1b[32m${timestampStr} 开始执行脚本: ${data.script_name}\x1b[0m\r\n`);
      // 显示后端返回的参数信息（如果存在）
      if (data.parameters && data.parameters.trim()) {
        tab.terminal.write(`\r\n\x1b[32m${timestampStr} 脚本参数: ${data.parameters}\x1b[0m\r\n`);
      }
      // 显示当前主机信息
      if (tab.hostId) {
        const hostInfo = hostsData.value.find(h => h.id === tab.hostId);
        if (hostInfo) {
          tab.terminal.write(`\r\n\x1b[32m${timestampStr} 目标主机: ${hostInfo.comment} (${hostInfo.address})\x1b[0m\r\n`);
        }
      }
      break;
    case 'host_start':
      tab.terminal.write(`\r\n\x1b[32m${timestampStr} 开始执行脚本\x1b[0m\r\n`);
      break;
    case 'host_result':
      if (data.output) {
        tab.terminal.write(`\r\n\x1b[34m${timestampStr} 执行输出:\x1b[0m\r\n`);
        // 直接写入输出，让xterm.js处理ANSI转义序列
        tab.terminal.write(data.output);
        if (!data.output.endsWith('\r\n') && !data.output.endsWith('\n')) {
          tab.terminal.write('\r\n');
        }
      }
      if (data.error) {
        tab.terminal.write(`\r\n\x1b[31m${timestampStr} 执行错误:\x1b[0m\r\n`);
        tab.terminal.write(`\x1b[31m${data.error}\x1b[0m\r\n`);
      }
      tab.terminal.write(`\r\n\x1b[32m${timestampStr} 脚本执行${data.success ? '成功' : '失败'}\x1b[0m\r\n`);
      break;
    case 'complete':
      tab.terminal.write(`\r\n\x1b[32m${timestampStr} 脚本执行完成\x1b[0m\r\n`);
      updateTabStatus(tabId, 'completed');
      break;
    case 'error':
      tab.terminal.write(`\r\n\x1b[31m${timestampStr} 执行错误: ${data.message}\x1b[0m\r\n`);
      updateTabStatus(tabId, 'error');
      break;
    case 'output':
      // 处理纯输出消息
      if (data.content) {
        // 直接写入内容，让xterm.js处理ANSI转义序列
        tab.terminal.write(data.content);
      }
      break;
  }
  
  // 每次写入内容后，如果是当前活动标签页，自动滚动到底部
  if (activeTabKey.value === tabId) {
    // 使用 nextTick 确保内容已经渲染
    nextTick(() => {
      if (tab.terminal) {
        tab.terminal.scrollToBottom();
      }
    });
  }
};

// 清理所有终端资源
const disposeAllTerminals = () => {
  terminalTabs.value.forEach(tab => {
    if (tab.websocket) {
      try {
        tab.websocket.close();
      } catch (e) {
        console.warn('关闭WebSocket警告:', e);
      }
    }
    
    if (tab.terminal) {
      try {
        // 检查fitAddon是否已经被加载到终端中
        if (tab.fitAddon && tab.terminal.loadedAddons && tab.terminal.loadedAddons.has(tab.fitAddon)) {
          try {
            tab.fitAddon.dispose();
          } catch (addonError) {
            // 忽略fitAddon销毁错误
            console.warn('FitAddon销毁警告（可忽略）:', addonError.message);
          }
        }
        tab.terminal.dispose();
      } catch (e) {
        // 只在非预期错误时输出警告
        if (!e.message.includes('Could not dispose an addon that has not been loaded')) {
          console.warn('清理终端资源警告:', e);
        }
      }
    }
    
    // 清理引用
    tab.terminal = null;
    tab.fitAddon = null;
    tab.websocket = null;
    tab.containerRef = null;
  });
  
  terminalTabs.value = [];
  activeTabKey.value = '';
};

// 取消实时执行
const cancelRealTimeExecute = () => {
  // 清理所有终端资源
  disposeAllTerminals();
  
  // 重置全屏状态
  isTerminalFullscreen.value = false;
  
  // 重置参数
  scriptParameters.value = '';
  realTimeExecuteModalVisible.value = false;
};

// 组件卸载前清理资源
onBeforeUnmount(() => {
  // 设置销毁标志，防止异步操作继续执行
  isEditorDisposing.value = true;
  
  // 清理所有终端资源
  disposeAllTerminals();
  
  // 重置全屏状态
  isTerminalFullscreen.value = false;
  
  // 清理Monaco Editor - 放在最后执行
  disposeMonacoEditor();
});

// 监听模态框显示状态
watch(realTimeExecuteModalVisible, async (newVal) => {
  if (newVal) {
    console.log('模态框打开，准备初始化标签页');
    // 等待DOM更新完成
    await nextTick();
    
    // 延迟初始化，确保模态框完全渲染
    setTimeout(() => {
      // 为所有标签页初始化终端
      terminalTabs.value.forEach(tab => {
        if (tab.containerRef && !tab.terminal) {
          initializeTerminalForTab(tab.id);
        }
      });
      
      // 再次延迟，刷新所有终端大小
      setTimeout(() => {
        refreshAllTerminalSizes();
      }, 300);
    }, 600);
  } else {
    // 模态框关闭时清理所有终端
    disposeAllTerminals();
    isTerminalFullscreen.value = false;
  }
});

// 监听全屏状态变化
watch(isTerminalFullscreen, (newVal) => {
  if (newVal) {
    document.body.style.overflow = 'hidden';
  } else {
    document.body.style.overflow = '';
  }
  
  // 在下一个tick中调整所有终端大小
  nextTick(() => {
    terminalTabs.value.forEach(tab => {
      if (tab.fitAddon && tab.terminal) {
        try {
          tab.fitAddon.fit();
        } catch (e) {
          console.warn('终端大小调整警告:', e);
        }
      }
    });
  });
});

// 监听活动标签页变化，初始化终端
watch(activeTabKey, async (newTabId, oldTabId) => {
  if (newTabId && realTimeExecuteModalVisible.value) {
    await nextTick();
    
    // 如果标签页还没有终端，先初始化
    setTimeout(() => {
      const tab = getTabById(newTabId);
      if (tab && tab.containerRef && !tab.terminal) {
        initializeTerminalForTab(newTabId);
      } else if (tab && tab.terminal && tab.fitAddon) {
        // 如果终端已存在，确保容器可见后调整大小
        try {
          // 等待CSS变化完成，确保容器从隐藏状态变为可见
          setTimeout(() => {
            if (tab.fitAddon && tab.terminal && activeTabKey.value === newTabId) {
              // 检查容器是否真正可见
              if (tab.containerRef && tab.containerRef.offsetWidth > 0 && tab.containerRef.offsetHeight > 0) {
                tab.fitAddon.fit();
                console.log(`标签页 ${newTabId} 终端大小已调整`);
              }
            }
          }, 100);
        } catch (e) {
          console.warn('切换标签页时调整终端大小警告:', e);
        }
      }
    }, 200);
  }
});

// 监听窗口大小变化，调整终端大小
const handleWindowResize = () => {
  terminalTabs.value.forEach(tab => {
    // 只调整当前活动标签页的终端大小
    if (tab.fitAddon && tab.terminal && activeTabKey.value === tab.id) {
      try {
        if (tab.containerRef && tab.containerRef.offsetWidth > 0) {
          tab.fitAddon.fit();
        }
      } catch (e) {
        console.warn('窗口大小变化时终端调整警告:', e);
      }
    }
  });
};

// 强制刷新所有终端大小（用于模态框显示后）
const refreshAllTerminalSizes = () => {
  terminalTabs.value.forEach(tab => {
    if (tab.fitAddon && tab.terminal && tab.containerRef) {
      try {
        // 如果是活动标签页，立即调整
        if (activeTabKey.value === tab.id && tab.containerRef.offsetWidth > 0) {
          tab.fitAddon.fit();
          console.log(`刷新标签页 ${tab.id} 终端大小`);
        }
      } catch (e) {
        console.warn('刷新终端大小警告:', e);
      }
    }
  });
};

// 组件挂载时获取数据和添加监听器
onMounted(() => {
  fetchScriptList();
  window.addEventListener('resize', handleWindowResize);
});

// 移除窗口大小变化监听器
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleWindowResize);
});
</script>

<style scoped>
.host-container {
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

/* 脚本表单容器样式 */
.script-form-container {
  padding: 20px;
}

/* 统一表单项宽度 */
.script-form-container .arco-form-item {
  margin-bottom: 20px;
}

.script-form-container .arco-form-item-content {
  width: 100%;
}

.script-form-container .arco-input,
.script-form-container .arco-select,
.script-form-container .arco-textarea,
.script-form-container .monaco-editor-container {
  width: 100%;
}

/* 脚本类型表单容器样式 */
.script-type-form-container {
  margin-top: 20px;
  padding: 20px;
  border-top: 1px solid #e5e6eb;
}

/* 统一脚本类型表单项宽度 */
.script-type-form-container .arco-form-item {
  margin-bottom: 20px;
}

.script-type-form-container .arco-form-item-content {
  width: 100%;
}

.script-type-form-container .arco-input,
.script-type-form-container .arco-textarea {
  width: 100%;
}

/* Monaco Editor 容器样式 */
.monaco-editor-container {
  width: 100%;
  height: 400px;
  border: 1px solid var(--arco-color-border);
  border-radius: 6px;
  overflow: hidden;
}

.monaco-editor-container:hover {
  border-color: #40a9ff;
}

.monaco-editor-container:focus-within {
  border-color: #40a9ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

/* 按钮区域样式 */
.form-buttons {
  margin-top: 30px;
}

.form-buttons .arco-form-item-content {
  justify-content: flex-start !important;
}

/* 实时执行输出样式 */
.execution-output {
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  height: 600px;
  max-height: calc(100vh - 300px); /* 响应式高度，在移动端自动适应 */
  display: flex;
  flex-direction: column;
  position: relative;
  background-color: #000;
  overflow: hidden; /* 防止内容溢出 */
}

/* 全屏终端样式 */
.execution-output.fullscreen-terminal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  max-height: 100vh; /* 限制最大高度 */
  z-index: 1000;
  border-radius: 0;
  border: none;
  overflow: hidden; /* 防止溢出 */
}

/* 全屏模式下的标签页容器 */
.execution-output.fullscreen-terminal .terminal-tabs-container {
  height: calc(100vh - 50px); /* 减去头部高度 */
  max-height: calc(100vh - 50px);
}

/* 全屏模式下的终端内容 */
.execution-output.fullscreen-terminal .output-content {
  height: 100%;
  max-height: 100%;
}

/* 终端头部 */
.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background-color: #1a1a1a;
  border-bottom: 1px solid #333;
  color: #fff;
}

.terminal-title {
  font-size: 14px;
  font-weight: 500;
}

.terminal-actions {
  display: flex;
  gap: 8px;
}

.fullscreen-btn {
  color: #fff;
  transition: all 0.2s;
}

.fullscreen-btn:hover {
  color: #165dff;
  background-color: rgba(255, 255, 255, 0.1);
}

/* 标签页容器 */
.terminal-tabs-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: #000;
  height: 0; /* 强制flex子元素计算高度 */
  min-height: 0; /* 允许收缩 */
}

/* 标签页样式 */
.terminal-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden; /* 防止溢出 */
}

.terminal-tabs :deep(.arco-tabs-content) {
  flex: 1;
  height: 0; /* 强制flex子元素计算高度 */
  min-height: 0; /* 允许收缩 */
  background-color: #000;
  overflow: hidden; /* 防止内容溢出 */
}

.terminal-tabs :deep(.arco-tabs-content-item) {
  height: 100%;
  padding: 0;
  overflow: hidden; /* 防止溢出 */
}

.terminal-tabs :deep(.arco-tabs-nav) {
  background-color: #1a1a1a;
  margin: 0;
  padding: 0 16px;
}

.terminal-tabs :deep(.arco-tabs-tab) {
  color: #ccc;
  border-color: #333;
}

.terminal-tabs :deep(.arco-tabs-tab-active) {
  color: #fff;
  background-color: #000;
  border-bottom-color: #000;
}

.terminal-tabs :deep(.arco-tabs-tab:hover) {
  color: #fff;
}

/* 标签页标题样式 */
.tab-title {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 200px;
}

.tab-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.tab-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.tab-close-icon {
  width: 14px;
  height: 14px;
  color: #999;
  cursor: pointer;
  transition: color 0.2s;
  flex-shrink: 0;
}

.tab-close-icon:hover {
  color: #ff4d4f;
}

.tab-status.status-idle {
  background-color: #666;
}

.tab-status.status-connecting {
  background-color: #faad14;
  animation: pulse 1.5s infinite;
}

.tab-status.status-executing {
  background-color: #52c41a;
  animation: pulse 1.5s infinite;
}

.tab-status.status-completed {
  background-color: #1890ff;
}

.tab-status.status-error {
  background-color: #ff4d4f;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* 终端内容区域 */
.output-content {
  flex: 1;
  overflow: hidden;
  background-color: #000;
  position: relative;
  height: 100%; /* 使用100%高度 */
  max-height: 100%; /* 限制最大高度 */
}

/* 终端容器样式 */
.terminal-container {
  width: 100%;
  height: 100%;
  max-height: 100%; /* 限制最大高度 */
  background-color: #000;
  position: relative;
  overflow: hidden; /* 防止内容溢出 */
}

/* 隐藏非活动终端，但保持DOM结构 */
.terminal-hidden {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  visibility: hidden;
  pointer-events: none;
  z-index: -1;
}

/* 确保终端元素样式正确 */
.output-content .xterm {
  height: 100% !important;
  width: 100% !important;
  font-family: Consolas, "Courier New", "SFMono-Regular", "Menlo", "Monaco", "Roboto Mono", "Ubuntu Mono", monospace !important;
  font-size: 14px !important;
}

/* xterm.js 相关样式 */
.output-content .xterm .xterm-viewport {
  background-color: transparent !important;
}

.output-content .xterm .xterm-screen {
  background-color: transparent !important;
}

/* 强制覆盖 xterm.js 字体渲染，确保ANSI颜色正确显示 */
.output-content .xterm,
.output-content .xterm .xterm-rows span,
.output-content .xterm .xterm-screen,
.output-content .xterm .xterm-scroll-area,
.output-content .xterm .xterm-char-measure-element {
  font-family: Consolas, "Courier New", "SFMono-Regular", "Menlo", "Monaco", "Roboto Mono", "Ubuntu Mono", monospace !important;
  font-size: 14px !important;
  font-weight: normal !important;
}

.params-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #8c8c8c;
  font-style: italic;
  white-space: pre-wrap;
  word-break: break-word;
}

/* 兼容旧样式 */
.output-line {
  margin-bottom: 4px;
}

.content {
  white-space: pre-wrap;
  word-break: break-word;
}

.output-line.info {
  color: #4caf50;
}

.output-line.error {
  color: #f44336;
}

.output-line.output {
  color: #2196f3;
}

.timestamp {
  color: #9e9e9e;
  margin-right: 8px;
}

.empty-output {
  color: #9e9e9e;
  text-align: center;
  padding: 20px;
  font-style: italic;
}

/* 空终端占位符样式 */
.empty-terminal-placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #000;
  color: #666;
}

.placeholder-content {
  text-align: center;
  padding: 40px 20px;
}

.placeholder-icon {
  margin-bottom: 16px;
  opacity: 0.6;
}

.placeholder-text h3 {
  margin: 0 0 8px 0;
  font-size: 16px;
  font-weight: 500;
  color: #888;
}

.placeholder-text p {
  margin: 0;
  font-size: 14px;
  color: #666;
  line-height: 1.5;
}

.placeholder-text .placeholder-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #888;
  font-style: italic;
}

/* 根据需要调整其他样式 */
</style>