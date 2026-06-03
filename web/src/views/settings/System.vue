<template>

    <!--  内容区域  -->
    <div class="content-area">
      <a-tabs :default-active-key="'panel'" type="card" >
        <a-tab-pane key="panel" :title="t('panelSettings')">
          <a-form :model="formState" layout="horizontal">
            <a-form-item :label="t('appName') + ':'" class="form-item">
              <a-input v-model="systemConfig.APP_NAME" :placeholder="t('enterAppName')" />
              <a-button type="primary" size="small" style="margin-left: 10px;" @click="saveAppName">{{ t('save') }}</a-button>
            </a-form-item>
            <a-form-item :label="t('version') + ':'" class="form-item">
              <a-input v-model="systemConfig.VERSION" :placeholder="t('enterVersion')" readonly />
            </a-form-item>
            <a-form-item :label="t('language') + ':'" class="form-item">
              <a-select v-model="formState.language" :placeholder="t('selectLanguage')" @change="handleLanguageChange">
                <a-option value="zh-CN">中文</a-option>
                <a-option value="en-US">English</a-option>
                <a-option value="zh-TW">繁體中文</a-option>
                <a-option value="ja-JP">日本語</a-option>
                <a-option value="ko-KR">한국어</a-option>
              </a-select>
            </a-form-item>
            <a-form-item :label="t('theme') + ':'" class="form-item">
              <a-select v-model="formState.theme" :placeholder="t('selectTheme')" @change="handleThemeChange">
                <a-option value="light">{{ t('light') }}</a-option>
                <a-option value="dark">{{ t('dark') }}</a-option>
              </a-select>
            </a-form-item>
            <a-form-item :label="t('loginNotification') + ':'" class="form-item">
              <a-switch v-model="formState.loginNotification" @change="handleLoginNotificationChange" />
            </a-form-item>
            <a-form-item :label="t('loginLimit') + ':'" class="form-item">
              <a-switch v-model="formState.loginLimit" @change="handleLoginLimitChange" />
            </a-form-item>
          </a-form>
          <a-form :model="systemConfig" layout="horizontal">
            <template v-if="isAdminUser">
              <a-form-item :label="t('timeZone') + ':'" class="form-item">
                <a-select v-model="systemConfig.TIMEZONE" :placeholder="t('selectTimezone')">
                  <a-option value="UTC">{{ t('utc') }}</a-option>
                  <a-option value="Asia/Shanghai">{{ t('asiaShanghai') }}</a-option>
                  <a-option value="Asia/Tokyo">{{ t('asiaTokyo') }}</a-option>
                  <a-option value="Europe/London">{{ t('europeLondon') }}</a-option>
                  <a-option value="Europe/Paris">{{ t('europeParis') }}</a-option>
                  <a-option value="America/New_York">{{ t('americaNewYork') }}</a-option>
                  <a-option value="America/Los_Angeles">{{ t('americaLosAngeles') }}</a-option>
                </a-select>
                <a-button type="primary" size="small" style="margin-left: 10px;" @click="saveTimezone">{{ t('save') }}</a-button>
              </a-form-item>
              <a-form-item :label="t('Timeout') + ':'" class="form-item">
                <a-input v-model="systemConfig.ACCESS_TOKEN_EXPIRE_MINUTES" :min="1" :max="1440" readonly />
                <a-button type="primary" size="small" style="margin-left: 10px;" @click="showTimeoutDialog">{{ t('settings') }}</a-button>
              </a-form-item>
              <a-form-item :label="t('debug') + ':'" class="form-item">
                <a-switch v-model="systemConfig.DEBUG" @change="handleDebugChange" />
              </a-form-item>
              <a-form-item :label="t('apiDoc') + ':'" class="form-item">
                <a-switch v-model="systemConfig.ENABLE_DOCS" @change="handleApiDocChange" />
                <a-link><icon-link /><a href="/api/v2/docs" target="_blank" class="api-doc-link">{{ t('apiDoc') }}</a></a-link>
              </a-form-item>
            </template>
            <template v-else>
              <a-form-item :label="t('timeZone') + ':'" class="form-item">
                <a-input v-model="systemConfig.TIMEZONE" :placeholder="t('selectTimezone')" readonly />
              </a-form-item>
            </template>
          </a-form>
        </a-tab-pane>
        <a-tab-pane key="security" :title="t('securitySettings')">
          <template v-if="isAdminUser">
            <a-form :model="systemConfig" layout="horizontal">
              <a-form-item :label="t('listeningAddress') + ':'" class="form-item">
                <a-input v-model="systemConfig.HOST" :placeholder="t('enterHost')" />
                <a-button type="primary" size="small" style="margin-left: 10px;" @click="showHostDialog">{{ t('save') }}</a-button>
              </a-form-item>
              <a-form-item :label="t('port') + ':'" class="form-item">
                <a-input-number v-model="systemConfig.PORT" :min="1" :max="65535" readonly style="width: 100%;" />
                <a-button type="primary" size="small" style="margin-left: 10px;" @click="showPortDialog">{{ t('settings') }}</a-button>
              </a-form-item>
              <a-form-item :label="t('securityEntrance') + ':'" class="form-item">
                <a-input v-model="systemConfig.SECURITY_ENTRANCE" readonly :placeholder="t('entranceNotSet')" />
                <a-button type="primary" size="small" style="margin-left: 10px;" @click="showEntranceDialog">{{ t('settings') }}</a-button>
              </a-form-item>
              <a-form-item :label="'SSL' + ':'" class="form-item">
                <a-switch v-model="systemConfig.SSL_ENABLED" @change="handleSSLChange" />
                <a-link style="margin-left: 10px;" @click="showCertDialog">{{ t('viewCert') }}</a-link>
              </a-form-item>
              <a-form-item :label="t('domainBinding') + ':'" class="form-item">
                <a-input v-model="systemConfig.DOMAIN_BINDING" placeholder="panel.example.com" />
                <a-button type="primary" size="small" style="margin-left: 10px;" @click="handleSaveDomainBinding">{{ t('save') }}</a-button>
              </a-form-item>
              <a-alert type="warning" show-icon  :closable="false" style="margin: -8px 0 8px 130px;">{{ t('domainBindingNote') }}</a-alert>
              <a-form-item :label="t('allowIPs') + ':'" class="form-item">
                <a-input v-model="systemConfig.ALLOW_IPS" :placeholder="t('allowIPsPlaceholder')" />
                <a-button type="primary" size="small" style="margin-left: 10px;" @click="handleSaveAllowIPs">{{ t('save') }}</a-button>
              </a-form-item>
              <a-alert type="warning" show-icon :closable="false" style="margin: -8px 0 8px 130px;">{{ t('allowIPsNote') }}</a-alert>
              <a-form-item :label="t('apiInterface') + ':'" class="form-item">
                <a-switch v-model="systemConfig.API_OPEN" @change="handleSaveApiOpen" />
                <span style="margin-left: 8px; font-size: 12px; color: var(--color-text-3);">{{ t('apiInterfaceNote') }}</span>
                <a-link  style="margin-left: 10px;" @click="handleOpenApiConfigDialog">{{ t('settings') }}</a-link>
              </a-form-item>
              <a-form-item :label="t('mfa') + ':'" class="form-item">
                <a-switch :model-value="systemConfig.MFA_ENABLED" @change="handleMFA" />
                <span style="margin-left: 8px; font-size: 12px; color: var(--color-text-3);">{{ t('mfaHelper') }}</span>
              </a-form-item>
            </a-form>
          </template>
          <template v-else>
            <a-form :model="systemConfig" layout="horizontal">
              <a-form-item :label="t('ipAddress') + ':'" class="form-item">
                <a-input v-model="systemConfig.HOST" readonly />
              </a-form-item>
              <a-form-item :label="t('port') + ':'" class="form-item">
                <a-input-number v-model="systemConfig.PORT" readonly style="width: 100%;" />
              </a-form-item>
            </a-form>
          </template>
        </a-tab-pane>
        <a-tab-pane key="server" :title="t('serverSettings')" v-if="isAdminUser">
          <a-tabs :default-active-key="'dns'" type="line" position="left" class="server-tabs">
            <a-tab-pane key="dns" :title="'DNS'">
              <a-form layout="horizontal" :model="serverForms.dns" style="max-width: 500px;">
                <a-form-item label="DNS1">
                  <a-input v-model="serverForms.dns.dns1" placeholder="114.114.114.114" allow-clear />
                </a-form-item>
                <a-form-item label="DNS2">
                  <a-input v-model="serverForms.dns.dns2" placeholder="8.8.8.8" allow-clear />
                </a-form-item>
                <a-form-item>
                  <a-space>
                    <a-button type="primary" size="small" @click="handleSaveDNS">{{ t('save') }}</a-button>
                    <a-button size="small" @click="handleTestDNS">{{ t('test') }}</a-button>
                  </a-space>
                </a-form-item>
              </a-form>
            </a-tab-pane>

            <a-tab-pane key="swap" :title="'Swap'">
              <a-form layout="horizontal" :model="serverForms.swap" style="max-width: 500px;">
                <a-form-item label="当前">
                  <span>{{ swapInfoText }}</span>
                </a-form-item>
                <a-form-item label="大小 (MB)">
                  <a-input-number v-model="serverForms.swap.size" :min="0" :max="8192" style="width: 200px;" />
                  <span class="desc" style="margin-left: 8px;">设为0则关闭Swap</span>
                </a-form-item>
                <a-form-item>
                  <a-button type="primary" size="small" @click="handleSaveSwap">{{ t('save') }}</a-button>
                </a-form-item>
              </a-form>
            </a-tab-pane>

            <a-tab-pane key="timezone" :title="t('timeZone')">
              <a-form layout="horizontal" :model="serverForms.timezone" style="max-width: 500px;">
                <a-form-item label="当前">
                  <span>{{ serverTimezoneText }}</span>
                </a-form-item>
                <a-form-item label="Area">
                  <a-select v-model="serverForms.timezone.area" style="width: 200px;">
                    <a-option v-for="item in timezoneZoneList" :key="item.area" :value="item.area">{{ item.area }}</a-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="Zone">
                  <a-select v-model="serverForms.timezone.zone" style="width: 200px;">
                    <a-option v-for="z in currentZoneList" :key="z" :value="z">{{ z }}</a-option>
                  </a-select>
                </a-form-item>
                <a-form-item>
                  <a-space>
                    <a-button type="primary" size="small" @click="handleSaveTimezone">{{ t('save') }}</a-button>
                    <a-button size="small" @click="handleSyncTime">{{ t('syncTime') }}</a-button>
                  </a-space>
                </a-form-item>
              </a-form>
            </a-tab-pane>

            <a-tab-pane key="password" :title="t('systemPassword')">
              <a-form layout="horizontal" :model="serverForms.password" style="max-width: 500px;">
                <a-form-item :label="t('username')">
                  <a-input v-model="serverForms.password.user" placeholder="root" style="width: 200px;" />
                </a-form-item>
                <a-form-item :label="t('newPassword')">
                  <a-input-password v-model="serverForms.password.password" style="width: 200px;" />
                </a-form-item>
                <a-form-item :label="t('confirmPassword')">
                  <a-input-password v-model="serverForms.password.confirmPassword" style="width: 200px;" />
                </a-form-item>
                <a-form-item>
                  <a-button type="primary" size="small" @click="handleSavePassword">{{ t('save') }}</a-button>
                </a-form-item>
              </a-form>
            </a-tab-pane>

            <a-tab-pane key="memory-disk" :title="t('memoryDisk')">
              <a-space style="margin-bottom: 16px;">
                <a-button size="small" type="primary" @click="showMemoryDiskModal = true">{{ t('create') }}</a-button>
              </a-space>
              <a-table :data="memoryDiskList" :columns="memoryDiskColumns" :pagination="false" size="small" v-if="memoryDiskList.length > 0">
                <template #action="{ record }">
                    <a-button type="text" status="danger" size="small" @click="handleDeleteMemoryDisk(record.path)">{{ t('delete') }}</a-button>
                </template>
              </a-table>
              <a-empty v-else :description="t('noMemoryDisk')" />
            </a-tab-pane>

            <a-tab-pane key="hosts" :title="'Hosts'">
              <a-space style="margin-bottom: 16px;">
                <a-button size="small" type="primary" @click="showHostsModal = true; hostsForm.domain = ''; hostsForm.ip = ''">{{ t('addHost') }}</a-button>
              </a-space>
              <a-table :data="hostsList" :columns="hostsColumns" :pagination="false" size="small" v-if="hostsList.length > 0">
                <template #action="{ record }">
                    <a-space>
                      <a-button type="text" size="small" @click="hostsForm.domain = record.domain; hostsForm.ip = record.ip; showHostsModal = true">{{ t('edit') }}</a-button>
                      <a-button type="text" size="small" @click="handleToggleHosts(record.domain, record.status === 1 ? 'pause' : 'resume')">
                        {{ record.status === 1 ? t('pause') : t('resume') }}
                      </a-button>
                      <a-button type="text" status="danger" size="small" @click="handleDeleteHosts(record.domain)">{{ t('delete') }}</a-button>
                    </a-space>
                </template>
              </a-table>
              <a-empty v-else :description="t('noHosts')" />
            </a-tab-pane>

          </a-tabs>
        </a-tab-pane>
      </a-tabs>
    </div>

    <!-- 重启服务确认对话框 -->
    <a-modal 
      v-model:visible="restartModalVisible" 
      :title="t('restartConfirmTitle')" 
      @ok="confirmRestart" 
      @cancel="cancelRestart"
    >
      <p>{{ restartModalType === 'save' ? t('restartConfirmMessage') : t('restartConfirmMessageDirect') }}</p>
    </a-modal>
    
    <!-- 证书查看对话框 -->
    <a-modal 
      v-model:visible="certModalVisible" 
      title="SSL" 
      :width="800"
      @ok="saveCertContent"
      @cancel="closeCertDialog"
      :mask-closable="false"
      :footer="false"
    >
      <div class="cert-upload-area">
        <input
          ref="certFileInputRef"
          type="file"
          multiple
          accept=".pem,.crt,.cert,.key,.cer"
          style="display: none;"
          @change="handleCertFileSelect"
        />
        <a-button type="secondary" @click="triggerCertFileSelect">
          <template #icon><icon-upload /></template>
          {{ t('uploadCertificate') }}
        </a-button>
        <span class="cert-upload-hint">{{ t('uploadCertHint') }}</span>
      </div>
      <div class="cert-content">
        <a-tabs v-model:active-key="activeCertTab" @change="handleCertTabChange">
          <a-tab-pane key="cert" title="PEM">
            <div ref="certMonacoEditorRef" class="monaco-editor-container"></div>
          </a-tab-pane>
          <a-tab-pane key="key" title="KEY">
            <div ref="keyMonacoEditorRef" class="monaco-editor-container"></div>
          </a-tab-pane>
        </a-tabs>
      </div>
      <div class="cert-actions">
        <a-button style="margin-right: 8px;" @click="closeCertDialog">{{ t('cancel') }}</a-button>
        <a-button type="primary" @click="saveCertContent">{{ t('save') }}</a-button>
      </div>
    </a-modal>
    
    <!-- 调试模式确认对话框 -->
    <a-modal 
      v-model:visible="debugConfirmModalVisible" 
      :title="t('debugConfirmTitle')" 
      @ok="confirmDebugChange" 
      @cancel="cancelDebugChange"
    >
      <p>{{ t('debugConfirmMessage') }}</p>
    </a-modal>
    
    <!-- 过期时间设置对话框 -->
    <a-modal 
      v-model:visible="timeoutModalVisible" 
      :title="t('timeoutSetTitle')" 
      @ok="confirmTimeoutChange" 
      @cancel="cancelTimeoutChange"
    >
      <a-form-item :label="t('Timeout') + ':'" class="form-item">
        <a-select v-model="timeoutValue" style="width: 100%;">
          <a-option value="15">15 {{ t('minutes') }}</a-option>
          <a-option value="30">30 {{ t('minutes') }}</a-option>
          <a-option value="60">60 {{ t('minutes') }}</a-option>
          <a-option value="120">120 {{ t('minutes') }}</a-option>
          <a-option value="360">360 {{ t('minutes') }}</a-option>
          <a-option value="720">12 {{ t('hours') }}</a-option>
          <a-option value="1440">24 {{ t('hours') }}</a-option>
        </a-select>
      </a-form-item>
    </a-modal>
    
    <!-- 主机地址保存对话框 -->
    <a-modal 
      v-model:visible="hostModalVisible" 
      :title="t('hostSaveTitle')" 
      @ok="confirmHostSave" 
      @cancel="cancelHostSave"
    >
      <p>{{ t('hostSaveConfirmMessage') }}</p>
    </a-modal>
    
    <!-- 端口设置对话框 -->
    <a-modal 
      v-model:visible="portModalVisible" 
      :title="t('portSetTitle')" 
      @ok="confirmPortChange" 
      @cancel="cancelPortChange"
    >
      <a-form-item :label="t('port') + ':'" class="form-item">
        <a-input-number v-model="portValue" :min="1" :max="65535" style="width: 100%;" />
      </a-form-item>
    </a-modal>
    
    <!-- SSL关闭确认对话框 -->
    <a-modal 
      v-model:visible="sslCloseModalVisible" 
      :title="t('sslCloseTitle')" 
      @ok="confirmSSLClose" 
      @cancel="cancelSSLClose"
    >
      <p>{{ t('sslCloseConfirmMessage') }}</p>
    </a-modal>
    
    <!-- 安全入口设置对话框 -->
    <a-modal 
      v-model:visible="entranceModalVisible" 
      :title="t('securityEntrance')" 
      @ok="confirmEntranceChange" 
      @cancel="cancelEntranceChange"
    >
      <a-form-item :label="t('securityEntrance') + ':'" class="form-item">
        <a-input v-model="entranceValue" :placeholder="t('entranceInputHelper')" />
      </a-form-item>
      <p class="entrance-hint">{{ t('entranceHelper') }}</p>
    </a-modal>

    <!-- 内存盘创建对话框 -->
    <a-modal v-model:visible="showMemoryDiskModal" :title="t('createMemoryDisk')" @ok="handleCreateMemoryDisk" @cancel="showMemoryDiskModal = false">
      <a-form layout="vertical" :model="memoryDiskForm">
        <a-form-item :label="t('path')" required>
          <a-input v-model="memoryDiskForm.path" placeholder="/tmp/mydisk">
            <template #suffix>
              <icon-folder
                style="cursor: pointer; color: #165DFF;"
                @click="showMiniFileManager = true"
              />
            </template>
          </a-input>
        </a-form-item>
        <a-form-item :label="t('size') + ' (MB)'" required>
          <a-input-number v-model="memoryDiskForm.size" :min="1" :max="8192" style="width: 100%;" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- Hosts 添加/编辑对话框 -->
    <a-modal v-model:visible="showHostsModal" :title="hostsForm.domain ? t('editHost') : t('addHost')" @ok="handleSaveHosts" @cancel="showHostsModal = false">
      <a-form layout="vertical" :model="hostsForm">
        <a-form-item :label="t('domain')" required>
          <a-input v-model="hostsForm.domain" placeholder="example.com" />
        </a-form-item>
        <a-form-item :label="'IP'" required>
          <a-input v-model="hostsForm.ip" placeholder="127.0.0.1" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- MiniFileManager 路径选择 -->
    <MiniFileManager
      :visible="showMiniFileManager"
      :initial-path="memoryDiskForm.path || '/'"
      select-mode="directory"
      @update:visible="showMiniFileManager = $event"
      @select="handleMiniFileManagerSelect"
    />

    <!-- API 接口配置对话框 -->
    <a-modal v-model:visible="apiConfigModalVisible" title="API Interface" @ok="handleSaveApiConfig" @cancel="handleCancelApiConfig" :mask-closable="false">
      <a-form layout="vertical" :model="apiConfigForm">
        <a-form-item label="API Key">
          <a-input-password v-model="apiConfigForm.API_KEY" readonly placeholder="Not Set" />
        </a-form-item>
        <div style="margin: -8px 0 12px 0;">
          <a-button type="primary" size="small" @click="handleGenerateApiKey">{{ t('generate') }}</a-button>
          <a-button size="small" style="margin-left: 8px;" @click="handleCopyApiKey">{{ t('copy') }}</a-button>
        </div>
        <a-form-item :label="t('ipWhitelist')">
          <a-input v-model="apiConfigForm.API_IP_WHITELIST" placeholder="0.0.0.0/0" />
        </a-form-item>
        <a-alert type="warning" show-icon :closable="false" style="margin: 0 0 12px 0;">{{ t('ipWhitelistFillinNote') }}</a-alert>
        <a-form-item :label="t('validityTime')">
          <a-input-number v-model="apiConfigForm.API_KEY_VALIDITY_TIME" :min="0" :max="1440" style="width: 100%;" />
          <span style="font-size: 12px; color: var(--color-text-3);">{{ t('unlimited') }}</span>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- MFA 设置对话框 -->
    <MfaSetting ref="mfaRef" @close="handleMfaClose" />

