<template>
  <div class="waf-dashboard">
    <div class="main-layout" v-if="wafBasicInfo">
      
      <!-- ================= 左侧列 ================= -->
      <div class="left-column">
        <div class="metrics-grid">
          <!-- 第一排 -->
          <div class="content-row">
            <div class="card-item card-3">
              <div class="card-content">
                <div class="status-content">
                  <div class="stat-item">
                    <span class="stat-label">{{ t('requestCount') }}</span>
                    <span class="stat-value">{{ wafBasicInfo.data?.access_logs?.request_count ?? 0 }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">{{ t('errorCount') }}</span>
                    <span class="stat-value">{{ wafBasicInfo.data?.access_logs?.error_count ?? 0 }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="card-item card-5">
              <div class="card-content">
                <div class="stats-content">
                  <div class="stat-item"><span class="stat-label">{{ t('blockCount') }}</span><span class="stat-value">{{ wafBasicInfo.data?.waf_logs?.block_count ?? 0 }}</span></div>
                  <div class="stat-item"><span class="stat-label">{{ t('attackIpCount') }}</span><span class="stat-value">{{ wafBasicInfo.data?.waf_logs?.attack_ip_count ?? 0 }}</span></div>
                  <div class="stat-item"><span class="stat-label">{{ t('recordCount') }}</span><span class="stat-value">{{ wafBasicInfo.data?.waf_logs?.record_count ?? 0 }}</span></div>
                </div>
              </div>
            </div>
          </div>

          <!-- 第二排 -->
          <div class="content-row">
            <div class="card-item card-3">
              <div class="card-content">
                <div class="status-content">
                  <div class="stat-item"><span class="stat-label">{{ t('blackwhiteBlockCount') }}</span><span class="stat-value">{{ wafBasicInfo.data?.blackwhite_logs?.block_count ?? 0 }}</span></div>
                  <div class="stat-item"><span class="stat-label">{{ t('blackwhiteRecordCount') }}</span><span class="stat-value">{{ wafBasicInfo.data?.blackwhite_logs?.record_count ?? 0 }}</span></div>
                </div>
              </div>
            </div>
            <div class="card-item card-5">
              <div class="card-content">
                <div class="stats-content">
                  <div class="stat-item"><span class="stat-label">{{ t('botverifiedCount') }}</span><span class="stat-value">{{ wafBasicInfo.data?.bot_logs?.verified_count ?? 0 }}</span></div>
                  <div class="stat-item"><span class="stat-label">{{ t('botchallengeCount') }}</span><span class="stat-value">{{ wafBasicInfo.data?.bot_logs?.challenge_count ?? 0 }}</span></div>
                  <div class="stat-item"><span class="stat-label">{{ t('botfailedCount') }}</span><span class="stat-value">{{ wafBasicInfo.data?.bot_logs?.failed_count ?? 0 }}</span></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 左侧底部：安全趋势 -->
        <!-- 世界地图有2D/3D  中国地图2D    -->

        <Map />
      </div>

      <!-- ================= 右侧列 ================= -->
      <div class="right-column">
        <!-- QPS 排 -->
        <div class="qps-row">
          <div class="card-item qps-card">
            <div class="header-controls"><h3>{{ t('visitStatus') }}</h3></div>
            <div class="card-content">
              <div ref="visitChart" class="chart-container"></div>
            </div>
          </div>
          <div class="card-item qps-card">
            <div class="header-controls"><h3>{{ t('blockStatus') }}</h3></div>
            <div class="card-content">
              <div ref="blockChart" class="chart-container"></div>
            </div>
          </div>
        </div>

        <!-- QPS流量分析 -->
        <div class="traffic-monitor-wrapper">
          <div class="card-item fill-card">
            <div class="header-controls"><h3>{{ t('realTimeQPS') }}</h3></div>
            <div class="card-content">
              <div ref="qpsChart" class="chart-container"></div>
            </div>
          </div>
        </div>

        <!-- 右侧底部 CARD：已更新区域 -->
        <div class="stretch-card-wrapper">
          <div class="card-item fill-card">
            <div class="card-content three-sections">
              <!-- 操作系统 -->
              <div class="section-item">
                <div class="section-header">{{ t('operatingSystems') }}</div>
                <div class="section-body client-stat-container">
                  <div class="chart-box"><div ref="osChart" class="mini-chart"></div></div>
                  <div class="list-box scrollable-list">
                    <div v-for="(item, index) in displayOS" :key="index" class="client-stat-item">
                      <span class="color-dot" :style="{ backgroundColor: getChartColor(index) }"></span>
                      <span class="stat-name">{{ item.name }}</span>
                      <span class="stat-num">{{ formatCount(item.count) }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <!-- 浏览器 -->
              <div class="section-item">
                <div class="section-header">{{ t('browser') }}</div>
                <div class="section-body client-stat-container">
                  <div class="chart-box"><div ref="browserChart" class="mini-chart"></div></div>
                  <div class="list-box scrollable-list">
                    <div v-for="(item, index) in displayBrowsers" :key="index" class="client-stat-item">
                      <span class="color-dot" :style="{ backgroundColor: getChartColor(index) }"></span>
                      <span class="stat-name">{{ item.name }}</span>
                      <span class="stat-num">{{ formatCount(item.count) }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <!-- 状态码 -->
              <div class="section-item">
                <div class="section-header">{{ t('statusCode') }}</div>
                <div class="section-body client-stat-container">
                  <div class="chart-box"><div ref="statusChart" class="mini-chart"></div></div>
                  <div class="list-box scrollable-list">
                    <div v-for="(item, index) in displayStatusCodes" :key="index" class="client-stat-item">
                      <span class="color-dot" :style="{ backgroundColor: getChartColor(index) }"></span>
                      <span class="stat-name">{{ item.status_code }}</span>
                      <span class="stat-num">{{ formatCount(item.count) }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { reactive, computed, onMounted, ref, onBeforeUnmount, nextTick } from 'vue';
import { t } from '../../utils/locale'
import { getWAFBasicInfo, getWAFQPS, getClientStats } from '../../api/waf'
import { Message } from '@arco-design/web-vue';
import * as echarts from 'echarts5'
import Map from '../../components/waf/Map.vue';

const wafBasicInfo = reactive({ data: {}, loading: false })
const qpsData = reactive({ data: { nodes: [] }, loading: false })

// 客户端统计数据状态
const clientStats = reactive({
  operating_systems: [],
  browsers: [],
  status_codes: []
})

// 计算属性：根据限制显示数量
const displayOS = computed(() => MAX_DISPLAY_ITEMS > 0 ? clientStats.operating_systems.slice(0, MAX_DISPLAY_ITEMS) : clientStats.operating_systems)
const displayBrowsers = computed(() => MAX_DISPLAY_ITEMS > 0 ? clientStats.browsers.slice(0, MAX_DISPLAY_ITEMS) : clientStats.browsers)
const displayStatusCodes = computed(() => MAX_DISPLAY_ITEMS > 0 ? clientStats.status_codes.slice(0, MAX_DISPLAY_ITEMS) : clientStats.status_codes)

// 图表 DOM 引用
const visitChart = ref(null)
const blockChart = ref(null)
const qpsChart = ref(null)
const osChart = ref(null)
const browserChart = ref(null)
const statusChart = ref(null)

// ECharts 实例
let visitChartInstance = null
let blockChartInstance = null
let qpsChartInstance = null
let osChartInstance = null
let browserChartInstance = null
let statusChartInstance = null

// 颜色面板（固定循环使用）
const colorPalette = ['#E6B08E', '#F39C12', '#E74C3C', '#3498DB', '#E67E22', '#2ECC71', '#9B59B6'];
const getChartColor = (index) => colorPalette[index % colorPalette.length];

// 格式化数字：23500 -> 23.5k
const formatCount = (num) => {
  if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
  return num;
};

// 限制列表显示数量（设为 0 表示不限制）
const MAX_DISPLAY_ITEMS = 0;

const fetchWAFBasicInfo = async () => {
  wafBasicInfo.loading = true
  try {
    const response = await getWAFBasicInfo()
    wafBasicInfo.data = response || {}
  } catch (error) {
    console.error('获取WAF基本信息失败:', error)
  } finally {
    wafBasicInfo.loading = false
  }
}

// 获取客户端统计并更新图表
const fetchClientStats = async () => {
  try {
    const response = await getClientStats();
    if (response) {
      clientStats.operating_systems = response.operating_systems || [];
      clientStats.browsers = response.browsers || [];
      clientStats.status_codes = response.status_codes || [];
      
      // 使用nextTick确保DOM更新后再更新图表
      nextTick(() => {
        // 检查环形图容器是否有尺寸
        const osReady = osChart.value && osChart.value.clientWidth > 0 && osChart.value.clientHeight > 0;
        const browserReady = browserChart.value && browserChart.value.clientWidth > 0 && browserChart.value.clientHeight > 0;
        const statusReady = statusChart.value && statusChart.value.clientWidth > 0 && statusChart.value.clientHeight > 0;
        
        const anyRingChartReady = osReady || browserReady || statusReady;
        
        // 只有当至少有一个环形图容器有尺寸时，才调用updateRingCharts
        if (anyRingChartReady || osChartInstance || browserChartInstance || statusChartInstance) {
          // 如果有容器准备就绪，或者图表实例已存在，就调用updateRingCharts
          updateRingCharts();
        } else {
          console.log('环形图容器尺寸为0，等待容器准备就绪');
          // 容器尺寸为0，不初始化图表，避免ECharts警告
        }
      });
    }
  } catch (error) {
    console.error('获取客户端统计失败:', error);
  }
};

const fetchWAFQPS = async () => {
  qpsData.loading = true
  try {
    const response = await getWAFQPS()
    if (response && response.data && response.data.nodes) {
      qpsData.data = response
    } else if (response && response.nodes) {
      qpsData.data = { data: { nodes: response.nodes } }
    } else {
      qpsData.data = { data: { nodes: [] } }
    }
    
    // 只有当图表实例未初始化时才检查是否需要初始化
    if (!visitChartInstance && !blockChartInstance && !qpsChartInstance) {
      // 检查容器是否有尺寸
      const visitReady = visitChart.value && visitChart.value.clientWidth > 0 && visitChart.value.clientHeight > 0;
      const blockReady = blockChart.value && blockChart.value.clientWidth > 0 && blockChart.value.clientHeight > 0;
      const qpsReady = qpsChart.value && qpsChart.value.clientWidth > 0 && qpsChart.value.clientHeight > 0;
      
      const anyContainerReady = visitReady || blockReady || qpsReady;
      
      if (anyContainerReady) {
        console.log('图表实例未初始化且容器准备就绪，尝试初始化');
        initCharts();
      } else {
        console.log('图表实例未初始化但容器尺寸为0，等待容器准备就绪');
        // 容器尺寸为0，不初始化图表，避免ECharts警告
      }
    } else {
      // 图表实例已存在，直接更新数据
      updateCharts();
    }
  } catch (error) {
    console.error('获取WAF QPS数据失败:', error);
  } finally {
    qpsData.loading = false;
  }
}

// 初始化客户端环形图
const updateRingCharts = () => {
  const configs = [
    { ref: osChart, instance: 'osChartInstance', data: clientStats.operating_systems, key: 'name', name: '操作系统图表' },
    { ref: browserChart, instance: 'browserChartInstance', data: clientStats.browsers, key: 'name', name: '浏览器图表' },
    { ref: statusChart, instance: 'statusChartInstance', data: clientStats.status_codes, key: 'status_code', name: '状态码图表' }
  ];

  configs.forEach(cfg => {
    if (!cfg.ref.value) {
      console.warn(`${cfg.name} DOM 元素不存在`);
      return;
    }
    
    let instance = null;
    if (cfg.instance === 'osChartInstance') instance = osChartInstance;
    if (cfg.instance === 'browserChartInstance') instance = browserChartInstance;
    if (cfg.instance === 'statusChartInstance') instance = statusChartInstance;

    try {
      if (!instance) {
        // 只有在初始化图表实例时才检查DOM尺寸
        // 检查 DOM 元素是否有尺寸
        if (cfg.ref.value.clientWidth === 0 || cfg.ref.value.clientHeight === 0) {
          // 只在控制台输出一次警告，避免重复警告
          console.warn(`${cfg.name} 容器尺寸为 0 (width: ${cfg.ref.value.clientWidth}, height: ${cfg.ref.value.clientHeight})，跳过初始化`);
          // 当容器尺寸为0时，不调用echarts.init，避免ECharts警告
          return;
        }
        
        instance = echarts.init(cfg.ref.value);
        console.log(`${cfg.name} 初始化成功，尺寸: ${cfg.ref.value.clientWidth}x${cfg.ref.value.clientHeight}`);
        if (cfg.instance === 'osChartInstance') osChartInstance = instance;
        if (cfg.instance === 'browserChartInstance') browserChartInstance = instance;
        if (cfg.instance === 'statusChartInstance') statusChartInstance = instance;
      }

      const option = {
        color: colorPalette,
        tooltip: {
          trigger: 'item',
          formatter: function(params) {
            let result = params.name + '<br/>';
            result += params.marker + ' Count: ' + params.value + ' 次<br/>';
            result += 'Percent: ' + params.percent + '%';
            return result;
          },
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          borderColor: '#40a9ff',
          borderWidth: 1,
          textStyle: {
            color: '#fff'
          },
          padding: 10,
          extraCssText: 'box-shadow: 0 0 10px rgba(0, 0, 0, 0.3); z-index: 9999;',
          // 确保tooltip不被容器截断
          confine: false,
          position: function(point, params, dom, rect, size) {
            // 调整tooltip位置，避免被截断
            const position = [0, 0];
            position[0] = point[0] + 10;
            position[1] = point[1] - 10;
            
            // 确保tooltip在可视区域内
            if (position[0] + size.contentSize[0] > rect.right) {
              position[0] = rect.right - size.contentSize[0] - 10;
            }
            if (position[1] - size.contentSize[1] < rect.top) {
              position[1] = rect.top + 10;
            }
            
            return position;
          }
        },
        series: [{
          type: 'pie',
          radius: ['55%', '85%'],
          center: ['50%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: { borderRadius: 4, borderColor: 'transparent', borderWidth: 2 },
          label: { show: false },
          data: cfg.data.map(item => ({ value: item.count, name: item[cfg.key] }))
        }]
      };
      instance.setOption(option);
    } catch (error) {
      console.error(`${cfg.name} 初始化失败:`, error);
    }
  });
};

const initCharts = () => {
  const initSingleChart = (chartRef, chartInstance, instanceName) => {
    if (!chartRef.value) {
      console.warn(`${instanceName} DOM 元素不存在`);
      return null;
    }
    
    try {
      if (!chartInstance) {
        // 只有在初始化图表实例时才检查DOM尺寸
        // 检查 DOM 元素是否有尺寸
        if (chartRef.value.clientWidth === 0 || chartRef.value.clientHeight === 0) {
          console.warn(`${instanceName} 容器尺寸为 0 (width: ${chartRef.value.clientWidth}, height: ${chartRef.value.clientHeight})，跳过初始化`);
          // 当容器尺寸为0时，不调用echarts.init，避免ECharts警告
          return null;
        }
        
        const instance = echarts.init(chartRef.value);
        console.log(`${instanceName} 初始化成功，尺寸: ${chartRef.value.clientWidth}x${chartRef.value.clientHeight}`);
        return instance;
      }
      return chartInstance;
    } catch (error) {
      console.error(`${instanceName} 初始化失败:`, error);
      return null;
    }
  };

  visitChartInstance = initSingleChart(visitChart, visitChartInstance, '访问情况图表');
  blockChartInstance = initSingleChart(blockChart, blockChartInstance, '拦截情况图表');
  qpsChartInstance = initSingleChart(qpsChart, qpsChartInstance, '实时QPS图表');
  
  // 只有当所有图表都初始化成功后才更新数据
  if (visitChartInstance || blockChartInstance || qpsChartInstance) {
    updateCharts();
  }
}

const updateCharts = () => {
  const nodes = qpsData.data.data?.nodes || []
  if (nodes.length === 0) return
  
  const times = nodes.map(node => node.time)
  const requestCounts = nodes.map(node => node.requests)
  const blockCounts = nodes.map(node => node.blocks)
  const qpsValues = nodes.map(node => node.qps)
  
  if (visitChartInstance) {
    visitChartInstance.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
      xAxis: { type: 'category', boundaryGap: false, data: times, axisLabel: { fontSize: 10, rotate: 45 } },
      yAxis: { type: 'value' },
      series: [{ name: 'Requests', type: 'line', smooth: true, data: requestCounts, areaStyle: { opacity: 0.2 }, itemStyle: { color: '#40a9ff' } }]
    })
  }

  if (blockChartInstance) {
    blockChartInstance.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
      xAxis: { type: 'category', boundaryGap: false, data: times, axisLabel: { fontSize: 10, rotate: 45 } },
      yAxis: { type: 'value' },
      series: [{ name: 'Blocks', type: 'line', smooth: true, data: blockCounts, areaStyle: { opacity: 0.2 }, itemStyle: { color: '#ff4d4f' } }]
    })
  }

  if (qpsChartInstance) {
    qpsChartInstance.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
      xAxis: { type: 'category', boundaryGap: false, data: times, axisLabel: { fontSize: 10, rotate: 45 } },
      yAxis: { type: 'value' },
      series: [{ name: 'QPS', type: 'line', smooth: true, data: qpsValues, areaStyle: { opacity: 0.2 }, itemStyle: { color: '#52c41a' } }]
    })
  }
}

