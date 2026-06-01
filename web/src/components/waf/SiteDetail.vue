<template>
  <a-drawer
    :visible="visible"
    @update:visible="(value) => emit('update:visible', value)"
    :title="t('siteDetail')"
    :width="isMobile ? '100%' : '1000px'"
    :footer="false"
  >
    <div class="site-detail" >
      <a-tabs default-active-key="1"  position="left">
        <a-tab-pane key="1" :title="t('basicInfo')">
          <div class="card-grid">
            <a-card hoverable>
              <div 
                :style="{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between', 
                }" 
              > 
                <span 
                  :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }"
                >
                  <a-typography-text>{{ t('protectionMode') }}</a-typography-text> 
                </span> 
                <a-select v-model="localSiteInfo.waf_mode" size="small" style="width: 120px" @change="handleWafModeChange"> 
                  <a-option value="block">{{ t('blockMode') }}</a-option> 
                  <a-option value="record">{{ t('recordMode') }}</a-option> 
                  <a-option value="Maintenance">{{ t('maintenanceMode') }}</a-option> 
                </a-select> 
              </div>
            </a-card>
                        <a-card hoverable>
              <div 
                :style="{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between', 
                }" 
              > 
                <span 
                  :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }"
                >
                  <a-typography-text>{{ t('botVerification') }}</a-typography-text> 
                </span> 
                <a-select v-model="localSiteInfo.bot_status" size="small" style="width: 140px" @change="handleBotStatusChange"> 
                  <a-option value="Disabled">{{ t('disabled') }}</a-option> 
                  <a-option value="Silent Verification">{{ t('silentVerification') }}</a-option> 
                  <a-option value="5s Verification">{{ t('5sVerification') }}</a-option> 
                  <a-option value="Slide Verification">{{ t('slideVerification') }}</a-option> 
                </a-select> 
              </div>
            </a-card>
            <a-card :title="t('domainName')">
              <template #extra>
                <a-button size="small" type="outline" @click="handleEditDomain">{{ t('config') }}</a-button>
              </template>
              {{ localSiteInfo.domain || '-' }}
            </a-card>
            <a-card :title="t('port')">
              <template #extra>
                <a-button size="small" type="outline" @click="handleEditPort">{{ t('config') }}</a-button>
              </template>
              {{ localSiteInfo.port || '-' }}
            </a-card>
            <a-card :title="t('ssl')">
              <template #extra>
                <a-button size="small" type="outline" @click="handleEditSSL">{{ t('config') }}</a-button>
              </template>
              <div>
                <a-tag :color="localSiteInfo.is_ssl ? 'green' : 'orange'">{{ localSiteInfo.is_ssl ? t('deployed') : t('notDeployed') }}</a-tag>
                <span v-if="localSiteInfo.is_ssl && localSiteInfo.ssl_cert_name" style="margin-left: 8px; color: #1D2129;">
                  {{ localSiteInfo.ssl_cert_name }}
                </span>
              </div>
            </a-card>
            <a-card hoverable>
              <div 
                :style="{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between', 
                }" 
              > 
                <span 
                  :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }"
                >
                  <a-typography-text>{{ t('ccProtection') }}</a-typography-text> 
                </span> 
                <a-switch v-model="localSiteInfo.cc_status" checked-value="Enabled" unchecked-value="Disabled" @change="handleCCStatusChange" />
              </div>
            </a-card>
            <a-card v-if="localSiteInfo.type === 'Reverse Proxy'" :title="t('upstreamServer')"> 
              <template #extra>
                <a-button size="small" type="outline" @click="handleEditUpstream">{{ t('config') }}</a-button>
              </template>
              {{ localSiteInfo.upstream_server || '-' }}
            </a-card>
            <a-card v-if="localSiteInfo.type === 'Static Site' || localSiteInfo.type === 'PHP Site'" :title="t('staticFilePath')"> 
              {{ localSiteInfo.upstream_server || '-' }}
            </a-card>
            <a-card v-if="localSiteInfo.type === 'PHP Site'" :title="t('phpFpmHost')"> 
              <template #extra>
                <a-button size="small" type="outline" @click="handleEditPhpFpm">{{ t('config') }}</a-button>
              </template>
              {{ localSiteInfo.php_fpm_host || '-' }}
            </a-card>

          </div>
        </a-tab-pane>
        <a-tab-pane key="2" :title="t('vulnerabilityProtection')">
          <div class="card-grid">
            <a-card hoverable>
              <div 
                :style="{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between', 
                }" 
              > 
                <span 
                  :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }"
                >
                  <a-typography-text>{{ t('sqlInjection') }}</a-typography-text> 
                </span> 
                <a-switch v-model="localSiteInfo.protection_status.sql_injection" checked-value="Enabled" unchecked-value="Disabled" @change="handleProtectionChange('sql_injection', localSiteInfo.protection_status?.sql_injection)" />
              </div>
            </a-card>
            <a-card hoverable>
              <div 
                :style="{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between', 
                }" 
              > 
                <span 
                  :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }"
                >
                  <a-typography-text>XSS</a-typography-text> 
                </span> 
                <a-switch v-model="localSiteInfo.protection_status.xss" checked-value="Enabled" unchecked-value="Disabled" @change="handleProtectionChange('xss', localSiteInfo.protection_status?.xss)" />
              </div>
            </a-card>
            <a-card hoverable>
              <div 
                :style="{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between', 
                }" 
              > 
                <span 
                  :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }"
                >
                  <a-typography-text>{{ t('commandInjection') }}</a-typography-text> 
                </span> 
                <a-switch v-model="localSiteInfo.protection_status.command_injection" checked-value="Enabled" unchecked-value="Disabled" @change="handleProtectionChange('command_injection', localSiteInfo.protection_status?.command_injection)" />
              </div>
            </a-card>
            <a-card hoverable>
              <div 
                :style="{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between', 
                }" 
              > 
                <span 
                  :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }"
                >
                  <a-typography-text>SSRF</a-typography-text> 
                </span> 
                <a-switch v-model="localSiteInfo.protection_status.ssrf" checked-value="Enabled" unchecked-value="Disabled" @change="handleProtectionChange('ssrf', localSiteInfo.protection_status?.ssrf)" />
              </div>
            </a-card>
            <a-card hoverable>
              <div 
                :style="{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between', 
                }" 
              > 
                <span 
                  :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }"
                >
                  <a-typography-text>{{ t('ldapInjection') }}</a-typography-text> 
                </span> 
                <a-switch v-model="localSiteInfo.protection_status.ldap_injection" checked-value="Enabled" unchecked-value="Disabled" @change="handleProtectionChange('ldap_injection', localSiteInfo.protection_status?.ldap_injection)" />
              </div>
            </a-card>
            <a-card hoverable>
              <div 
                :style="{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between', 
                }" 
              > 
                <span 
                  :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }"
                >
                  <a-typography-text>CSRF</a-typography-text> 
                </span> 
                <a-switch v-model="localSiteInfo.protection_status.csrf" checked-value="Enabled" unchecked-value="Disabled" @change="handleProtectionChange('csrf', localSiteInfo.protection_status?.csrf)" />
              </div>
            </a-card>
            <a-card hoverable>
              <div 
                :style="{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between', 
                }" 
              > 
                <span 
                  :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }"
                >
                  <a-typography-text>{{ t('fileInclusion') }}</a-typography-text> 
                </span> 
                <a-switch v-model="localSiteInfo.protection_status.file_inclusion" checked-value="Enabled" unchecked-value="Disabled" @change="handleProtectionChange('file_inclusion', localSiteInfo.protection_status?.file_inclusion)" />
              </div>
            </a-card>
            <a-card hoverable>
              <div 
                :style="{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between', 
                }" 
              > 
                <span 
                  :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }"
                >
                  <a-typography-text>{{ t('fileUpload') }}</a-typography-text> 
                </span> 
                <a-switch v-model="localSiteInfo.protection_status.file_upload" checked-value="Enabled" unchecked-value="Disabled" @change="handleProtectionChange('file_upload', localSiteInfo.protection_status?.file_upload)" />
              </div>
            </a-card>
            <a-card hoverable>
              <div 
                :style="{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between', 
                }" 
              > 
                <span 
                  :style="{ display: 'flex', alignItems: 'center', color: '#1D2129' }"
                >
                  <a-typography-text>{{ t('scanner') }}</a-typography-text> 
                </span> 
                <a-switch v-model="localSiteInfo.protection_status.scanner" checked-value="Enabled" unchecked-value="Disabled" @change="handleProtectionChange('scanner', localSiteInfo.protection_status?.scanner)" />
              </div>
            </a-card>
          </div>
        </a-tab-pane>
        <a-tab-pane key="3" :title="t('siteConfigFile')">
          <SiteConfigFile :site-name="localSiteInfo.name" @refresh="emit('refresh')" />
        </a-tab-pane>
     </a-tabs>
    </div>

    <!-- 确认对话框 -->
    <a-modal
      v-model:visible="confirmModalVisible"
      :title="confirmModalTitle"
      @ok="handleConfirm"
      @cancel="handleCancel"
    >
      <p>{{ confirmModalContent }}</p>
    </a-modal>

    <!-- 编辑对话框 -->
    <a-modal
      v-model:visible="editModalVisible"
      :title="editModalTitle"
      @ok="handleEditConfirm"
      @cancel="handleEditCancel"
    >
      <a-form :model="editForm" layout="vertical">
        <a-form-item v-if="editModalType === 'domain'" :label="t('domainName')">
          <a-input v-model="editForm.domain" :placeholder="t('enterDomain')" />
        </a-form-item>
        <a-form-item v-if="editModalType === 'port'" :label="t('port')">
          <a-input v-model="editForm.port" :placeholder="t('enterPort')" />
        </a-form-item>
        <a-form-item v-if="editModalType === 'upstream'" :label="t('upstreamServer')">
          <a-input v-model="editForm.upstream_server" :placeholder="t('enterUpstreamServer')" />
        </a-form-item>
        <a-form-item v-if="editModalType === 'php_fpm'" :label="t('phpFpmHost')">
          <a-input v-model="editForm.php_fpm_host" :placeholder="t('enterPhpFpmHost')" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- SSL配置对话框 -->
    <a-modal
      v-model:visible="sslModalVisible"
      :title="t('sslConfig')"
      @ok="handleSSLConfirm"
      @cancel="handleSSLCancel"
    >
      <a-form :model="sslForm" layout="vertical">
        <a-form-item :label="t('sslEnabled')">
          <a-switch v-model="sslForm.enabled" />
        </a-form-item>
        <a-form-item v-if="sslForm.enabled" :label="t('sslCertificate')">
          <a-select v-model="sslForm.cert_name" :placeholder="t('selectCertificate')" allow-search>
            <a-option v-for="cert in sslCertList" :key="cert.name" :value="cert.name">
              {{ cert.name }}
            </a-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </a-drawer>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import { t } from '../../utils/locale';
