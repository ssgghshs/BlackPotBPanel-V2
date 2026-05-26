<template>
  <div class="stretch-card-wrapper">
    <div class="card-item fill-card">
      <div class="main-content">
        <!-- 左边：地图区域 -->
        <div class="map-section">
          <div class="header-controls">
            <h3>{{ t('map') }}</h3>
          </div>
          <div class="card-content">
            <div ref="mapChartRef" class="map-container"></div>
          </div>
        </div>

        <!-- 右边：信息卡片 -->
        <div class="info-card">
          <a-tabs default-active-key="1" type="card" @change="(key) => activeTab = key">
            <a-tab-pane key="1" :title="t('justAccess')">
              <div class="table-container">
                <div v-if="accessLogs.length === 0" class="table-row">
                  <span class="table-cell region">{{ t('noData')}}</span>
                  <span class="table-cell count">-</span>
                </div>
                <div v-for="(item, index) in accessLogs.slice(0, 10)" :key="index" class="table-row">
                  <span class="table-cell region">{{ item.location }}</span>
                  <span class="table-cell count">{{ item.count.toLocaleString() }}</span>
                </div>
              </div>
            </a-tab-pane>
            <a-tab-pane key="2" :title="t('justBlock')">
              <div class="table-container">
                <div v-if="wafLogs.length === 0" class="table-row">
                  <span class="table-cell region">{{ t('noData')}}</span>
                  <span class="table-cell count">-</span>
                </div>
                <div v-for="(item, index) in wafLogs.slice(0, 10)" :key="index" class="table-row">
                  <span class="table-cell region">{{ item.location }}</span>
                  <span class="table-cell count">{{ item.count.toLocaleString() }}</span>
                </div>
              </div>
            </a-tab-pane>
          </a-tabs>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue';
import { t } from '../../utils/locale';
import { getLocationStats } from '../../api/waf';
import * as echarts from 'echarts5';
import worldMapJson from '../../utils/map/world.json';

echarts.registerMap('world', worldMapJson);

const mapChartRef = ref(null);
let chartInstance = null;
const resizeHandler = () => chartInstance?.resize();

const accessLogs = ref([]);
const wafLogs = ref([]);
const activeTab = ref('1');

