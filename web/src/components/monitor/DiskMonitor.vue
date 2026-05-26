<template>
  <div class="disk-monitor">
    <!-- 单个磁盘显示 -->
    <template v-if="disks.length <= 1">
      <div class="disk-section">
        <div class="section-title">{{ t('diskUsage') }}</div>
        <div class="disk-grid">
          <a-popover  position="bottom">
            <template #content>
              <a-descriptions :column="2" :label-style="{ fontWeight: 'bold' }" :bordered="true">
                <a-descriptions-item :label="t('deviceName')" :span="2">{{ disk.device || '未知' }}</a-descriptions-item>
                <a-descriptions-item :label="t('mountPoint')">{{ disk.mountpoint || '未知' }}</a-descriptions-item>
                <a-descriptions-item :label="t('fileSystem')">{{ disk.fstype || '未知' }}</a-descriptions-item>
                <a-descriptions-item :label="t('usageRate')">{{ disk.percent || 0 }}%</a-descriptions-item>
                <a-descriptions-item :label="t('usedInodes')">{{ disk.inodesUsed || 0 }}</a-descriptions-item>
                <a-descriptions-item :label="t('totalCapacity')">{{ disk.total || 0 }}GB</a-descriptions-item>
                <a-descriptions-item :label="t('totalInodes')">{{ disk.inodesTotal || 0 }}</a-descriptions-item>
                <a-descriptions-item :label="t('usedCapacity')">{{ disk.used || 0 }}GB</a-descriptions-item>
                <a-descriptions-item :label="t('inodeUsageRate')">{{ disk.inodesUsedPercent || 0 }}%</a-descriptions-item>
              </a-descriptions>
            </template>
            <div class="disk-item">
              <div class="chart-wrapper" :class="{ 'loading': loading }">
                <div ref="diskChart" class="chart-container"></div>
                <div v-if="loading" class="chart-overlay">
                  <div class="skeleton-circle"></div>
                </div>
              </div>
              <div class="item-info">
                <div class="item-title">{{ getDiskDisplayPath(disk) }}</div>
                <div class="item-detail">{{ disk.used }}GB / {{ disk.total }}GB</div>
              </div>
            </div>
          </a-popover>
        </div>
      </div>
    </template>
    
    <!-- 多个磁盘显示 -->
    <template v-else>
      <div class="disk-section">
        <div class="section-title">{{ t('diskUsage') }}</div>
        <div class="disk-grid">
          <a-popover v-for="(disk, index) in disks" :key="index" position="bottom">
            <template #content>
              <a-descriptions :column="2" :label-style="{ fontWeight: 'bold' }" :bordered="true">
                <a-descriptions-item :label="t('deviceName')" :span="2">{{ disk.device || '未知' }}</a-descriptions-item>
                <a-descriptions-item :label="t('mountPoint')">{{ disk.mountpoint || '未知' }}</a-descriptions-item>
                <a-descriptions-item :label="t('fileSystem')">{{ disk.fstype || '未知' }}</a-descriptions-item>
                <a-descriptions-item :label="t('usageRate')">{{ disk.percent || 0 }}%</a-descriptions-item>
                <a-descriptions-item :label="t('usedInodes')">{{ disk.inodesUsed || 0 }}</a-descriptions-item>
                <a-descriptions-item :label="t('totalCapacity')">{{ disk.total || 0 }}GB</a-descriptions-item>
                <a-descriptions-item :label="t('totalInodes')">{{ disk.inodesTotal || 0 }}</a-descriptions-item>
                <a-descriptions-item :label="t('usedCapacity')">{{ disk.used || 0 }}GB</a-descriptions-item>
                <a-descriptions-item :label="t('inodeUsageRate')">{{ disk.inodesUsedPercent || 0 }}%</a-descriptions-item>
              </a-descriptions>
            </template>
            <div class="disk-item">
              <div class="chart-wrapper" :class="{ 'loading': loading }">
                <div :ref="el => { if (el) diskCharts[index] = el }" class="chart-container"></div>
                <div v-if="loading" class="chart-overlay">
                  <div class="skeleton-circle"></div>
                </div>
              </div>
              <div class="item-info">
                <div class="item-title">{{ getDiskDisplayPath(disk) }}</div>
                <div class="item-detail">{{ disk.used }}GB / {{ disk.total }}GB</div>
              </div>
            </div>
          </a-popover>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
import * as echarts from 'echarts5';
import { t } from '../../utils/locale';
import { Popover as APopover, Descriptions as ADescriptions, DescriptionsItem as ADescriptionsItem} from '@arco-design/web-vue';

