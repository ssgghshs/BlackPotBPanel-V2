<template>
  <div class="compact-system-monitor">
    <div class="header-controls">
      <h3>{{ t('resourceMonitor') }}</h3>
    </div>
    <a-row :gutter="10" style="margin: 0 -5px;" class="monitor-row">
      <!-- CPU监控 -->
      <a-col :span="8" style="padding: 5px;">
        <a-popover placement="top" position="bottom">
          <template #content>
            <a-descriptions :column="2" bordered>
              <a-descriptions-item :label="t('cores')">{{ cpu.cores }}</a-descriptions-item>
              <a-descriptions-item :label="t('threads')">{{ cpu.threads }}</a-descriptions-item>
              <a-descriptions-item :label="t('cpuModelName')" :span="2">{{ cpu.cpuModelName || t('unknown') }}</a-descriptions-item>
            </a-descriptions>
          </template>
          <div class="monitor-item">
            <div class="chart-wrapper" :class="{ 'loading': loading }">
              <div ref="cpuChart" class="chart-container"></div>
              <div v-if="loading" class="chart-overlay">
                <div class="skeleton-circle"></div>
              </div>
            </div>
            <div class="item-info">
              <div class="item-title">{{ t('cpuUsage') }}</div>
              <div class="item-detail">{{ cpu.cores }}{{ t('cores') }} / {{ cpu.threads }}{{ t('threads') }}</div>
            </div>
          </div>
        </a-popover>
      </a-col>

      <!-- 内存监控 -->
      <a-col :span="8" style="padding: 5px;">
        <a-popover placement="top" position="bottom">
          <template #content>
            <a-descriptions :column="2" bordered>
              <a-descriptions-item :label="t('memoryPercent')">{{ memory.percent }}%</a-descriptions-item>
              <a-descriptions-item :label="t('swapPercent')">{{ memory.swappercent }}%</a-descriptions-item>
              <a-descriptions-item :label="t('memoryTotal')">{{ memory.total }}GB</a-descriptions-item>
              <a-descriptions-item :label="t('swapTotal')">{{ memory.swaptotal }}GB</a-descriptions-item>
              <a-descriptions-item :label="t('memoryUsed')">{{ memory.used }}GB</a-descriptions-item>
              <a-descriptions-item :label="t('swapUsed')">{{ memory.swapused }}GB</a-descriptions-item>
            </a-descriptions>
          </template>
          <div class="monitor-item">
            <div class="chart-wrapper" :class="{ 'loading': loading }">
              <div ref="memoryChart" class="chart-container"></div>
              <div v-if="loading" class="chart-overlay">
                <div class="skeleton-circle"></div>
              </div>
            </div>
            <div class="item-info">
              <div class="item-title">{{ t('memoryUsage') }}</div>
              <div class="item-detail">{{ memory.used }}GB / {{ memory.total }}GB</div>
            </div>
          </div>
        </a-popover>
      </a-col>

      <!-- 负载状态 -->
      <a-col :span="8" style="padding: 5px;">
        <div class="monitor-item">
          <div class="chart-wrapper" :class="{ 'loading': loading }">
            <div ref="loadChart" class="chart-container"></div>
            <div v-if="loading" class="chart-overlay">
              <div class="skeleton-circle"></div>
            </div>
          </div>
          <div class="item-info">
            <div class="item-title">{{ t('loadStatus') }}</div>
            <div class="item-detail">{{ getLoadStatus() }}</div>
          </div>
        </div>
      </a-col>
    </a-row>
    
    <!-- 磁盘监控 - 单独起一排 -->
    <a-row :gutter="10" style="margin: 0 -5px; margin-top: 10px;">
      <a-col :span="24" style="padding: 5px;">
        <div class="disk-monitor-wrapper">
          <DiskMonitor :disk-data="diskData" :loading="loading" />
        </div>
      </a-col>
    </a-row>
  </div>
</template>