</template>

<script setup>
import { reactive, onMounted, computed, ref } from 'vue';
import { t, changeLocale, getCurrentLocale } from '../../utils/locale'
import { Message} from '@arco-design/web-vue';
import { IconLink, IconUpload, IconFolder } from '@arco-design/web-vue/es/icon';
import { getEnvConfig, updateEnvConfig, generateApiKey, restartService, getSSLCert, updateSSLCert, getSystemSettings, setDNS, testDNS, setSwap, setTimezone, syncTime, setSystemPassword, createMemoryDisk, deleteMemoryDisk, addHosts, deleteHosts, toggleHosts } from '../../api/system';
// 导入用户状态和函数
import { isAdmin, fetchCurrentUser as fetchCurrentUserStore } from '../../stores/user';
import MiniFileManager from '../../components/file/MiniFileManager.vue';
import MfaSetting from '../../components/mfa/MfaSetting.vue';

const formState = reactive({
  closePanel: false,
  theme: 'light', // 默认主题为亮色
  panelName: '',
  language: 'zh-CN', // 添加语言设置，默认为中文
  loginNotification: true, // 登录提示默认开启
  loginLimit: true,
});

const systemConfig = reactive({
  APP_NAME: '',
  VERSION: '',
  DEBUG: false,
  ENABLE_DOCS: true,
  TIMEZONE: 'UTC',
  ACCESS_TOKEN_EXPIRE_MINUTES: '30', // 改为字符串类型
  HOST: '0.0.0.0',
  PORT: 8000, // 确保默认值是数字类型
  SSL_ENABLED: false,
  SECURITY_ENTRANCE: '',
  DOMAIN_BINDING: '',
  ALLOW_IPS: '',
  API_OPEN: true,
  API_KEY: '',
  API_IP_WHITELIST: '127.0.0.1',
  API_KEY_VALIDITY_TIME: 0,
  MFA_ENABLED: false,
  MFA_INTERVAL: 30
});