const handleResize = () => {
  [visitChartInstance, blockChartInstance, qpsChartInstance, osChartInstance, browserChartInstance, statusChartInstance].forEach(inst => {
    inst?.resize()
  })
}

onMounted(() => {
  fetchWAFBasicInfo()
  fetchClientStats()
  
  // 使用多个 nextTick 确保 DOM 完全渲染
  nextTick(() => {
    nextTick(() => {
      // 再次检查DOM尺寸，确保容器有正确的尺寸
      const checkAndInitCharts = (retryCount = 0) => {
        const maxRetries = 20; // 最大重试次数
        
        // 检查容器是否存在
        const visitExists = visitChart.value !== null;
        const blockExists = blockChart.value !== null;
        const qpsExists = qpsChart.value !== null;
        
        // 检查容器是否有尺寸
        const visitReady = visitExists && visitChart.value.clientWidth > 0 && visitChart.value.clientHeight > 0;
        const blockReady = blockExists && blockChart.value.clientWidth > 0 && blockChart.value.clientHeight > 0;
        const qpsReady = qpsExists && qpsChart.value.clientWidth > 0 && qpsChart.value.clientHeight > 0;
        
        const allContainersReady = visitReady || blockReady || qpsReady;
        const anyContainerExists = visitExists || blockExists || qpsExists;
        
        if (allContainersReady) {
          console.log('图表容器准备就绪，初始化图表');
          initCharts();
          fetchWAFQPS();
        } else {
          if (retryCount < maxRetries) {
            // 只在重试次数较少且至少有一个容器存在时输出警告
            if (retryCount < 3 && anyContainerExists) {
              console.warn(`图表容器尺寸未准备好，延迟初始化 (${retryCount + 1}/${maxRetries})`);
              console.log('容器尺寸状态:');
              console.log('- 访问情况图表:', visitExists ? `width: ${visitChart.value.clientWidth}, height: ${visitChart.value.clientHeight}` : 'DOM不存在');
              console.log('- 拦截情况图表:', blockExists ? `width: ${blockChart.value.clientWidth}, height: ${blockChart.value.clientHeight}` : 'DOM不存在');
              console.log('- 实时QPS图表:', qpsExists ? `width: ${qpsChart.value.clientWidth}, height: ${qpsChart.value.clientHeight}` : 'DOM不存在');
            }
            setTimeout(() => checkAndInitCharts(retryCount + 1), 100);
          } else {
            console.error('图表容器尺寸长时间未准备好，停止重试');
            // 不再强制初始化图表，避免ECharts警告
            // 图表会在容器尺寸变为非0时通过其他途径初始化
            console.log('图表初始化将在容器尺寸变为非0时自动进行');
          }
        }
      };
      
      checkAndInitCharts();
      
      window.qpsInterval = setInterval(() => {
        fetchWAFQPS()
        fetchClientStats()
      }, 5000)
    })
  })
  
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  if (window.qpsInterval) clearInterval(window.qpsInterval)
  window.removeEventListener('resize', handleResize);
  [visitChartInstance, blockChartInstance, qpsChartInstance, osChartInstance, browserChartInstance, statusChartInstance].forEach(inst => {
    inst?.dispose()
  })
})
</script>