<script>
import { getSystemInfo } from '../../api/monitor.js'
import * as echarts from 'echarts5';
import DiskMonitor from './DiskMonitor.vue';
import { t } from '../../utils/locale';
import { Popover as APopover, Descriptions as ADescriptions, DescriptionsItem as ADescriptionsItem } from '@arco-design/web-vue';
export default {
  name: 'CompactSystemMonitor',
  components: {
    DiskMonitor,
    APopover,
    ADescriptions,
    ADescriptionsItem
  },
  setup() {
    return { t };
  },
  data() {
    return {
      cpu: {
        percent: 0,
        cores: 0,
        threads: 0,
        load_avg: [0, 0, 0],
        cpuModelName: ''
      },
      memory: {
        percent: 0,
        used: 0,
        total: 0,
        swappercent: 0,
        swaptotal: 0,
        swapused: 0
      },
      diskData: {}, // 磁盘数据传递给磁盘监控组件
      loading: true,
      timer: null,
      charts: {
        cpu: null,
        memory: null,
        load: null
      },
      resizeObserver: null,
      chartInitializationAttempts: 0,
      maxInitializationAttempts: 5
    }
  },
  mounted() {
    this.initCharts()
    this.fetchSystemInfo()
    // 使用更安全的定时器设置方式
    this.$nextTick(() => {
      this.timer = setInterval(() => {
        if (this._isDestroyed) return // 组件已销毁则不执行
        this.fetchSystemInfo()
      }, 5000)
    })
    
    // 添加窗口大小调整监听器
    window.addEventListener('resize', this.handleResize)
  },
  beforeDestroy() {
    // 更安全的定时器清理
    if (this.timer) {
      clearInterval(this.timer)
      this.timer = null
    }
    // 销毁所有图表实例
    this.destroyCharts()
    // 移除窗口大小调整监听器
    window.removeEventListener('resize', this.handleResize)
    // 断开ResizeObserver
    if (this.resizeObserver) {
      this.resizeObserver.disconnect()
      this.resizeObserver = null
    }
  },
  // Vue 3兼容性处理
  beforeUnmount() {
    // 更安全的定时器清理
    if (this.timer) {
      clearInterval(this.timer)
      this.timer = null
    }
    // 销毁所有图表实例
    this.destroyCharts()
    // 移除窗口大小调整监听器
    window.removeEventListener('resize', this.handleResize)
    // 断开ResizeObserver
    if (this.resizeObserver) {
      this.resizeObserver.disconnect()
      this.resizeObserver = null
    }
  },
  methods: {
    initCharts() {
      try {
        // 确保DOM完全渲染后再初始化图表
        this.$nextTick(() => {
          // 添加延迟确保容器尺寸已确定
          setTimeout(() => {
            if (this.$refs.cpuChart && this.$refs.memoryChart && this.$refs.loadChart) {
              // 检查容器尺寸
              if (this.$refs.cpuChart.clientWidth > 0 && this.$refs.cpuChart.clientHeight > 0) {
                this.initializeChartInstances();
              } else {
                // 使用ResizeObserver监听容器尺寸变化
                this.setupResizeObserver();
              }
            }
          }, 100); // 延迟100ms确保容器尺寸已确定
        });
      } catch (error) {
        console.error('初始化图表时出错:', error);
      }
    },
    
    setupResizeObserver() {
      // 创建ResizeObserver实例
      if (window.ResizeObserver) {
        this.resizeObserver = new ResizeObserver(entries => {
          for (let entry of entries) {
            if (entry.contentRect.width > 0 && entry.contentRect.height > 0) {
              console.log('检测到容器尺寸变化，开始初始化图表');
              this.initializeChartInstances();
              // 初始化完成后断开观察器
              if (this.resizeObserver) {
                this.resizeObserver.disconnect();
                this.resizeObserver = null;
              }
              break;
            }
          }
        });
        
        // 开始观察所有图表容器
        if (this.$refs.cpuChart) this.resizeObserver.observe(this.$refs.cpuChart);
        if (this.$refs.memoryChart) this.resizeObserver.observe(this.$refs.memoryChart);
        if (this.$refs.loadChart) this.resizeObserver.observe(this.$refs.loadChart);
      } else {
        // 如果浏览器不支持ResizeObserver，使用轮询方式
        console.warn('浏览器不支持ResizeObserver，使用轮询方式初始化图表');
        this.pollForContainerSize();
      }
    },
    
    pollForContainerSize() {
      // 轮询检查容器尺寸
      const pollInterval = setInterval(() => {
        if (this.chartInitializationAttempts >= this.maxInitializationAttempts) {
          console.error('达到最大初始化尝试次数，停止轮询');
          clearInterval(pollInterval);
          return;
        }
        
        if (this.$refs.cpuChart && 
            this.$refs.cpuChart.clientWidth > 0 && 
            this.$refs.cpuChart.clientHeight > 0) {
          console.log('轮询检测到容器尺寸可用，开始初始化图表');
          this.initializeChartInstances();
          clearInterval(pollInterval);
        } else {
          this.chartInitializationAttempts++;
          console.warn(`轮询检查容器尺寸，第${this.chartInitializationAttempts}次尝试`);
        }
      }, 300);
      
      // 设置最大轮询时间
      setTimeout(() => {
        clearInterval(pollInterval);
        if (!this.charts.cpu) {
          console.warn('轮询超时，强制设置默认尺寸初始化图表');
          // 强制设置容器尺寸
          if (this.$refs.cpuChart) {
            this.$refs.cpuChart.style.width = '140px';
            this.$refs.cpuChart.style.height = '140px';
          }
          if (this.$refs.memoryChart) {
            this.$refs.memoryChart.style.width = '140px';
            this.$refs.memoryChart.style.height = '140px';
          }
          if (this.$refs.loadChart) {
            this.$refs.loadChart.style.width = '140px';
            this.$refs.loadChart.style.height = '140px';
          }
          this.initializeChartInstances();
        }
      }, 3000); // 3秒后超时
    },
    
    initializeChartInstances() {
      try {
        // 检查是否已经初始化
        if (this.charts.cpu) {
          console.log('图表已初始化，跳过重复初始化');
          return;
        }
        
        console.log('开始初始化图表实例');
        this.charts.cpu = echarts.init(this.$refs.cpuChart);
        this.charts.memory = echarts.init(this.$refs.memoryChart);
        this.charts.load = echarts.init(this.$refs.loadChart);
        
        // 设置初始空图表 - 显示百分比
        const defaultOption = {
          series: [{
            type: 'pie',
            startAngle: 0,
            endAngle: 360,
            radius: ['70%', '90%'],
            center: ['50%', '50%'],
            avoidLabelOverlap: false,
            emphasis: {
              scale: false
            },
            label: {
              show: true,  // 显示标签
              position: 'center',  // 标签位置在中心
              formatter: '0%',  // 初始化时显示0%
              fontSize: 20,
              fontWeight: 'bold',
              color: '#333'
            },
            labelLine: {
              show: false
            },
            // 使饼图更加圆润
            roundCap: true,
            showEmptyCircle: true,
            emptyCircleStyle: {
              color: 'transparent',
              borderColor: '#f0f0f0',
              borderWidth: 2
            },
            data: [{
              value: 0,
              itemStyle: {
                color: '#ddd',
                borderRadius: 10,
                borderCap: 'round',
                borderJoin: 'round'
              }
            }, {
              value: 100,
              itemStyle: {
                color: '#f0f0f0'  // 修改这里，从 'transparent' 改为 '#f0f0f0'
              }
            }]
          }]
        };
        
        Object.values(this.charts).forEach(chart => {
          if (chart) {
            chart.setOption(JSON.parse(JSON.stringify(defaultOption)));
          }
        });
        
        console.log('图表实例初始化完成');
      } catch (error) {
        console.error('初始化图表实例时出错:', error);
      }
    },
    
    updateCharts() {
      try {
        // 确保图表实例存在
        if (!this.charts.cpu || !this.charts.memory || !this.charts.load) {
          // 如果图表未初始化，尝试重新初始化
          if (this.$refs.cpuChart && this.$refs.memoryChart && this.$refs.loadChart) {
            console.warn('图表实例未初始化完成，尝试重新初始化');
            this.initializeChartInstances();
            return;
          } else {
            console.warn('图表实例未初始化完成且容器引用不存在');
            return;
          }
        }

        // 更新CPU图表 - 显示直接的percent值
        const cpuOption = {
          series: [{
            type: 'pie',
            startAngle: 0,
            endAngle: 360,
            radius: ['70%', '90%'],
            center: ['50%', '50%'],
            avoidLabelOverlap: false,
            emphasis: {
              scale: false
            },
            label: {
              show: true,  // 显示标签
              position: 'center',  // 标签位置在中心
              formatter: this.cpu.percent + '%',  // 直接显示percent值
              fontSize: 20,
              fontWeight: 'bold',
              color: '#333'
            },
            labelLine: {
              show: false
            },
            // 使饼图更加圆润
            roundCap: true,
            showEmptyCircle: true,
            emptyCircleStyle: {
              color: 'transparent',
              borderColor: '#f0f0f0',
              borderWidth: 2
            },
            data: [{
              value: this.cpu.percent,
              itemStyle: {
                color: this.getProgressColor(this.cpu.percent),
                borderRadius: 10,
                borderCap: 'round',
                borderJoin: 'round'
              }
            }, {
              value: 100 - this.cpu.percent,
              itemStyle: {
                color: 'transparent'
              }
            }]
          }]
        };
        this.charts.cpu.setOption(cpuOption, true);
        
        // 更新内存图表 - 显示直接的percent值
        const memoryOption = {
          series: [{
            type: 'pie',
            startAngle: 0,
            endAngle: 360,
            radius: ['70%', '90%'],
            center: ['50%', '50%'],
            avoidLabelOverlap: false,
            emphasis: {
              scale: false
            },
            label: {
              show: true,  // 显示标签
              position: 'center',  // 标签位置在中心
              formatter: this.memory.percent + '%',  // 直接显示percent值
              fontSize: 20,
              fontWeight: 'bold',
              color: '#333'
            },
            labelLine: {
              show: false
            },
            // 使饼图更加圆润
            roundCap: true,
            showEmptyCircle: true,
            emptyCircleStyle: {
              color: 'transparent',
              borderColor: '#f0f0f0',
              borderWidth: 2
            },
            data: [{
              value: this.memory.percent,
              itemStyle: {
                color: this.getProgressColor(this.memory.percent),
                borderRadius: 10,
                borderCap: 'round',
                borderJoin: 'round'
              }
            }, {
              value: 100 - this.memory.percent,
              itemStyle: {
                color: 'transparent'
              }
            }]
          }]
        };
        this.charts.memory.setOption(memoryOption, true);
        
        // 更新负载图表 - 显示直接的percent值
        const loadPercent = this.getLoadPercentage();
        const loadOption = {
          series: [{
            type: 'pie',
            startAngle: 0,
            endAngle: 360,
            radius: ['70%', '90%'],
            center: ['50%', '50%'],
            avoidLabelOverlap: false,
            emphasis: {
              scale: false
            },
            label: {
              show: true,  // 显示标签
              position: 'center',  // 标签位置在中心
              formatter: loadPercent + '%',  // 直接显示percent值
              fontSize: 20,
              fontWeight: 'bold',
              color: '#333'
            },
            labelLine: {
              show: false
            },
            // 使饼图更加圆润
            roundCap: true,
            showEmptyCircle: true,
            emptyCircleStyle: {
              color: 'transparent',
              borderColor: '#f0f0f0',
              borderWidth: 2
            },
            data: [{
              value: loadPercent,
              itemStyle: {
                color: this.getLoadColor(),
                borderRadius: 10,
                borderCap: 'round',
                borderJoin: 'round'
              }
            }, {
              value: 100 - loadPercent,
              itemStyle: {
                color: 'transparent'
              }
            }]
          }]
        };
        this.charts.load.setOption(loadOption, true);
      } catch (error) {
        console.error('更新图表时出错:', error);
      }
    },
    getProgressColor(percent) {
      if (percent < 40) return '#67C23A'
      if (percent < 70) return '#E6A23C'
      return '#F56C6C'
    },
    getLoadPercentage() {
      const load = this.cpu.load_avg[0] || 0
      return Math.min(100, Math.round((load / this.cpu.cores) * 100))
    },
    getLoadColor() {
      const percent = this.getLoadPercentage()
      if (percent < 40) return '#67C23A'
      if (percent < 70) return '#E6A23C'
      return '#F56C6C'
    },
    getLoadStatus() {
      const percent = this.getLoadPercentage()
      if (percent < 40) return this.t('runningSmooth')
      if (percent < 70) return this.t('moderateLoad')
      return this.t('highLoad')
    },
    async fetchSystemInfo() {
      // 防止组件销毁后仍然执行
      if (this._isDestroyed || this._isBeingDestroyed) {
        return
      }
      
      try {
        const response = await getSystemInfo()
        
        // 防止组件销毁后仍然更新状态
        if (this._isDestroyed || this._isBeingDestroyed) {
          return
        }
        
        // 检查不同的响应结构
        let data = null
        if (response && response.code === 200) {
          // 直接返回的数据结构
          data = response.data
        } else if (response.data && response.data.code === 200) {
          // 嵌套的数据结构
          data = response.data.data
        }
        
        if (data) {
          // 防止组件销毁后仍然更新状态
          if (this._isDestroyed || this._isBeingDestroyed) {
            return
          }
          
          // 更新CPU数据
          this.cpu.percent = Math.round(data.cpu.percent * 10) / 10
          this.cpu.cores = data.cpu.cores
          this.cpu.threads = data.cpu.threads
          this.cpu.load_avg = data.cpu.load_avg || [0, 0, 0]
          this.cpu.cpuModelName = data.cpu.cpuModelName || ''
          
          // 更新内存数据
          this.memory.percent = Math.round(data.memory.percent * 10) / 10
          this.memory.used = Math.round(data.memory.used * 100) / 100
          this.memory.total = Math.round(data.memory.total * 100) / 100
          
          // 更新交换内存数据
          if (data.memory.swappercent !== undefined) {
            this.memory.swappercent = Math.round(data.memory.swappercent * 10) / 10
          }
          if (data.memory.swaptotal !== undefined) {
            this.memory.swaptotal = Math.round(data.memory.swaptotal * 100) / 100
          }
          if (data.memory.swapused !== undefined) {
            this.memory.swapused = Math.round(data.memory.swapused * 100) / 100
          }
          
          // 更新磁盘数据 - 传递给磁盘监控组件
          this.diskData = data.disk || {}
          
          // 更新所有图表
          this.updateCharts()
        }
      } catch (error) {
        // 防止组件销毁后仍然更新状态
        if (this._isDestroyed || this._isBeingDestroyed) {
          return
        }
        
        console.error('获取系统信息失败:', error)
      } finally {
        // 防止组件销毁后仍然更新状态
        if (!this._isDestroyed && !this._isBeingDestroyed) {
          this.loading = false
        }
      }
    },
    handleResize() {
      // 窗口大小调整时，重新调整图表大小
      if (this.charts.cpu) {
        this.charts.cpu.resize()
      }
      if (this.charts.memory) {
        this.charts.memory.resize()
      }
      if (this.charts.load) {
        this.charts.load.resize()
      }
    },
    destroyCharts() {
      // 销毁所有图表实例
      Object.values(this.charts).forEach(chart => {
        if (chart) {
          chart.dispose()
        }
      })
      // 清空图表引用
      this.charts = {
        cpu: null,
        memory: null,
        load: null
      }
    },
  }
}
</script>