export default {
  name: 'DiskMonitor',
  setup() {
    return { t };
  },
  props: {
    diskData: {
      type: Object,
      default: () => ({})
    },
    loading: {
      type: Boolean,
      default: false
    },
    size: {
      type: String,
      default: 'medium',
      validator: (value) => ['small', 'medium', 'large', 'auto'].includes(value)
    }
  },
  data() {
    return {
      // 单个磁盘数据（向后兼容）
      disk: {
        device: '',
        mountpoint: '',
        fstype: '',
        percent: 0,
        used: 0,
        total: 0,
        inodesTotal: 0,
        inodesUsed: 0,
        inodesUsedPercent: 0
      },
      // 所有磁盘数据
      disks: [],
      chart: null,
      // 为每个磁盘图表创建单独的引用
      diskCharts: {},
      diskChartInstances: {},
      // 响应式观察器
      resizeObserver: null
    }
  },
  watch: {
    diskData: {
      handler(newVal) {
        this.updateDiskData(newVal);
      },
      deep: true,
      immediate: true
    }
  },
  mounted() {
    this.initCharts();
    this.initResizeObserver();
  },
  computed: {
    chartSize() {
      const sizes = {
        small: { width: 60, height: 60, fontSize: 14 },
        medium: { width: 100, height: 100, fontSize: 20 },
        large: { width: 140, height: 140, fontSize: 24 },
        auto: { width: '100%', height: '100%', fontSize: 20 }
      };
      return sizes[this.size] || sizes.medium;
    },
    containerClass() {
      return `size-${this.size}`;
    }
  },
  beforeDestroy() {
    this.destroyCharts();
    this.destroyResizeObserver();
  },
  beforeUnmount() {
    this.destroyCharts();
    this.destroyResizeObserver();
  },
  methods: {
    updateDiskData(data) {
      if (!data) return;
      
      // 更新磁盘数据 - 处理所有磁盘
      if (data.all_disks && data.all_disks.length > 0) {
        this.disks = data.all_disks.map(disk => ({
          device: disk.device || '',
          mountpoint: disk.mountpoint || '',
          fstype: disk.fstype || '',
          percent: Math.round(disk.percent * 10) / 10 || 0,
          used: Math.round(disk.used * 100) / 100 || 0,
          total: Math.round(disk.total * 100) / 100 || 0,
          inodesTotal: disk.inodesTotal || 0,
          inodesUsed: disk.inodesUsed || 0,
          inodesUsedPercent: Math.round(disk.inodesUsedPercent * 10) / 10 || 0
        }));
        
        // 更新单个磁盘数据（向后兼容）
        const primaryDisk = data.all_disks[0];
        this.disk.device = primaryDisk.device || '';
        this.disk.mountpoint = primaryDisk.mountpoint || '';
        this.disk.fstype = primaryDisk.fstype || '';
        this.disk.percent = Math.round(primaryDisk.percent * 10) / 10 || 0;
        this.disk.used = Math.round(primaryDisk.used * 100) / 100 || 0;
        this.disk.total = Math.round(primaryDisk.total * 100) / 100 || 0;
        this.disk.inodesTotal = primaryDisk.inodesTotal || 0;
        this.disk.inodesUsed = primaryDisk.inodesUsed || 0;
        this.disk.inodesUsedPercent = Math.round(primaryDisk.inodesUsedPercent * 10) / 10 || 0;
        
        // 在下一个DOM更新周期初始化磁盘图表
        this.$nextTick(() => {
          if (this.disks.length > 1) {
            this.initializeDiskCharts();
          } else {
            this.initializeChart();
          }
        });
      } else {
        // 兼容旧版本，只有单个磁盘信息
        this.disks = [{
          device: 'C:',
          mountpoint: 'C:\\',
          percent: Math.round(data.percent * 10) / 10 || 0,
          used: Math.round(data.used * 100) / 100 || 0,
          total: Math.round(data.total * 100) / 100 || 0,
          inodesTotal: data.inodesTotal || 0,
          inodesUsed: data.inodesUsed || 0,
          inodesUsedPercent: Math.round(data.inodesUsedPercent * 10) / 10 || 0
        }];
        
        // 更新单个磁盘数据
        this.disk.device = data.device || 'C:';
          this.disk.mountpoint = data.mountpoint || 'C:\\';
          this.disk.fstype = data.fstype || 'NTFS';
          this.disk.percent = Math.round(data.percent * 10) / 10 || 0;
          this.disk.used = Math.round(data.used * 100) / 100 || 0;
          this.disk.total = Math.round(data.total * 100) / 100 || 0;
          this.disk.inodesTotal = data.inodesTotal || 0;
          this.disk.inodesUsed = data.inodesUsed || 0;
          this.disk.inodesUsedPercent = Math.round(data.inodesUsedPercent * 10) / 10 || 0;
        
        this.$nextTick(() => {
          this.initializeChart();
        });
      }
      
      // 更新图表
      this.$nextTick(() => {
        this.updateCharts();
      });
    },
    
    initCharts() {
      // 初始化图表将在数据更新时进行
    },
    
    initializeChart() {
      try {
        const chartElement = this.$refs.diskChart;
        if (chartElement && !this.chart) {
          // 检查 DOM 元素是否有有效的尺寸
          const rect = chartElement.getBoundingClientRect();
          if (rect.width === 0 || rect.height === 0) {
            // 如果尺寸为 0，延迟初始化
            setTimeout(() => {
              this.initializeChart();
            }, 100);
            return;
          }
          
          this.chart = echarts.init(chartElement);
          
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
                show: true,
                position: 'center',
                formatter: '0%',
                fontSize: 20,
                fontWeight: 'bold',
                color: '#333'
              },
              labelLine: {
                show: false
              },
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
                  color: '#f0f0f0'
                }
              }]
            }]
          };
          
          this.chart.setOption(JSON.parse(JSON.stringify(defaultOption)));
        }
      } catch (error) {
        console.error('初始化磁盘图表时出错:', error);
      }
    },
    
    // 初始化磁盘图表
    initializeDiskCharts() {
      try {
        // 为每个磁盘创建图表实例
        this.disks.forEach((disk, index) => {
          const chartElement = this.diskCharts[index];
          if (chartElement && !this.diskChartInstances[index]) {
            // 检查 DOM 元素是否有有效的尺寸
            const rect = chartElement.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) {
              // 如果尺寸为 0，延迟初始化
              setTimeout(() => {
                this.initializeDiskCharts();
              }, 100);
              return;
            }
            
            this.diskChartInstances[index] = echarts.init(chartElement);
            
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
                  show: true,
                  position: 'center',
                  formatter: '0%',
                  fontSize: 20,
                  fontWeight: 'bold',
                  color: '#333'
                },
                labelLine: {
                  show: false
                },
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
                    color: '#f0f0f0'
                  }
                }]
              }]
            };
            
            this.diskChartInstances[index].setOption(JSON.parse(JSON.stringify(defaultOption)));
          }
        });
      } catch (error) {
        console.error('初始化磁盘图表时出错:', error);
      }
    },
    
    updateCharts() {
      try {
        // 更新磁盘图表 - 单个磁盘时使用旧方式
        if (this.disks.length <= 1 && this.chart) {
          const diskOption = {
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
                show: true,
                position: 'center',
                formatter: this.disk.percent + '%',
                fontSize: 20,
                fontWeight: 'bold',
                color: '#333'
              },
              labelLine: {
                show: false
              },
              roundCap: true,
              showEmptyCircle: true,
              emptyCircleStyle: {
                color: 'transparent',
                borderColor: '#f0f0f0',
                borderWidth: 2
              },
              data: [{
                value: this.disk.percent,
                itemStyle: {
                  color: this.getProgressColor(this.disk.percent),
                  borderRadius: 10,
                  borderCap: 'round',
                  borderJoin: 'round'
                }
              }, {
                value: 100 - this.disk.percent,
                itemStyle: {
                  color: 'transparent'
                }
              }]
            }]
          };
          this.chart.setOption(diskOption, true);
        } else {
          // 更新磁盘图表 - 为每个磁盘更新图表
          this.disks.forEach((disk, index) => {
            if (this.diskChartInstances[index]) {
              const diskOption = {
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
                    show: true,
                    position: 'center',
                    formatter: disk.percent + '%',
                    fontSize: 20,
                    fontWeight: 'bold',
                    color: '#333'
                  },
                  labelLine: {
                    show: false
                  },
                  roundCap: true,
                  showEmptyCircle: true,
                  emptyCircleStyle: {
                    color: 'transparent',
                    borderColor: '#f0f0f0',
                    borderWidth: 2
                  },
                  data: [{
                    value: disk.percent,
                    itemStyle: {
                      color: this.getProgressColor(disk.percent),
                      borderRadius: 10,
                      borderCap: 'round',
                      borderJoin: 'round'
                    }
                  }, {
                    value: 100 - disk.percent,
                    itemStyle: {
                      color: 'transparent'
                    }
                  }]
                }]
              };
              this.diskChartInstances[index].setOption(diskOption, true);
            }
          });
        }
      } catch (error) {
        console.error('更新磁盘图表时出错:', error);
      }
    },
    
    getProgressColor(percent) {
      if (percent < 40) return '#67C23A'
      if (percent < 70) return '#E6A23C'
      return '#F56C6C'
    },
    
    // 获取磁盘显示路径
    getDiskDisplayPath(disk) {
      // 直接返回 mountpoint 或 device，优先 mountpoint
      return disk.mountpoint || disk.device || '/';
    },
    
    handleResize() {
      // 窗口大小调整时，重新调整图表大小
      if (this.chart) {
        this.chart.resize()
      }
      
      // 调整所有磁盘图表大小
      Object.values(this.diskChartInstances).forEach(chart => {
        if (chart) {
          chart.resize()
        }
      });
    },

    destroyCharts() {
      // 销毁图表实例
      if (this.chart) {
        this.chart.dispose()
        this.chart = null
      }
      
      // 销毁所有磁盘图表实例
      Object.values(this.diskChartInstances).forEach(chart => {
        if (chart) {
          chart.dispose()
        }
      });
      
      this.diskChartInstances = {}
    },
    
    initResizeObserver() {
      // 初始化响应式观察器
      if (typeof ResizeObserver !== 'undefined') {
        this.resizeObserver = new ResizeObserver(() => {
          this.handleResize()
        })
        
        // 观察容器元素
        const container = this.$el
        if (container) {
          this.resizeObserver.observe(container)
        }
      } else {
        // 降级到 window resize 事件
        window.addEventListener('resize', this.handleResize)
      }
    },
    
    destroyResizeObserver() {
      // 销毁响应式观察器
      if (this.resizeObserver) {
        this.resizeObserver.disconnect()
        this.resizeObserver = null
      } else {
        // 移除 window resize 事件监听器
        window.removeEventListener('resize', this.handleResize)
      }
    }
  }
}
</script>

