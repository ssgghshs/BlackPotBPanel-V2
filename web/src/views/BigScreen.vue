<template>
  <div class="attack-screen" :style="getThemeStyle()">
    <div class="screen-header">
      <h1 class="title">{{ screenConfig.title}}</h1>
      <div class="header-right">
        <div class="time-display">{{ currentTime }}</div>
        <a-tabs type="card" size="small" @change="(key) => activeTab = key">
          <a-tab-pane key="1" :title="t('justAccess')"></a-tab-pane>
          <a-tab-pane key="2" :title="t('justBlock')"></a-tab-pane>
        </a-tabs>
        <button class="fullscreen-btn" @click="toggleFullscreen">
          <span class="fullscreen-icon">{{ isFullscreen ? '⛶' : '⛶' }}</span>
        </button>
      </div>
    </div>

    <div class="main-content">
      <div class="map-wrapper">
        <div class="map-section">
          <div ref="mapChartRef" class="map-container"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue';
import { useRouter } from 'vue-router';
import { t } from '../utils/locale';
import { getBigScreenConfig, getLocationStats } from '../api/waf';
import { Message } from '@arco-design/web-vue';

import * as echarts from 'echarts5';

const router = useRouter();

const mapChartRef = ref(null);
let chartInstance = null;
let mapDataCache = null;

const screenConfig = ref({
  title: '',
  theme: '',
  screen: true
});

const presetThemes = [
  { name: '深蓝科技', value: '#0a1929', colors: ['#0a1929', '#1a2a4a', '#0d1f3c'] },
  { name: '紫色幻彩', value: '#1a0a2e', colors: ['#1a0a2e', '#2d1b4e', '#1f0d3c'] },
  { name: '绿色生态', value: '#0a2e1a', colors: ['#0a2e1a', '#1a4a2e', '#0d3c1f'] },
  { name: '红色警戒', value: '#2e0a0a', colors: ['#2e0a0a', '#4a1a1a', '#3c0d0d'] },
  { name: '橙色活力', value: '#2e1a0a', colors: ['#2e1a0a', '#4a2e1a', '#3c1f0d'] },
  { name: '青色清新', value: '#0a2e2e', colors: ['#0a2e2e', '#1a4a4a', '#0d3c3c'] }
];

const currentTime = ref('');
let timeInterval = null;
const isFullscreen = ref(false);

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

const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen();
    isFullscreen.value = true;
  } else {
    document.exitFullscreen();
    isFullscreen.value = false;
  }
};

const handleFullscreenChange = () => {
  isFullscreen.value = !!document.fullscreenElement;
};

const fetchScreenConfig = async () => {
  try {
    const res = await getBigScreenConfig();
    if (res) {
      screenConfig.value = {
        title: res.title || '攻击监控大屏',
        theme: res.theme || '#0a1929',
        screen: res.screen !== false
      };
      if (!screenConfig.value.screen) {
        Message.warning('Screen is Disabled');
        setTimeout(() => {
          router.push('/');
        }, 1500);
      }
    }
  } catch (error) {
    console.error('获取大屏配置失败:', error);
  }
};

const getThemeStyle = () => {
  const theme = screenConfig.value.theme;
  const preset = presetThemes.find(p => p.value === theme);
  if (preset) {
    return {
      background: `linear-gradient(135deg, ${preset.colors[0]} 0%, ${preset.colors[1]} 50%, ${preset.colors[2]} 100%)`
    };
  }
  if (theme && theme.startsWith('#') && theme.length === 7) {
    const r = parseInt(theme.slice(1, 3), 16);
    const g = parseInt(theme.slice(3, 5), 16);
    const b = parseInt(theme.slice(5, 7), 16);
    const darker = `rgb(${Math.floor(r * 0.6)}, ${Math.floor(g * 0.6)}, ${Math.floor(b * 0.6)})`;
    return {
      background: `linear-gradient(135deg, ${theme} 0%, ${darker} 50%, ${theme} 100%)`
    };
  }
  return {
    background: 'linear-gradient(135deg, #0a1929 0%, #1a2a4a 50%, #0d1f3c 100%)'
  };
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
  chartInstance.hideLoading();
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
        areaColor: '#0a1929',
        borderColor: '#1d4a6e'
      },
      left: '2%', right: '2%', top: '5%', bottom: '2%'
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
    }, {
      name: '攻击目标',
      type: 'scatter',
      coordinateSystem: 'geo',
      data: [{ name: '目标服务器', value: [116.4, 39.9] }],
      symbol: 'circle',
      symbolSize: 20,
      itemStyle: {
        color: '#52c41a',
        shadowBlur: 20,
        shadowColor: '#52c41a'
      },
      label: {
        show: true,
        position: 'bottom',
        formatter: '{b}',
        color: '#52c41a',
        fontSize: 12
      }
    }]
  };

  chartInstance.setOption(option, true);
};

const updateTime = () => {
  const now = new Date();
  currentTime.value = now.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });
};

const fetchMapJson = async () => {
  if (mapDataCache) return mapDataCache;
  const module = await import('../utils/map/world.json');
  mapDataCache = module.default;
  echarts.registerMap('world', mapDataCache);
  return mapDataCache;
};

