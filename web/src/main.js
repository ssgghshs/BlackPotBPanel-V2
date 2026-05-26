import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ArcoVue from '@arco-design/web-vue';
import '@arco-design/web-vue/dist/arco.css';

// 引入全局语言状态管理
import { locale } from './utils/locale';
// 引入加载状态管理
import { startGlobalLoading, endGlobalLoading } from './utils/loading';

// 配置 Monaco Editor Web Worker
self.MonacoEnvironment = {
  // 处理 Web Worker 创建失败的情况
  getWorker: function (workerId, label) {
    // 创建一个虚拟的 Worker，避免 UI 阻塞
    const workerScript = `
      self.onmessage = function() {
        // 空操作，避免错误
      };
    `;
    const blob = new Blob([workerScript], { type: 'application/javascript' });
    return new Worker(URL.createObjectURL(blob));
  }
};


// 应用初始化时显示加载状态
startGlobalLoading()

// 在应用启动时设置主题
const savedTheme = localStorage.getItem('theme');
if (savedTheme === 'dark') {
  document.body.setAttribute('arco-theme', 'dark');
}

const app = createApp(App)
app.use(router)
app.use(ArcoVue, {
  // 使用响应式的语言设置
  locale
})

// 等待路由准备完成后挂载应用
router.isReady().then(() => {
  app.mount('#app')
  // 延迟关闭加载状态
  setTimeout(() => {
    endGlobalLoading()
  }, 1000) // 延迟关闭加载状态
})