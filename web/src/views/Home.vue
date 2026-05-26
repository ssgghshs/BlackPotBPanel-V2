<template>
  <div class="home-container">
    <div class="first-container">
      <nav class="horizontal-menu">
        <ul>
          <li><router-link to="/home">{{ t('dashboard') }}</router-link></li>
        </ul>
        <!-- 右侧功能区域 -->
        <div class="right-section">
          <!-- 面板资源占用 -->
          <PanelResource :title="t('panelResource')" />
          

          <!-- 语言切换图标按钮 -->
          <div class="language-switch">
            <a-dropdown @select="handleLanguageSelect">
              <a-button size="mini" type="text" class="language-button">
                <icon-language class="language-icon" />
              </a-button>
              <template #content>
                <a-doption value="zh-CN">简体中文</a-doption>
                <a-doption value="en-US">English</a-doption>
                <a-doption value="zh-TW">繁體中文</a-doption>
                <a-doption value="ja-JP">日本語</a-doption>
                <a-doption value="ko-KR">한국어</a-doption>
              </template>
            </a-dropdown>
          </div>
          
          <!-- 用户信息区域 -->
          <div class="user-info">
            <icon-user class="user-icon" />
            <span class="username">{{ username }}</span>
          </div>
        </div>
      </nav>
    </div>
    
    <div class="second-container" style="display: flex; gap: 16px;">
      <div style="flex: 7;">
        <!-- 资源监控(CPU使用率、内存使用率、硬盘使用率、负载) 四个圆盘再一排-->
        <SystemMonitor/>
      </div>
      <div style="flex: 3;">
        <!-- 主机信息 -->
        <HostInfo/>
      </div>
      <!-- 两个板块横向排列  7:3比例，资源监控为7，主机信息为3，注意板块区分 高度相同对齐-->
    </div>

    <div class="third-container" style="display: flex; gap: 16px;">
      <div style="flex: 1;">
        <!-- 网络流量监控 -->
        <NetworkTrafficMonitor/>
      </div>
      <div style="flex: 1;">
        <!-- 磁盘 I/O 监控 -->
        <DiskIOMonitor/>
      </div>
      <!-- 两个板块横向排列  5:5比例，网络流量监控为5，系统信息为3 注意板块区分，高度相同对齐-->
    </div>
  </div>

  <!-- 修改密码弹窗 -->
  <a-modal
    :visible="showChangePasswordModal"
    :title="t('changePassword')"
    @ok="handleChangePassword"
    @cancel="handleCancelChangePassword"
    :ok-text="t('confirm')"
    :cancel-text="t('cancel')"
    :maskClosable="false"
    :escToClose="false"
  >
    <a-form :model="passwordForm" :rules="passwordRules" ref="passwordFormRef" layout="vertical">
      <a-form-item field="newPassword" :label="t('newPassword')">
        <a-input-password
          v-model="passwordForm.newPassword"
          :placeholder="t('enterNewPassword')"
          size="large"
        />
      </a-form-item>
      <a-form-item field="confirmPassword" :label="t('confirmPassword')">
        <a-input-password
          v-model="passwordForm.confirmPassword"
          :placeholder="t('enterConfirmPassword')"
          size="large"
        />
      </a-form-item>
    </a-form>
  </a-modal>
  <!-- 页脚 -->
  <Footer/>
</template>

<script setup>
import { t,changeLocale } from '../utils/locale';
import { IconLanguage, IconUser } from '@arco-design/web-vue/es/icon';
import { Button, Message, Modal, Dropdown } from '@arco-design/web-vue';
import { ref, onMounted, reactive, computed, onBeforeUnmount } from 'vue';
import { getCurrentUser, changePassword } from '../api/user';
import { updateCommonSettings } from '../api/system';
import PanelResource from '../components/monitor/PanelResource.vue';
import Footer from '../components/Footer.vue'
import * as echarts from 'echarts5';
import SystemMonitor from '../components/monitor/SystemMonitor.vue'
import HostInfo from '../components/monitor/HostInfo.vue'
import NetworkTrafficMonitor from '../components/monitor/NetworkTrafficMonitor.vue'
import DiskIOMonitor from '../components/monitor/DiskIOMonitor.vue'