// 当前用户信息（保留用于兼容性，实际使用store中的currentUser）
const currentUser = reactive({
  username: '',
  is_admin: false
});

// API 接口配置对话框
const apiConfigModalVisible = ref(false);
const apiConfigForm = reactive({
  API_KEY: '',
  API_IP_WHITELIST: '127.0.0.1',
  API_KEY_VALIDITY_TIME: 0
});

// MFA 设置对话框
const mfaRef = ref(null);
const handleMFA = (value) => {
  if (value) {
    // 开启 MFA → 弹出 MFA 对话框
    mfaRef.value?.acceptParams()
  } else {
    // 关闭 MFA → 直接保存
    updateEnvConfig({ MFA_ENABLED: false }).then(() => {
      Message.success(t.value('mfaClose'))
      systemConfig.MFA_ENABLED = false
    }).catch((error) => {
      Message.error(error.response?.data?.detail || t.value('updateFailed'))
    })
  }
}
const handleMfaClose = () => {
  // MFA 对话框关闭后，刷新配置
  fetchSystemConfig()
}

// 重启服务确认对话框可见性
const restartModalVisible = ref(false);
const restartModalType = ref('save'); // 'save' 或 'direct'

// 证书查看对话框
const certModalVisible = ref(false);
const activeCertTab = ref('cert');
const sslCertData = ref({
  cert_content: '',
  key_content: '',
  message: ''
});

// Monaco Editor 引用
const certMonacoEditorRef = ref(null);
const keyMonacoEditorRef = ref(null);
const certFileInputRef = ref(null);
let certMonacoEditor = null;
let keyMonacoEditor = null;

// 调试模式确认对话框
const debugConfirmModalVisible = ref(false);
const originalDebugValue = ref(true);

// 过期时间设置对话框
const timeoutModalVisible = ref(false);
const timeoutValue = ref(30); // 默认30分钟

// 主机地址保存对话框
const hostModalVisible = ref(false);
const hostValue = ref('0.0.0.0'); // 默认主机地址

// 端口设置对话框
const portModalVisible = ref(false);
const portValue = ref(8000); // 默认端口

