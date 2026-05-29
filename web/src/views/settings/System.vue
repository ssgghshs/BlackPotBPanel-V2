<template>
  <a-card class="settings-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('system') }}</span>
      </div>
    </template>

    <!--  内容区域  -->
    <div class="content-area">
      <a-tabs :default-active-key="'panel'" :tab-position="'top'" type="card" >
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
              <a-form-item :label="t('ipAddress') + ':'" class="form-item">
                <a-input v-model="systemConfig.HOST" :placeholder="t('enterHost')" />
                <a-button type="primary" size="small" style="margin-left: 10px;" @click="showHostDialog">{{ t('save') }}</a-button>
              </a-form-item>
              <div class="ip-hint">{{ t('ipHint') }}</div>
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
      <a-button type="primary" style="margin-top: 10px;" @click="saveCertContent">{{ t('save') }}</a-button>
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
  </a-card>
</template>

<script setup>
import { reactive, onMounted, computed, ref } from 'vue';
import { t, changeLocale, getCurrentLocale } from '../../utils/locale'
import { Message} from '@arco-design/web-vue';
import { IconLink } from '@arco-design/web-vue/es/icon';
import { getEnvConfig, updateEnvConfig, restartService, getSSLCert, updateSSLCert } from '../../api/system';
// 导入用户状态和函数
import { isAdmin, fetchCurrentUser as fetchCurrentUserStore } from '../../stores/user';

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
  SECURITY_ENTRANCE: ''
});

// 当前用户信息（保留用于兼容性，实际使用store中的currentUser）
const currentUser = reactive({
  username: '',
  is_admin: false
});

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
    console.error('获取证书内容失败:', error);
    Message.error('获取证书内容失败: ' + (error.message || '未知错误'));
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

// 组件挂载时设置当前语言和主题
onMounted(() => {
  // 先设置默认值，稍后会被API返回的值覆盖
  formState.language = getCurrentLocale();
  
  // 获取当前用户信息和系统配置（优先从API获取配置）
  fetchCurrentUser().then(() => {
    fetchSystemConfig();
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
</style>