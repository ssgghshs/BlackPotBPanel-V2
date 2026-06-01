<template>
  <a-card class="waf-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('siteslist') }}</span>
        <div class="header-actions">
          <a-button type="outline" @click="openCreateModal">{{ t('createSite') }}</a-button>
          <a-button type="outline" @click="fetchSiteList">{{ t('refresh') }}</a-button>
        </div>
      </div>
    </template>

    <!-- 站点列表表格 -->
    <a-table 
      :columns="columns" 
      :data="siteList" 
      :loading="loading" 
      :pagination="pagination"
      @page-change="handlePageChange"
      @page-size-change="handlePageSizeChange"
      row-key="name"
    >
      <template #requests="{ record }">
        <div style="display: flex; gap: 8px; align-items: center; justify-content: center;">
          <a-tag color="green">{{ record.today_requests }}</a-tag>
          <span>/</span>
          <a-tag color="red">{{ record.today_blocks }}</a-tag>
        </div>
      </template>
      <template #type="{ record }">
        <a-tag :color="getTypeColor(record.type)">
          {{ record.type === 'Static Site' ? t('staticSite') : (record.type === 'PHP Site' ? t('phpSite') : t('reverseProxy')) }}
        </a-tag>
      </template>
      <template #waf_mode="{ record }">
        <a-select v-model="record.waf_mode" size="small" style="width: 120px" @change="handleWafModeChange(record)">
          <a-option value="block">{{ t('blockMode') }}</a-option>
          <a-option value="record">{{ t('recordMode') }}</a-option>
          <a-option value="Maintenance">{{ t('maintenanceMode') }}</a-option>
        </a-select>
      </template>
      <template #domain="{ record }">
        <span>{{ record.domain }}/{{ record.port }}</span>
      </template>
      <template #is_ssl="{ record }">
        <a-tag :color="record.is_ssl ? 'green' : 'orange'">
          {{ record.is_ssl ? t('yes') : t('no') }}
        </a-tag>
      </template>
      <template #bot_status="{ record }">
        <a-select v-model="record.bot_status" size="small" style="width: 140px" @change="handleBotStatusChange(record)">
          <a-option value="Disabled">{{ t('disabled') }}</a-option>
          <a-option value="Silent Verification">{{ t('silentVerification') }}</a-option>
          <a-option value="5s Verification">{{ t('5sVerification') }}</a-option>
          <a-option value="Slide Verification">{{ t('slideVerification') }}</a-option>
        </a-select>
      </template>
      <template #cc_status="{ record }">
        <a-switch v-model="record.cc_status" checked-value="Enabled" unchecked-value="Disabled" @change="handleCCStatusChange(record)" />
      </template>
      <template #operation="{ record }">
        <a-link type="text" size="small" @click="handleViewDetail(record)">{{ t('detail') }}</a-link>
        <a-link type="text" size="small" @click="handleViewLogs(record)">{{ t('log') }}</a-link>
        <a-link type="text" size="small" status="danger" @click="handleDeleteSite(record)">{{ t('delete') }}</a-link>
      </template>
    </a-table>

    <!-- 站点详情抽屉 -->
    <SiteDetail 
      v-model:visible="detailDrawerVisible"
      :site-info="selectedSite"
      @refresh="handleDetailRefresh"
    />

    <!-- 站点日志抽屉 -->
    <SiteLog 
      v-model:visible="logDrawerVisible"
      :site-name="selectedSite.name"
    />

    <!-- 确认对话框 -->
    <a-modal
      v-model:visible="confirmModalVisible"
      :title="confirmModalTitle"
      @ok="handleConfirm"
      @cancel="handleCancel"
    >
      <p>{{ confirmModalContent }}</p>
    </a-modal>

    <!-- 创建站点抽屉 -->
    <a-drawer
      v-model:visible="createModalVisible"
      :title="t('createSite')"
      width="600px"
      @close="handleCreateCancel"
      :footer="false"
    >
      <div class="drawer-content">
        <a-form :model="createForm" layout="vertical" ref="createFormRef">
          <a-form-item :label="t('siteName')" field="site_name" :rules="[{ required: true, message: t('fillRequiredFields') }]">
            <a-input v-model="createForm.site_name" :placeholder="t('enterSiteName')" />
          </a-form-item>
          <a-form-item :label="t('type')" required>
            <a-radio-group v-model="createForm.site_type" type="button">
              <a-radio value="Static Site">{{ t('staticSite') }}</a-radio>
              <a-radio value="PHP Site">{{ t('phpSite') }}</a-radio>
              <a-radio value="Reverse Proxy">{{ t('reverseProxy') }}</a-radio>
            </a-radio-group>
          </a-form-item>
          <a-form-item :label="t('domainName')" field="domain" :rules="[{ required: true, message: t('fillRequiredFields') }]">
            <a-input v-model="createForm.domain" :placeholder="t('enterDomain')" />
          </a-form-item>
          <a-form-item :label="t('port')" field="port" :rules="[{ required: true, message: t('fillRequiredFields') }]">
            <a-input v-model="createForm.port" :placeholder="t('enterPort')" />
          </a-form-item>
          <a-form-item v-if="createForm.site_type === 'Reverse Proxy'" :label="t('upstreamServer')" field="upstream_server" :rules="upstreamRules">
            <a-input v-model="createForm.upstream_server" :placeholder="t('enterUpstreamServer')" />
          </a-form-item>
          <a-form-item v-if="createForm.site_type === 'PHP Site'" :label="t('phpFpmHost')" field="php_fpm_host">
            <a-input v-model="createForm.php_fpm_host" :placeholder="t('enterPhpFpmHost')" />
          </a-form-item>
          <a-form-item :label="t('ssl')">
            <a-switch v-model="createForm.is_ssl" />
          </a-form-item>
          <a-form-item v-if="createForm.is_ssl" :label="t('sslCertificate')" field="ssl_cert_name" :rules="[{ required: true, message: t('fillSSLCertName') }]">
            <a-select v-model="createForm.ssl_cert_name" :placeholder="t('selectCertificate')" allow-search>
              <a-option v-for="cert in sslCertList" :key="cert.name" :value="cert.name">
                {{ cert.name }}
              </a-option>
            </a-select>
          </a-form-item>
          <a-form-item v-if="createForm.site_type === 'Static Site' || createForm.site_type === 'PHP Site'" :label="t('indexContent')">
            <a-textarea v-model="createForm.index_content" :placeholder="t('indexContentPlaceholder')" :rows="6" />
          </a-form-item>
          <div class="drawer-footer">
            <a-button @click="handleCreateCancel">{{ t('cancel') }}</a-button>
            <a-button type="primary" @click="handleCreateSite" :loading="createLoading">{{ t('confirm') }}</a-button>
          </div>
        </a-form>
      </div>
    </a-drawer>
  </a-card>
