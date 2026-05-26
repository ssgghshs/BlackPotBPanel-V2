<template>
  <a-drawer
    :visible="visible"
    :title="title"
    placement="right"
    :width="isMobile ? '90%' : 800"
    :closable="true"
    :maskClosable="true"
    :footer="false"
    @update:visible="(val) => emit('update:visible', val)"
    @close="handleClose"
  >
      <!-- CPU使用率监控 -->
      <div class="chart-section">
        <div class="chart-header">
          <h3>{{ t('cpuUsage') }}</h3>
        </div>
        <div class="chart-wrapper" :class="{ 'loading': loading }">
          <div ref="cpuChart" class="chart-container"></div>
          <div v-if="loading" class="chart-overlay">
            <div class="skeleton-line" v-for="i in 5" :key="10+i"></div>
          </div>
        </div>
      </div>

      <!-- 内存使用监控 -->
      <div class="chart-section">
        <div class="chart-header">
          <h3>{{ t('memoryUsage') }}</h3>
        </div>
        <div class="chart-wrapper" :class="{ 'loading': loading }">
          <div ref="memoryChart" class="chart-container"></div>
          <div v-if="loading" class="chart-overlay">
            <div class="skeleton-line" v-for="i in 5" :key="20+i"></div>
          </div>
        </div>
      </div>

      <!-- 磁盘IO监控 -->
      <div class="chart-section">
        <div class="chart-header">
          <h3>{{ t('diskIO') }}</h3>
        </div>
        <div class="chart-wrapper" :class="{ 'loading': loading }">
          <div ref="diskChart" class="chart-container"></div>
          <div v-if="loading" class="chart-overlay">
            <div class="skeleton-line" v-for="i in 5" :key="40+i"></div>
          </div>
        </div>
      </div>

      <!-- 网络流量监控 -->
      <div class="chart-section">
        <div class="chart-header">
          <h3>{{ t('networkTraffic') }}</h3>
        </div>
        <div class="chart-wrapper" :class="{ 'loading': loading }">
          <div ref="networkChart" class="chart-container"></div>
          <div v-if="loading" class="chart-overlay">
            <div class="skeleton-line" v-for="i in 5" :key="30+i"></div>
          </div>
        </div>
      </div>

      <!-- 错误状态显示 -->
      <div class="error-message" v-if="error">
        {{ t('fetchMonitorDataFailed') }}
      </div>
  </a-drawer>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount, watch } from 'vue';
import { t } from '../../utils/locale';
import { Drawer as ADrawer } from '@arco-design/web-vue';
import { getContainerStats } from '../../api/container';
import * as echarts from 'echarts5'
import 'echarts5/lib/chart/line';

// 响应式判断是否为移动设备
const isMobile = ref(window.innerWidth < 768);
// 节点ID
const selectedHostId = ref('');
// 加载状态
const loading = ref(false);
// 错误状态
const error = ref(false);
// 监控数据
const monitorData = ref(null);
// 当前统计数据（用于显示最新值）
const currentStats = ref({
  cpu_percentage: 0,
  memory_usage: 0,
  memory_limit: 0,
  network_rx_bytes: 0,
  network_tx_bytes: 0,
  block_read_bytes: 0,
  block_write_bytes: 0
});
// 图表实例引用
const cpuChart = ref(null);
const memoryChart = ref(null);
const networkChart = ref(null);
const diskChart = ref(null);
// 图表实例对象
let chartInstances = {
  cpu: null,
  memory: null,
  network: null,
  disk: null
};
// 图表数据存储
const chartData = ref({
  timestamps: [],
  cpu: [],
  memory: [],
  networkRx: [],
  networkTx: [],
  diskRead: [],
  diskWrite: []
});
// 数据点数量限制
const MAX_DATA_POINTS = 20;
// 刷新定时器
const refreshTimer = ref(null);
// 刷新间隔（毫秒）
const defaultRefreshInterval = 5000; // 默认5秒刷新一次
let currentRefreshInterval = defaultRefreshInterval;
// 错误计数器
const errorCount = ref(0);
// 最大重试次数
const MAX_RETRY_COUNT = 3;
// 最大刷新间隔
const MAX_REFRESH_INTERVAL = 30000; // 最大30秒