// 注册组件
const AButton = Button;

// 用户信息
const username = ref('');

// 资源监控数据
const cpuUsage = ref(45);
const memoryUsage = ref(60);
const diskUsage = ref(75);
const systemLoad = ref(2.5);

// 系统信息数据
const systemInfo = reactive({
  os: 'Ubuntu 20.04 LTS',
  kernel: '5.4.0-74-generic',
  uptime: '12 days, 5 hours, 32 minutes',
  hostname: 'server-01'
});

// 图表引用
const networkChartRef = ref();
let networkChart = null;

// 修改密码弹窗相关
const showChangePasswordModal = ref(false);
const passwordFormRef = ref();

const passwordForm = reactive({
  newPassword: '',
  confirmPassword: ''
});

const passwordRules = computed(() => ({
  newPassword: [
    { required: true, message: t.value('enterNewPassword') },
    { minLength: 6, message: t.value('passwordMinLength') }
  ],
  confirmPassword: [
    { required: true, message: t.value('enterConfirmPassword') },
    {
      validator: (value, cb) => {
        if (passwordForm.newPassword && value !== passwordForm.newPassword) {
          cb(t.value('passwordNotMatch'));
        } else {
          cb();
        }
      }
    }
  ]
}));

// 获取用户信息
const fetchUserInfo = async () => {
  try {
    const response = await getCurrentUser();
    console.log('用户信息响应:', response);

    // 安全地访问响应数据
    const userData = response?.data || response;
    username.value = userData?.username || userData?.name || 'User';
  } catch (error) {
    console.error('获取用户信息失败:', error);
    username.value = 'User';
  }
};

// 数据更新定时器
let dataUpdateTimer = null;
let isComponentMounted = true;

// 组件卸载前清理
onBeforeUnmount(() => {
  isComponentMounted = false;
  
  if (networkChart) {
    try {
      networkChart.dispose();
    } catch (e) {
      console.warn('图表销毁失败:', e);
    }
    networkChart = null;
  }
  
  if (dataUpdateTimer) {
    clearInterval(dataUpdateTimer);
    dataUpdateTimer = null;
  }
});

// 组件挂载时获取用户信息并检查是否需要显示修改密码弹窗
onMounted(() => {
  fetchUserInfo();

  // 初始化图表
  initCharts();

  // 启动定时器更新数据
  startDataUpdate();

  // 检查是否需要显示修改密码弹窗
  const isDefaultPassword = localStorage.getItem('isDefaultPassword');
  if (isDefaultPassword === 'true') {
    // 延迟显示弹窗，确保界面已完全加载
    setTimeout(() => {
      if (isComponentMounted) {
        showChangePasswordModal.value = true;
      }
    }, 500);
  }
});

// 初始化图表
const initCharts = () => {
  // 确保组件仍然挂载
  if (!isComponentMounted) {
    return;
  }
  
  if (networkChartRef.value) {
    networkChart = echarts.init(networkChartRef.value);
    updateNetworkChart();
  }
};

// 更新网络流量图表
const updateNetworkChart = () => {
  // 确保组件仍然挂载且图表实例存在
  if (!isComponentMounted || !networkChart) return;

  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: '{b}<br/>{a0}: {c0} KB/s<br/>{a1}: {c1} KB/s'
    },
    legend: {
      data: ['接收流量', '发送流量']
    },
    xAxis: {
      type: 'category',
      data: []
    },
    yAxis: {
      type: 'value',
      name: '流量 (KB/s)'
    },
    series: [
      {
        name: '接收流量',
        type: 'line',
        data: []
      },
      {
        name: '发送流量',
        type: 'line',
        data: []
      }
    ]
  };

  networkChart.setOption(option);
};

// 启动数据更新
const startDataUpdate = () => {
  dataUpdateTimer = setInterval(() => {
    // 确保组件仍然挂载
    if (!isComponentMounted) {
      return;
    }
    
    // 模拟更新数据
    cpuUsage.value = Math.floor(Math.random() * 100);
    memoryUsage.value = Math.floor(Math.random() * 100);
    diskUsage.value = Math.floor(Math.random() * 100);
    systemLoad.value = (Math.random() * 5).toFixed(2);

    // 更新图表
    updateNetworkChart();
  }, 5000); // 每5秒更新一次
};

