<template>
  <a-card class="ansible-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('playbook') }}</span>
      </div>
    </template>

    <!--  内容区域  -->
    <div class="content-area">
      <!-- 1的为主机列表 - 占1/4宽度靠左 -->
      <div class="host-list-section">
        <a-table 
          :columns="columns" 
          :data="hostData" 
          :pagination="false" 
          :scroll="{ y: 600 }"
          :row-selection="rowSelection"
          v-model:selectedKeys="selectedRowKeys"
          row-key="id"
        >
          <template #actions="{ record }">
            <a-link >ping</a-link>
          </template>
        </a-table>
      </div>

      <!-- 2的为日志输出黑框 -->
      <div class="log-section">
        <!-- 日志输出区域 -->
      </div>
      
      <!--3的剧本列表 -->
      <div class="playbook-section">
        <!-- 剧本列表区域 -->
        <a-table 
          :columns="playbookColumns" 
          :data="playbookData" 
          :pagination="false" 
          :scroll="{ y: 600 }"
          row-key="id"
        >
          <template #actions="{ record }">
            <a-link >{{ t('execute') }}</a-link>
          </template>
        </a-table>
      </div>
    </div>

  </a-card>
</template>

<script setup>
import { reactive, ref, watch, onMounted } from 'vue';
import { t } from '../../utils/locale'
import { Table, Link } from '@arco-design/web-vue';
import { getHosts } from '../../api/host';



// 选中的行keys
const selectedRowKeys = ref([]);

// 选中的主机列表
const selectedHosts = ref([]);

// 表格行选择配置
const rowSelection = {
  type: 'checkbox',
  showCheckedAll: true,
  fixed: true
};

// 表格列定义
const columns = [
  {
    title: t.value('hostAddress'),
    dataIndex: 'address',
    width: 180,
    align: 'left'
  },
  {
    title: t.value('status'),
    dataIndex: 'status',
    width: 80,
    align: 'left'
  },
  {
    title: t.value('actions'),
    slotName: 'actions',
    width: 100,
    align: 'right'
  }
];

// 主机数据
const hostData = ref([]);

// 加载主机列表
const loadHosts = async () => {
  try {
    const response = await getHosts();
    console.log('API响应:', response); // 调试日志
    // 处理API响应，根据用户提供的API响应示例，响应直接是数组
    let hosts = [];
    if (Array.isArray(response)) {
      // 如果响应直接是数组（根据用户提供的API响应示例）
      hosts = response;
    } else if (response && Array.isArray(response.data)) {
      // 如果响应是对象，且data字段是数组
      hosts = response.data;
    }
    // 为每个主机添加status字段，默认值为online
    hostData.value = hosts.map(host => ({
      ...host,
      status: 'online' // 默认状态为online，可以根据实际需求调整
    }));
    console.log('主机列表:', hostData.value); // 调试日志
  } catch (error) {
    console.error('获取主机列表失败:', error);
    // 清空主机列表
    hostData.value = [];
  }
};

// 在组件挂载时加载主机列表
onMounted(async () => {
  await loadHosts();
});

// 更新选中的主机列表
const updateSelectedHosts = () => {
  selectedHosts.value = hostData.value.filter(host => 
    selectedRowKeys.value.includes(host.id)
  );
  console.log('Selected hosts:', selectedHosts.value);
};

// 监听选中状态变化，自动更新选中的主机列表
watch(selectedRowKeys, () => {
  updateSelectedHosts();
}, { deep: true });

// 选择主机的处理函数
const selectHost = (record) => {
  console.log('Selected host:', record);
};

// 剧本列表列定义
const playbookColumns = [
  {
    title: t.value('name'),
    dataIndex: 'name',
    width: 180,
    align: 'left'
  },
  {
    title: t.value('actions'),
    slotName: 'actions',
    width: 100,
    align: 'right'
  }
];

// 剧本列表数据
const playbookData = ref([
  { id: 1, name: 'playbook1.yml' },
  { id: 2, name: 'playbook2.yml'},
  { id: 3, name: 'playbook3.yml' }
]);
</script>

<style scoped>
.ansible-container {
  padding: 20px;
  height: calc(100vh - 120px);
  box-sizing: border-box;
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

.desc {
  margin-top: 4px;
  color: #8c8c8c;
  font-size: 12px;
}

/* 内容区域布局 */
.content-area {
  display: flex;
  gap: 10px;
  height: calc(100% - 80px);
  margin-top: 20px;
  align-items: flex-start;
}

/* 主机列表区域 - 占1/4宽度靠左 */
.host-list-section {
  width: 25%;
  height: 100%;
  background-color: var(--color-bg-2);
  border: 1px solid var(--color-border-2);
  border-radius: 4px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 日志输出区域 */
.log-section {
  flex: 2;
  height: 400px;
  background-color: #000000;
  border-radius: 4px;
  overflow: hidden;
}

/* 剧本列表区域 */
.playbook-section {
  width: 25%;
  height: 100%;
  background-color: var(--color-bg-2);
  border: 1px solid var(--color-border-2);
  border-radius: 4px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 表格样式调整 */
:deep(.arco-table) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

:deep(.arco-table-container) {
  flex: 1;
  overflow: auto;
}
</style>