// 需要重启的配置项（用于判断是否需要提示重启）
const restartRequiredConfigs = ['DEBUG', 'ENABLE_DOCS', 'TIMEZONE', 'ACCESS_TOKEN_EXPIRE_MINUTES', 'HOST', 'PORT', 'SSL_ENABLED'];

// 计算属性：是否为管理员用户（使用user.js中统一的角色判断）
const isAdminUser = computed(() => {
  return isAdmin.value;
});

// 处理语言切换
const handleLanguageChange = async (value) => {
  changeLocale(value);
  try {
    // 直接调用updateEnvConfig更新语言设置
    const response = await updateEnvConfig({ LANGUAGE: value });
    console.log('语言设置更新成功:', response);
    // 保存到本地存储作为备份
    localStorage.setItem('language', value);
  } catch (error) {
    console.error('语言设置更新失败:', error);
    Message.error(`${t.value('updateConfigFailed')}: ${error.message || t.value('unknownError')}`);
  }
};

// 处理登录提示切换
const handleLoginNotificationChange = async (value) => {
  try {
    // 直接调用updateEnvConfig更新登录通知设置
    const response = await updateEnvConfig({ LOGIN_NOTIFY: value });
    console.log('登录通知设置更新成功:', response);
    // 保存到本地存储作为备份
    localStorage.setItem('loginNotification', value);
  } catch (error) {
    console.error('登录通知设置更新失败:', error);
    Message.error(`${t.value('updateConfigFailed')}: ${error.message || t.value('unknownError')}`);
  }
};

const handleLoginLimitChange = async (value) => {
  try {
    const response = await updateEnvConfig({ LOGIN_LIMIT: value });
    console.log('登录限制设置更新成功:', response);
    if (value) {
      Message.info(t.value('loginLimitEnabled'));
    } else {
      Message.info(t.value('loginLimitDisabled'));
    }
  } catch (error) {
    console.error('登录限制设置更新失败:', error);
    Message.error(`${t.value('updateConfigFailed')}: ${error.message || t.value('unknownError')}`);
  }
};

// 处理主题切换
const handleThemeChange = async (value) => {
  // 先应用主题效果
  if (value === 'dark') {
    // 设置为暗黑主题
    document.body.setAttribute('arco-theme', 'dark');
  } else {
    // 恢复亮色主题
    document.body.removeAttribute('arco-theme');
  }
  
  // 触发自定义事件，通知其他组件主题已更改
  window.dispatchEvent(new CustomEvent('theme-change', { detail: value }));
  
  try {
    // 直接调用updateEnvConfig更新主题设置
    const response = await updateEnvConfig({ THEME: value });
    console.log('主题设置更新成功:', response);
    // 保存到本地存储作为备份
    localStorage.setItem('theme', value);
  } catch (error) {
    console.error('主题设置更新失败:', error);
    Message.error(`${t.value('updateConfigFailed')}: ${error.message || t.value('unknownError')}`);
  }
};

// 获取当前用户信息（使用user.js中统一的函数）
const fetchCurrentUser = async () => {
  try {
    // 调用stores/user.js中的fetchCurrentUser来统一管理用户状态
    const user = await fetchCurrentUserStore();
    
    // 兼容性处理：更新本地currentUser对象
    if (user && user.username) {
      currentUser.username = user.username;
      currentUser.is_admin = user.role === 'admin';
    }
  } catch (error) {
    console.error('获取当前用户信息失败:', error);
  }
};

// 获取系统配置
const fetchSystemConfig = async () => {
  try {
    const response = await getEnvConfig();
    console.log('API Response:', response); // 调试信息
    
    // 检查响应数据结构 - 由于响应拦截器已经处理过了，直接使用response
    let configs = {};
    
    // 处理响应拦截器处理过的数据结构
    if (response) {
      if (response.configs) {
        // 标准结构: { configs: {...}, message: "..." }
        configs = response.configs;
      } else {
        // 可能是其他结构
        configs = response;
      }
    } else {
      throw new Error(t.value('responseDataEmpty'));
    }
    
    console.log('解析后的configs:', configs); // 调试信息
    
    // 更新表单数据（只更新允许的配置项）
    if (configs.APP_NAME !== undefined) systemConfig.APP_NAME = configs.APP_NAME;
    if (configs.VERSION !== undefined) systemConfig.VERSION = configs.VERSION;
    if (configs.DEBUG !== undefined) {
      systemConfig.DEBUG = configs.DEBUG === 'True' || configs.DEBUG === 'true' || configs.DEBUG === true;
    }
    if (configs.ENABLE_DOCS !== undefined) {
      systemConfig.ENABLE_DOCS = configs.ENABLE_DOCS === 'True' || configs.ENABLE_DOCS === 'true' || configs.ENABLE_DOCS === true;
    }
    if (configs.TIMEZONE !== undefined) systemConfig.TIMEZONE = configs.TIMEZONE;
    if (configs.ACCESS_TOKEN_EXPIRE_MINUTES !== undefined) {
      systemConfig.ACCESS_TOKEN_EXPIRE_MINUTES = String(parseInt(configs.ACCESS_TOKEN_EXPIRE_MINUTES) || 30);
    }
    if (configs.HOST !== undefined) {
      systemConfig.HOST = configs.HOST;
    }
    if (configs.PORT !== undefined) {
      systemConfig.PORT = parseInt(configs.PORT) || 8000;
    }
    if (configs.SSL_ENABLED !== undefined) {
      systemConfig.SSL_ENABLED = configs.SSL_ENABLED === 'True' || configs.SSL_ENABLED === 'true' || configs.SSL_ENABLED === true;
    }
    if (configs.SECURITY_ENTRANCE !== undefined) {
      systemConfig.SECURITY_ENTRANCE = configs.SECURITY_ENTRANCE;
    }
    if (configs.DOMAIN_BINDING !== undefined) {
      systemConfig.DOMAIN_BINDING = configs.DOMAIN_BINDING;
    }
    if (configs.ALLOW_IPS !== undefined) {
      systemConfig.ALLOW_IPS = configs.ALLOW_IPS;
    }
    if (configs.MFA_ENABLED !== undefined) {
      systemConfig.MFA_ENABLED = configs.MFA_ENABLED === 'True' || configs.MFA_ENABLED === true;
    }
    if (configs.MFA_INTERVAL !== undefined) {
      systemConfig.MFA_INTERVAL = parseInt(configs.MFA_INTERVAL, 10);
    }
    if (configs.API_OPEN !== undefined) {
      systemConfig.API_OPEN = configs.API_OPEN === 'True' || configs.API_OPEN === true;
    }
    if (configs.API_KEY !== undefined) {
      systemConfig.API_KEY = configs.API_KEY;
    }
    if (configs.API_IP_WHITELIST !== undefined) {
      systemConfig.API_IP_WHITELIST = configs.API_IP_WHITELIST;
    }
    if (configs.API_KEY_VALIDITY_TIME !== undefined) {
      systemConfig.API_KEY_VALIDITY_TIME = Number(configs.API_KEY_VALIDITY_TIME);
    }
    
    // 更新用户界面配置（从API获取）
    if (configs.LANGUAGE !== undefined) {
      formState.language = configs.LANGUAGE;
      changeLocale(configs.LANGUAGE); // 应用语言设置
    }
    
    if (configs.THEME !== undefined) {
      formState.theme = configs.THEME;
      // 应用主题设置
      if (configs.THEME === 'dark') {
        document.body.setAttribute('arco-theme', 'dark');
      } else {
        document.body.removeAttribute('arco-theme');
      }
      // 保存到本地存储
      localStorage.setItem('theme', configs.THEME);
      // 触发主题变更事件
      window.dispatchEvent(new CustomEvent('theme-change', { detail: configs.THEME }));
    }
    
    if (configs.LOGIN_NOTIFY !== undefined) {
      formState.loginNotification = configs.LOGIN_NOTIFY === 'True' || configs.LOGIN_NOTIFY === 'true' || configs.LOGIN_NOTIFY === true;
      // 保存到本地存储
      localStorage.setItem('loginNotification', formState.loginNotification);
    }
    if (configs.LOGIN_LIMIT !== undefined) {
      formState.loginLimit = configs.LOGIN_LIMIT === 'True' || configs.LOGIN_LIMIT === 'true' || configs.LOGIN_LIMIT === true;
    }
  } catch (error) {
    console.error(t.value('getConfigFailed'), error);
    Message.error(`${t.value('getConfigFailed')}: ${error.message || t.value('unknownError')}`);
  }
};

// ==================== 服务器设置（系统设置）====================

