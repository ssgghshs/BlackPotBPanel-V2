<template>
  <a-card class="process-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('process') }}</span>
      </div>
    </template>

    <!-- 搜索和控制栏 -->
      <a-space :size="12" wrap>
        <a-select 
          v-model="searchFilters.status" 
          :placeholder="t('status')"
          allow-clear
          style="width: 150px"
        >
          <a-option value="running">{{ t('running') }}</a-option>
          <a-option value="sleeping">{{ t('sleeping') }}</a-option>
          <a-option value="idle">{{ t('idle') }}</a-option>
          <a-option value="zombie">{{ t('zombie') }}</a-option>
          <a-option value="stopped">{{ t('stopped') }}</a-option>
          <a-option value="defunct">{{ t('defunct') }}</a-option>
          <a-option value="waiting">{{ t('waiting') }}</a-option>
        </a-select>
        
        <a-input 
          v-model="searchFilters.pid" 
          :placeholder="t('pid')"
          allow-clear
          style="width: 150px"
        />
        
        <a-input 
          v-model="searchFilters.name" 
          :placeholder="t('processName')"
          allow-clear
          style="width: 200px"
        />
        
        <a-input 
          v-model="searchFilters.user" 
          :placeholder="t('user')"
          allow-clear
          style="width: 150px"
        />
        
        <a-switch 
          v-model="autoRefresh" 
          @change="handleAutoRefreshChange"
        >
          <template #checked>
            {{ t('autoRefreshOn') }}
          </template>
          <template #unchecked>
            {{ t('autoRefreshOff') }}
          </template>
        </a-switch>
      </a-space>

    <!-- 进程列表表格 -->
    <a-table 
      :columns="columns" 
      :data="filteredProcesses" 
      :loading="loading"
      :scroll="scroll"
      row-key="pid"
      :pagination="pagination"
      @page-change="handlePageChange"
      @page-size-change="handlePageSizeChange"
    >
      <template #create_time="{ record }">
        {{ formatDate(record.create_time) }}
      </template>
      <template #cpu_percent="{ record }">
        {{ formatPercent(record.cpu_percent) }}
      </template>
      <template #memory_percent="{ record }">
        {{ formatPercent(record.memory_percent) }}
      </template>
      <template #status="{ record }">
        <a-tag :color="getStatusColor(record.status)">
          {{ getStatusText(record.status) }}
        </a-tag>
      </template>
      <template #operation="{ record }">
        <a-link key="detail" @click="showProcessDetail(record)">
          {{ t('detail') }}
        </a-link>
        <a-link key="terminate" status="danger" @click="handleTerminateProcess(record)">
          {{ t('terminate') }}
        </a-link>
      </template>
    </a-table>
  </a-card>
  
  <!-- 进程详情对话框 -->
    <a-modal
      v-model:visible="detailDialogVisible"
      :title="t('detail')"
      :width="900"
      @ok="handleDialogOk"
      @cancel="handleDialogCancel"
      :footer="false"
      body-style="max-height: 70vh; overflow-y: auto;"
    >
      <div class="dialog-content">
        <a-skeleton v-if="detailLoading" :rows="12" :paragraph="{ rows: 12 }" :loading="detailLoading" />
        <a-tabs v-else v-model:active-key="activeTabKey" default-active-key="basic" position="left" style="width: 100%;" @change="handleTabChange">
          <!-- 基本信息标签页 -->
          <a-tab-pane key="basic" :title="t('basicInfo')">
            <div v-if="currentProcess" class="tab-content">
              <a-descriptions :column="2" bordered>
                <a-descriptions-item :label="t('name')">{{ currentProcess.name }}</a-descriptions-item>
                <a-descriptions-item :label="t('status')">{{ currentProcess.status }}</a-descriptions-item>
                <a-descriptions-item :label="t('pid')">{{ currentProcess.PID }}</a-descriptions-item>
                <a-descriptions-item :label="t('parentPid')">{{ currentProcess.PPID }}</a-descriptions-item>
                <a-descriptions-item :label="t('threads')">{{ currentProcess.numThreads }}</a-descriptions-item>
                <a-descriptions-item :label="t('connection')">{{ currentProcess.numConnections }}</a-descriptions-item>
                <a-descriptions-item :label="t('diskRead')">{{ currentProcess.diskRead }}</a-descriptions-item>
                <a-descriptions-item :label="t('diskWrite')">{{ currentProcess.diskWrite }}</a-descriptions-item>
                <a-descriptions-item :label="t('user')">{{ currentProcess.username }}</a-descriptions-item>
                <a-descriptions-item :label="t('startTime')">{{ currentProcess.startTime }}</a-descriptions-item>
                <a-descriptions-item :label="t('startCommand')" :span="2">{{ currentProcess.cmdLine }}</a-descriptions-item>
              </a-descriptions>
            </div>
            <div v-else class="empty-content">
              <a-empty :description="t('noData')" />
            </div>
          </a-tab-pane>
          <!-- 资源使用标签页 -->
          <a-tab-pane key="memoryUsage" :title="t('memoryUsage')">  
            <div v-if="currentProcess" class="tab-content">
              <a-descriptions :column="2" bordered>
                <a-descriptions-item label="rss">{{ currentProcess.rss }}</a-descriptions-item>
                <a-descriptions-item label="swap">{{ currentProcess.swap }}</a-descriptions-item>
                <a-descriptions-item label="vms">{{ currentProcess.vms }}</a-descriptions-item>
                <a-descriptions-item label="hwm">{{ currentProcess.hwm }}</a-descriptions-item>
                <a-descriptions-item label="data">{{ currentProcess.data }}</a-descriptions-item>
                <a-descriptions-item label="stack">{{ currentProcess.stack }}</a-descriptions-item>
                <a-descriptions-item label="locked">{{ currentProcess.locked }}</a-descriptions-item>
              </a-descriptions>
            </div>
            <div v-else class="empty-content">
              <a-empty :description="t('noData')" />
            </div>
          </a-tab-pane>
          <!-- 文件标签页 -->
          <a-tab-pane key="file" :title="t('file')">
            <div class="tab-content">
              <a-skeleton v-if="detailLoading" :rows="8" :paragraph="{ rows: 8 }" :loading="detailLoading" />
              <template v-else>
                <div v-if="currentProcess">
                  <a-table
                    v-if="currentProcess.openFiles && currentProcess.openFiles.length > 0"
                    :columns="fileColumns"
                    :data="currentProcess.openFiles"
                    bordered
                    row-key="fd"
                    :pagination="false"
                    size="small"
                    :scroll="{ y: 400 }"
                  >
                  </a-table>
                  <div v-else class="empty-content">
                    <a-empty :description="t('noData')" />
                  </div>
                </div>
                <div v-else class="empty-content">
                  <a-empty :description="t('noData')" />
                </div>
              </template>
            </div>
          </a-tab-pane>

          <!-- 环境变量标签页 -->
          <a-tab-pane key="environment" :title="t('environmentVariables')">
            <div class="tab-content env-tab-content">
              <a-skeleton v-if="detailLoading" :rows="15" paragraph />
              <template v-else-if="currentProcess">
                <div v-show="currentProcess.envs && currentProcess.envs.length > 0" ref="envEditorRef" class="monaco-editor-container"></div>
                <a-empty
                  v-show="!currentProcess.envs || currentProcess.envs.length === 0"
                  :description="t('noData')"
                  style="margin: 40px 0;"
                />
              </template>
            </div>
          </a-tab-pane>

          <!-- 网络标签页 -->
          <a-tab-pane key="network" :title="t('network')">
            <div class="tab-content">
              <a-skeleton v-if="detailLoading" :rows="8" :paragraph="{ rows: 8 }" :loading="detailLoading" />
              <template v-else>
                <div v-if="currentProcess">
                  <a-table
                    v-if="currentProcess.connects && currentProcess.connects.length > 0"
                    :columns="networkColumns"
                    :data="currentProcess.connects"
                    bordered
                    :pagination="{ pageSize: 20, showQuickJumper: true }"
                    size="small"
                    :scroll="{ y: 400 }"
                  >
                  </a-table>
                  <div v-else class="empty-content">
                    <a-empty :description="t('noData')" />
                  </div>
                </div>
                <div v-else class="empty-content">
                  <a-empty :description="t('noData')" />
                </div>
              </template>
            </div>
          </a-tab-pane>
        </a-tabs>
      </div>
    </a-modal>
  
  <!-- 终止进程确认对话框 -->
  <a-modal
    v-model:visible="terminateDialogVisible"
    :title="t('terminateProcess')"
    :width="600"
    @ok="confirmTerminateProcess"
    @cancel="handleTerminateCancel"
  >
    <div style="padding: 20px 0;">
      <p>{{ t('terminateProcessConfirm') }}</p>
      <p style="margin-top: 10px; color: #666;">{{ t('processName') }}: {{ processToTerminate?.name }}</p>
      <p style="color: #666;">{{ t('pid') }}: {{ processToTerminate?.pid }}</p>
    </div>
  </a-modal>