</template>

<script setup>
import { reactive, ref, computed, onMounted, watch } from 'vue';
import { t } from '../../utils/locale'
import { getSiteList, updateBasicSiteConfig, deleteSite, createSite, getSSLCertList } from '../../api/waf'
import { Message } from '@arco-design/web-vue';
import SiteDetail from '../../components/waf/SiteDetail.vue';
import SiteLog from '../../components/waf/SiteLog.vue';

// 响应式数据
const siteList = ref([]);
const loading = ref(false);
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showTotal: true,
  showJumper: true,
  pageSizeOptions: [10, 20, 50, 100],
  showPageSize: true
});

// 抽屉状态
const detailDrawerVisible = ref(false);
const logDrawerVisible = ref(false);
const selectedSite = ref({});

// 确认对话框状态
const confirmModalVisible = ref(false);
const confirmModalTitle = ref('');
const confirmModalContent = ref('');
const pendingUpdate = ref(null); // 存储待更新的操作

// 创建站点对话框状态
const createModalVisible = ref(false);
const createLoading = ref(false);
const createForm = ref({
  site_name: '',
  site_type: 'Static Site',
  domain: '',
  port: '',
  upstream_server: '',
  php_fpm_host: '',
  is_ssl: false,
  ssl_cert_name: '',
  index_content: ''
});
const sslCertList = ref([]);
const createFormRef = ref(null);

const upstreamRules = computed(() => [
  { required: true, message: t.value('fillUpstreamServer') },
  {
    validator: (value, callback) => {
      if (value && !/^https?:\/\/.+/.test(value)) {
        callback(t.value('invalidUpstreamServer'));
      } else {
        callback();
      }
    }
  }
]);