const serverForms = reactive({
  dns: { dns1: '', dns2: '' },
  swap: { size: 0 },
  timezone: { area: 'Asia', zone: 'Shanghai' },
  password: { user: 'root', password: '', confirmPassword: '' }
})

const showMemoryDiskModal = ref(false)
const showHostsModal = ref(false)
const showMiniFileManager = ref(false)
const memoryDiskForm = reactive({ path: '', size: 256 })
const hostsForm = reactive({ domain: '', ip: '' })

const timezoneZoneList = ref([])
const memoryDiskList = ref([])
const hostsList = ref([])

const swapInfoText = computed(() => {
  const s = serverForms.swap
  return `Total: ${s._total || 0} MB, Used: ${s._used || 0} MB, Free: ${s._free || 0} MB`
})

const serverTimezoneText = computed(() => {
  return `${serverForms.timezone.area}/${serverForms.timezone.zone} (${serverForms.timezone._date || ''})`
})

const currentZoneList = computed(() => {
  const area = serverForms.timezone.area
  const found = timezoneZoneList.value.find(item => item.area === area)
  return found ? found.zones : []
})

const memoryDiskColumns = computed(() => [
  { title: t.value('path'), dataIndex: 'path' },
  { title: t.value('size'), dataIndex: 'sizeText' },
  { title: t.value('action'), slotName: 'action', width: 100 }
])

const hostsColumns = computed(() => [
  { title: t.value('domainName'), dataIndex: 'domain' },
  { title: 'IP', dataIndex: 'ip' },
  { title: t.value('status'), dataIndex: 'statusText' },
  { title: t.value('action'), slotName: 'action', width: 180 }
])

const fetchServerSettings = async () => {
  try {
    const res = await getSystemSettings()
    // DNS
    if (res.dns) {
      serverForms.dns.dns1 = res.dns.dns1 || ''
      serverForms.dns.dns2 = res.dns.dns2 || ''
    }
    // Swap
    if (res.swap) {
      serverForms.swap._total = res.swap.total || 0
      serverForms.swap._used = res.swap.used || 0
      serverForms.swap._free = res.swap.free || 0
      serverForms.swap.size = res.swap.size ? Math.round(res.swap.size / 1024 / 1024) : 0
    }
    // Timezone
    if (res.timezone) {
      serverForms.timezone.area = res.timezone.current_area || 'Asia'
      serverForms.timezone.zone = res.timezone.current_zone || 'Shanghai'
      serverForms.timezone._date = res.timezone.date || ''
      if (res.timezone.zone_list) {
        timezoneZoneList.value = res.timezone.zone_list
      }
    }
    // Hosts
    if (res.hosts) {
      hostsList.value = Object.values(res.hosts).map(item => ({
        ...item,
        statusText: item.status === 1 ? 'Enabled' : 'Disabled',
        ip: item.ip || item.domain
      }))
    }
    // Memory disk
    if (res.memory_disk) {
      const mountInfo = res.memory_disk.mount_info || {}
      memoryDiskList.value = Object.keys(mountInfo).map(path => ({
        path,
        ...mountInfo[path],
        sizeText: mountInfo[path].size ? `${mountInfo[path].size} MB` : '-'
      }))
    }
  } catch (error) {
    console.error('获取系统设置失败:', error)
    Message.error(t.value('getConfigFailed'))
  }
}

// DNS
const handleSaveDNS = async () => {
  try {
    const res = await setDNS({ dns1: serverForms.dns.dns1, dns2: serverForms.dns.dns2 })
    Message.success(t.value('configSaveSuccess'))
  } catch (error) {
    Message.error(t.value('configSaveFailed') + ': ' + (error.message || t.value('unknownError')))
  }
}

const handleTestDNS = async () => {
  try {
    const res = await testDNS({ dns1: serverForms.dns.dns1, dns2: serverForms.dns.dns2 })
    if (res.status) {
      Message.success(t.value('dnsAvailable'))
    } else {
      Message.warning(t.value('dnsUnavailable'))
    }
  } catch (error) {
    Message.error(t.value('dnsTestFailed') + ': ' + (error.message || t.value('unknownError')))
  }
}

// Swap
const handleSaveSwap = async () => {
  try {
    const res = await setSwap({ size: serverForms.swap.size })
    Message.success(t.value('configSaveSuccess'))
    await fetchServerSettings()
  } catch (error) {
    Message.error(t.value('configSaveFailed') + ': ' + (error.message || t.value('unknownError')))
  }
}

// Timezone
const handleSaveTimezone = async () => {
  try {
    const res = await setTimezone({ area: serverForms.timezone.area, zone: serverForms.timezone.zone })
    Message.success(t.value('configSaveSuccess'))
    await fetchServerSettings()
  } catch (error) {
    Message.error(t.value('configSaveFailed') + ': ' + (error.message || t.value('unknownError')))
  }
}

const handleSyncTime = async () => {
  try {
    const res = await syncTime()
    Message.success(t.value('timeSyncSuccess'))
    await fetchServerSettings()
  } catch (error) {
    Message.error(t.value('timeSyncFailed') + ': ' + (error.message || t.value('unknownError')))
  }
}

// Password
const handleSavePassword = async () => {
  if (serverForms.password.password !== serverForms.password.confirmPassword) {
    Message.error(t.value('passwordMismatch'))
    return
  }
  try {
    const res = await setSystemPassword({
      user: serverForms.password.user,
      password: serverForms.password.password,
      confirm_password: serverForms.password.confirmPassword
    })
    Message.success(t.value('configSaveSuccess'))
    serverForms.password.password = ''
    serverForms.password.confirmPassword = ''
  } catch (error) {
    Message.error(t.value('configSaveFailed') + ': ' + (error.message || t.value('unknownError')))
  }
}

// Memory disk
const handleCreateMemoryDisk = async () => {
  if (!memoryDiskForm.path) {
    Message.error(t.value('createMemoryDisk'))
    return
  }
  try {
    const res = await createMemoryDisk({ path: memoryDiskForm.path, size: memoryDiskForm.size })
    Message.success(t.value('configSaveSuccess'))
    showMemoryDiskModal.value = false
    await fetchServerSettings()
  } catch (error) {
    Message.error(t.value('configSaveFailed') + ': ' + (error.message || t.value('unknownError')))
  }
}

const handleMiniFileManagerSelect = (data) => {
  if (data.path) {
    memoryDiskForm.path = data.path
  }
  showMiniFileManager.value = false
}

const handleDeleteMemoryDisk = async (path) => {
  try {
    const res = await deleteMemoryDisk({ path })
    Message.success(t.value('configSaveSuccess'))
    await fetchServerSettings()
  } catch (error) {
    Message.error(t.value('configSaveFailed') + ': ' + (error.message || t.value('unknownError')))
  }
}

// Hosts
const handleSaveHosts = async () => {
  if (!hostsForm.domain || !hostsForm.ip) {
    Message.error(t.value('addHost'))
    return
  }
  try {
    const res = await addHosts({ domain: hostsForm.domain, ip: hostsForm.ip })
    Message.success(t.value('configSaveSuccess'))
    showHostsModal.value = false
    await fetchServerSettings()
  } catch (error) {
    Message.error(t.value('configSaveFailed') + ': ' + (error.message || t.value('unknownError')))
  }
}

const handleDeleteHosts = async (domain) => {
  try {
    const res = await deleteHosts({ domain })
    Message.success(t.value('configSaveSuccess'))
    await fetchServerSettings()
  } catch (error) {
    Message.error(t.value('configSaveFailed') + ': ' + (error.message || t.value('unknownError')))
  }
}

const handleToggleHosts = async (domain, act) => {
  try {
    const res = await toggleHosts({ domain, act })
    Message.success(t.value('configSaveSuccess'))
    await fetchServerSettings()
  } catch (error) {
    Message.error(t.value('configSaveFailed') + ': ' + (error.message || t.value('unknownError')))
  }
}

// 确认重启服务
const confirmRestart = async () => {
  try {
    const response = await restartService();
    
    // 检查响应数据 - 由于响应拦截器已经处理过了，直接使用response
    let message = t.value('restartRequestSubmitted');
    if (response && response.message) {
      // 标准结构: { message: "...", status: "..." }
      // 不直接使用后端返回的消息，而是使用前端的国际化消息
      message = t.value('restartRequestSubmitted');
    }
    
    Message.success(message);
    
    // 关闭对话框
    restartModalVisible.value = false;
  } catch (error) {
    console.error(t.value('restartFailed'), error);
    Message.error(`${t.value('restartFailed')}: ${error.message || t.value('unknownError')}`);
    
    // 关闭对话框
    restartModalVisible.value = false;
  }
};