// 监听窗口大小变化
const handleResize = () => {
  isMobile.value = window.innerWidth < 768;
};

// 格式化内存数据（字节转MB/GB）
const formatMemory = (bytes) => {
  if (!bytes || bytes === 0) return '0 MB';
  const mb = bytes / (1024 * 1024);
  if (mb < 1024) {
    return Math.round(mb * 100) / 100 + ' MB';
  }
  const gb = mb / 1024;
  return Math.round(gb * 100) / 100 + ' GB';
};

// 格式化网络数据（字节转KB/MB）
const formatNetwork = (bytes) => {
  if (!bytes || bytes === 0) return '0 KB';
  const kb = bytes / 1024;
  if (kb < 1024) {
    return Math.round(kb * 100) / 100 + ' KB';
  }
  const mb = kb / 1024;
  return Math.round(mb * 100) / 100 + ' MB';
};

// 格式化磁盘IO数据（字节转KB/MB）
const formatDiskIO = (bytes) => {
  return formatNetwork(bytes); // 使用相同的格式化逻辑
};

// 处理宿主变化事件
const handleHostChange = (event) => {
  selectedHostId.value = event.detail.hostId;
  // 如果抽屉已打开且有容器信息，则获取监控数据
  if (props.visible && props.containerInfo.id) {
    // 清空历史数据，准备新节点的数据
    resetChartData();
    fetchContainerStats();
  }
};

// 重置图表数据
const resetChartData = () => {
  chartData.value = {
    timestamps: [],
    cpu: [],
    memory: [],
    networkRx: [],
    networkTx: [],
    diskRead: [],
    diskWrite: []
  };
  currentStats.value = {
    cpu_percentage: 0,
    memory_usage: 0,
    memory_limit: 0,
    network_rx_bytes: 0,
    network_tx_bytes: 0,
    block_read_bytes: 0,
    block_write_bytes: 0
  };
  
  // 重置错误状态
  resetErrorState();
};

// 初始化组件
onMounted(() => {
  window.addEventListener('resize', handleResize);
  window.addEventListener('containerHostChanged', handleHostChange);
  
  // 尝试从localStorage获取已保存的宿主ID
  const savedHostId = localStorage.getItem('selectedContainerHostId');
  if (savedHostId) {
    selectedHostId.value = savedHostId;
  }
});

// 组件销毁前清理
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
  window.removeEventListener('containerHostChanged', handleHostChange);
  stopAutoRefresh();
  destroyCharts();
  resetErrorState();
});

// 定义props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  containerInfo: {
    type: Object,
    default: () => ({})
  }
});

// 定义emits
const emit = defineEmits(['update:visible', 'close']);

// 计算抽屉标题
const title = computed(() => {
  return props.containerInfo.name 
    ? `${t.value('containerMonitor')}: ${props.containerInfo.name}`
    : t.value('containerMonitor');
});

// 处理关闭抽屉
const handleClose = () => {
  // 关闭抽屉时停止自动刷新
  stopAutoRefresh();
  emit('update:visible', false);
  emit('close');
};

// 启动自动刷新
const startAutoRefresh = () => {
  // 先停止可能存在的定时器
  stopAutoRefresh();
  
  // 设置新的定时器
  refreshTimer.value = setInterval(() => {
    if (selectedHostId.value && props.containerInfo.id) {
      fetchContainerStats();
    }
  }, currentRefreshInterval);
};

// 停止自动刷新
const stopAutoRefresh = () => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value);
    refreshTimer.value = null;
  }
};

// 监听抽屉可见状态变化
watch(() => props.visible, async (newVisible) => {
  if (newVisible) {
    // 抽屉打开时，等待DOM更新后初始化图表
    await new Promise(resolve => setTimeout(resolve, 100));
    initCharts();
    
    // 获取数据并开始自动刷新
    if (selectedHostId.value && props.containerInfo.id) {
      fetchContainerStats();
      startAutoRefresh();
    }
  } else {
    // 抽屉关闭时，停止自动刷新并销毁图表
    stopAutoRefresh();
    destroyCharts();
  }
});

// 监听容器信息变化
watch(() => props.containerInfo.id, (newContainerId) => {
  if (props.visible && selectedHostId.value && newContainerId) {
    // 容器变化时重新获取数据
    fetchContainerStats();
  }
});