<style scoped>
.disk-monitor {
  width: 100%;
  height: 100%;
}

.section-title {
  font-weight: bold;
  color: var(--color-text-1);
  margin-bottom: 10px;
  font-size: 14px;
  text-align: left;
}

.disk-section {
  width: 100%;
}

.disk-grid {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-start;
  gap: 15px;
  max-height: 200px;
  overflow-y: auto;
  width: 100%;
}

.disk-item {
  text-align: left;
  flex: 0 0 auto;
  width: 100px;
}

.monitor-item {
  text-align: left;
  width: 100%;
}

.chart-wrapper {
  position: relative;
  display: block;
  width: 100px;
  height: 100px;
  margin: 0;
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

.item-info {
  font-size: 12px;
  text-align: left;
}

.item-title {
  font-weight: bold;
  color: var(--color-text-1);
  text-align: left;
}

.item-detail {
  color: var(--color-text-2);
  text-align: left;
}

/* 平板适配 */
@media (max-width: 1024px) {
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
  
  .disk-item {
    width: 90px;
  }
  
  .item-info {
    font-size: 11px;
  }
}

/* 移动端适配 */
@media (max-width: 768px) {
  .disk-monitor {
    padding: 10px 0;
  }
  
  .section-title {
    font-size: 13px;
    margin-bottom: 8px;
    text-align: center;
  }
  
  .disk-grid {
    justify-content: center;
    gap: 12px;
    max-height: 180px;
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
  
  .disk-item {
    width: 80px;
  }
  
  .item-info {
    font-size: 10px;
  }
  
  .item-title {
    font-size: 11px;
  }
  
  .item-detail {
    font-size: 9px;
  }
}

/* 小屏幕适配 */
@media (max-width: 480px) {
  .disk-monitor {
    padding: 8px 0;
  }
  
  .section-title {
    font-size: 12px;
    margin-bottom: 6px;
  }
  
  .disk-grid {
    gap: 10px;
    max-height: 160px;
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
  
  .disk-item {
    width: 70px;
  }
  
  .item-info {
    font-size: 9px;
  }
  
  .item-title {
    font-size: 10px;
  }
  
  .item-detail {
    font-size: 8px;
  }
}

/* 超小屏幕适配 */
@media (max-width: 320px) {
  .disk-monitor {
    padding: 6px 0;
  }
  
  .section-title {
    font-size: 11px;
    margin-bottom: 5px;
  }
  
  .disk-grid {
    gap: 8px;
    max-height: 140px;
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
  
  .disk-item {
    width: 60px;
  }
  
  .item-info {
    font-size: 8px;
  }
  
  .item-title {
    font-size: 9px;
  }
  
  .item-detail {
    font-size: 7px;
  }
}

/* 自定义滚动条样式 */
.disk-grid::-webkit-scrollbar {
  height: 6px;
}

.disk-grid::-webkit-scrollbar-track {
  background: var(--color-bg-2);
  border-radius: 3px;
}

.disk-grid::-webkit-scrollbar-thumb {
  background: var(--color-fill-3);
  border-radius: 3px;
}

.disk-grid::-webkit-scrollbar-thumb:hover {
  background: var(--color-fill-4);
}
</style>