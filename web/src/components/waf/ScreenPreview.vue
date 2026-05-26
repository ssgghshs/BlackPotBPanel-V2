<template>
  <div class="screen-preview" :style="getThemeStyle()">
    <div class="preview-header-row">
      <h1 class="preview-title">{{ title }}</h1>
    </div>

    <div class="preview-main-content">
      <div class="preview-map-wrapper">
        <div class="preview-map-section">
          <div ref="mapChartRef" class="preview-map-container"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { t } from '../../utils/locale';
import * as echarts from 'echarts5';

const props = defineProps({
  title: {
    type: String,
    default: '攻击监控大屏'
  },
  theme: {
    type: String,
    default: '#0a1929'
  }
});

const presetThemes = [
  { name: '深蓝科技', value: '#0a1929', colors: ['#0a1929', '#1a2a4a', '#0d1f3c'] },
  { name: '紫色幻彩', value: '#1a0a2e', colors: ['#1a0a2e', '#2d1b4e', '#1f0d3c'] },
  { name: '绿色生态', value: '#0a2e1a', colors: ['#0a2e1a', '#1a4a2e', '#0d3c1f'] },
  { name: '红色警戒', value: '#2e0a0a', colors: ['#2e0a0a', '#4a1a1a', '#3c0d0d'] },
  { name: '橙色活力', value: '#2e1a0a', colors: ['#2e1a0a', '#4a2e1a', '#3c1f0d'] },
  { name: '青色清新', value: '#0a2e2e', colors: ['#0a2e2e', '#1a4a4a', '#0d3c3c'] }
];

const mapChartRef = ref(null);
let chartInstance = null;
let mapDataCache = null;

const stats = ref({
  totalAttacks: 128956,
  blockedIPs: 8423,
  todayAttacks: 2341,
  highLevelThreats: 127
});

const attackLogs = ref([
  { id: 1, time: '12:34:56', ip: '192.168.1.1', location: '北京', type: 'SQL注入' },
  { id: 2, time: '12:34:55', ip: '10.0.2.15', location: '上海', type: 'XSS攻击' },
  { id: 3, time: '12:34:54', ip: '172.16.0.5', location: '深圳', type: 'CC攻击' },
  { id: 4, time: '12:34:53', ip: '8.8.8.8', location: '美国', type: 'DDoS攻击' },
  { id: 5, time: '12:34:52', ip: '1.1.1.1', location: '澳大利亚', type: '暴力破解' },
  { id: 6, time: '12:34:51', ip: '2.2.2.2', location: '德国', type: 'SQL注入' }
]);

const getAttackTypeColor = (type) => {
  const colorMap = {
    'SQL注入': 'red',
    'XSS攻击': 'orange',
    'CC攻击': 'purple',
    'DDoS攻击': 'magenta',
    '暴力破解': 'cyan',
    '扫描探测': 'blue'
  };
  return colorMap[type] || 'gray';
};