<style scoped>
.waf-dashboard {
  padding: 15px;
  box-sizing: border-box;
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.main-layout {
  display: flex;
  gap: 15px;
  flex: 1;
  min-height: 0;
  align-items: stretch;
}

.left-column {
  flex: 8;
  display: flex;
  flex-direction: column;
  gap: 15px;
  height: 100%;
  min-height: 0;
}

.right-column {
  flex: 4;
  display: flex;
  flex-direction: column;
  gap: 15px;
  height: 100%;
  min-height: 0;
}

.stretch-card-wrapper {
  flex: 1;
  display: flex;
  min-height: 0;
}

.fill-card {
  width: 100%;
  height: 100%;
}

.card-item {
  background: var(--color-bg-1);
  padding: 12px;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.metrics-grid {
  display: flex;
  flex-direction: column;
  gap: 15px;
  flex-shrink: 0;
}

.content-row {
  display: flex;
  gap: 15px;
  min-height: 80px;
}

.content-row:last-child {
  margin-bottom: 0;
}

.card-3 {
  width: 37.5%;
  min-width: 0;
}

.card-5 {
  width: 62.5%;
  min-width: 0;
}

.qps-row {
  display: flex;
  gap: 15px;
  flex: 0 0 auto;
  min-height: 180px;
  height: 25vh;
  max-height: 280px;
}

.qps-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.traffic-monitor-wrapper {
  flex: 0 0 auto;
  min-height: 160px;
  height: 22vh;
  max-height: 250px;
  display: flex;
  flex-direction: column;
}

.card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 0;
  overflow: hidden;
}

.status-content,
.stats-content {
  display: flex;
  gap: 10px;
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 6px 4px;
  background: var(--color-bg-2);
  border-radius: 4px;
  border: 1px solid var(--color-neutral-3);
}

.header-controls h3 {
  margin: 0 0 8px 0;
  font-size: 13px;
  color: var(--color-text-1);
}

.stat-label {
  font-size: 11px;
  color: var(--color-text-2);
}

.stat-value {
  font-size: clamp(14px, 1.5vw, 18px);
  font-weight: 600;
}

.three-sections {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 8px;
  padding: 8px 0;
}

.section-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-2);
  border-radius: 4px;
  border: 1px solid var(--color-neutral-3);
  overflow: hidden;
  min-height: 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 10px;
  background: var(--color-fill-2);
  border-bottom: 1px solid var(--color-neutral-3);
  font-size: 11px;
  color: var(--color-text-2);
  font-weight: 500;
}