import { updateBasicSiteConfig, updateSiteSSLConfig, updateSiteProtectionConfig, getSSLCertList } from '../../api/waf';
import { Message } from '@arco-design/web-vue';
import SiteConfigFile from './SiteConfigFile.vue';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  siteInfo: {
    type: Object,
    default: () => ({})
  }
});

const emit = defineEmits(['update:visible', 'refresh']);

// 本地站点数据副本
const localSiteInfo = ref({
  ...props.siteInfo,
  protection_status: props.siteInfo.protection_status || {}
});

// 监听 props.siteInfo 变化，更新本地副本
watch(() => props.siteInfo, (newVal) => {
  localSiteInfo.value = {
    ...newVal,
    protection_status: newVal.protection_status || {}
  };
}, { deep: true, immediate: true });

// 响应式布局相关
const isMobile = ref(false);

const checkIsMobile = () => {
  isMobile.value = window.innerWidth < 768;
};

// 确认对话框状态
const confirmModalVisible = ref(false);
const confirmModalTitle = ref('');
const confirmModalContent = ref('');
const pendingUpdate = ref(null); // 存储待更新的操作

// 编辑对话框状态
const editModalVisible = ref(false);
const editModalTitle = ref('');
const editModalType = ref('');
const editForm = ref({
  domain: '',
  port: '',
  upstream_server: '',
  php_fpm_host: ''
});