// 初始化CPU图表
const initCPUChart = () => {
  if (!cpuChart.value) return;
  
  if (chartInstances.cpu) {
    chartInstances.cpu.dispose();
  }
  
  chartInstances.cpu = echarts.init(cpuChart.value);
  chartInstances.cpu.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      formatter: function(params) {
        if (!params || params.length === 0) return '';
        // 格式化时间
        const date = new Date(params[0].name);
        const timeStr = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;
        
        // 构建tooltip内容
        let content = `${timeStr}<br/>`;
        params.forEach(item => {
          let formattedValue = item.value;
          let unit = '';
          
          // 内存使用特殊处理：四舍五入到2位小数并添加MB单位
          if (item.seriesName.includes('内存')) {
            formattedValue = Number(item.value).toFixed(2);
            unit = ' MB';
          } else if (item.seriesName.includes('CPU')) {
            // CPU使用率保持不变，已有%单位
            unit = ' %';
          }
          
          content += `${item.marker} ${item.seriesName}: ${formattedValue}${unit}<br/>`;
        });
        return content;
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: chartData.value.timestamps,
      axisLabel: {
        formatter: (value) => {
          const date = new Date(value);
          return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;
        }
      }
    },
    yAxis: {
      type: 'value',
      name: 'CPU使用率(%)',
      axisLabel: {
        formatter: '{value} %'
      },
      // 设置动态最大值：当前CPU使用率的1.2倍，但不小于20%且不超过100%
      max: function(value) {
        // 获取当前CPU数据的最大值
        const maxValue = Math.max(...chartData.value.cpu, 0);
        // 计算动态最大值
        const dynamicMax = Math.min(Math.max(maxValue * 1.2, 20), 100);
        // 向上取整到最近的10的倍数，使刻度更美观
        return Math.ceil(dynamicMax / 10) * 10;
      }
    },
    series: [{
      name: 'CPU使用率',
      type: 'line',
      smooth: true,
      data: chartData.value.cpu,
      lineStyle: {
        width: 2,
        color: '#5470c6'
      },
      itemStyle: {
        color: '#5470c6'
      },
      areaStyle: {
        opacity: 0.3,
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{
          offset: 0,
          color: 'rgba(84, 112, 198, 0.8)'
        }, {
          offset: 1,
          color: 'rgba(84, 112, 198, 0.1)'
        }])
      }
    }]
  });
};

// 初始化内存图表
const initMemoryChart = () => {
  if (!memoryChart.value) return;
  
  if (chartInstances.memory) {
    chartInstances.memory.dispose();
  }
  
  chartInstances.memory = echarts.init(memoryChart.value);
  chartInstances.memory.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      formatter: function(params) {
        if (!params || params.length === 0) return '';
        // 格式化时间
        const date = new Date(params[0].name);
        const timeStr = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;
        
        // 构建tooltip内容
        let content = `${timeStr}<br/>`;
        params.forEach(item => {
          let formattedValue = item.value;
          let unit = '';
          
          // 内存特殊处理：四舍五入到2位小数并添加MB单位
          if (item.seriesName.includes('内存使用')) {
            formattedValue = Number(item.value).toFixed(2);
            unit = ' MB';
          } else if (item.seriesName.includes('CPU')) {
            // CPU使用率保持不变，已有%单位
            unit = ' %';
          }
          
          content += `${item.marker} ${item.seriesName}: ${formattedValue}${unit}<br/>`;
        });
        return content;
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: chartData.value.timestamps,
      axisLabel: {
        formatter: (value) => {
          const date = new Date(value);
          return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '内存使用(MB)',
      axisLabel: {
        formatter: (value) => {
          return Math.round(value) + ' MB';
        }
      }
    },
    series: [{
      name: '内存使用',
      type: 'line',
      smooth: true,
      data: chartData.value.memory,
      lineStyle: {
        width: 2,
        color: '#91cc75'
      },
      itemStyle: {
        color: '#91cc75'
      },
      areaStyle: {
        opacity: 0.3,
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{
          offset: 0,
          color: 'rgba(145, 204, 117, 0.8)'
        }, {
          offset: 1,
          color: 'rgba(145, 204, 117, 0.1)'
        }])
      }
    }]
  });
};