</template>

<script setup>
import { reactive, ref, computed, onMounted, onUnmounted } from 'vue';
import { t } from '../../utils/locale'
import { processesGet, processGetDetail, processTerminate } from '../../api/security'
import { Message } from '@arco-design/web-vue';

// 响应式数据
const processes = ref([]);
const loading = ref(false);
// 是否显示骨架屏
const showSkeleton = ref(false);
// 自动刷新开关
const autoRefresh = ref(false);
// 自动刷新定时器
let refreshTimer = null;
// 搜索过滤条件
const searchFilters = reactive({
  status: '',
  pid: '',
  name: '',
  user: ''
});
// 分页相关数据
const pagination = reactive({
  current: 1,
  pageSize: 50,
  total: 0,
  showTotal: true,
  showJumper: true,
  pageSizeOptions: [20, 50, 100, 200],
  showPageSize: true
});
// 对话框可见状态
const detailDialogVisible = ref(false);
// 对话框加载状态
const detailLoading = ref(false);
// 当前选中的进程详情
const currentProcess = ref(null);
// Monaco编辑器相关
const envEditorRef = ref(null);
let envEditor = null;
// 当前活动的标签页
const activeTabKey = ref('basic');
// 终止进程确认对话框
const terminateDialogVisible = ref(false);
// 当前要终止的进程
const processToTerminate = ref(null);