// SSL配置对话框状态
const sslModalVisible = ref(false);
const sslForm = ref({
  enabled: false,
  cert_name: ''
});
const sslCertList = ref([]);

// 计算属性
const protectionStatus = computed(() => {
  const protectionStatusData = localSiteInfo.value.protection_status || {};
  return {
    sql_injection: protectionStatusData.sql_injection === 'Enabled',
    xss: protectionStatusData.xss === 'Enabled',
    command_injection: protectionStatusData.command_injection === 'Enabled',
    ssrf: protectionStatusData.ssrf === 'Enabled',
    ldap_injection: protectionStatusData.ldap_injection === 'Enabled',
    csrf: protectionStatusData.csrf === 'Enabled',
    file_inclusion: protectionStatusData.file_inclusion === 'Enabled',
    file_upload: protectionStatusData.file_upload === 'Enabled',
    scanner: protectionStatusData.scanner === 'Enabled'
  };
});

// 处理防护模式变化
const handleWafModeChange = () => {
  // 保存原始值
  const originalValue = props.siteInfo.waf_mode;
  confirmModalTitle.value = t.value('confirmUpdate');
  confirmModalContent.value = `${t.value('confirmUpdateWafMode')}`;
  pendingUpdate.value = {
    type: 'waf_mode',
    data: {
      waf_mode: localSiteInfo.value.waf_mode
    },
    originalValue: originalValue
  };
  confirmModalVisible.value = true;
};