.more-count {
  font-size: 10px;
  color: var(--color-text-3);
  background: var(--color-fill-1);
  padding: 1px 6px;
  border-radius: 10px;
}

.client-stat-container {
  display: flex !important;
  flex-direction: row !important;
  padding: 8px !important;
  align-items: stretch;
  overflow: hidden;
}

.chart-box {
  flex: 0 0 30%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mini-chart {
  width: 100%;
  height: 100%;
  min-height: 60px;
  min-width: 60px;
}

.list-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding-left: 15px;
  padding-right: 10px;
}

.scrollable-list {
  justify-content: flex-start;
  overflow-y: auto;
  max-height: 100%;
}

.scrollable-list::-webkit-scrollbar {
  width: 4px;
}

.scrollable-list::-webkit-scrollbar-thumb {
  background: var(--color-neutral-3);
  border-radius: 2px;
}

.scrollable-list::-webkit-scrollbar-track {
  background: transparent;
}

.client-stat-item {
  display: flex;
  align-items: center;
  margin-bottom: 4px;
  font-size: 12px;
  line-height: 1.2;
}

.color-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  margin-right: 8px;
  flex-shrink: 0;
}

.stat-name {
  flex: 1;
  color: var(--color-text-2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-right: 10px;
}

.stat-num {
  color: var(--color-text-1);
  font-weight: 600;
  text-align: right;
  min-width: 45px;
}

.placeholder-content {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  border: 1px dashed var(--color-neutral-3);
  border-radius: 4px;
  color: var(--color-text-3);
  font-size: 12px;
}

.chart-container {
  width: 100%;
  height: 100%;
  min-height: 120px;
  min-width: 150px;
}

@media (max-width: 1600px) {
  .qps-row {
    min-height: 160px;
    height: 22vh;
  }
  .traffic-monitor-wrapper {
    min-height: 140px;
    height: 20vh;
  }
}

@media (max-width: 1200px) {
  .waf-dashboard {
    height: auto;
    min-height: calc(100vh - 100px);
    overflow: auto;
  }
  .main-layout {
    flex-direction: column;
  }
  .left-column,
  .right-column {
    height: auto;
    flex: none;
  }
  .qps-row {
    height: auto;
    min-height: 200px;
  }
  .traffic-monitor-wrapper {
    height: auto;
    min-height: 180px;
  }
  .content-row {
    min-height: 70px;
  }
}

@media (max-width: 768px) {
  .waf-dashboard {
    padding: 10px;
  }
  .main-layout {
    gap: 10px;
  }
  .content-row {
    flex-direction: column;
  }
  .card-3,
  .card-5 {
    width: 100%;
  }
  .qps-row {
    flex-direction: column;
  }
  .client-stat-container {
    flex-direction: column !important;
  }
  .chart-box {
    flex: 0 0 auto;
    height: 120px;
  }
  .list-box {
    padding-left: 0;
    padding-top: 8px;
  }
}
</style>