const getThemeStyle = () => {
  const theme = props.theme;
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

const fetchMapJson = async () => {
  if (mapDataCache) return mapDataCache;
  try {
    const module = await import('../../utils/map/world.json');
    mapDataCache = module.default;
    echarts.registerMap('world', mapDataCache);
    return mapDataCache;
  } catch (e) {
    console.error('Failed to load map:', e);
    return null;
  }
};

const generateAttackPoints = () => {
  const points = [];
  const locations = [
    { name: '北京', coord: [116.4, 39.9] },
    { name: '上海', coord: [121.4, 31.2] },
    { name: '美国', coord: [-100, 40] },
    { name: '俄罗斯', coord: [90, 60] },
    { name: '德国', coord: [10, 51] },
    { name: '日本', coord: [138, 36] },
    { name: '韩国', coord: [128, 36] },
    { name: '澳大利亚', coord: [133, -27] }
  ];

  for (let i = 0; i < 30; i++) {
    const loc = locations[Math.floor(Math.random() * locations.length)];
    points.push({
      name: loc.name,
      value: [
        loc.coord[0] + (Math.random() - 0.5) * 20,
        loc.coord[1] + (Math.random() - 0.5) * 10
      ]
    });
  }
  return points;
};

const renderMap = async () => {
  if (!chartInstance) return;
  chartInstance.showLoading({ text: '', textColor: '#fff', maskColor: 'rgba(0,0,0,0.1)' });

  const mapData = await fetchMapJson();
  if (!mapData) return;

  const points = generateAttackPoints();

  const option = {
    backgroundColor: 'transparent',
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
      left: '2%', right: '2%', top: '5%', bottom: '2%',
      regions: [
        { name: 'China', itemStyle: { areaColor: '#165DFF', borderColor: '#4080ff' } }
      ]
    },
    series: [
      {
        name: '攻击来源',
        type: 'effectScatter',
        coordinateSystem: 'geo',
        data: points.slice(0, 15),
        symbolSize: function (val) {
          return Math.random() * 10 + 5;
        },
        showEffectOn: 'render',
        rippleEffect: {
          brushType: 'stroke',
          scale: 3
        },
        itemStyle: {
          color: '#ff4d4f',
          shadowBlur: 10,
          shadowColor: '#ff4d4f'
        }
      },
      {
        name: '攻击目标',
        type: 'scatter',
        coordinateSystem: 'geo',
        data: [{ name: '目标服务器', value: [116.4, 39.9] }],
        symbol: 'circle',
        symbolSize: 15,
        itemStyle: {
          color: '#52c41a',
          shadowBlur: 15,
          shadowColor: '#52c41a'
        },
        label: {
          show: true,
          position: 'bottom',
          formatter: '{b}',
          color: '#52c41a',
          fontSize: 10
        }
      }
    ]
  };

  chartInstance.setOption(option, true);
  chartInstance.hideLoading();
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

  if (chartInstance) {
    chartInstance.dispose();
  }

  chartInstance = echarts.init(mapChartRef.value);
  renderMap();
};

watch(() => props.theme, () => {
  nextTick(() => {
    if (chartInstance) {
      renderMap();
    }
  });
});

onMounted(() => {
  nextTick(() => {
    initChart();
  });
});

onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.dispose();
    chartInstance = null;
  }
});
</script>

<style scoped>
.screen-preview {
  padding: 20px;
  height: 100%;
  color: #fff;
  display: flex;
  flex-direction: column;
  gap: 20px;
  box-sizing: border-box;
}

.preview-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-title {
  font-size: 28px;
  font-weight: 700;
  margin: 0;
  background: linear-gradient(90deg, #00d4ff, #165DFF);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-shadow: 0 0 30px rgba(22, 93, 255, 0.5);
}

.preview-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.preview-stat-card {
  background: rgba(22, 93, 255, 0.1);
  border: 1px solid rgba(22, 93, 255, 0.3);
  border-radius: 8px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  backdrop-filter: blur(10px);
}

.preview-stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
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

.preview-stat-info {
  display: flex;
  flex-direction: column;
}

.preview-stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
}

.preview-stat-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.preview-main-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
  height: calc(100% - 60px);
}

.preview-map-wrapper {
  width: 90%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-map-section {
  width: 100%;
  height: 100%;
  background: rgba(22, 93, 255, 0.05);
  border: 1px solid rgba(22, 93, 255, 0.2);
  border-radius: 8px;
  overflow: hidden;
}

.preview-map-container {
  width: 100%;
  height: 100%;
  min-height: 280px;
}

.preview-attack-list {
  flex: 1;
  background: rgba(22, 93, 255, 0.05);
  border: 1px solid rgba(22, 93, 255, 0.2);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.preview-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(22, 93, 255, 0.2);
}

.preview-list-header h3 {
  margin: 0;
  font-size: 14px;
  color: #fff;
}

.preview-attack-table {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.preview-table-header {
  display: grid;
  grid-template-columns: 60px 90px 60px 70px;
  gap: 8px;
  padding: 10px 12px;
  background: rgba(22, 93, 255, 0.1);
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
  font-weight: 500;
}

.preview-table-body {
  flex: 1;
  overflow-y: auto;
}

.preview-table-row {
  display: grid;
  grid-template-columns: 60px 90px 60px 70px;
  gap: 8px;
  padding: 8px 12px;
  font-size: 11px;
  border-bottom: 1px solid rgba(22, 93, 255, 0.1);
  transition: background 0.2s;
}

.preview-table-row:hover {
  background: rgba(22, 93, 255, 0.1);
}

.col-time {
  color: rgba(255, 255, 255, 0.6);
}

.col-ip {
  color: #00d4ff;
  font-family: 'Monaco', 'Menlo', monospace;
}

.col-location {
  color: #fff;
}

.col-type {
  display: flex;
  align-items: center;
}
</style>