// 文件表格列定义
const fileColumns = [
  {
    title: t.value('path'),
    dataIndex: 'path',
    key: 'path',
    ellipsis: true
  },
  {
    title: 'fd',
    dataIndex: 'fd',
    key: 'fd',
    width: 90
  },
];

// 网络连接表格列定义
const networkColumns = computed(() => [
  {
    title: t.value('type'),
    dataIndex: 'type',
    key: 'type',
    width: 80
  },
  {
    title: t.value('status'),
    dataIndex: 'status',
    key: 'status',
    width: 120
  },
  {
    title: t.value('localAddress'),
    key: 'localaddr',
    width: 200,
    render: ({ record }) => {
      if (record.localaddr?.address) {
        return record.localaddr.address;
      }
      if (record.localaddr?.ip && record.localaddr?.port) {
        return `${record.localaddr.ip}:${record.localaddr.port}`;
      }
      return '-';
    }
  },
  {
    title: t.value('remoteAddress'),
    key: 'remoteaddr',
    width: 200,
    render: ({ record }) => {
      if (record.remoteaddr?.address) {
        return record.remoteaddr.address;
      }
      if (record.remoteaddr?.ip && record.remoteaddr?.port) {
        return `${record.remoteaddr.ip}:${record.remoteaddr.port}`;
      }
      return '-';
    }
  }
]);

