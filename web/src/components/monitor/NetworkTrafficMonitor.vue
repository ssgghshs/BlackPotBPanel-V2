<template>
  <div class="network-traffic-monitor">
    <div class="header-controls">
      <h3>{{ t('networkTrafficMonitor') }}</h3>
      <div class="interface-selector">
        <a-select 
          v-model="selectedInterface" 
          :options="interfaceOptions" 
          :placeholder="t('selectNetworkInterface')" 
          style="width: 200px;"
          @change="handleInterfaceChange"
        />
      </div>
    </div>

    <!-- 图表容器 -->
    <div ref="chartContainer" class="chart-container" v-show="!loading && !error">
    </div>
    
    <!-- 加载状态 -->
    <div class="chart-skeleton" v-show="loading">
      <div class="skeleton-line" v-for="i in 5" :key="i"></div>
    </div>
    
    <!-- 错误状态 -->
    <div class="error" v-show="error">
      {{ error }}
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount, nextTick, computed } from 'vue'
import { getNetworkTraffic } from '../../api/monitor.js'
import * as echarts from 'echarts5'
import { Select } from '@arco-design/web-vue'
import '@arco-design/web-vue/es/select/style/css.js'
import { t } from '../../utils/locale'

export default {
  name: 'NetworkTrafficMonitor',
  components: {
    ASelect: Select
  },
  setup() {
    const chartContainer = ref(null)
    let chartInstance = null
    const loading = ref(true)
    const error = ref('')
    const selectedInterface = ref('all') // 默认选择全部网卡
    const allInterfaces = ref([]) // 存储所有网卡名称
    
    // 图表数据
    const chartData = ref({
      timestamps: [],
      interfaces: {
        recv: [],
        sent: []
      }
    })
    
    // 历史数据长度限制
    const MAX_DATA_POINTS = 12

    // 网卡选项
    const interfaceOptions = computed(() => {
      const options = [{ label: t.value('allNetworkInterfaces'), value: 'all' }]
      allInterfaces.value.forEach(interfaceName => {
        options.push({ label: interfaceName, value: interfaceName })
      })
      return options
    })
    
    // 初始化图表
    const initChart = () => {
      if (chartContainer.value) {
        // 检查容器是否有宽度和高度
        if (chartContainer.value.clientWidth === 0 || chartContainer.value.clientHeight === 0) {
          return false;
        }
        
        // 检查是否已经初始化
        if (chartInstance) {
          console.log('图表已初始化，跳过重复初始化');
          return true;
        }
        
        try {
          chartInstance = echarts.init(chartContainer.value)
          updateChart()
          return true
        } catch (error) {
          console.error('初始化图表实例时出错:', error);
          return false;
        }
      }
      return false
    }
    
    // 更新图表
    const updateChart = () => {
      if (!chartInstance) return
      
      // 处理X轴数据
      let xAxisData = chartData.value.timestamps
      if (xAxisData.length === 0) {
        xAxisData = ['无数据']
      }
      
      const option = {
        tooltip: {
          trigger: 'axis',
          formatter: (params) => {
            let result = params[0].axisValueLabel + '<br/>'
            params.forEach(param => {
              result += `${param.marker} ${param.seriesName}: ${param.value} KB/s<br/>`
            })
            return result
          }
        },
        legend: {
          data: [t.value('receivedTraffic'), t.value('sentTraffic')],
          bottom: 0
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: xAxisData
        },
        yAxis: {
          type: 'value',
          name: t.value('traffic') + ' (KB/s)'
        },
        series: [
          {
            name: t.value('receivedTraffic'),
            type: 'line',
            smooth: true,
            data: chartData.value.interfaces.recv.length > 0 ? chartData.value.interfaces.recv : [0],
            areaStyle: {
              opacity: 0.1
            },
            lineStyle: {
              width: 2,
              color: 'green' // 绿色
            },
            itemStyle: {
              color: 'green' // 绿色
            },
            animation: true,
            animationDuration: 300
          },
          {
            name: t.value('sentTraffic'),
            type: 'line',
            smooth: true,
            data: chartData.value.interfaces.sent.length > 0 ? chartData.value.interfaces.sent : [0],
            areaStyle: {
              opacity: 0.1
            },
            lineStyle: {
              width: 2,
              color: 'orange' // 橙色
            },
            itemStyle: {
              color: 'orange' // 橙色
            },
            animation: true,
            animationDuration: 300
          }
        ]
      }
      
      chartInstance.setOption(option, true)
    }
    
    // 处理网卡选择变化
    const handleInterfaceChange = () => {
      // 不清空现有数据，实现无缝刷新
      // 重新获取数据
      fetchNetworkTraffic()
    }
    
    // 获取网络流量数据
    const fetchNetworkTraffic = async () => {
      try {
        // 只有在初次加载时显示loading状态，后续更新不显示loading
        if (chartData.value.timestamps.length === 0) {
          loading.value = true
        }
        error.value = ''
        
        const response = await getNetworkTraffic()
        
        // 检查响应数据结构
        let data = null
        if (response && response.code === 200) {
          data = response.data
        } else if (response.data && response.data.code === 200) {
          data = response.data.data
        } else {
          throw new Error('数据格式错误：缺少 interfaces 数据')
        }
        
        if (data) {
          // 更新网卡列表
          if (data.interfaces) {
            allInterfaces.value = Object.keys(data.interfaces)
          } else {
            throw new Error('数据格式错误：缺少 interfaces 数据')
          }
          
          // 处理数据
          processData(data)
          
          // 确保图表已初始化
          if (!chartInstance) {
            const initialized = initChart()
            if (!initialized) {
              // 如果初始化失败，设置轮询重试
              let pollCount = 0
              const pollInterval = setInterval(() => {
                pollCount++
                const initialized = initChart()
                if (initialized || pollCount > 10) {
                  clearInterval(pollInterval)
                  if (initialized) {
                    updateChart()
                  }
                }
              }, 300)
              
              // 设置最大轮询时间
              setTimeout(() => {
                clearInterval(pollInterval)
                if (!chartInstance) {
                  console.warn('轮询超时，强制初始化图表')
                  // 强制设置容器尺寸并初始化
                  if (chartContainer.value) {
                    chartContainer.value.style.width = '100%'
                    chartContainer.value.style.height = '100%'
                    initChart()
                    updateChart()
                  }
                }
              }, 3000)
            }
          } else {
            updateChart()
          }
        }
      } catch (err) {
        console.error('获取网络流量数据失败:', err)
        error.value = t.value('getNetworkTrafficFailed') + ': ' + (err.message || '')
      } finally {
        // 只有在初次加载时隐藏loading状态
        if (chartData.value.timestamps.length > 0) {
          loading.value = false
        }
      }
    }
    
    // 处理数据
    const processData = (data) => {
      // 获取时间戳
      const now = new Date()
      const timestamp = now.toTimeString().slice(0, 5) // "HH:MM"
      
      // 初始化数据结构（仅在第一次时初始化）
      if (chartData.value.timestamps.length === 0) {
        chartData.value.interfaces = {
          recv: [],
          sent: []
        }
      }
      
      // 添加时间戳
      chartData.value.timestamps.push(timestamp)
      
      // 计算接收和发送流量（KB/s）
      let totalRecv = 0
      let totalSent = 0
      
      if (data.interfaces) {
        if (selectedInterface.value === 'all') {
          // 计算所有网卡的总流量
          Object.values(data.interfaces).forEach(interfaceData => {
            totalRecv += interfaceData.bytes_recv_per_sec || 0
            totalSent += interfaceData.bytes_sent_per_sec || 0
          })
        } else {
          // 计算选定网卡的流量
          const interfaceData = data.interfaces[selectedInterface.value]
          if (interfaceData) {
            totalRecv = interfaceData.bytes_recv_per_sec || 0
            totalSent = interfaceData.bytes_sent_per_sec || 0
          }
        }
      }
      
      // 转换为KB/s（后端现在返回的是字节/秒）
      const recvKB = Math.round(totalRecv / 1024 * 100) / 100
      const sentKB = Math.round(totalSent / 1024 * 100) / 100
      
      // 添加到数据数组
      chartData.value.interfaces.recv.push(recvKB)
      chartData.value.interfaces.sent.push(sentKB)
      
      // 限制数据点数量
      if (chartData.value.timestamps.length > MAX_DATA_POINTS) {
        chartData.value.timestamps.shift()
        chartData.value.interfaces.recv.shift()
        chartData.value.interfaces.sent.shift()
      }
    }
    
    // 窗口大小调整处理
    const handleResize = () => {
      if (chartInstance) {
        nextTick(() => {
          chartInstance.resize()
        })
      }
    }
    
    // 组件挂载
    onMounted(() => {
      // 延迟初始化图表，确保DOM已渲染
      nextTick(() => {
        const initialized = initChart()
        if (!initialized) {
          // 如果初始化失败，设置轮询重试
          let pollCount = 0
          const pollInterval = setInterval(() => {
            pollCount++
            const initialized = initChart()
            if (initialized || pollCount > 10) {
              clearInterval(pollInterval)
            }
          }, 300)
        }
      })
      
      fetchNetworkTraffic()
      
      // 设置定时器定期更新数据
      const timer = setInterval(() => {
        fetchNetworkTraffic()
      }, 5000)
      
      // 监听窗口大小变化
      window.addEventListener('resize', handleResize)
      
      // 组件卸载前清理
      onBeforeUnmount(() => {
        if (timer) {
          clearInterval(timer)
        }
        window.removeEventListener('resize', handleResize)
        if (chartInstance) {
          chartInstance.dispose()
          chartInstance = null
        }
      })
    })
    
    return {
      chartContainer,
      loading,
      error,
      selectedInterface,
      interfaceOptions,
      handleInterfaceChange,
      t
    }
  }
}
</script>