// 表格列定义
const columns = computed(() => [
  {
    title: t.value('siteName'),
    dataIndex: 'name',
    width: 120
  },
  {
    title: t.value('todayRequestsBlocks'),
    dataIndex: 'requests',
    slotName: 'requests',
    width: 150,
    align: 'center'
  },
  {
    title: t.value('type'),
    dataIndex: 'type',
    slotName: 'type',
    width: 120
  },
  {
    title: t.value('protectionMode'),
    dataIndex: 'waf_mode',
    slotName: 'waf_mode',
    width: 140
  },
  {
    title: t.value('domain'),
    dataIndex: 'domain',
    slotName: 'domain',
    width: 200
  },
  {
    title: t.value('ssl'),
    dataIndex: 'is_ssl',
    slotName: 'is_ssl',
    width: 100,
    align: 'center'
  },
  {
    title: t.value('botVerification'),
    dataIndex: 'bot_status',
    slotName: 'bot_status',
    width: 160
  },
  {
    title: t.value('ccProtection'),
    dataIndex: 'cc_status',
    slotName: 'cc_status',
    width: 100,
    align: 'center'
  },
  {      
    title: t.value('action'),      
    dataIndex: 'operation',      
    slotName: 'operation',      
    width: 150,      
    fixed: 'right'    }
]);

// 获取站点列表
const fetchSiteList = async (page = 1) => {
  try {
    loading.value = true;
    const response = await getSiteList();
    
    if (response && response.sites && Array.isArray(response.sites)) {
      siteList.value = response.sites;
      pagination.total = response.sites.length;
    } else {
      siteList.value = [];
      pagination.total = 0;
    }
  } catch (error) {
    console.error('获取站点列表失败:', error);
    Message.error(t.value('getSiteListFailed'));
    siteList.value = [];
    pagination.total = 0;
  } finally {
    loading.value = false;
  }
};

// 处理分页变化
const handlePageChange = (page) => {
  pagination.current = page;
};

// 处理分页大小变化
const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize;
  pagination.current = 1;
};

// 查看站点日志
const handleViewLogs = (site) => {
  selectedSite.value = site;
  logDrawerVisible.value = true;
};

// 查看站点详情
const handleViewDetail = (site) => {
  selectedSite.value = { ...site };
  detailDrawerVisible.value = true;
};

// 处理详情页刷新
const handleDetailRefresh = async () => {
  await fetchSiteList();
  // 更新当前选中的站点信息
  const updatedSite = siteList.value.find(site => site.name === selectedSite.value.name);
  if (updatedSite) {
    selectedSite.value = { ...updatedSite };
  }
};

// 处理防护模式变化
const handleWafModeChange = (record) => {
  confirmModalTitle.value = t.value('confirmUpdate');
  confirmModalContent.value = `${t.value('confirmUpdateWafMode')}`;
  pendingUpdate.value = {
    type: 'waf_mode',
    record: record
  };
  confirmModalVisible.value = true;
};

// 处理BOT验证变化
const handleBotStatusChange = (record) => {
  confirmModalTitle.value = t.value('confirmUpdate');
  confirmModalContent.value = `${t.value('confirmUpdateBotStatus')}`;
  pendingUpdate.value = {
    type: 'bot_status',
    record: record
  };
  confirmModalVisible.value = true;
};

// 处理CC保护变化
const handleCCStatusChange = (record) => {
  confirmModalTitle.value = t.value('confirmUpdate');
  confirmModalContent.value = `${t.value('confirmUpdateCcStatus')}`;
  pendingUpdate.value = {
    type: 'cc_status',
    record: record
  };
  confirmModalVisible.value = true;
};

// 处理确认
const handleConfirm = async () => {
  if (!pendingUpdate.value) return;
  
  const { type, record } = pendingUpdate.value;
  
  try {
    if (type === 'delete') {
      await deleteSite(record.name);
      Message.success(t.value('deleteSuccess'));
    } else if (type === 'waf_mode') {
      await updateBasicSiteConfig(record.name, {
        waf_mode: record.waf_mode
      });
    } else if (type === 'bot_status') {
      // 转换bot_status为bot_enabled和bot_verify_enabled
      let bot_enabled = 0;
      let bot_verify_enabled = 0;
      
      if (record.bot_status === 'Silent Verification') {
        bot_enabled = 1;
        bot_verify_enabled = 0;
      } else if (record.bot_status === '5s Verification') {
        bot_enabled = 1;
        bot_verify_enabled = 1;
      } else if (record.bot_status === 'Slide Verification') {
        bot_enabled = 1;
        bot_verify_enabled = 2;
      }
      
      await updateBasicSiteConfig(record.name, {
        bot_enabled,
        bot_verify_enabled
      });
    } else if (type === 'cc_status') {
      const cc_enabled = record.cc_status === 'Enabled' ? 1 : 0;
      await updateBasicSiteConfig(record.name, {
        cc_enabled
      });
    }
    
    Message.success(t.value('updateSuccess'));
    // 刷新站点列表
    await fetchSiteList();
  } catch (error) {
    console.error('更新失败:', error);
    Message.error(t.value('updateFailed'));
    // 恢复原始值
    fetchSiteList();
  } finally {
    confirmModalVisible.value = false;
    pendingUpdate.value = null;
  }
};