<style scoped>
.compact-system-monitor .arco-card {
  margin-bottom: 10px;
  border-radius: 8px;
}

.compact-system-monitor {
  background: var(--color-bg-1);
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  height: 390px;
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

.monitor-row {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  width: 100%;
}

.monitor-item {
  text-align: center;
  padding: 8px;
  border-radius: 8px;
  background-color: var(--color-bg-2);
  display: flex;
  flex-direction: column;
  align-items: center;
  border: 1px solid var(--color-neutral-3);
}

.item-info {
  font-size: 12px;
  text-align: center;
  width: 100%;
}

.item-title {
  font-weight: bold;
  color: var(--color-text-1);
  text-align: center;
}

.item-detail {
  color: var(--color-text-2);
  text-align: center;
}

.chart-wrapper {
  position: relative;
  display: block;
  width: 100px;
  height: 100px;
  margin: 0 auto;
}

.chart-container {
  width: 100%;
  height: 100%;
}

.chart-wrapper.loading {
  opacity: 0.5;
}

.chart-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100px;
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.skeleton-circle {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(90deg, var(--color-bg-3) 25%, var(--color-bg-2) 50%, var(--color-bg-3) 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
}

@keyframes loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* 平板适配 */
@media (max-width: 1024px) {
  .compact-system-monitor {
    height: 450px;
    padding: 12px;
  }
  
  .chart-wrapper {
    width: 90px;
    height: 90px;
  }
  
  .chart-overlay {
    width: 90px;
    height: 90px;
  }
  
  .skeleton-circle {
    width: 72px;
    height: 72px;
  }
  
  .monitor-item {
    padding: 6px;
  }
  
  .item-info {
    font-size: 11px;
  }
}

/* 移动端适配 */
@media (max-width: 768px) {
  .compact-system-monitor {
    height: 430px;
    padding: 10px;
    border-radius: 6px;
  }
  
  .chart-wrapper {
    width: 80px;
    height: 80px;
  }
  
  .chart-overlay {
    width: 80px;
    height: 80px;
  }
  
  .skeleton-circle {
    width: 64px;
    height: 64px;
  }
  
  .monitor-item {
    padding: 5px;
  }
  
  .item-info {
    font-size: 10px;
  }
}

/* 小屏幕适配 */
@media (max-width: 480px) {
  .compact-system-monitor {
    height: 390px;
    padding: 8px;
    border-radius: 4px;
  }
  
  .chart-wrapper {
    width: 70px;
    height: 70px;
  }
  
  .chart-overlay {
    width: 70px;
    height: 70px;
  }
  
  .skeleton-circle {
    width: 56px;
    height: 56px;
  }
  
  .monitor-item {
    padding: 4px;
  }
  
  .item-title {
    font-size: 9px;
  }
  
  .item-detail {
    font-size: 8px;
  }
}

/* 超小屏幕适配 */
@media (max-width: 320px) {
  .compact-system-monitor {
    height: 360px;
    padding: 6px;
    border-radius: 4px;
  }
  
  .chart-wrapper {
    width: 60px;
    height: 60px;
  }
  
  .chart-overlay {
    width: 60px;
    height: 60px;
  }
  
  .skeleton-circle {
    width: 48px;
    height: 48px;
  }
  
  .monitor-item {
    padding: 3px;
  }
  
  .item-title {
    font-size: 8px;
  }
  
  .item-detail {
    font-size: 7px;
  }
}

/* 暗色主题适配 */
[arco-theme="dark"] .compact-system-monitor {
  background: var(--color-bg-1) !important;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3) !important;
}

[arco-theme="dark"] .monitor-item {
  background-color: var(--color-bg-2) !important;
}

[arco-theme="dark"] .item-header {
  color: var(--color-text-1) !important;
}

[arco-theme="dark"] .item-title {
  color: var(--color-text-1) !important;
}

[arco-theme="dark"] .item-detail {
  color: var(--color-text-2) !important;
}

.disk-monitor-wrapper {
  width: 100%;
  height: 100%;
  border: 1px solid var(--color-neutral-3);
  border-radius: 8px;
  padding: 8px;
  background-color: var(--color-bg-2);
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: center;
}
</style>