// 初始化网络图表
const initNetworkChart = () => {
  if (!networkChart.value) return;
  
  if (chartInstances.network) {
    chartInstances.network.dispose();
  }
  
  chartInstances.network = echarts.init(networkChart.value);
  chartInstances.network.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      formatter: function(params) {
        if (!params || params.length === 0) return '';
        // 格式化时间
        const date = new Date(params[0].name);
        const timeStr = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;
        
        // 构建tooltip内容
        let content = `${timeStr}<br/>`;
        params.forEach(item => {
          let formattedValue = item.value;
          let unit = '';
          
          // 网络流量特殊处理：四舍五入到2位小数并添加KB单位
          if (item.seriesName.includes('接收') || item.seriesName.includes('发送')) {
            formattedValue = Number(item.value).toFixed(2);
            unit = ' KB';
          } else if (item.seriesName.includes('CPU')) {
            // CPU使用率保持不变，已有%单位
            unit = ' %';
          }
          
          content += `${item.marker} ${item.seriesName}: ${formattedValue}${unit}<br/>`;
        });
        return content;
      }
    },
    legend: {
      data: ['接收', '发送'],
      top: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: chartData.value.timestamps,
      axisLabel: {
        formatter: (value) => {
          const date = new Date(value);
          return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '流量(KB)',
      axisLabel: {
        formatter: (value) => {
          return Math.round(value) + ' KB';
        }
      }
    },
    series: [
      {
        name: '接收',
        type: 'line',
        smooth: true,
        data: chartData.value.networkRx,
        lineStyle: {
          width: 2,
          color: '#fac858'
        },
        itemStyle: {
          color: '#fac858'
        }
      },
      {
        name: '发送',
        type: 'line',
        smooth: true,
        data: chartData.value.networkTx,
        lineStyle: {
          width: 2,
          color: '#ee6666'
        },
        itemStyle: {
          color: '#ee6666'
        }
      }
    ]
  });
};

// 初始化磁盘IO图表
const initDiskChart = () => {
  if (!diskChart.value) return;
  
  if (chartInstances.disk) {
    chartInstances.disk.dispose();
  }
  
  chartInstances.disk = echarts.init(diskChart.value);
  chartInstances.disk.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      formatter: function(params) {
        if (!params || params.length === 0) return '';
        // 格式化时间
        const date = new Date(params[0].name);
        const timeStr = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;
        
        // 构建tooltip内容
        let content = `${timeStr}<br/>`;
        params.forEach(item => {
          let formattedValue = item.value;
          let unit = '';
          
          // 磁盘IO特殊处理：四舍五入到2位小数并添加MB单位
          if (item.seriesName.includes('读取') || item.seriesName.includes('写入')) {
            formattedValue = Number(item.value).toFixed(2);
            unit = ' MB';
          } else if (item.seriesName.includes('CPU')) {
            // CPU使用率保持不变，已有%单位
            unit = ' %';
          }
          
          content += `${item.marker} ${item.seriesName}: ${formattedValue}${unit}<br/>`;
        });
        return content;
      }
    },
    legend: {
      data: ['读取', '写入'],
      top: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: chartData.value.timestamps,
      axisLabel: {
        formatter: (value) => {
          const date = new Date(value);
          return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '数据量(MB)',
      axisLabel: {
        formatter: (value) => {
          // 数据已转换为MB，直接格式化显示
          return value < 0.01 ? (value * 1024).toFixed(1) + ' KB' : value.toFixed(2) + ' MB';
        }
      }
    },
    series: [
      {
        name: '读取',
        type: 'line',
        smooth: true,
        data: chartData.value.diskRead,
        lineStyle: {
          width: 2,
          color: '#73c0de'
        },
        itemStyle: {
          color: '#73c0de'
        }
      },
      {
        name: '写入',
        type: 'line',
        smooth: true,
        data: chartData.value.diskWrite,
        lineStyle: {
          width: 2,
          color: '#3ba272'
        },
        itemStyle: {
          color: '#3ba272'
        }
      }
    ]
  });
};