// 处理BOT验证变化
const handleBotStatusChange = () => {
  // 保存原始值
  const originalValue = props.siteInfo.bot_status;
  confirmModalTitle.value = t.value('confirmUpdate');
  confirmModalContent.value = `${t.value('confirmUpdateBotStatus')}`;
  
  // 转换bot_status为bot_enabled和bot_verify_enabled
  let bot_enabled = 0;
  let bot_verify_enabled = 0;
  
  if (localSiteInfo.value.bot_status === 'Silent Verification') {
    bot_enabled = 1;
    bot_verify_enabled = 0;
  } else if (localSiteInfo.value.bot_status === '5s Verification') {
    bot_enabled = 1;
    bot_verify_enabled = 1;
  } else if (localSiteInfo.value.bot_status === 'Slide Verification') {
    bot_enabled = 1;
    bot_verify_enabled = 2;
  }
  
  pendingUpdate.value = {
    type: 'bot_status',
    data: {
      bot_enabled,
      bot_verify_enabled
    },
    originalValue: originalValue
  };
  confirmModalVisible.value = true;
};

// 处理CC保护变化
const handleCCStatusChange = () => {
  // 保存原始值
  const originalValue = props.siteInfo.cc_status;
  confirmModalTitle.value = t.value('confirmUpdate');
  confirmModalContent.value = `${t.value('confirmUpdateCcStatus')}`;
  pendingUpdate.value = {
    type: 'cc_status',
    data: {
      cc_enabled: localSiteInfo.value.cc_status === 'Enabled' ? 1 : 0
    },
    originalValue: originalValue
  };
  confirmModalVisible.value = true;
};

// 处理编辑域名
const handleEditDomain = () => {
  editModalTitle.value = t.value('editDomain');
  editModalType.value = 'domain';
  editForm.value.domain = localSiteInfo.value.domain || '';
  editModalVisible.value = true;
};

// 处理编辑端口
const handleEditPort = () => {
  editModalTitle.value = t.value('editPort');
  editModalType.value = 'port';
  editForm.value.port = localSiteInfo.value.port || '';
  editModalVisible.value = true;
};

// 处理编辑上游服务器
const handleEditUpstream = () => {
  editModalTitle.value = t.value('editUpstreamServer');
  editModalType.value = 'upstream';
  editForm.value.upstream_server = localSiteInfo.value.upstream_server || '';
  editModalVisible.value = true;
};

// 处理编辑 PHP-FPM 地址
const handleEditPhpFpm = () => {
  editModalTitle.value = t.value('editPhpFpmHost');
  editModalType.value = 'php_fpm';
  editForm.value.php_fpm_host = localSiteInfo.value.php_fpm_host || '';
  editModalVisible.value = true;
};

// 处理确认
const handleConfirm = async () => {
  if (!pendingUpdate.value || !localSiteInfo.value.name) return;
  
  try {
    let response;
    if (pendingUpdate.value.type === 'protection') {
      // 处理漏洞防护更新
      response = await updateSiteProtectionConfig(localSiteInfo.value.name, pendingUpdate.value.data);
    } else {
      // 处理其他更新
      response = await updateBasicSiteConfig(localSiteInfo.value.name, pendingUpdate.value.data);
    }
    Message.success(t.value('updateSuccess'));
    // 触发刷新事件
    emit('refresh');
  } catch (error) {
    console.error('更新失败:', error);
    Message.error(t.value('updateFailed'));
  } finally {
    confirmModalVisible.value = false;
    pendingUpdate.value = null;
  }
};