// 表格滚动配置
const scroll = {
  x: 1300,
  y: 600
};

// 表格列定义
const columns = computed(() => [
  {
    title: t.value('pid'),
    dataIndex: 'pid',
    width: 100
  },
  {
    title: t.value('processName'),
    dataIndex: 'name',
    width: 200
  },
  {
    title: t.value('parentPid'),
    dataIndex: 'ppid',
    width: 100
  },
  {
    title: t.value('threads'),
    dataIndex: 'threads',
    width: 100
  },
  {
    title: t.value('user'),
    dataIndex: 'user',
    width: 120
  },
  {    
    title: t.value('status'),    
    dataIndex: 'status',    
    slotName: 'status',    
    width: 100  },
  {
    title: t.value('cpuUsage'),
    dataIndex: 'cpu_percent',
    slotName: 'cpu_percent',
    width: 120
  },
  {
    title: t.value('memoryUsage'),
    dataIndex: 'memory_percent',
    slotName: 'memory_percent',
    width: 120
  },
  {
    title: t.value('startTime'),
    dataIndex: 'create_time',
    slotName: 'create_time',
    width: 180
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

// 格式化百分比
const formatPercent = (value) => {
  if (value === null || value === undefined) return '0%';
  return `${value.toFixed(2)}%`;
};



// 状态颜色映射（避免重复判断）
const statusColorMap = {
  'idle': 'orange',
  'sleeping': 'blue',
  'running': 'green',
  'zombie': 'red',
  'stopped': 'yellow',
  'defunct': 'purple',
  'waiting': 'gray'
};

// 获取状态颜色
const getStatusColor = (status) => {
  return statusColorMap[status] || 'default';
};

// 获取状态文本
const getStatusText = (status) => {
  return t.value(status) || status;
};

// 过滤后的进程列表（优化：减少不必要的过滤操作）
const filteredProcesses = computed(() => {
  const { status, pid, name, user } = searchFilters;
  
  // 如果没有任何过滤条件，直接返回原数组
  if (!status && !pid && !name && !user) {
    return processes.value;
  }
  
  // 预处理搜索条件（避免在循环中重复处理）
  const lowerName = name ? name.toLowerCase() : '';
  const lowerUser = user ? user.toLowerCase() : '';
  
  return processes.value.filter(p => {
    // 状态过滤
    if (status && p.status !== status) return false;
    
    // PID过滤
    if (pid && !String(p.pid).includes(pid)) return false;
    
    // 进程名称过滤
    if (lowerName && (!p.name || !p.name.toLowerCase().includes(lowerName))) return false;
    
    // 用户过滤
    if (lowerUser && (!p.user || !p.user.toLowerCase().includes(lowerUser))) return false;
    
    return true;
  });
});

// 处理分页变化
const handlePageChange = (page) => {
  pagination.current = page;
  fetchProcesses();
};

// 处理分页大小变化
const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize;
  pagination.current = 1;
  fetchProcesses();
};

// 获取进程列表
const fetchProcesses = async (silent = false) => {
  try {
    // 静默刷新时不显示loading状态
    if (!silent) {
      loading.value = true;
    }
    
    // 计算分页参数
    const skip = (pagination.current - 1) * pagination.pageSize;
    const limit = pagination.pageSize;
    
    const response = await processesGet({ skip, limit });
    
    // 处理响应数据
    let processList = [];
    if (response && response.data && Array.isArray(response.data)) {
      processList = response.data;
      // 更新总条数
      if (response.total) {
        pagination.total = response.total;
      }
    } else if (response && Array.isArray(response)) {
      processList = response;
    }
    
    if (processList.length > 0) {
      // 使用 requestAnimationFrame 优化渲染时机
      requestAnimationFrame(() => {
        processes.value = processList;
      });
    } else {
      processes.value = [];
      if (!silent) {
        Message.warning(t.value('noProcessData'));
      }
    }
  } catch (error) {
    console.error('获取进程列表失败:', error);
    if (!silent) {
      Message.error(t.value('getProcessesFailed'));
    }
    processes.value = [];
  } finally {
    if (!silent) {
      loading.value = false;
    }
  }
};

// 初始化Monaco编辑器
const initEnvEditor = async () => {
  if (!envEditorRef.value || envEditor) return;
  
  try {
    // 动态导入monaco-editor
    const monaco = await import('monaco-editor');
    
    // 获取环境变量内容
    const envContent = currentProcess.value?.envs?.join('\n') || '';
    
    // 创建编辑器实例
    envEditor = monaco.editor.create(envEditorRef.value, {
      value: envContent,
      language: 'plaintext',
      theme: 'vs-dark',
      automaticLayout: true,
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      fontSize: 13,
      tabSize: 2,
      readOnly: true,
      lineNumbers: 'on',
      wordWrap: 'off'
    });
  } catch (error) {
    console.error('Failed to load Monaco Editor:', error);
    Message.error('加载编辑器失败');
  }
};

// 显示进程详情
const showProcessDetail = async (process) => {
  console.log('查看进程详情:', process);
  
  try {
      // 设置加载状态
      detailLoading.value = true;
      // 清空之前的进程详情
      currentProcess.value = null;
      
      // 销毁之前的编辑器实例
      if (envEditor) {
        envEditor.dispose();
        envEditor = null;
      }
      
      // 打开对话框显示加载状态
      detailDialogVisible.value = true;
      
      // 调用API获取进程详情
      const response = await processGetDetail(process.pid);
      
      if (response && response.PID) {
        // 保存获取到的进程详情
        currentProcess.value = response;
        // 重置标签页到基本信息
        activeTabKey.value = 'basic';
        
        // 等待DOM更新后初始化编辑器
        await new Promise(resolve => setTimeout(resolve, 150));
        if (envEditorRef.value && response.envs && response.envs.length > 0) {
          await initEnvEditor();
        }
      } else {
        Message.warning(t.value('noProcessDetailData'));
      }
    } catch (error) {
      console.error('获取进程详情失败:', error);
      Message.error(t.value('getProcessDetailFailed'));
    } finally {
      detailLoading.value = false;
    }
};

// 处理对话框确认
const handleDialogOk = () => {
  detailDialogVisible.value = false;
};

// 处理对话框取消
const handleDialogCancel = () => {
  detailDialogVisible.value = false;
  // 重置标签页
  activeTabKey.value = 'basic';
};

// 处理标签页切换
const handleTabChange = async (key) => {
  console.log('标签页切换到:', key);
  
  // 如果切换到环境变量标签页且编辑器未初始化
  if (key === 'environment' && !envEditor && currentProcess.value?.envs?.length > 0) {
    // 等待DOM更新
    await new Promise(resolve => setTimeout(resolve, 150));
    if (envEditorRef.value) {
      await initEnvEditor();
    }
  }
  
  // 如果编辑器已存在，触发布局更新
  if (key === 'environment' && envEditor) {
    setTimeout(() => {
      envEditor.layout();
    }, 100);
  }
};

// 处理终止进程
const handleTerminateProcess = (process) => {
  console.log('准备终止进程:', process);
  processToTerminate.value = process;
  terminateDialogVisible.value = true;
};

// 确认终止进程
const confirmTerminateProcess = async () => {
  if (!processToTerminate.value) return;
  
  try {
    loading.value = true;
    console.log('正在终止进程:', processToTerminate.value.pid);
    
    // 调用API终止进程
    await processTerminate(processToTerminate.value.pid);
    
    Message.success(t.value('terminateProcessSuccess'));
    
    // 刷新进程列表
    await fetchProcesses();
    
    // 如果当前正在查看的就是被终止的进程，关闭详情对话框
    if (currentProcess.value && currentProcess.value.PID === processToTerminate.value.pid) {
      detailDialogVisible.value = false;
      currentProcess.value = null;
    }
  } catch (error) {
    console.error('终止进程失败:', error);
    Message.error(t.value('terminateProcessFailed'));
  } finally {
    loading.value = false;
    terminateDialogVisible.value = false;
    processToTerminate.value = null;
  }
};

// 取消终止进程
const handleTerminateCancel = () => {
  terminateDialogVisible.value = false;
  processToTerminate.value = null;
};

// 启动自动刷新
const startAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer);
  }
  refreshTimer = setInterval(() => {
    fetchProcesses(true); // 静默刷新
  }, 5000); // 5秒刷新一次
};