const locationCoords = {
  '中国': [116.4551, 40.2539],
  'China': [116.4551, 40.2539],
  '美国': [-95.7129, 37.0902],
  'United States': [-95.7129, 37.0902],
  '俄罗斯': [55.7558, 37.6173],
  'Russia': [55.7558, 37.6173],
  '日本': [138.2529, 36.2046],
  'Japan': [138.2529, 36.2046],
  '韩国': [127.7669, 35.9078],
  'South Korea': [127.7669, 35.9078],
  '德国': [10.4515, 51.1657],
  'Germany': [10.4515, 51.1657],
  '法国': [2.2137, 46.2276],
  'France': [2.2137, 46.2276],
  '英国': [-3.4360, 55.3781],
  'United Kingdom': [-3.4360, 55.3781],
  '印度': [78.9629, 20.5937],
  'India': [78.9629, 20.5937],
  '巴西': [-51.9253, -14.2350],
  'Brazil': [-51.9253, -14.2350],
  '澳大利亚': [133.7751, -25.2744],
  'Australia': [133.7751, -25.2744],
  '加拿大': [-106.3468, 56.1304],
  'Canada': [-106.3468, 56.1304],
  '意大利': [12.5674, 41.8719],
  'Italy': [12.5674, 41.8719],
  '西班牙': [-3.7492, 40.4637],
  'Spain': [-3.7492, 40.4637],
  '荷兰': [4.9041, 52.3676],
  'Netherlands': [4.9041, 52.3676],
  '波兰': [19.1451, 51.9194],
  'Poland': [19.1451, 51.9194],
  '土耳其': [35.2433, 38.9637],
  'Turkey': [35.2433, 38.9637],
  '越南': [108.2772, 14.0583],
  'Vietnam': [108.2772, 14.0583],
  '泰国': [100.9925, 15.8700],
  'Thailand': [100.9925, 15.8700],
  '印度尼西亚': [113.9213, -0.7893],
  'Indonesia': [113.9213, -0.7893],
  '马来西亚': [101.9758, 4.2105],
  'Malaysia': [101.9758, 4.2105],
  '新加坡': [103.8198, 1.3521],
  'Singapore': [103.8198, 1.3521],
  '菲律宾': [121.7740, 12.8797],
  'Philippines': [121.7740, 12.8797],
  '巴基斯坦': [69.3451, 30.3753],
  'Pakistan': [69.3451, 30.3753],
  '孟加拉国': [90.3563, 23.6850],
  'Bangladesh': [90.3563, 23.6850],
  '埃及': [31.2357, 30.0444],
  'Egypt': [31.2357, 30.0444],
  '南非': [22.9375, -30.5595],
  'South Africa': [22.9375, -30.5595],
  '尼日利亚': [8.6753, 9.0820],
  'Nigeria': [8.6753, 9.0820],
  '肯尼亚': [37.9062, -0.0236],
  'Kenya': [37.9062, -0.0236],
  '阿根廷': [-63.6167, -38.4161],
  'Argentina': [-63.6167, -38.4161],
  '墨西哥': [-102.5528, 23.6345],
  'Mexico': [-102.5528, 23.6345],
  '智利': [-71.5430, -35.6751],
  'Chile': [-71.5430, -35.6751],
  '哥伦比亚': [-74.0721, 4.7110],
  'Colombia': [-74.0721, 4.7110],
  '秘鲁': [-75.0152, -9.1900],
  'Peru': [-75.0152, -9.1900],
  '委内瑞拉': [-66.5897, 6.4238],
  'Venezuela': [-66.5897, 6.4238],
  '乌克兰': [31.1656, 48.3794],
  'Ukraine': [31.1656, 48.3794],
  '瑞典': [18.6435, 60.1282],
  'Sweden': [18.6435, 60.1282],
  '挪威': [8.4689, 60.4720],
  'Norway': [8.4689, 60.4720],
  '芬兰': [25.7488, 61.9241],
  'Finland': [25.7488, 61.9241],
  '丹麦': [9.5018, 56.2639],
  'Denmark': [9.5018, 56.2639],
  '捷克': [15.4730, 49.8175],
  'Czech Republic': [15.4730, 49.8175],
  '奥地利': [14.5501, 47.5162],
  'Austria': [14.5501, 47.5162],
  '瑞士': [7.4474, 46.8182],
  'Switzerland': [7.4474, 46.8182],
  '比利时': [4.4699, 50.5039],
  'Belgium': [4.4699, 50.5039],
  '爱尔兰': [-8.2439, 53.4129],
  'Ireland': [-8.2439, 53.4129],
  '葡萄牙': [-8.2245, 39.3999],
  'Portugal': [-8.2245, 39.3999],
  '希腊': [21.8243, 39.0742],
  'Greece': [21.8243, 39.0742],
  '罗马尼亚': [24.9668, 45.9432],
  'Romania': [24.9668, 45.9432],
  '匈牙利': [19.5033, 47.1625],
  'Hungary': [19.5033, 47.1625],
  '保加利亚': [25.4858, 42.7339],
  'Bulgaria': [25.4858, 42.7339],
  '克罗地亚': [15.2000, 45.1000],
  'Croatia': [15.2000, 45.1000],
  '塞尔维亚': [21.0059, 44.0166],
  'Serbia': [21.0059, 44.0166],
  '斯洛伐克': [19.6960, 48.6690],
  'Slovakia': [19.6960, 48.6690],
  '斯洛文尼亚': [14.9955, 46.1512],
  'Slovenia': [14.9955, 46.1512],
  '立陶宛': [23.8813, 55.1694],
  'Lithuania': [23.8813, 55.1694],
  '拉脱维亚': [24.6032, 56.8796],
  'Latvia': [24.6032, 56.8796],
  '爱沙尼亚': [25.0136, 58.5953],
  'Estonia': [25.0136, 58.5953],
  '新西兰': [174.8860, -40.9006],
  'New Zealand': [174.8860, -40.9006],
  '以色列': [34.8516, 31.0461],
  'Israel': [34.8516, 31.0461],
  '阿联酋': [53.8478, 23.4241],
  'United Arab Emirates': [53.8478, 23.4241],
  '沙特阿拉伯': [45.0792, 23.8859],
  'Saudi Arabia': [45.0792, 23.8859],
  '伊拉克': [43.6793, 33.2232],
  'Iraq': [43.6793, 33.2232],
  '伊朗': [53.6880, 32.4279],
  'Iran': [53.6880, 32.4279],
  '台湾': [121.5200, 25.0192],
  'Taiwan': [121.5200, 25.0192],
  '香港': [114.1777, 22.3036],
  'Hong Kong': [114.1777, 22.3036],
  '澳门': [113.5497, 22.2009],
  'Macau': [113.5497, 22.2009],
  'Unknown': [0, 20]
};

const fetchLocationStats = async () => {
  try {
    const res = await getLocationStats();
    if (res) {
      accessLogs.value = res.access_logs || [];
      wafLogs.value = res.waf_logs || [];
      updateMapData();
    }
  } catch (error) {
    console.error('获取地点统计失败:', error);
  }
};

const getCurrentData = () => {
  return activeTab.value === '1' ? accessLogs.value : wafLogs.value;
};