// 处理取消
const handleCancel = () => {
  // 恢复原始值
  if (pendingUpdate.value) {
    if (pendingUpdate.value.type === 'waf_mode') {
      localSiteInfo.value.waf_mode = pendingUpdate.value.originalValue;
    } else if (pendingUpdate.value.type === 'bot_status') {
      localSiteInfo.value.bot_status = pendingUpdate.value.originalValue;
    } else if (pendingUpdate.value.type === 'cc_status') {
      localSiteInfo.value.cc_status = pendingUpdate.value.originalValue;
    } else if (pendingUpdate.value.type === 'protection' && pendingUpdate.value.protectionType) {
      if (!localSiteInfo.value.protection_status) {
        localSiteInfo.value.protection_status = {};
      }
      localSiteInfo.value.protection_status[pendingUpdate.value.protectionType] = pendingUpdate.value.originalValue;
    }
  }
  confirmModalVisible.value = false;
  pendingUpdate.value = null;
};

// 处理编辑确认
const handleEditConfirm = async () => {
  if (!localSiteInfo.value.name) return;
  
  try {
    let updateData = {};
    
    if (editModalType.value === 'domain') {
      updateData.domain = editForm.value.domain;
    } else if (editModalType.value === 'port') {
      updateData.port = editForm.value.port;
    } else if (editModalType.value === 'upstream') {
      updateData.upstream_server = editForm.value.upstream_server;
    } else if (editModalType.value === 'php_fpm') {
      updateData.php_fpm_host = editForm.value.php_fpm_host;
    }
    
    const response = await updateBasicSiteConfig(localSiteInfo.value.name, updateData);
    Message.success(t.value('updateSuccess'));
    // 触发刷新事件
    emit('refresh');
  } catch (error) {
    console.error('更新失败:', error);
    Message.error(t.value('updateFailed'));
  } finally {
    editModalVisible.value = false;
  }
};

// 处理编辑取消
const handleEditCancel = () => {
  editModalVisible.value = false;
};

// 处理编辑SSL
const handleEditSSL = async () => {
  sslModalVisible.value = true;
  sslForm.value.enabled = localSiteInfo.value.is_ssl || false;
  sslForm.value.cert_name = localSiteInfo.value.ssl_cert_name || '';
  await loadSSLCertList();
};

// 加载SSL证书列表
const loadSSLCertList = async () => {
  try {
    const response = await getSSLCertList();
    if (response && response.certs) {
      sslCertList.value = response.certs;
    }
  } catch (error) {
    console.error('获取SSL证书列表失败:', error);
    Message.error(t.value('getSSLCertListFailed'));
  }
};

// 处理SSL配置确认
const handleSSLConfirm = async () => {
  if (!localSiteInfo.value.name) return;
  
  if (sslForm.value.enabled && !sslForm.value.cert_name) {
    Message.warning(t.value('pleaseSelectCertificate'));
    return;
  }
  
  try {
    const sslData = {
      enabled: sslForm.value.enabled,
      cert_name: sslForm.value.cert_name,
      http2: true,
      ssl_protocols: 'TLSv1.2 TLSv1.3',
      ssl_ciphers: 'ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384'
    };
    
    const response = await updateSiteSSLConfig(localSiteInfo.value.name, sslData);
    Message.success(t.value('updateSuccess'));
    // 触发刷新事件
    emit('refresh');
    sslModalVisible.value = false;
  } catch (error) {
    console.error('更新SSL配置失败:', error);
    Message.error(t.value('updateFailed'));
  }
};

// 处理SSL配置取消
const handleSSLCancel = () => {
  sslModalVisible.value = false;
};

// 处理漏洞防护开关变化
const handleProtectionChange = (protectionType, value) => {
  // 保存原始值，并转换为字符串
  const originalValue = props.siteInfo.protection_status?.[protectionType] ? 'Enabled' : 'Disabled';
  confirmModalTitle.value = t.value('confirmUpdate');
  confirmModalContent.value = `${t.value('confirmUpdateProtection')} ${t.value(protectionType) || protectionType}?`;
  pendingUpdate.value = {
    type: 'protection',
    data: {
      [protectionType]: value === 'Enabled'
    },
    protectionType: protectionType,
    originalValue: originalValue
  };
  confirmModalVisible.value = true;
};

// 组件挂载时获取数据
onMounted(() => {
  window.addEventListener('resize', checkIsMobile);
  checkIsMobile();
});

onUnmounted(() => {
  window.removeEventListener('resize', checkIsMobile);
});
</script>

<style scoped>
.site-detail {
  padding: 20px;
  line-height: 1.6;
}

.card-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

.info-card {
  margin-bottom: 20px;
}

.request-count {
  color: #52c41a;
  font-weight: 500;
}

.block-count {
  color: #ff4d4f;
  font-weight: 500;
}
</style>
