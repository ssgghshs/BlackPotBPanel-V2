<template>
  <a-card class="network-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('network') }}</span>
      </div>
    </template>

    <!-- 搜索和控制栏 -->
    <a-space :size="12" wrap>
      <a-select 
        v-model="searchFilters.type" 
        :placeholder="t('type')"
        allow-clear
        style="width: 120px"
      >
        <a-option value="tcp">TCP</a-option>
        <a-option value="udp">UDP</a-option>
      </a-select>
      
      <a-input 
        v-model="searchFilters.pid" 
        :placeholder="t('pid')"
        allow-clear
        style="width: 120px"
      />
      
      <a-input 
        v-model="searchFilters.name" 
        :placeholder="t('processName')"
        allow-clear
        style="width: 200px"
      />
      
      <a-input 
        v-model="searchFilters.localAddress" 
        :placeholder="t('localAddress')"
        allow-clear
        style="width: 180px"
      />
      
      <a-input 
        v-model="searchFilters.remoteAddress" 
        :placeholder="t('remoteAddress')"
        allow-clear
        style="width: 180px"
      />
      
      <a-select 
        v-model="searchFilters.status" 
        :placeholder="t('status')"
        allow-clear
        style="width: 120px"
      >
        <a-option value="LISTEN">LISTEN</a-option>
        <a-option value="ESTABLISHED">ESTABLISHED</a-option>
        <a-option value="TIME_WAIT">TIME_WAIT</a-option>
        <a-option value="CLOSE_WAIT">CLOSE_WAIT</a-option>
        <a-option value="NONE">NONE</a-option>
      </a-select>
      
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

    <!-- 网络连接列表表格 -->
    <a-table 
      :columns="columns" 
      :data="filteredConnections" 
      :loading="loading"
      :scroll="scroll"
      row-key="id"
      :pagination="pagination"
      @page-change="handlePageChange"
      @page-size-change="handlePageSizeChange"
    >
      <template #type="{ record }">
        <a-tag :color="getTypeColor(record.type)">
          {{ record.type.toUpperCase() }}
        </a-tag>
      </template>
      <template #status="{ record }">
        <a-tag :color="getStatusColor(record.status)">
          {{ getStatusText(record.status) }}
        </a-tag>
      </template>
    </a-table>
  </a-card>
</template>

<script setup>
import { reactive, ref, computed, onMounted, onUnmounted } from 'vue';
import { t } from '../../utils/locale'
import { networkGetConnections } from '../../api/security'
import { Message } from '@arco-design/web-vue';

// 响应式数据
const connections = ref([]);
const loading = ref(false);
// 是否显示骨架屏
const showSkeleton = ref(false);
// 自动刷新开关
const autoRefresh = ref(false);
// 自动刷新定时器
let refreshTimer = null;
// 搜索过滤条件
const searchFilters = reactive({
  type: '',
  pid: '',
  name: '',
  localAddress: '',
  remoteAddress: '',
  status: ''
});
// 分页相关数据
const pagination = reactive({
  current: 1,
  pageSize: 50,
  total: 0,
  pageSizeOptions: [20, 50, 100, 200],
  showPageSize: true,
  showJumper: true,
  showTotal: true
});

// 表格滚动配置
const scroll = {
  x: 1300,
  y: 600
};

// 表格列定义
const columns = computed(() => [
  {
    title: t.value('type'),
    dataIndex: 'type',
    slotName: 'type',
    width: 100
  },
  {
    title: t.value('pid'),
    dataIndex: 'pid',
    width: 80
  },
  {
    title: t.value('processName'),
    dataIndex: 'name',
    width: 180
  },
  {
    title: t.value('localAddress'),
    dataIndex: 'local_address',
    width: 180
  },
  {
    title: t.value('remoteAddress'),
    dataIndex: 'remote_address',
    width: 180
  },
  {
    title: t.value('status'),
    dataIndex: 'status',
    slotName: 'status',
    width: 120
  }
]);