// 初始化所有图表
const initCharts = () => {
  try {
    initCPUChart();
    initMemoryChart();
    initNetworkChart();
    initDiskChart();
    
    // 添加窗口大小改变时的图表重绘
    window.addEventListener('resize', resizeCharts);
  } catch (error) {
    console.error('图表初始化失败:', error);
  }
};

// 更新图表数据
const updateCharts = () => {
  try {
    // 更新CPU图表
    if (chartInstances.cpu) {
      // 计算动态最大值
      const maxValue = Math.max(...chartData.value.cpu, 0);
      const dynamicMax = Math.min(Math.max(maxValue * 1.2, 20), 100);
      const roundedMax = Math.ceil(dynamicMax / 10) * 10;
      
      chartInstances.cpu.setOption({
        xAxis: {
          data: chartData.value.timestamps
        },
        yAxis: {
          max: roundedMax
        },
        series: [{
          data: chartData.value.cpu
        }]
      });
    }
    
    // 更新内存图表
    if (chartInstances.memory) {
      chartInstances.memory.setOption({
        xAxis: {
          data: chartData.value.timestamps
        },
        series: [{
          data: chartData.value.memory
        }]
      });
    }
    
    // 更新网络图表
    if (chartInstances.network) {
      chartInstances.network.setOption({
        xAxis: {
          data: chartData.value.timestamps
        },
        series: [
          {
            data: chartData.value.networkRx
          },
          {
            data: chartData.value.networkTx
          }
        ]
      });
    }
    
    // 更新磁盘IO图表
    if (chartInstances.disk) {
      chartInstances.disk.setOption({
        xAxis: {
          data: chartData.value.timestamps
        },
        series: [
          {
            data: chartData.value.diskRead
          },
          {
            data: chartData.value.diskWrite
          }
        ]
      });
    }
  } catch (error) {
    console.error('图表数据更新失败:', error);
  }
};

// 调整图表大小
const resizeCharts = () => {
  try {
    Object.values(chartInstances).forEach(chart => {
      if (chart) {
        chart.resize();
      }
    });
  } catch (error) {
    console.error('图表大小调整失败:', error);
  }
};

// 销毁图表
const destroyCharts = () => {
  try {
    Object.values(chartInstances).forEach(chart => {
      if (chart) {
        chart.dispose();
      }
    });
    chartInstances = {
      cpu: null,
      memory: null,
      network: null,
      disk: null
    };
    
    // 移除窗口大小改变事件监听
    window.removeEventListener('resize', resizeCharts);
  } catch (error) {
    console.error('图表销毁失败:', error);
  }
};

// 重置错误状态和刷新间隔
const resetErrorState = () => {
  errorCount.value = 0;
  currentRefreshInterval = defaultRefreshInterval;
  // 如果定时器正在运行，重新启动以应用新的间隔
  if (refreshTimer.value) {
    startAutoRefresh();
  }
};

// 根据错误次数调整刷新间隔
const adjustRefreshInterval = (hasError) => {
  if (hasError) {
    // 错误时增加刷新间隔，但不超过最大值
    errorCount.value++;
    // 指数退避策略：每次错误将间隔增加50%
    currentRefreshInterval = Math.min(
      currentRefreshInterval * 1.5,
      MAX_REFRESH_INTERVAL
    );
    
    // 如果定时器正在运行，重新启动以应用新的间隔
    if (refreshTimer.value) {
      startAutoRefresh();
    }
  } else if (errorCount.value > 0) {
    // 成功时减少错误计数，但不低于0
    errorCount.value = Math.max(0, errorCount.value - 1);
    
    // 如果错误计数回到0，重置刷新间隔
    if (errorCount.value === 0) {
      resetErrorState();
    }
  }
};