// 处理取消
const handleCancel = () => {
  // 恢复原始值
  fetchSiteList();
  confirmModalVisible.value = false;
  pendingUpdate.value = null;
};

// 处理删除站点
const handleDeleteSite = (record) => {
  confirmModalTitle.value = t.value('confirmDelete');
  confirmModalContent.value = `${t.value('confirmDeleteSite')}: ${record.name} (${record.type === 'Static Site' ? t.value('staticSite') : (record.type === 'PHP Site' ? t.value('phpSite') : t.value('reverseProxy'))})`;
  pendingUpdate.value = {
    type: 'delete',
    record: record
  };
  confirmModalVisible.value = true;
};

// 打开创建站点对话框
const openCreateModal = async () => {
  createForm.value = {
    site_name: '',
    site_type: 'Static Site',
    domain: '',
    port: '',
    upstream_server: '',
    php_fpm_host: '',
    is_ssl: false,
    ssl_cert_name: '',
    index_content: ''
  };
  try {
    const res = await getSSLCertList({ limit: 200 });
    sslCertList.value = res?.certs || [];
  } catch (e) {
    sslCertList.value = [];
  }
  createModalVisible.value = true;
};

// 处理创建站点
const handleCreateSite = async () => {
  const { site_name, site_type, domain, port, upstream_server, php_fpm_host, is_ssl, ssl_cert_name } = createForm.value;

  if (!site_name || !domain || !port) {
    Message.warning(t.value('fillRequiredFields'));
    return;
  }
  if (site_type === 'Reverse Proxy' && !upstream_server) {
    Message.warning(t.value('fillUpstreamServer'));
    return;
  }
  if (is_ssl && !ssl_cert_name) {
    Message.warning(t.value('fillSSLCertName'));
    return;
  }

  try {
    const errors = await createFormRef.value?.validate();
    if (errors) {
      Message.warning(t.value('fillRequiredFields'));
      return;
    }
  } catch {
    Message.warning(t.value('fillRequiredFields'));
    return;
  }

  createLoading.value = true;
  try {
    await createSite({
      site_name: createForm.value.site_name,
      site_type,
      domain: createForm.value.domain,
      port: createForm.value.port,
      upstream_server: upstream_server || '',
      php_fpm_host: php_fpm_host || '',
      is_ssl,
      ssl_cert_name: is_ssl ? ssl_cert_name : '',
      index_content: createForm.value.index_content || ''
    });
    Message.success(t.value('createSuccess'));
    createModalVisible.value = false;
    await fetchSiteList();
  } catch (error) {
    console.error('创建站点失败:', error);
    Message.error(t.value('createFailed'));
  } finally {
    createLoading.value = false;
  }
};

// 关闭创建站点对话框
const handleCreateCancel = () => {
  createModalVisible.value = false;
};

// 监听抽屉关闭，自动刷新列表
watch(detailDrawerVisible, (newVal, oldVal) => {
  if (oldVal === true && newVal === false) {
    fetchSiteList();
  }
});

watch(logDrawerVisible, (newVal, oldVal) => {
  if (oldVal === true && newVal === false) {
    fetchSiteList();
  }
});

// 获取类型标签颜色
const getTypeColor = (type) => {
  if (type === 'Static Site') return 'blue';
  if (type === 'PHP Site') return 'arcoblue';
  return 'purple';
};

// 组件挂载时获取数据
onMounted(() => {
  fetchSiteList();
});
</script>

<style scoped>
.waf-container {
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 15px;
  font-size: 1.3em;
  padding: 20px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.title {
  margin: 0;
  padding: 0;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.desc {
  margin-top: 4px;
  color: #8c8c8c;
  font-size: 12px;
}

.drawer-content {
  padding: 20px;
}

.drawer-footer {
  margin-top: 30px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
