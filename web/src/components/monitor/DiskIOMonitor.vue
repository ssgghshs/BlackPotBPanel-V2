<template>
  <div class="disk-io-monitor">
    <div class="header-controls">
      <h3>{{ t('diskIOMonitor') }}</h3>
      <div class="disk-selector">
        <a-select 
          v-model="selectedDisk" 
          :options="diskOptions" 
          :placeholder="t('selectDisk')" 
          style="width: 200px;"
          @change="handleDiskChange"
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
import { getDiskIO } from '../../api/monitor.js'
import * as echarts from 'echarts5'
import { Select } from '@arco-design/web-vue'
import '@arco-design/web-vue/es/select/style/css.js'
import { t } from '../../utils/locale'

export default {
  name: 'DiskIOMonitor',
  components: {
    ASelect: Select
  },
  setup() {
    const chartContainer = ref(null)
    let chartInstance = null
    const loading = ref(true)
    const error = ref('')
    const selectedDisk = ref('all') // 默认选择全部磁盘
    const allDisks = ref([]) // 存储所有磁盘名称
    
    // 图表数据
    const chartData = ref({
      timestamps: [],
      disks: {
        read: [],
        write: []
      }
    })
    
    // 历史数据长度限制
    const MAX_DATA_POINTS = 12

    // 磁盘选项
    const diskOptions = computed(() => {
      const options = [{ label: t.value('allDisks'), value: 'all' }]
      allDisks.value.forEach(diskName => {
        options.push({ label: diskName, value: diskName })
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
          data: [t.value('readSpeed'), t.value('writeSpeed')],
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
          name: t.value('speed') + ' (KB/s)'
        },
        series: [
          {
            name: t.value('readSpeed'),
            type: 'line',
            smooth: true,
            data: chartData.value.disks.read.length > 0 ? chartData.value.disks.read : [0],
            areaStyle: {
              opacity: 0.1
            },
            lineStyle: {
              width: 2,
              color: 'green' 
            },
            itemStyle: {
              color: 'green' 
            },
            animation: true,
            animationDuration: 300
          },
          {
            name: t.value('writeSpeed'),
            type: 'line',
            smooth: true,
            data: chartData.value.disks.write.length > 0 ? chartData.value.disks.write : [0],
            areaStyle: {
              opacity: 0.1
            },
            lineStyle: {
              width: 2,
              color: 'orange'
            },
            itemStyle: {
              color: 'orange'
            },
            animation: true,
            animationDuration: 300
          }
        ]
      }
      
      chartInstance.setOption(option, true)
    }
    
    // 处理磁盘选择变化
    const handleDiskChange = () => {
      // 不清空现有数据，实现无缝刷新
      // 重新获取数据
      fetchDiskIO()
    }
    
    // 获取磁盘 I/O 数据
    const fetchDiskIO = async () => {
      try {
        // 只有在初次加载时显示loading状态，后续更新不显示loading
        if (chartData.value.timestamps.length === 0) {
          loading.value = true
        }
        error.value = ''
        
        const response = await getDiskIO()
        
        // 检查响应数据结构
        let data = null
        if (response && response.code === 200) {
          data = response.data
        } else if (response.data && response.data.code === 200) {
          data = response.data.data
        } else {
          throw new Error('数据格式错误：缺少 disks 数据')
        }
        
        if (data) {
          // 更新磁盘列表
          if (data.disks) {
            allDisks.value = Object.keys(data.disks)
          } else {
            throw new Error('数据格式错误：缺少 disks 数据')
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
        console.error('获取磁盘 I/O 数据失败:', err)
        error.value = t.value('getDiskIOFailed') + ': ' + (err.message || '')
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
      
      // 确保数据结构存在
      if (!chartData.value.disks.read) {
        chartData.value.disks.read = []
      }
      if (!chartData.value.disks.write) {
        chartData.value.disks.write = []
      }
      
      // 添加时间戳
      chartData.value.timestamps.push(timestamp)
      
      // 计算读取和写入速度（KB/s）
      let totalRead = 0
      let totalWrite = 0
      
      if (data.disks) {
        if (selectedDisk.value === 'all') {
          // 计算所有磁盘的总速度
          Object.values(data.disks).forEach(diskData => {
            totalRead += diskData.read_bytes_per_sec || 0
            totalWrite += diskData.write_bytes_per_sec || 0
          })
        } else {
          // 计算选定磁盘的速度
          const diskData = data.disks[selectedDisk.value]
          if (diskData) {
            totalRead = diskData.read_bytes_per_sec || 0
            totalWrite = diskData.write_bytes_per_sec || 0
          }
        }
      }
      
      // 转换为KB/s（后端现在返回的是字节/秒）
      const readKB = Math.round(totalRead / 1024 * 100) / 100
      const writeKB = Math.round(totalWrite / 1024 * 100) / 100
      
      // 添加到数据数组
      chartData.value.disks.read.push(readKB)
      chartData.value.disks.write.push(writeKB)
      
      // 限制数据点数量
      if (chartData.value.timestamps.length > MAX_DATA_POINTS) {
        chartData.value.timestamps.shift()
        chartData.value.disks.read.shift()
        chartData.value.disks.write.shift()
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
      
      fetchDiskIO()
      
      // 设置定时器定期更新数据
      const timer = setInterval(() => {
        fetchDiskIO()
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
      selectedDisk,
      diskOptions,
      handleDiskChange,
      t
    }
  }
}
</script>

<style scoped>
.disk-io-monitor {
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

.disk-selector {
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
  .disk-io-monitor {
    height: 350px;
    padding: 12px;
  }
  
  .header-controls {
    margin-bottom: 8px;
  }
  
  .header-controls h3 {
    font-size: 15px;
  }
  
  .disk-selector :deep(.arco-select) {
    width: 150px !important;
  }
}

/* 移动端适配 */
@media (max-width: 768px) {
  .disk-io-monitor {
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
  
  .disk-selector {
    width: 100%;
  }
  
  .disk-selector :deep(.arco-select) {
    width: 100% !important;
  }
}

@media (max-width: 480px) {
  .disk-io-monitor {
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
  .disk-io-monitor {
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
[arco-theme="dark"] .disk-io-monitor {
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