// 获取容器监控数据的方法
const fetchContainerStats = async () => {
  // 检查是否有必要的参数
  if (!selectedHostId.value || !props.containerInfo.id) {
    console.error('缺少必要参数：节点ID或容器ID');
    error.value = true;
    return;
  }
  
  // 记录是否为首次加载
  const isInitialLoad = chartData.value.timestamps.length === 0;
  
  // 只有首次加载才显示loading
  if (isInitialLoad) {
    loading.value = true;
  }
  
  let retryCount = 0;
  let hasData = false;
  
  while (retryCount <= (errorCount.value > 0 ? MAX_RETRY_COUNT : 0)) {
    try {
      error.value = false;
      
      // 调用API获取容器监控数据
      const response = await getContainerStats(selectedHostId.value, props.containerInfo.id);
      
      // 检查响应是否有效
      if (!response) {
        throw new Error('获取监控数据响应为空');
      }
      
      // 处理不同格式的响应
      let stats = response.data || response;
      
      // 确保stats是一个对象
      if (typeof stats !== 'object' || stats === null) {
        throw new Error('获取监控数据格式不正确');
      }
      
      // 保存监控数据
      monitorData.value = stats;
      console.log('容器监控数据获取成功:', stats);
      
      // 转换为数值类型
      const newStats = {
        cpu_percentage: Number(stats.cpu_percentage) || 0,
        memory_usage: Number(stats.memory_usage) || 0,
        memory_limit: Number(stats.memory_limit) || 0,
        network_rx_bytes: Number(stats.network_rx_bytes) || 0,
        network_tx_bytes: Number(stats.network_tx_bytes) || 0,
        block_read_bytes: Number(stats.block_read_bytes) || 0,
        block_write_bytes: Number(stats.block_write_bytes) || 0
      };
      
      // 数据平滑过渡
      const smoothTransition = (current, target) => {
        // 如果是首次加载或者数据相差太大，直接使用目标值
        if (isInitialLoad || Math.abs(current - target) > current * 2) {
          return target;
        }
        // 否则使用线性插值，平滑过渡（70%的新值，30%的旧值）
        return current * 0.3 + target * 0.7;
      };
      
      // 更新当前统计数据，应用平滑过渡
      currentStats.value = {
        cpu_percentage: smoothTransition(currentStats.value.cpu_percentage, newStats.cpu_percentage),
        memory_usage: smoothTransition(currentStats.value.memory_usage, newStats.memory_usage),
        memory_limit: newStats.memory_limit, // 内存限制一般不变，直接更新
        network_rx_bytes: smoothTransition(currentStats.value.network_rx_bytes, newStats.network_rx_bytes),
        network_tx_bytes: smoothTransition(currentStats.value.network_tx_bytes, newStats.network_tx_bytes),
        block_read_bytes: smoothTransition(currentStats.value.block_read_bytes, newStats.block_read_bytes),
        block_write_bytes: smoothTransition(currentStats.value.block_write_bytes, newStats.block_write_bytes)
      };
      
      // 添加新的数据点
      const timestamp = stats.timestamp ? new Date(stats.timestamp).toISOString() : new Date().toISOString();
      
      // 更新时间序列数据，保持数据点数量限制
      chartData.value.timestamps.push(timestamp);
      chartData.value.cpu.push(Number(stats.cpu_percentage) || 0);
      // 内存单位转换为MB
      chartData.value.memory.push((Number(stats.memory_usage) || 0) / (1024 * 1024));
      // 网络数据转换为KB
      chartData.value.networkRx.push((Number(stats.network_rx_bytes) || 0) / 1024);
      chartData.value.networkTx.push((Number(stats.network_tx_bytes) || 0) / 1024);
      // 磁盘IO转换为MB
      chartData.value.diskRead.push((Number(stats.block_read_bytes) || 0) / (1024 * 1024));
      chartData.value.diskWrite.push((Number(stats.block_write_bytes) || 0) / (1024 * 1024));
      
      // 保持数据点数量限制
      if (chartData.value.timestamps.length > MAX_DATA_POINTS) {
        chartData.value.timestamps.shift();
        chartData.value.cpu.shift();
        chartData.value.memory.shift();
        chartData.value.networkRx.shift();
        chartData.value.networkTx.shift();
        chartData.value.diskRead.shift();
        chartData.value.diskWrite.shift();
      }
      
      // 确保所有数据数组长度一致
      const dataArrays = [
        chartData.value.cpu,
        chartData.value.memory,
        chartData.value.networkRx,
        chartData.value.networkTx,
        chartData.value.diskRead,
        chartData.value.diskWrite
      ];
      
      const maxLength = chartData.value.timestamps.length;
      dataArrays.forEach(arr => {
        if (arr.length > maxLength) {
          arr.length = maxLength; // 截断过长的数组
        } else if (arr.length < maxLength) {
          // 填充不足的数组
          while (arr.length < maxLength) {
            arr.push(0);
          }
        }
      });
      
      // 更新图表
      updateCharts();
      
      // 标记成功获取数据
      hasData = true;
      
      // 调整刷新间隔（成功情况）
      adjustRefreshInterval(false);
      
      // 成功后跳出重试循环
      break;
    } catch (err) {
      retryCount++;
      
      // 如果是最后一次重试或首次加载时出错，记录并处理
      if (retryCount > (errorCount.value > 0 ? MAX_RETRY_COUNT : 0)) {
        console.error('获取容器监控数据失败:', err.message || err);
        error.value = true;
        
        // 错误处理时保留最后一次成功的数据
        if (monitorData.value === null) {
          // 如果是首次加载出错，重置currentStats
          if (isInitialLoad) {
            currentStats.value = {
              cpu_percentage: 0,
              memory_usage: 0,
              memory_limit: 0,
              network_rx_bytes: 0,
              network_tx_bytes: 0,
              block_read_bytes: 0,
              block_write_bytes: 0
            };
          }
        } else {
          // 非首次加载且有历史数据时，使用平滑过渡的默认值
          const defaultStats = {
            cpu_percentage: currentStats.value.cpu_percentage * 0.9, // 轻微下降模拟正常波动
            memory_usage: currentStats.value.memory_usage,
            memory_limit: currentStats.value.memory_limit,
            network_rx_bytes: currentStats.value.network_rx_bytes * 0.8, // 轻微下降
            network_tx_bytes: currentStats.value.network_tx_bytes * 0.8, // 轻微下降
            // 保持与正常数据处理一致，使用MB单位
            block_read_bytes: currentStats.value.block_read_bytes * 0.8,
            block_write_bytes: currentStats.value.block_write_bytes * 0.8
          };
          
          // 应用平滑过渡的默认值
          currentStats.value = defaultStats;
        }
        
        // 添加空数据点以保持图表连续性
        if (chartData.value.timestamps.length > 0) {
          const currentTime = new Date().toISOString();
          chartData.value.timestamps.push(currentTime);
          
          // 对于错误点，使用null值表示数据中断，ECharts会自动断开线条
          chartData.value.cpu.push(null);
          chartData.value.memory.push(null);
          chartData.value.networkRx.push(null);
          chartData.value.networkTx.push(null);
          chartData.value.diskRead.push(null);
          chartData.value.diskWrite.push(null);
          
          // 保持数据点数量限制
          if (chartData.value.timestamps.length > MAX_DATA_POINTS) {
            chartData.value.timestamps.shift();
            chartData.value.cpu.shift();
            chartData.value.memory.shift();
            chartData.value.networkRx.shift();
            chartData.value.networkTx.shift();
            chartData.value.diskRead.shift();
            chartData.value.diskWrite.shift();
          }
          
          updateCharts();
        }
        
        // 调整刷新间隔（错误情况）
        adjustRefreshInterval(true);
      } else {
        // 不是最后一次重试，等待一小段时间后重试
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
  }
  
  // 只有首次加载才重置loading状态
  if (isInitialLoad) {
    loading.value = false;
  }
};
</script>

<style scoped>
.chart-section {
  background: var(--color-bg-1);
  border-radius: 0;
  padding: 15px;
  margin-bottom: 20px;
  border: 1px solid var(--color-border);
}

.chart-section:last-child {
  margin-bottom: 0;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--color-border-1);
}

.chart-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-1);
  display: flex;
  align-items: center;
}