// 取消重启服务
const cancelRestart = () => {
  restartModalVisible.value = false;
};



// 显示证书对话框
const showCertDialog = async () => {
  try {
    const response = await getSSLCert();
    // 确保正确更新响应式数据
    sslCertData.value.cert_content = response.cert_content || '';
    sslCertData.value.key_content = response.key_content || '';
    sslCertData.value.message = response.message || '';
    certModalVisible.value = true;
    
    // 添加一个微任务延迟，确保DOM已完全渲染
    await new Promise(resolve => setTimeout(resolve, 0));
    
    // 初始化编辑器
    if ((activeCertTab.value === 'cert' && certMonacoEditorRef.value && !certMonacoEditor) ||
        (activeCertTab.value === 'key' && keyMonacoEditorRef.value && !keyMonacoEditor)) {
      initCertEditor();
    } else if (certMonacoEditor && keyMonacoEditor) {
      // 如果编辑器已经存在，更新其内容
      if (activeCertTab.value === 'cert') {
        certMonacoEditor.setValue(sslCertData.value.cert_content || '');
      } else {
        keyMonacoEditor.setValue(sslCertData.value.key_content || '');
      }
    }
  } catch (error) {
    Message.error(t.value('getCertFailed') + ': ' + (error.message || t.value('unknownError')));
  }
};

// 处理证书标签页切换
const handleCertTabChange = (key) => {
  activeCertTab.value = key;
  // 添加一个微任务延迟，确保DOM已完全渲染
  setTimeout(() => {
    // 如果编辑器已经初始化，直接更新内容
    if (certMonacoEditor && keyMonacoEditor) {
      if (key === 'cert') {
        certMonacoEditor.setValue(sslCertData.value.cert_content || '');
      } else {
        keyMonacoEditor.setValue(sslCertData.value.key_content || '');
      }
    } else {
      // 否则初始化编辑器
      initCertEditor();
    }
  }, 0);
};

// 初始化证书 Monaco 编辑器
const initCertEditor = async () => {
  // 根据当前激活的标签页初始化对应的编辑器
  if (activeCertTab.value === 'cert') {
    if (!certMonacoEditorRef.value || certMonacoEditor) return;
    
    try {
      // 动态导入monaco-editor
      const monaco = await import('monaco-editor');
      
      // 创建编辑器实例
      certMonacoEditor = monaco.editor.create(certMonacoEditorRef.value, {
        value: sslCertData.value.cert_content || '',
        language: 'plaintext',
        theme: 'vs-dark',
        automaticLayout: true,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        fontSize: 14,
        tabSize: 2,
        readOnly: false,
        fontFamily: 'Consolas, "Courier New", "SFMono-Regular", "Menlo", "Monaco", "Roboto Mono", "Ubuntu Mono", monospace',
        wordWrap: 'on'
      });
    } catch (error) {
      console.error('Failed to load Monaco Editor:', error);
      Message.error(`${t.value('load')} Monaco Editor ${t.value('failed')}`);
    }
  } else if (activeCertTab.value === 'key') {
    if (!keyMonacoEditorRef.value || keyMonacoEditor) return;
    
    try {
      // 动态导入monaco-editor
      const monaco = await import('monaco-editor');
      
      // 创建编辑器实例
      keyMonacoEditor = monaco.editor.create(keyMonacoEditorRef.value, {
        value: sslCertData.value.key_content || '',
        language: 'plaintext',
        theme: 'vs-dark',
        automaticLayout: true,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        fontSize: 14,
        tabSize: 2,
        readOnly: false,
        fontFamily: 'Consolas, "Courier New", "SFMono-Regular", "Menlo", "Monaco", "Roboto Mono", "Ubuntu Mono", monospace',
        wordWrap: 'on'
      });
    } catch (error) {
      console.error('Failed to load Monaco Editor:', error);
      Message.error(`${t.value('load')} Monaco Editor ${t.value('failed')}`);
    }
  }
};

// 关闭证书对话框
const closeCertDialog = () => {
  certModalVisible.value = false;
  
  // 销毁编辑器实例
  if (certMonacoEditor) {
    certMonacoEditor.dispose();
    certMonacoEditor = null;
  }
  
  if (keyMonacoEditor) {
    keyMonacoEditor.dispose();
    keyMonacoEditor = null;
  }
};

// 触发证书文件选择
const triggerCertFileSelect = () => {
  if (certFileInputRef.value) {
    certFileInputRef.value.click();
  }
};

// 处理证书文件选择
const handleCertFileSelect = (e) => {
  const files = Array.from(e.target.files);
  if (files.length === 0) return;

  for (const file of files) {
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target.result;
      const lowerName = file.name.toLowerCase();

      if (lowerName.includes('key')) {
        sslCertData.value.key_content = content;
        if (keyMonacoEditor) {
          keyMonacoEditor.setValue(content);
        }
      } else {
        sslCertData.value.cert_content = content;
        if (certMonacoEditor) {
          certMonacoEditor.setValue(content);
        }
      }
      Message.success(`${t.value('fileUploaded')}: ${file.name}`);
    };
    reader.readAsText(file);
  }

  e.target.value = '';
};

// 保存证书内容
const saveCertContent = async () => {
  try {
    // 从编辑器获取内容
    const certContent = certMonacoEditor ? certMonacoEditor.getValue() : sslCertData.value.cert_content;
    const keyContent = keyMonacoEditor ? keyMonacoEditor.getValue() : sslCertData.value.key_content;
    
    // 调用API更新证书内容
    const response = await updateSSLCert({
      cert_content: certContent,
      key_content: keyContent
    });
    
    Message.success(t.value('configSaveSuccess'));
    
    // 更新响应式数据，以便下次打开时显示最新内容
    sslCertData.value.cert_content = certContent;
    sslCertData.value.key_content = keyContent;
    
    // 不关闭对话框，让用户继续编辑
  } catch (error) {
    console.error('保存证书内容失败:', error);
    Message.error(`${t.value('updateConfigFailed')}: ${error.message || t.value('unknownError')}`);
  }
};

// 处理调试模式开关变化
const handleDebugChange = (value) => {
  // 保存原始值
  originalDebugValue.value = !value;
  // 立即恢复原始值，因为开关已经被切换了
  systemConfig.DEBUG = originalDebugValue.value;
  // 显示确认对话框
  debugConfirmModalVisible.value = true;
};

// 确认修改调试模式
const confirmDebugChange = async () => {
  try {
    // 更新配置为新值
    const newValue = !originalDebugValue.value;
    const response = await updateEnvConfig({ DEBUG: newValue });
    console.log('调试模式更新成功:', response);
    Message.success(t.value('configSaveSuccess'));
    // 重新获取配置以确保同步
    await fetchSystemConfig();
  } catch (error) {
    console.error('调试模式更新失败:', error);
    Message.error(`${t.value('updateConfigFailed')}: ${error.message || t.value('unknownError')}`);
  } finally {
    // 关闭确认对话框
    debugConfirmModalVisible.value = false;
  }
};

// 取消修改调试模式
const cancelDebugChange = () => {
  // 关闭确认对话框，开关状态已经是原始值了
  debugConfirmModalVisible.value = false;
};

// 处理API文档开关变化
const handleApiDocChange = async (value) => {
  try {
    // 直接更新配置
    const response = await updateEnvConfig({ ENABLE_DOCS: value });
    console.log('API文档设置更新成功:', response);
    Message.success(t.value('configSaveSuccess'));
    // 重新获取配置以确保同步
    await fetchSystemConfig();
  } catch (error) {
    console.error('API文档设置更新失败:', error);
    Message.error(`${t.value('updateConfigFailed')}: ${error.message || t.value('unknownError')}`);
    // 恢复原始值
    systemConfig.ENABLE_DOCS = !value;
  }
};

// 显示过期时间设置对话框
const showTimeoutDialog = () => {
  // 设置对话框中的初始值为当前值
  timeoutValue.value = systemConfig.ACCESS_TOKEN_EXPIRE_MINUTES;
  // 显示对话框
  timeoutModalVisible.value = true;
};

// 确认修改过期时间
const confirmTimeoutChange = async () => {
  try {
    // 更新配置，将字符串转换为数字
    const response = await updateEnvConfig({ ACCESS_TOKEN_EXPIRE_MINUTES: parseInt(timeoutValue.value) });
    console.log('过期时间更新成功:', response);
    Message.success(t.value('configSaveSuccess'));
    // 重新获取配置以确保同步
    await fetchSystemConfig();
  } catch (error) {
    console.error('过期时间更新失败:', error);
    Message.error(`${t.value('updateConfigFailed')}: ${error.message || t.value('unknownError')}`);
  } finally {
    // 关闭对话框
    timeoutModalVisible.value = false;
  }
};