// 停止自动刷新
const stopAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
};

// 处理自动刷新开关变化
const handleAutoRefreshChange = (value) => {
  if (value) {
    startAutoRefresh();
  } else {
    stopAutoRefresh();
  }
};

// 优化组件挂载时的加载体验
onMounted(() => {
  // 先显示骨架屏
  showSkeleton.value = true;
  
  // 短暂延迟后开始加载数据
  setTimeout(() => {
    fetchProcesses().then(() => {
      // 数据加载完成后隐藏骨架屏
      showSkeleton.value = false;
    });
  }, 100);
});

// 组件卸载时清理定时器和对话框状态
onUnmounted(() => {
  stopAutoRefresh();
  // 销毁编辑器实例
  if (envEditor) {
    envEditor.dispose();
    envEditor = null;
  }
  // 确保对话框在组件卸载时关闭
  detailDialogVisible.value = false;
  // 清空选中的进程信息
  currentProcess.value = null;
});
</script>

<style scoped>
.process-container {
  padding: 20px;
  height: 850px;
  overflow: hidden;
  box-sizing: border-box;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: flex-start;
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


/* 根据需要调整其他样式 */

.dialog-content {
  padding: 20px 0;
  min-height: 400px;
  display: flex;
  flex-direction: column;
}

.tab-content {
  padding: 20px;
  background-color: #fafafa;
  border-radius: 4px;
}

.empty-content {
  padding: 60px 0;
  text-align: center;
  color: #8c8c8c;
  font-size: 14px;
}

/* 调整标签页样式 */
:deep(.arco-tabs-left .arco-tabs-content) {
  padding-left: 20px;
}

/* 调整描述列表样式 */
:deep(.arco-descriptions-item-label) {
  font-weight: 600;
  color: var(--color-text-1);
  font-size: 14px;
  background-color: var(--color-fill-2);
}

:deep(.arco-descriptions-item-content) {
  color: var(--color-text-2);
  font-size: 14px;
  word-break: break-all;
  background-color: var(--color-bg-2);
}

/* 优化表格边框和间距 */
:deep(.arco-descriptions-table) {
  border-collapse: collapse;
}

:deep(.arco-descriptions-table td) {
  padding: 10px 16px;
  border: 1px solid var(--color-border-2);
}

/* 调整标签页左侧导航样式 */
:deep(.arco-tabs-left .arco-tabs-nav) {
  border-right: 1px solid var(--arco-color-primary-5);
  background-color: var(--arco-color-primary-5);
}

/* 优化标签页内容区域 */
:deep(.arco-tabs-content) {
  padding: 0;
}

/* 增加标签页内容区域的内边距 */
.tab-content {
  padding: 0;
  background-color: transparent;
}

/* Monaco编辑器容器样式 */
.monaco-editor-container {
  width: 100%;
  height: 400px;
  border: 1px solid var(--color-border-2);
  border-radius: 4px;
  overflow: hidden;
}

.env-tab-content {
  padding: 0 !important;
}

/* 优化空状态样式 */
.empty-content {
  padding: 60px 0;
  text-align: center;
}
</style>