.chart-value {
  font-size: 14px;
  font-weight: normal;
  padding: 2px 6px;
  background: transparent;
  border-radius: 0;
  color: var(--color-text-1);
  min-width: 0;
  text-align: right;
}

.chart-wrapper {
  position: relative;
  width: 100%;
  height: 220px;
}

.chart-container {
  width: 100%;
  height: 100%;
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;
}

.chart-wrapper.loading {
  opacity: 0.6;
}

.chart-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--color-bg-2);
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 20px;
  z-index: 10;
}

.skeleton-line {
  height: 16px;
  background: linear-gradient(90deg, var(--color-bg-3) 25%, var(--color-bg-2) 50%, var(--color-bg-3) 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
  margin-bottom: 12px;
  border-radius: 4px;
}

.skeleton-line:nth-child(1) { width: 90%; }
.skeleton-line:nth-child(2) { width: 80%; }
.skeleton-line:nth-child(3) { width: 85%; }
.skeleton-line:nth-child(4) { width: 75%; }
.skeleton-line:nth-child(5) { width: 60%; }

@keyframes loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.error-message {
  padding: 15px;
  text-align: center;
  color: var(--color-danger);
  background: var(--color-danger-light-1);
  border-radius: 4px;
  margin: 20px 0;
  border: 1px solid var(--color-danger-light-3);
  font-size: 14px;
}

/* 响应式适配 - 平板 */
@media (max-width: 1024px) {
  .container-monitor-content {
    padding: 12px;
  }
  
  .chart-section {
    padding: 12px;
    margin-bottom: 15px;
  }
  
  .chart-wrapper {
    height: 180px;
  }
  
  .chart-header h3 {
    font-size: 13px;
  }
  
  .chart-value {
    font-size: 12px;
    padding: 3px 6px;
    min-width: 50px;
  }
}

/* 响应式适配 - 移动端 */
@media (max-width: 768px) {
  .container-monitor-content {
    padding: 10px;
  }
  
  .chart-section {
    padding: 10px;
    margin-bottom: 12px;
  }
  
  .chart-wrapper {
    height: 160px;
  }
  
  .chart-header h3 {
    font-size: 12px;
  }
  
  .chart-value {
    font-size: 12px;
    padding: 2px 4px;
    min-width: 40px;
  }
  
  .chart-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    margin-bottom: 10px;
    padding-bottom: 6px;
  }
  
  .chart-overlay {
    padding: 15px;
  }
  
  .skeleton-line {
    height: 14px;
    margin-bottom: 10px;
  }
}

