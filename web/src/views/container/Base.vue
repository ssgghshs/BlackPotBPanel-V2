<template>
  <div class="container-container">
    <div v-if="checking" class="docker-checking">
      <a-spin :tip="t('loading')" />
    </div>

    <template v-else>
      <nav class="horizontal-menu">
        <ul>
          <li v-for="item in menuItems" :key="item.to">
            <router-link v-if="dockerReady" :to="item.to">{{ item.label }}</router-link>
            <a v-else class="menu-link-disabled">{{ item.label }}</a>
          </li>
        </ul>
        <div class="host-selector">
          <span class="host-label">{{ t('containerHost') }}:</span>
          <AButton
            size="small"
            :loading="isRefreshing"
            @click="refreshContainerHosts"
            :style="{ marginRight: '8px' }"
            title="刷新宿主列表"
          >
            <ReloadOutlined />
          </AButton>
          <ASelect 
            v-model="selectedHost" 
            @change="onHostChange" 
            placeholder="请选择容器宿主"
            :style="{ minWidth: '150px' }"
          >
            <AOption v-for="host in containerHosts" :key="host.id" :value="host.id">
              {{ host.name }} 
            </AOption>
          </ASelect>
        </div>
      </nav>

      <router-view v-if="dockerReady" />

      <div v-else class="docker-stopped-hint">
        <a-result :status="dockerHint.status" :title="dockerHint.title">
          <template #subtitle>
            {{ dockerHint.subtitle }}
          </template>
          <template #extra>
            <a-button type="primary" @click="checkDockerStatus">{{ t('refresh') }}</a-button>
          </template>
        </a-result>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { t } from '../../utils/locale';
import { useRouter } from 'vue-router';
import { getContainerNodes, checkLocalDockerStatus } from '../../api/container';
import { Select as ASelect, Option as AOption, Button as AButton } from '@arco-design/web-vue';
import { ReloadOutlined } from '@ant-design/icons-vue';

const checking = ref(true);
const dockerReady = ref(false);
const dockerHint = ref({ status: 'warning', title: '', subtitle: '' });

const menuItems = computed(() => [
  { to: '/container/overview', label: t.value('overview') },
  { to: '/container/containers', label: t.value('containers') },
  { to: '/container/images', label: t.value('images') },
  { to: '/container/networks', label: t.value('networks') },
  { to: '/container/volumes', label: t.value('volumes') },
  { to: '/container/compose', label: t.value('compose') },
  { to: '/container/containerHost', label: t.value('containerHost') },
]);

const checkDockerStatus = async () => {
  checking.value = true;
  try {
    const res = await checkLocalDockerStatus();
    if (res.installed && res.running) {
      dockerReady.value = true;
    } else if (!res.installed) {
      dockerReady.value = false;
      dockerHint.value = {
        status: 'error',
        title: t.value('dockerNotInstalled'),
        subtitle: t.value('dockerNotInstalledHint'),
      };
    } else if (!res.running) {
      dockerReady.value = false;
      dockerHint.value = {
        status: 'warning',
        title: t.value('dockerNotRunning'),
        subtitle: t.value('dockerNotRunningHint'),
      };
    }
  } catch {
    dockerReady.value = false;
    dockerHint.value = {
      status: 'error',
      title: t.value('dockerNotInstalled'),
      subtitle: t.value('dockerNotInstalledHint'),
    };
  } finally {
    checking.value = false;
  }
};

// 容器宿主列表数据
const containerHosts = ref([]);
const selectedHost = ref(null);
const router = useRouter();
const isRefreshing = ref(false); // 添加刷新状态标识

// 刷新容器宿主列表的函数
const refreshContainerHosts = async () => {
  try {
    isRefreshing.value = true;
    const response = await getContainerNodes();
    // 根据后端API返回的DockerNodeList格式，正确获取节点数组
    containerHosts.value = response.items || [];
    
    // 如果有宿主数据，确保选中的宿主ID仍然有效
    if (containerHosts.value.length > 0) {
      // 检查当前选中的宿主ID是否在新列表中
      const currentSelectedHost = containerHosts.value.find(host => host.id === selectedHost.value);
      
      if (!currentSelectedHost) {
        // 如果当前选中的宿主不存在于新列表中，则选择第一个或从localStorage恢复
        const savedHostId = localStorage.getItem('selectedContainerHostId');
        const savedHost = savedHostId ? containerHosts.value.find(host => host.id.toString() === savedHostId) : null;
        
        if (savedHost) {
          selectedHost.value = savedHost.id;
        } else {
          selectedHost.value = containerHosts.value[0].id;
          localStorage.setItem('selectedContainerHostId', selectedHost.value);
        }
        
        // 当重新选择宿主时，触发事件通知子组件
        emitHostChange(selectedHost.value);
      }
    } else {
      // 如果没有宿主数据，清除选择
      selectedHost.value = '';
      localStorage.removeItem('selectedContainerHostId');
    }
  } catch (error) {
    console.error('刷新容器宿主列表失败:', error);
  } finally {
    isRefreshing.value = false;
  }
};

// 初始化时从API获取容器宿主列表并默认选择第一个
onMounted(async () => {
  await checkDockerStatus();
  if (dockerReady.value) {
    refreshContainerHosts();
  }
});

// 发出宿主变化事件
const emitHostChange = (hostId) => {
  // 使用自定义事件通知子组件
  window.dispatchEvent(new CustomEvent('containerHostChanged', {
    detail: { hostId: hostId }
  }));
  
  console.log('宿主变化事件已发出:', hostId);
};

// 处理宿主切换事件
const onHostChange = () => {
  // 保存当前选中的宿主ID到localStorage
  localStorage.setItem('selectedContainerHostId', selectedHost.value);
  
  // 通知其他组件宿主已更改
  emitHostChange(selectedHost.value);
  
  // 根据需要刷新当前页面的数据
  const currentPath = router.currentRoute.value.path;
  if (currentPath.includes('/container/')) {
    router.go(0); // 简单的刷新方式，实际应用中可能需要更优雅的方式
  }
};
</script>

<style scoped> 
.container-container {
  padding: 5px 20px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.docker-checking {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

.docker-stopped-hint {
  padding: 60px 20px;
  text-align: center;
}

/* 容器宿主选择器样式 */
.host-selector {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 刷新按钮在暗色主题下的样式 */
body[arco-theme="dark"] .host-selector .arco-btn {
  background-color: #373739 !important;
  border-color: #424244 !important;
  color: #cccccc !important;
}

body[arco-theme="dark"] .host-selector .arco-btn:hover {
  background-color: #424244 !important;
  border-color: #4e4e50 !important;
}

.host-label {
  font-size: 14px;
  color: #666;
  white-space: nowrap;
}
</style>

<!-- 使用非scoped样式确保在所有主题下保持一致 -->
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
}

/* 暗色主题下水平菜单容器 */
body[arco-theme="dark"] .horizontal-menu {
  background: #232324 !important;
  border: 1px solid #424244 !important;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3) !important;
}

/* 暗色主题下宿主选择器标签 */
body[arco-theme="dark"] .host-label {
  color: #cccccc !important;
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

.menu-link-disabled {
  color: #ccc !important;
  cursor: not-allowed !important;
}

body[arco-theme="dark"] .menu-link-disabled {
  color: #555 !important;
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
</style>