// 类型颜色映射
const getTypeColor = (type) => {
  const colorMap = {
    'tcp': 'blue',
    'udp': 'green'
  };
  return colorMap[type] || 'default';
};

// 状态颜色映射
const getStatusColor = (status) => {
  const colorMap = {
    'LISTEN': 'green',
    'ESTABLISHED': 'blue',
    'TIME_WAIT': 'orange',
    'CLOSE_WAIT': 'red',
    'NONE': 'default'
  };
  return colorMap[status] || 'default';
};

// 获取状态文本
const getStatusText = (status) => {
  return status;
};

// 过滤后的连接列表
const filteredConnections = computed(() => {
  const { type, pid, name, localAddress, remoteAddress, status } = searchFilters;
  
  // 如果没有任何过滤条件，直接返回原数组
  if (!type && !pid && !name && !localAddress && !remoteAddress && !status) {
    return connections.value;
  }
  
  // 预处理搜索条件
  const lowerName = name ? name.toLowerCase() : '';
  const lowerLocalAddress = localAddress ? localAddress.toLowerCase() : '';
  const lowerRemoteAddress = remoteAddress ? remoteAddress.toLowerCase() : '';
  
  return connections.value.filter(conn => {
    // 类型过滤
    if (type && conn.type !== type) return false;
    
    // PID过滤
    if (pid && !String(conn.pid).includes(pid)) return false;
    
    // 进程名称过滤
    if (lowerName && (!conn.name || !conn.name.toLowerCase().includes(lowerName))) return false;
    
    // 本地地址过滤
    if (lowerLocalAddress && !conn.local_address.toLowerCase().includes(lowerLocalAddress)) return false;
    
    // 远程地址过滤
    if (lowerRemoteAddress && !conn.remote_address.toLowerCase().includes(lowerRemoteAddress)) return false;
    
    // 状态过滤
    if (status && conn.status !== status) return false;
    
    return true;
  });
});

// 处理分页变化
const handlePageChange = (page) => {
  pagination.current = page;
  fetchNetworkConnections();
};

// 处理分页大小变化
const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize;
  pagination.current = 1;
  fetchNetworkConnections();
};

// 获取网络连接列表
const fetchNetworkConnections = async (silent = false) => {
  try {
    // 静默刷新时不显示loading状态
    if (!silent) {
      loading.value = true;
    }
    
    // 计算分页参数
    const skip = (pagination.current - 1) * pagination.pageSize;
    const limit = pagination.pageSize;
    
    const response = await networkGetConnections({ skip, limit });
    
    // 处理响应数据
    let connectionList = [];
    if (response && response.data && Array.isArray(response.data)) {
      // 为每个连接添加唯一ID
      connectionList = response.data.map((conn, index) => ({
        ...conn,
        id: `${conn.type}-${conn.pid}-${index}-${conn.local_address}`
      }));
      // 更新总条数
      if (response.total) {
        pagination.total = response.total;
      }
    } else {
      connectionList = [];
      if (!silent) {
        Message.warning(t.value('noNetworkData'));
      }
    }
    
    // 使用 requestAnimationFrame 优化渲染时机
    requestAnimationFrame(() => {
      connections.value = connectionList;
    });
  } catch (error) {
    console.error('获取网络连接列表失败:', error);
    if (!silent) {
      Message.error(t.value('getNetworkFailed'));
    }
    connections.value = [];
  } finally {
    if (!silent) {
      loading.value = false;
    }
  }
};

// 启动自动刷新
const startAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer);
  }
  refreshTimer = setInterval(() => {
    fetchNetworkConnections(true); // 静默刷新
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

// 组件挂载时加载数据
onMounted(() => {
  // 先显示骨架屏
  showSkeleton.value = true;
  
  // 短暂延迟后开始加载数据
  setTimeout(() => {
    fetchNetworkConnections().then(() => {
      // 数据加载完成后隐藏骨架屏
      showSkeleton.value = false;
    });
  }, 100);
});

// 组件卸载时清理定时器
onUnmounted(() => {
  stopAutoRefresh();
});
</script>

<style scoped>
.network-container {
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
</style>