/* 响应式适配 - 小屏幕 */
@media (max-width: 480px) {
  .container-monitor-content {
    padding: 8px;
  }
  
  .chart-section {
    padding: 8px;
    margin-bottom: 10px;
  }
  
  .chart-wrapper {
    height: 140px;
  }
  
  .chart-header h3 {
    font-size: 11px;
  }
  
  .chart-value {
    font-size: 11px;
  }
  
  .chart-header h3::before {
    height: 12px;
  }
}

/* 响应式适配 - 超小屏幕 */
@media (max-width: 320px) {
  .container-monitor-content {
    padding: 6px;
  }
  
  .chart-section {
    padding: 6px;
    margin-bottom: 8px;
  }
  
  .chart-wrapper {
    height: 120px;
  }
  
  .chart-header h3 {
    font-size: 10px;
  }
  
  .chart-value {
    font-size: 10px;
  }
  
  .chart-header {
    margin-bottom: 8px;
    padding-bottom: 4px;
  }
  
  .skeleton-line {
    height: 10px;
    margin-bottom: 6px;
  }
}

/* 暗色主题适配 */
[arco-theme="dark"] .container-monitor-content {
  background: var(--color-bg-1);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
}

[arco-theme="dark"] .chart-section {
  background: var(--color-bg-2);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
  border-color: var(--color-border-3);
}

[arco-theme="dark"] .chart-section:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  border-color: var(--color-border-4);
}

[arco-theme="dark"] .chart-overlay {
  background: var(--color-bg-2);
}

[arco-theme="dark"] .error-message {
  color: var(--color-danger-light-5);
  background-color: var(--color-danger-light-1);
  border-color: var(--color-danger-light-3);
}

[arco-theme="dark"] .chart-value {
  background: var(--color-primary-light-1);
  color: var(--color-primary-light-5);
}

/* 自定义滚动条样式 */
.container-monitor-content::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.container-monitor-content::-webkit-scrollbar-track {
  background: var(--color-bg-2);
  border-radius: 3px;
}

.container-monitor-content::-webkit-scrollbar-thumb {
  background: var(--color-fill-3);
  border-radius: 3px;
}

.container-monitor-content::-webkit-scrollbar-thumb:hover {
  background: var(--color-fill-4);
}
</style>