const getMaxCount = (data) => {
  if (!data || data.length === 0) return 1;
  return Math.max(...data.map(item => item.count));
};

const updateMapData = () => {
  if (!chartInstance) return;
  const data = getCurrentData().filter(item =>
    item.location !== 'Unknown' && locationCoords[item.location]
  );
  const maxCount = getMaxCount(data);

  const scatterData = data.map(item => {
    const coords = locationCoords[item.location] || locationCoords['Unknown'];
    const ratio = maxCount > 1 ? item.count / maxCount : 0;
    const isBlock = activeTab.value === '2';
    const baseColor = isBlock ? [255, 77, 79] : [22, 93, 255];
    return {
      name: item.location,
      value: [...coords, item.count],
      itemStyle: {
        color: `rgba(${baseColor[0]}, ${baseColor[1]}, ${baseColor[2]}, ${0.3 + ratio * 0.7})`
      }
    };
  });

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        if (params.data && params.data.name) {
          return `${params.data.name}: ${params.data.value[2]}`;
        }
        return '';
      }
    },
    geo: {
      map: 'world',
      roam: false,
      emphasis: {
        itemStyle: { areaColor: '#165DFF' },
        label: { show: false }
      },
      itemStyle: {
        areaColor: '#e8f3ff',
        borderColor: '#94bfff'
      },
      left: '5%', right: '5%', top: '5%', bottom: '5%'
    },
    visualMap: {
      show: true,
      min: 0,
      max: maxCount,
      calculable: false,
      orient: 'vertical',
      right: '2%',
      top: 'center',
      inRange: {
        color: activeTab.value === '2' 
          ? ['rgba(255, 77, 79, 0.2)', 'rgba(255, 77, 79, 0.8)'] 
          : ['rgba(22, 93, 255, 0.2)', 'rgba(22, 93, 255, 0.8)']
      },
      textStyle: {
        color: '#fff'
      }
    },
    series: [{
      type: 'effectScatter',
      coordinateSystem: 'geo',
      data: scatterData,
      symbolSize: (val, params) => {
        const ratio = maxCount > 1 ? params.data.value[2] / maxCount : 0;
        return 10 + ratio * 25;
      },
      label: {
        show: false
      },
      emphasis: {
        scale: 1.5
      },
      rippleEffect: {
        brushType: 'stroke',
        scale: 3
      }
    }]
  };

  chartInstance.setOption(option, true);
};

watch(activeTab, () => {
  updateMapData();
});

const initChart = (retryCount = 0) => {
  const maxRetries = 5;

  if (!mapChartRef.value) {
    if (retryCount < maxRetries) {
      setTimeout(() => initChart(retryCount + 1), 200);
    }
    return;
  }

  const containerWidth = mapChartRef.value.clientWidth;
  const containerHeight = mapChartRef.value.clientHeight;

  if (containerWidth === 0 || containerHeight === 0) {
    if (retryCount < maxRetries) {
      setTimeout(() => initChart(retryCount + 1), 200);
    }
    return;
  }

  chartInstance = echarts.init(mapChartRef.value);
  updateMapData();
};

onMounted(() => {
  nextTick(() => {
    initChart();
    fetchLocationStats();
    window.addEventListener('resize', resizeHandler);
  });
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeHandler);
  chartInstance?.dispose();
});
</script>

<style scoped>
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

.main-content {
  display: flex;
  gap: 12px;
  height: 100%;
}

/* 地图区域 */
.map-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.header-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.header-controls h3 {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-1);
}

.card-content {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
  position: relative;
}

.map-container {
  width: 100%;
  height: 100%;
  min-height: 200px;
}

.info-card {
  width: 200px;
  min-width: 160px;
  background: var(--color-bg-2);
  border-radius: 6px;
  padding: 10px;
  display: flex;
  flex-direction: column;
}

.info-header {
  margin-bottom: 12px;
}

.info-header h3 {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-1);
}

.info-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 11px;
  color: var(--color-text-3);
}

.info-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-1);
}

.table-container {
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
  max-height: 350px;
}

.table-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 8px;
  background: var(--color-bg-1);
  border-radius: 4px;
  font-size: 12px;
}

.table-cell.region {
  color: var(--color-text-1);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table-cell.count {
  color: var(--color-text-2);
  font-weight: 500;
  text-align: right;
  min-width: 60px;
}

@media (max-width: 1200px) {
  .main-content {
    flex-direction: column;
  }
  .info-card {
    width: 100%;
    min-width: 100%;
    flex-direction: row;
    gap: 10px;
  }
  .map-container {
    min-height: 300px;
  }
  .table-container {
    max-height: 200px;
  }
}

@media (max-width: 768px) {
  .info-card {
    flex-direction: column;
  }
  .map-container {
    min-height: 250px;
  }
}
</style>