<style scoped>
.network-traffic-monitor {
  background: var(--color-bg-1);
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  height: 380px;
  display: flex;
  flex-direction: column;
}

.header-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.header-controls h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-1);
}

.interface-selector {
  display: flex;
  align-items: center;
}

.chart-container {
  flex: 1;
  width: 100%;
  min-height: 0;
  position: relative;
  transition: opacity 0.3s ease;
}

.chart-skeleton {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--color-bg-2);
  border-radius: 4px;
  padding: 20px;
  box-sizing: border-box;
  transition: opacity 0.3s ease;
}

.skeleton-line {
  height: 20px;
  background: linear-gradient(90deg, var(--color-bg-3) 25%, var(--color-bg-2) 50%, var(--color-bg-3) 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
  margin-bottom: 15px;
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

.error {
  padding: 10px;
  text-align: center;
  font-size: 14px;
  color: var(--color-danger-light-5);
  background-color: var(--color-danger-light-1);
  border-radius: 4px;
  transition: opacity 0.3s ease;
}

/* 平板适配 */
@media (max-width: 1024px) {
  .network-traffic-monitor {
    height: 350px;
    padding: 12px;
  }
  
  .header-controls {
    margin-bottom: 8px;
  }
  
  .header-controls h3 {
    font-size: 15px;
  }
  
  .interface-selector :deep(.arco-select) {
    width: 150px !important;
  }
}

/* 移动端适配 */
@media (max-width: 768px) {
  .network-traffic-monitor {
    height: 320px;
    padding: 10px;
    border-radius: 6px;
  }
  
  .header-controls {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    margin-bottom: 10px;
  }
  
  .header-controls h3 {
    font-size: 16px;
  }
  
  .interface-selector {
    width: 100%;
  }
  
  .interface-selector :deep(.arco-select) {
    width: 100% !important;
  }
}

@media (max-width: 480px) {
  .network-traffic-monitor {
    height: 280px;
    padding: 8px;
  }
  
  .header-controls {
    margin-bottom: 8px;
  }
  
  .header-controls h3 {
    font-size: 15px;
  }
  
  .chart-skeleton {
    padding: 15px;
  }
  
  .skeleton-line {
    margin-bottom: 12px;
  }
}

/* 超小屏幕适配 */
@media (max-width: 320px) {
  .network-traffic-monitor {
    height: 250px;
    padding: 6px;
    border-radius: 4px;
  }
  
  .header-controls h3 {
    font-size: 14px;
  }
  
  .chart-skeleton {
    padding: 10px;
  }
  
  .skeleton-line {
    height: 16px;
    margin-bottom: 10px;
  }
}

/* 暗色主题适配 */
[arco-theme="dark"] .network-traffic-monitor {
  background: var(--color-bg-1) !important;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3) !important;
}

[arco-theme="dark"] .chart-skeleton {
  background: var(--color-bg-2) !important;
}

[arco-theme="dark"] .error {
  color: var(--color-danger-light-5) !important;
  background-color: var(--color-danger-light-1) !important;
}
</style>