// 取消修改过期时间
const cancelTimeoutChange = () => {
  // 关闭对话框
  timeoutModalVisible.value = false;
};

// 显示主机地址保存对话框
const showHostDialog = () => {
  // 保存当前主机地址到临时变量
  hostValue.value = systemConfig.HOST;
  // 显示对话框
  hostModalVisible.value = true;
};

// 确认保存主机地址
const confirmHostSave = async () => {
  try {
    // 更新配置
    const response = await updateEnvConfig({ HOST: systemConfig.HOST });
    console.log('主机地址更新成功:', response);
    Message.success(t.value('configSaveSuccess'));
    // 重新获取配置以确保同步
    await fetchSystemConfig();
  } catch (error) {
    console.error('主机地址更新失败:', error);
    Message.error(`${t.value('updateConfigFailed')}: ${error.message || t.value('unknownError')}`);
  } finally {
    // 关闭对话框
    hostModalVisible.value = false;
  }
};

// 取消保存主机地址
const cancelHostSave = () => {
  // 关闭对话框
  hostModalVisible.value = false;
};

// 显示端口设置对话框
const showPortDialog = () => {
  // 设置对话框中的初始值为当前值，转换为数字类型
  portValue.value = parseInt(systemConfig.PORT) || 8000;
  // 显示对话框
  portModalVisible.value = true;
};

// 确认修改端口
const confirmPortChange = async () => {
  try {
    // 更新配置
    const response = await updateEnvConfig({ PORT: portValue.value });
    console.log('端口更新成功:', response);
    Message.success(t.value('configSaveSuccess'));
    // 重新获取配置以确保同步
    await fetchSystemConfig();
    
    // 添加延迟后自动跳转到新的端口
    setTimeout(() => {
      redirectToNewPort();
    }, 1500);
  } catch (error) {
    console.error('端口更新失败:', error);
    Message.error(`${t.value('updateConfigFailed')}: ${error.message || t.value('unknownError')}`);
  } finally {
    // 关闭对话框
    portModalVisible.value = false;
  }
};

// 取消修改端口
const cancelPortChange = () => {
  // 关闭对话框
  portModalVisible.value = false;
};

// SSL关闭确认对话框
const sslCloseModalVisible = ref(false);

// 安全入口设置对话框
const entranceModalVisible = ref(false);
const entranceValue = ref('');

const originalSSLValue = ref(false);

// 处理SSL开关变化
const handleSSLChange = async (value) => {
  if (value) {
    // 开启SSL，直接触发请求
    try {
      const response = await updateEnvConfig({ SSL_ENABLED: value });
      console.log('SSL开启成功:', response);
      Message.success(t.value('configSaveSuccess'));
      // 重新获取配置以确保同步
      await fetchSystemConfig();
      
      // 添加延迟后自动跳转到HTTPS
      setTimeout(() => {
        redirectToHttps();
      }, 1500);
    } catch (error) {
      console.error('SSL开启失败:', error);
      Message.error(`${t.value('updateConfigFailed')}: ${error.message || t.value('unknownError')}`);
      // 恢复原始值
      systemConfig.SSL_ENABLED = !value;
    }
  } else {
    // 关闭SSL，需要提示警告
    // 立即恢复原始值，因为v-model已经更新了绑定的值
    systemConfig.SSL_ENABLED = true;
    sslCloseModalVisible.value = true;
  }
};

// 确认关闭SSL
const confirmSSLClose = async () => {
  try {
    const response = await updateEnvConfig({ SSL_ENABLED: false });
    console.log('SSL关闭成功:', response);
    Message.success(t.value('configSaveSuccess'));
    // 重新获取配置以确保同步
    await fetchSystemConfig();
    
    // 添加延迟后自动跳转到HTTP
    setTimeout(() => {
      redirectToHttp();
    }, 1500);
  } catch (error) {
    console.error('SSL关闭失败:', error);
    Message.error(`${t.value('updateConfigFailed')}: ${error.message || t.value('unknownError')}`);
  } finally {
    // 关闭对话框
    sslCloseModalVisible.value = false;
  }
};

// 取消关闭SSL
const cancelSSLClose = () => {
  // 关闭对话框，恢复原始值
  sslCloseModalVisible.value = false;
  systemConfig.SSL_ENABLED = true;
};

// 安全入口设置
const showEntranceDialog = () => {
  entranceValue.value = systemConfig.SECURITY_ENTRANCE || '';
  entranceModalVisible.value = true;
};

const confirmEntranceChange = async () => {
  entranceModalVisible.value = false;
  const newEntrance = entranceValue.value;
  try {
    await updateEnvConfig({ SECURITY_ENTRANCE: newEntrance });
    systemConfig.SECURITY_ENTRANCE = newEntrance;
    if (newEntrance) {
      const currentUrl = window.location.href.split('?')[0].split('#')[0];
      const baseUrl = currentUrl.replace(/\/+$/, '');
      Message.success(`${t.value('updateSuccess')} ${t.value('entranceNewUrl')}`);
    } else {
      Message.success(t.value('entranceDisabled'));
    }
  } catch (error) {
    console.error('安全入口设置更新失败:', error);
    Message.error(`${t.value('updateFailed')}: ${error.message || t.value('unknownError')}`);
  }
};

const cancelEntranceChange = () => {
  entranceModalVisible.value = false;
};

// 自动跳转到HTTPS
const redirectToHttps = () => {
  try {
    // 获取当前URL信息
    const currentUrl = new URL(window.location.href);
    // 获取配置的端口，如果没有配置则使用当前端口
    const port = systemConfig.PORT || currentUrl.port || (currentUrl.protocol === 'https:' ? '443' : '80');
    
    // 构造新的HTTPS URL
    let newUrl = `https://${currentUrl.hostname}`;
    
    // 如果端口不是默认的443，则添加端口号
    if (port && port !== '443') {
      newUrl += `:${port}`;
    }
    
    // 保持路径和其他参数
    newUrl += currentUrl.pathname + currentUrl.search + currentUrl.hash;
    
    // 跳转到新的URL
    window.location.replace(newUrl);
  } catch (error) {
    console.error('跳转到HTTPS失败:', error);
    Message.error('跳转到HTTPS失败，请手动访问');
  }
};

// 自动跳转到HTTP
const redirectToHttp = () => {
  try {
    // 获取当前URL信息
    const currentUrl = new URL(window.location.href);
    // 获取配置的端口，如果没有配置则使用当前端口
    const port = systemConfig.PORT || currentUrl.port || (currentUrl.protocol === 'http:' ? '80' : '8000');
    
    // 构造新的HTTP URL
    let newUrl = `http://${currentUrl.hostname}`;
    
    // 如果端口不是默认的80，则添加端口号
    if (port && port !== '80') {
      newUrl += `:${port}`;
    }
    
    // 保持路径和其他参数
    newUrl += currentUrl.pathname + currentUrl.search + currentUrl.hash;
    
    // 跳转到新的URL
    window.location.replace(newUrl);
  } catch (error) {
    console.error('跳转到HTTP失败:', error);
    Message.error('jump to http failed');
  }
};

// 自动跳转到新的端口
const redirectToNewPort = () => {
  try {
    // 获取当前URL信息
    const currentUrl = new URL(window.location.href);
    // 获取配置的端口
    const port = systemConfig.PORT || currentUrl.port || '8000';
    
    // 构造新的URL
    let newUrl = `${currentUrl.protocol}//${currentUrl.hostname}`;
    
    // 如果端口不是默认端口，则添加端口号
    if ((currentUrl.protocol === 'https:' && port !== '443') || 
        (currentUrl.protocol === 'http:' && port !== '80')) {
      newUrl += `:${port}`;
    }
    
    // 保持路径和其他参数
    newUrl += currentUrl.pathname + currentUrl.search + currentUrl.hash;
    
    // 跳转到新的URL
    window.location.replace(newUrl);
  } catch (error) {
    console.error('跳转到新端口失败:', error);
    Message.error('jump to new port failed');
  }
};

// 保存应用名称
const saveAppName = async () => {
  try {
    const response = await updateEnvConfig({ APP_NAME: systemConfig.APP_NAME });
    console.log('Save App Name Response:', response);
    Message.success(t.value('configSaveSuccess'));
  } catch (error) {
    console.error('保存应用名称失败:', error);
    Message.error(t.value('configSaveFailed') + ': ' + (error.message || t.value('unknownError')));
  }
};