// 停止数据更新
const stopDataUpdate = () => {
  if (dataUpdateTimer) {
    clearInterval(dataUpdateTimer);
    dataUpdateTimer = null;
  }
};

// 切换语言函数
const handleLanguageSelect = async (value) => {
  changeLocale(value);
  
  try {
    // 调用updateCommonSettings API更新语言设置
    await updateCommonSettings({ LANGUAGE: value });
    console.log('语言设置更新成功:', value);
  } catch (error) {
    console.error('更新语言设置失败:', error);
    // 语言更新失败不影响前端显示，因为我们已经在前端切换了语言
  }
};

// 修改密码处理函数
const handleChangePassword = async () => {
  // 先进行表单验证
  const errors = await passwordFormRef.value?.validate().catch(error => {
    // 表单验证失败，直接返回，不执行密码修改逻辑
    console.log('表单验证失败:', error);
    return false;
  });

  // 如果验证失败或者返回了错误，则不继续执行密码修改逻辑
  if (errors === false || (errors && Object.keys(errors).length > 0)) {
    return;
  }

  // 验证通过后执行密码修改逻辑
  try {
    await changePassword({
      current_password: 'admin@123', // 默认密码
      new_password: passwordForm.newPassword
    });

    Message.success(t.value('passwordChangeSuccess'));

    // 关闭弹窗
    showChangePasswordModal.value = false;

    // 清除标记
    localStorage.removeItem('isDefaultPassword');
  } catch (error) {
    console.error('修改密码失败:', error);
    const backendMessage = error.response?.data?.detail;
    if (backendMessage) {
      Message.error(t.value('passwordChangeFailed') + ': ' + backendMessage);
    } else {
      Message.error(t.value('passwordChangeFailed'));
    }
  }
};

// 取消修改密码处理函数
const handleCancelChangePassword = () => {
  Modal.confirm({
    title: t.value('cancelChangePassword'),
    content: t.value('cancelChangePasswordConfirm'),
    okText: t.value('confirm'),
    cancelText: t.value('cancel'),
    onOk: () => {
      showChangePasswordModal.value = false;
      // 清除标记
      localStorage.removeItem('isDefaultPassword');
    }
  });
};
</script>