const renderMap = async () => {
  if (!chartInstance) return;
  chartInstance.showLoading({ text: '', textColor: '#fff', maskColor: 'rgba(0,0,0,0.1)' });

  await fetchMapJson();
  updateMapData();
};

const initChart = (retryCount = 0) => {
  const maxRetries = 20;

  if (!mapChartRef.value) {
    if (retryCount < maxRetries) {
      setTimeout(() => initChart(retryCount + 1), 100);
    }
    return;
  }

  const containerWidth = mapChartRef.value.clientWidth;
  const containerHeight = mapChartRef.value.clientHeight;

  if (containerWidth === 0 || containerHeight === 0) {
    if (retryCount < maxRetries) {
      setTimeout(() => initChart(retryCount + 1), 100);
    }
    return;
  }

  chartInstance = echarts.init(mapChartRef.value);
  renderMap();
};

watch(activeTab, () => {
  updateMapData();
});

onMounted(() => {
  nextTick(() => {
    fetchScreenConfig();
    initChart();
    fetchLocationStats();
    updateTime();
    timeInterval = setInterval(updateTime, 1000);
    document.addEventListener('fullscreenchange', handleFullscreenChange);
  });
});

onBeforeUnmount(() => {
  if (timeInterval) {
    clearInterval(timeInterval);
  }
  document.removeEventListener('fullscreenchange', handleFullscreenChange);
  chartInstance?.dispose();
});
</script>

<style scoped>
.attack-screen {
  width: 100%;
  height: 100vh;
  color: #fff;
  padding: 20px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow: hidden;
}

.screen-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-right :deep(.arco-tabs-card) {
  background: transparent;
}

.header-right :deep(.arco-tabs-card .arco-tabs-tab) {
  background: rgba(22, 93, 255, 0.2);
  border: 1px solid rgba(22, 93, 255, 0.3);
  color: #00d4ff;
  border-radius: 6px 6px 0 0;
}

.header-right :deep(.arco-tabs-card .arco-tabs-tab.arco-tabs-tab-active) {
  background: rgba(22, 93, 255, 0.4);
  border-color: rgba(22, 93, 255, 0.5);
  color: #fff;
}

.header-right :deep(.arco-tabs-card .arco-tabs-content) {
  display: none;
}

.title {
  font-size: 28px;
  font-weight: 700;
  margin: 0;
  background: linear-gradient(90deg, #00d4ff, #165DFF);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-shadow: 0 0 30px rgba(22, 93, 255, 0.5);
}

.time-display {
  font-size: 18px;
  color: #00d4ff;
  font-family: 'Monaco', 'Menlo', monospace;
}

.fullscreen-btn {
  width: 36px;
  height: 36px;
  border-radius: 6px;
  background: rgba(22, 93, 255, 0.2);
  border: 1px solid rgba(22, 93, 255, 0.3);
  color: #00d4ff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
}

.fullscreen-btn:hover {
  background: rgba(22, 93, 255, 0.4);
  border-color: rgba(22, 93, 255, 0.5);
}

.fullscreen-icon {
  font-size: 18px;
}

.stats-container {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.stat-card {
  background: rgba(22, 93, 255, 0.1);
  border: 1px solid rgba(22, 93, 255, 0.3);
  border-radius: 8px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  backdrop-filter: blur(10px);
}

.stat-icon {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.icon-text {
  font-size: 24px;
}

.attack-icon {
  background: linear-gradient(135deg, #ff4d4f, #ff7875);
}

.block-icon {
  background: linear-gradient(135deg, #1677ff, #4096ff);
}

.today-icon {
  background: linear-gradient(135deg, #722ed1, #b37feb);
}

.high-icon {
  background: linear-gradient(135deg, #fa8c16, #ffc53d);
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
}

.stat-label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
}

.main-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
}

.map-wrapper {
  width: 90%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.map-section {
  width: 100%;
  height: 100%;
  background: rgba(22, 93, 255, 0.05);
  border: 1px solid rgba(22, 93, 255, 0.2);
  border-radius: 8px;
  overflow: hidden;
}

.map-container {
  width: 100%;
  height: 100%;
}

.attack-list {
  flex: 1;
  background: rgba(22, 93, 255, 0.05);
  border: 1px solid rgba(22, 93, 255, 0.2);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid rgba(22, 93, 255, 0.2);
}

.list-header h3 {
  margin: 0;
  font-size: 16px;
  color: #fff;
}

.attack-table {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.table-header {
  display: grid;
  grid-template-columns: 80px 110px 80px 80px;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(22, 93, 255, 0.1);
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  font-weight: 500;
}

.table-body {
  flex: 1;
  overflow-y: auto;
}

.table-row {
  display: grid;
  grid-template-columns: 80px 110px 80px 80px;
  gap: 8px;
  padding: 10px 16px;
  font-size: 12px;
  border-bottom: 1px solid rgba(22, 93, 255, 0.1);
  transition: background 0.2s;
}

.table-row:hover {
  background: rgba(22, 93, 255, 0.1);
}

.col-time {
  color: rgba(255, 255, 255, 0.6);
}

.col-ip {
  color: #00d4ff;
  font-family: 'Monaco', monospace;
}

.col-location {
  color: #fff;
}

.col-type {
  display: flex;
  align-items: center;
}
</style>