// 保存时区
const saveTimezone = async () => {
  try {
    const response = await updateEnvConfig({ TIMEZONE: systemConfig.TIMEZONE });
    console.log('Save Timezone Response:', response);
    Message.success(t.value('configSaveSuccess'));
  } catch (error) {
    console.error('保存时区失败:', error);
    Message.error(t.value('configSaveFailed') + ': ' + (error.message || t.value('unknownError')));
  }
};

const handleSaveDomainBinding = async () => {
  try {
    const response = await updateEnvConfig({ DOMAIN_BINDING: systemConfig.DOMAIN_BINDING });
    Message.success(t.value('configSaveSuccess'));
  } catch (error) {
    Message.error(t.value('configSaveFailed') + ': ' + (error.message || t.value('unknownError')));
  }
};

const handleSaveAllowIPs = async () => {
  try {
    await updateEnvConfig({ ALLOW_IPS: systemConfig.ALLOW_IPS });
    Message.success(t.value('configSaveSuccess'));
  } catch (error) {
    Message.error(t.value('configSaveFailed') + ': ' + (error.message || t.value('unknownError')));
  }
};

const handleSaveApiOpen = async () => {
  try {
    await updateEnvConfig({ API_OPEN: systemConfig.API_OPEN });
    Message.success(t.value('configSaveSuccess'));
  } catch (error) {
    Message.error(t.value('configSaveFailed') + ': ' + (error.message || t.value('unknownError')));
  }
};

const handleGenerateApiKey = async () => {
  try {
    const res = await generateApiKey();
    systemConfig.API_KEY = res.data.API_KEY;
    apiConfigForm.API_KEY = res.data.API_KEY;
    Message.success(t.value('generateApiKeySuccess'));
  } catch (error) {
    Message.error(t.value('generateApiKeyFailed') + ': ' + (error.message || t.value('unknownError')));
  }
};

const handleCopyApiKey = async () => {
  const key = apiConfigForm.API_KEY || systemConfig.API_KEY;
  if (!key) {
    Message.warning(t.value('generateApiKeyFirst'));
    return;
  }
  try {
    await navigator.clipboard.writeText(key);
    Message.success('Copy success');
  } catch {
    const textarea = document.createElement('textarea');
    textarea.value = key;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand('copy');
      Message.success('Copy success');
    } catch {
      Message.error('Copy failed, please copy manually');
    }
    document.body.removeChild(textarea);
  }
};

const handleOpenApiConfigDialog = () => {
  apiConfigForm.API_KEY = systemConfig.API_KEY;
  apiConfigForm.API_IP_WHITELIST = systemConfig.API_IP_WHITELIST;
  apiConfigForm.API_KEY_VALIDITY_TIME = systemConfig.API_KEY_VALIDITY_TIME;
  apiConfigModalVisible.value = true;
};

const handleSaveApiConfig = async () => {
  try {
    await updateEnvConfig({
      API_KEY: apiConfigForm.API_KEY,
      API_IP_WHITELIST: apiConfigForm.API_IP_WHITELIST,
      API_KEY_VALIDITY_TIME: apiConfigForm.API_KEY_VALIDITY_TIME
    });
    systemConfig.API_KEY = apiConfigForm.API_KEY;
    systemConfig.API_IP_WHITELIST = apiConfigForm.API_IP_WHITELIST;
    systemConfig.API_KEY_VALIDITY_TIME = apiConfigForm.API_KEY_VALIDITY_TIME;
    apiConfigModalVisible.value = false;
    Message.success(t.value('configSaveSuccess'));
  } catch (error) {
    Message.error(t.value('configSaveFailed') + ': ' + (error.message || t.value('unknownError')));
  }
};

const handleCancelApiConfig = () => {
  apiConfigModalVisible.value = false;
};

// 组件挂载时设置当前语言和主题
onMounted(() => {
  // 先设置默认值，稍后会被API返回的值覆盖
  formState.language = getCurrentLocale();
  
  // 获取当前用户信息和系统配置（优先从API获取配置）
  fetchCurrentUser().then(() => {
    fetchSystemConfig();
    fetchServerSettings();
  });
});

const saveSettings = () => {
  // 在这里处理保存逻辑
};
</script>

<style scoped>
.settings-container {
  padding: 20px;
}

:deep(.arco-form) {
  width: 100%;
  max-width: 600px;
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

.content-area {
  margin-top: 20px;
}

/* 调整表单项样式，使标签和控件在同一行 */
:deep(.form-item .arco-form-item-label) {
  white-space: nowrap;
  padding-right: 10px;
  width: 130px; /* 增加标签宽度以适应英文文本 */
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 在小屏幕上调整布局 */
@media (max-width: 768px) {
  :deep(.form-item .arco-form-item-label) {
    width: 110px;
  }
  
  :deep(.arco-form) {
    max-width: 100%;
  }
}

/* 在超小屏幕上使用垂直布局 */
@media (max-width: 480px) {
  :deep(.form-item .arco-form-item-label) {
    width: 100%;
    text-align: left;
    margin-bottom: 5px;
  }
  
  :deep(.arco-form-item-control) {
    width: 100%;
  }
}

.desc {
  margin-top: 4px;
  color: #8c8c8c;
  font-size: 12px;
}

.entrance-hint {
  font-size: 12px;
  color: var(--color-text-3);
  margin-top: 4px;
  line-height: 1.5;
}

/* Monaco Editor 容器样式 */
.monaco-editor-container {
  height: 400px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  overflow: hidden;
  background: #1e1e1e;
}

</style>

<!-- 使用非scoped样式确保在所有主题下保持一致 -->
<style>
/* 确保卡片容器在所有主题下保持白色背景 */
.settings-container :deep(.arco-card) {
  background: #ffffff !important;
  border: 1px solid #ebebeb !important;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
}

/* 确保表单标签在所有主题下保持黑色文字 */
.settings-container :deep(.arco-form-item-label) {
  color: #333 !important;
}

/* 确保描述文字在所有主题下保持灰色 */
.desc {
  color: #8c8c8c !important;
}

/* 确保选择框在所有主题下保持白色背景 */
.settings-container :deep(.arco-select-view) {
  background-color: #ffffff !important;
  border-color: #ebebeb !important;
  color: #333 !important;
}

.settings-container :deep(.arco-select-view:hover) {
  background-color: #ffffff !important;
  border-color: #cccccc !important;
}

.settings-container :deep(.arco-select-view:focus) {
  background-color: #ffffff !important;
  border-color: #3c7eff !important;
  box-shadow: 0 0 0 2px rgba(64, 132, 255, 0.2) !important;
}

.settings-container :deep(.arco-select-view-single .arco-select-view-input) {
  color: #333 !important;
}

.settings-container :deep(.arco-select-view-single .arco-select-view-input::placeholder) {
  color: #999 !important;
}

/* API文档链接样式 */
.api-doc-link {
  font-family: inherit;
  font-size: inherit;
  color: #1890ff;
  text-decoration: none;
}

.api-doc-link:hover {
  color: #40a9ff;
  text-decoration: underline;
}

/* 证书内容样式 */
.cert-content {
  max-height: 600px;
  overflow: auto;
}

.cert-upload-area {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.cert-upload-hint {
  font-size: 12px;
  color: var(--color-text-3);
}

.cert-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.cert-text {
  background: #000000;
  padding: 15px;
  border-radius: 4px;
  max-height: 400px;
  overflow: auto;
  border: 1px solid #333;
}

.cert-text pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: Consolas, "Courier New", "SFMono-Regular", "Menlo", "Monaco", "Roboto Mono", "Ubuntu Mono", monospace;
  font-size: 13px;
  line-height: 1.5;
  color: #ffffff;
  background: transparent;
}

/* IP绑定提示文字 */
.ip-hint {
  color: #faad14 !important;
  font-size: 12px;
  margin: -10px 0 10px 100px;
  line-height: 1.4;
}

/* 服务器设置标签页布局 */
.server-tabs {
  min-height: 400px;
}

:deep(.server-tabs .arco-tabs-content) {
  padding: 8px 20px;
}

:deep(.server-tabs .arco-tabs-content-inner) {
  padding-top: 0;
}

:deep(.server-tabs .arco-form-item) {
  margin-bottom: 16px;
}

/* 空状态居中 */
:deep(.arco-empty) {
  padding: 20px 0;
}
</style>