<style scoped>
.home-container {
  padding: 5px 20px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* 主容器 */
.first-container {
  padding: 0;
}

.second-container {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
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

.two-container:first-child {
  flex: 7;
}

.two-container:last-child {
  flex: 3;
}

.third-container {
  display: flex;
  gap: 10px;
}

.three-container:first-child {
  flex: 1;
}

.three-container:last-child {
  flex: 1;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .home-container {
    padding: 5px 10px;
  }
  
  .second-container,
  .third-container {
    flex-direction: column;
    gap: 10px;
  }
  
  .second-container > div,
  .third-container > div {
    width: 100%;
  }
  
  .horizontal-menu ul {
    flex-wrap: wrap;
  }
  
  .right-section {
    position: static;
    margin-top: 5px;
  }
}
</style>

<!-- 使用非scoped样式来确保暗色主题样式能正确应用 -->
<style>
/* 水平菜单容器 */
.horizontal-menu {
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  padding: 6px 8px;
  margin-bottom: 20px;
  overflow: hidden;
  display: flex;
  align-items: center;
  border: 1px solid #ebebeb;
  position: relative;
}

/* 暗色主题下水平菜单容器 */
body[arco-theme="dark"] .horizontal-menu {
  background: #232324 !important;
  border: 1px solid #424244 !important;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3) !important;
}

.two-container {
  padding: 70px;
  margin-bottom: 20px; /* 添加底部边距 */
}

.three-container {
  padding: 70px;
  margin-bottom: 20px; /* 添加底部边距 */
}

.horizontal-menu ul {
  display: flex;
  list-style: none;
  padding: 0;
  margin: 0;
  gap: 12px;
}

.horizontal-menu li {
  margin: 0;
}

.horizontal-menu a {
  display: flex;
  align-items: center;
  text-decoration: none;
  color: #666;
  font-size: 14px;
  padding: 8px 12px;
  border-radius: 6px;
  transition: all 0.2s ease;
  position: relative;
  cursor: pointer;
}

/* 暗色主题下菜单项 */
body[arco-theme="dark"] .horizontal-menu a {
  color: #cccccc !important;
  background: transparent !important;
}

.horizontal-menu a::before {
  margin-right: 8px;
  font-size: 14px;
  display: inline-block;
}

/* 悬停状态 */
.horizontal-menu a:hover {
  background-color: #e8f4ff;
  color: #333;
}

/* 暗色主题下悬停状态 */
body[arco-theme="dark"] .horizontal-menu a:hover {
  background-color: #373739 !important;
  color: #ffffff !important;
}

/* 激活状态（选中项） */
.horizontal-menu a.router-link-active {
  background-color: var(--color-primary-light-1);
  color: rgb(var(--primary-6));
  font-weight: 500;
}

/* 暗色主题下激活状态 */
body[arco-theme="dark"] .horizontal-menu a.router-link-active {
  background-color: rgba(64, 132, 255, 0.2) !important;
  color: #3c7eff !important;
}

/* 激活状态下的下划线 */
.horizontal-menu a.router-link-active::after {
  content: "";
  position: absolute;
  left: 25%;
  bottom: 0;
  width: 50%;
  height: 2px;
  background-color: rgb(var(--primary-6));
  border-radius: 1px;
}

/* 适配不同路由路径的激活状态 */
.horizontal-menu a.router-link-active,
.horizontal-menu a.router-link-exact-active {
  background-color: var(--color-primary-light-1);
  color: rgb(var(--primary-6));
}

/* 暗色主题下激活状态 */
body[arco-theme="dark"] .horizontal-menu a.router-link-active,
body[arco-theme="dark"] .horizontal-menu a.router-link-exact-active {
  background-color: rgba(64, 132, 255, 0.2) !important;
  color: #3c7eff !important;
}

/* 右侧功能区域 */
.right-section {
  position: absolute;
  right: 10px;
  display: flex;
  align-items: center;
  gap: 15px;
}

/* 语言切换按钮 */
.language-switch {
  display: flex;
  align-items: center;
}

/* 暗色主题下语言切换按钮 */
body[arco-theme="dark"] .language-switch .arco-btn {
  color: #ffffff !important;
  background-color: transparent !important;
}

body[arco-theme="dark"] .language-switch .arco-btn:hover {
  background-color: #373739 !important;
}

/* 用户信息区域 */
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-icon {
  font-size: 20px;
  color: #666;
  transition: color 0.2s ease;
}

/* 暗色主题下用户图标 */
body[arco-theme="dark"] .user-icon {
  color: #cccccc !important;
}

.user-icon:hover {
  color: rgb(var(--primary-6));
}

.username {
  font-size: 14px;
  color: #333;
  font-weight: 500;
  white-space: nowrap;
}

/* 暗色主题下用户名 */
body[arco-theme="dark"] .username {
  color: #ffffff !important;
}

/* 语言切换按钮样式 */
.language-button {
  font-size: 24px !important;
}

/* 语言图标样式 */
.language-icon {
  font-size: 24px !important;
  width: 24px !important;
  height: 24px !important;
}

/* 暗色主题下卡片容器 */
body[arco-theme="dark"] .two-container,
body[arco-theme="dark"] .three-container {
  background-color: #232324 !important;
  border: 1px solid #424244 !important;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3) !important;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .home-container {
    padding: 5px 10px;
  }
  
  .second-container,
  .third-container {
    flex-direction: column;
    gap: 10px;
  }
  
  .second-container > div,
  .third-container > div {
    width: 100%;
  }
  
  .horizontal-menu {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .horizontal-menu ul {
    flex-wrap: wrap;
    width: 100%;
  }
  
  .right-section {
    position: static;
    margin-top: 5px;
    align-self: flex-end;
  }
  
  .two-container,
  .three-container {
    padding: 20px;
  }
}
</style>