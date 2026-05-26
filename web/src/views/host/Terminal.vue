<template>
  <!-- 外层容器 -->
  <div class="terminal-container" :class="{ 'fullscreen': isFullscreen }">
    <div class="terminal-layout" :class="{ 'fullscreen-layout': isFullscreen }">
      <!-- 标签页区域 -->
      <div class="tabs-container">
        <a-tabs type="card-gutter" :editable="true" @delete="handleDelete" auto-switch v-model:active-key="activeKey">
          <template #extra>
            <!-- 非全屏状态下显示添加按钮 -->
            <a-dropdown v-if="!isFullscreen" @select="handleHostSelect" trigger="click">
              <a-button type="text" size="small">
                <template #icon>
                  <icon-plus />
                </template>
              </a-button>
              <template #content>
                <a-doption v-for="host in hostData" :key="host.id" :value="host">
                  {{ host.address }}
                </a-doption>
                <a-doption v-if="hostData.length === 0" disabled>
                  {{ t('noHostsAvailable') }}
                </a-doption>
              </template>
            </a-dropdown>
          </template>
          <a-tab-pane v-for="(item, index) of data" :key="item.key" :title="item.title" :closable="data.length > 1">
            <!-- 终端内容 -->
            <div class="terminal-content" v-if="item.terminal">
              <div class="terminal-wrapper">
                <!-- 固定的终端背景框 -->
                <div :ref="el => setTerminalRef(el, item.key)" class="terminal-element"></div>
                
                <!-- 在终端背景框上显示状态信息 -->
                <div v-if="item.connectionStatus === 'connecting'" class="terminal-overlay">
                  <div class="status-info">
                    <a-spin />
                    <span>{{ t('connectingToHost') }}...</span>
                  </div>
                </div>
                
                <div v-else-if="item.connectionStatus === 'error'" class="terminal-overlay">
                  <div class="status-info">
                    <a-alert type="error" :title="t('connectionFailed')">
                      {{ item.errorMessage || t('connectionFailedMessage') }}
                    </a-alert>
                    <div class="action-buttons">
                      <a-button type="primary" @click="initConnection(item)">
                        {{ t('retry') }}
                      </a-button>
                    </div>
                  </div>
                </div>
               
                <!-- 工具栏始终显示 -->
                <div class="terminal-toolbar">
                  <a-button 
                    type="primary" 
                    size="small" 
                    @click="initConnection(item)" 
                    :disabled="item.connectionStatus === 'connecting' || item.connectionStatus === 'connected'"
                  >
                    {{ t('connect') }}
                  </a-button>
                  <a-button 
                    type="primary" 
                    size="small" 
                    @click="handleReconnect(item)" 
                    :disabled="item.connectionStatus === 'connecting'"
                  >
                    {{ t('reconnect') }}
                  </a-button>
                  <a-button 
                    type="outline" 
                    size="small" 
                    @click="handleDisconnect(item)"
                    :disabled="item.connectionStatus !== 'connected'"
                  >
                    {{ t('disconnect') }}
                  </a-button>
                  <a-button 
                    type="outline" 
                    size="small" 
                    @click="clearTerminal(item)"
                  >
                    {{ t('clear') }}
                  </a-button>
                  <a-button 
                    type="outline" 
                    size="small" 
                    @click="toggleFullscreen"
                    :title="isFullscreen ? t('exitFullscreen') : t('enterFullscreen')"
                  >
                    <template #icon>
                      <icon-fullscreen-exit v-if="isFullscreen" />
                      <icon-fullscreen v-else />
                    </template>
                  </a-button>
                </div>
              </div>
            </div>
            <div v-else class="placeholder-content">
              {{ item.content }}
            </div>
          </a-tab-pane>
        </a-tabs>
      </div>
      
      <!-- 侧边栏收起/展开按钮 -->
      <div class="sidebar-toggle" @click="toggleSidebar">
        <icon-left-circle v-if="!sidebarCollapsed" class="toggle-icon" />
        <icon-right-circle v-else class="toggle-icon" />
      </div>
      
      <!-- 侧边栏 -->
      <div v-if="!sidebarCollapsed" class="sidebar">
        <a-tabs type="card" default-active-key="1" lazy-load>
          <a-tab-pane key="1" :title="t('hosts')">
            <a-table :columns="columns" :data="hostData" :loading="loading" :pagination="false" :scroll="{ y: 400 }">
              <template #actions="{ record }">
                <a-link @click="connectToHost(record)">{{ t('connect') }}</a-link>
              </template>
            </a-table>
          </a-tab-pane>
          <a-tab-pane key="2" :title="t('commands')">
            <div style="margin-bottom: 16px; text-align: right;">
              <a-button type="primary" size="small" @click="showAddCommandModal">
                <template #icon>
                  <icon-plus />
                </template>
                {{ t('addCommand') }}
              </a-button>
            </div>
            <a-table :columns="commandColumns" :data="commandData" :loading="commandLoading" :pagination="false" :scroll="{ y: 400 }">
              <template #actions="{ record }">
                <a-link @click="executeCommand(record)">{{ t('execute') }}</a-link>
                <a-link @click="editCommand(record)">{{ t('edit') }}</a-link>
                <a-link status="danger" @click="deleteCommand(record)">{{ t('delete') }}</a-link>
              </template>
            </a-table>
          </a-tab-pane>
        </a-tabs>
      </div>

    </div>
  </div>

  <!-- 添加命令弹窗 -->
  <a-modal
    v-model:visible="addCommandModalVisible"
    :title="t('addCommand')"
    :ok-loading="addCommandLoading"
    @ok="submitAddCommand"
    @cancel="closeAddCommandModal"
    :width="500"
  >
    <a-form :model="addCommandForm" layout="vertical">
      <a-form-item :label="t('commandName')" required>
        <a-input
          v-model="addCommandForm.name"
          :placeholder="t('pleaseEnterCommandName')"
          :max-length="100"
          show-word-limit
        />
      </a-form-item>
      <a-form-item :label="t('commandContent')" required>
          <a-textarea 
            v-model="addCommandForm.command"
            :placeholder="t('pleaseEnterCommandContent')" 
            allow-clear
            :rows="8"
            :max-length="1000"
            show-word-limit
          />
      </a-form-item>
    </a-form>
  </a-modal>

  <!-- 编辑命令弹窗 -->
  <a-modal
    v-model:visible="editCommandModalVisible"
    :title="t('editCommand')"
    :ok-loading="editCommandLoading"
    @ok="submitEditCommand"
    @cancel="closeEditCommandModal"
    :width="500"
  >
    <a-form :model="editCommandForm" layout="vertical">
      <a-form-item :label="t('commandName')" required>
        <a-input
          v-model="editCommandForm.name"
          :placeholder="t('pleaseEnterCommandName')"
          :max-length="100"
          show-word-limit
        />
      </a-form-item>
      <a-form-item :label="t('commandContent')" required>
          <a-textarea 
            v-model="editCommandForm.command"
            :placeholder="t('pleaseEnterCommandContent')" 
            allow-clear
            :rows="8"
            :max-length="1000"
            show-word-limit
          />
      </a-form-item>
    </a-form>
  </a-modal>

</template>
<script>
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue';
import { Table, Button, Message, Dropdown, Modal, Form, Input } from '@arco-design/web-vue';
import { IconPlus, IconLeftCircle, IconRightCircle, IconFullscreen, IconFullscreenExit } from '@arco-design/web-vue/es/icon';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { getHosts, getHostCommands, createHostCommand, updateHostCommand, deleteHostCommand, generateTerminalToken, connectTerminal } from '../../api/host';
import { t } from '../../utils/locale';
import * as monaco from 'monaco-editor';

export default {
  components: {
    'a-table': Table,
    'a-button': Button,
    'a-dropdown': Dropdown,
    'a-doption': Dropdown.Option,
    'a-modal': Modal,
    'a-form': Form,
    'a-form-item': Form.Item,
    'a-input': Input,
    'a-textarea': Input,

    'icon-plus': IconPlus,
    'icon-left-circle': IconLeftCircle,
    'icon-right-circle': IconRightCircle,
    'icon-fullscreen': IconFullscreen,
    'icon-fullscreen-exit': IconFullscreenExit,
  },
  setup() {
    // 表格列定义 - 只保留地址和操作两列
    const columns = computed(() => [
      {
        title: t.value('hostAddress'),
        dataIndex: 'address',
        width: 180,
        align: 'left' // 主机地址列靠左对齐
      },
      {
        title: t.value('actions'),
        slotName: 'actions',
        width: 120,
        align: 'right' // 操作列靠右对齐
      }
    ]);
    
    const hostData = ref([]);
    const loading = ref(false);
    const terminalRefs = ref({});
    const activeKey = ref('1'); // 当前激活的标签页key
    const sidebarCollapsed = ref(false); // 侧边栏收起状态
    const isFullscreen = ref(false); // 全屏状态
    const showHostModal = ref(false); // 主机选择弹窗状态
    const data = ref([
      {
        key: '1',
        title: 'Localhost',
        content: 'Localhost terminal',
        terminal: true,
        hostInfo: null,
        connectionStatus: 'disconnected', // connecting, connected, disconnected, error
        errorMessage: '',
        disconnectReason: '',
        websocket: null,
        isConnecting: false,
        connectTimeout: null,
        term: null,
        fitAddon: null
      }
    ]);

    // 设置终端引用
    const setTerminalRef = (el, key) => {
      if (el) {
        terminalRefs.value[key] = el;
      }
    };

    // 获取主机列表
    const fetchHosts = async () => {
      try {
        loading.value = true;
        const response = await getHosts();
        console.log('API响应数据:', response);
        // 根据实际API响应结构调整
        let hosts = [];
        
        if (response && Array.isArray(response)) {
          // 如果响应直接是数组
          hosts = response;
        } else if (response && response.data && Array.isArray(response.data)) {
          // 如果响应包含data字段且为数组
          hosts = response.data;
        } else {
          // 如果以上都不匹配，使用空数组
          hosts = [];
        }
        
        hostData.value = hosts;
        console.log('处理后的主机数据:', hostData.value);
        
        // 自动连接本机终端（127.0.0.1）
        const localhost = hosts.find(host => host.address === '127.0.0.1');
        if (localhost) {
          // 更新第一个标签页的主机信息
          data.value[0].hostInfo = localhost;
          data.value[0].title = localhost.address;
          // 自动连接
          nextTick(() => {
            initConnection(data.value[0]);
          });
        }
      } catch (error) {
        console.error('获取主机列表失败:', error);
      } finally {
        loading.value = false;
      }
    };

    // 初始化连接
    const initConnection = async (tabItem) => {
      if (tabItem.isConnecting) return;
      
      try {
        tabItem.isConnecting = true;
        tabItem.connectionStatus = 'connecting';
        tabItem.errorMessage = '';
        tabItem.disconnectReason = '';
        
        const tokenResponse = await generateTerminalToken(tabItem.hostInfo.id);
        if (!tokenResponse.success || !tokenResponse.token) {
          throw new Error('Failed to generate terminal token');
        }
        
        tabItem.websocket = connectTerminal(tabItem.hostInfo.id, tokenResponse.token);
        
        tabItem.websocket.onopen = () => handleWebSocketOpen(tabItem);
        tabItem.websocket.onmessage = (event) => handleWebSocketMessage(tabItem, event);
        tabItem.websocket.onclose = (event) => handleWebSocketClose(tabItem, event);
        tabItem.websocket.onerror = (error) => handleWebSocketError(tabItem, error);
      } catch (error) {
        console.error('连接失败:', error);
        tabItem.connectionStatus = 'error';
        tabItem.errorMessage = error.message || t.value('connectionFailedMessage');
        Message.error(t.value('connectionFailed') + ': ' + (error.message || t.value('unknownError')));
      } finally {
        tabItem.isConnecting = false;
      }
    };

    // WebSocket 打开
    const handleWebSocketOpen = (tabItem) => {
      tabItem.connectionStatus = 'connected';
      
      nextTick(() => {
        initializeTerminal(tabItem);
      });
      Message.success(t.value('connectionSuccessful'));
    };

    // WebSocket 消息
    const handleWebSocketMessage = (tabItem, event) => {
      if (tabItem.term) {
        try {
          const data = JSON.parse(event.data);
          // 只处理错误消息
          if (data && typeof data === 'object' && data.error) {
            tabItem.term.write(`\r\n\x1b[1;31m*** 错误: ${data.error} ***\x1b[0m\r\n`);
            return;
          }
        } catch {
          // JSON 解析失败，说明是普通文本
        }
        // 所有非错误消息都写入终端
        try {
          tabItem.term.write(event.data);
        } catch (e) {
          console.warn('Terminal write error:', e);
        }
      }
    };

    // WebSocket 关闭
    const handleWebSocketClose = (tabItem, event) => {
      tabItem.connectionStatus = 'disconnected';
      tabItem.disconnectReason = t.value('userDisconnected');
    };

    // WebSocket 错误
    const handleWebSocketError = (tabItem, error) => {
      console.error('WebSocket错误:', error);
      tabItem.connectionStatus = 'error';
      tabItem.errorMessage = error.message || t.value('connectionFailedMessage');
      Message.error(t.value('connectionFailed') + ': ' + (error.message || t.value('unknownError')));
    };



    // 初始化终端
    const initializeTerminal = (tabItem) => {
      // 获取终端引用元素
      const terminalElement = terminalRefs.value[tabItem.key];
      if (!terminalElement) {
        console.error('Terminal element not found for key:', tabItem.key);
        return;
      }
      
      if (tabItem.term) {
        tabItem.term.dispose();
        tabItem.term = null;
      }
      
      tabItem.term = new Terminal({
        cursorBlink: true,
        fontSize: 14,
        fontFamily: 'Consolas, "Courier New", "SFMono-Regular", "Menlo", "Monaco", "Roboto Mono", "Ubuntu Mono", monospace',
        theme: {
          background: '#000000',
          foreground: '#ffffff',
          cursor: '#ffffff',
          selectionBackground: '#264f78',
          selectionForeground: '#ffffff',
          cursorAccent: '#000000',
          black: '#000000',
          red: '#cd3131',
          green: '#0dbc79',
          yellow: '#e5e510',
          blue: '#2472c8',
          magenta: '#bc3fbc',
          cyan: '#11a8cd',
          white: '#e5e5e5',
          brightBlack: '#666666',
          brightRed: '#f14c4c',
          brightGreen: '#23d18b',
          brightYellow: '#f5f543',
          brightBlue: '#3b8eea',
          brightMagenta: '#d670d6',
          brightCyan: '#29b8db',
          brightWhite: '#e5e5e5',
        },
        allowTransparency: false,
        scrollback: 5000,
        fontWeight: 'normal',
        fontWeightBold: 'bold',
        lineHeight: 1.2,
        letterSpacing: 0,
      });
      
      tabItem.fitAddon = new FitAddon();
      tabItem.term.loadAddon(tabItem.fitAddon);
      
      // 清空终端元素内容并添加终端
      terminalElement.innerHTML = '';
      tabItem.term.open(terminalElement);
      
      // 发送用户输入到后端（不进行本地回显，由后端返回）
      tabItem.term.onData((data) => {
        if (tabItem.websocket && tabItem.websocket.readyState === WebSocket.OPEN) {
          const message = JSON.stringify({ type: 'input', data: data });
          tabItem.websocket.send(message);
        }
      });

      // 特殊按键处理
      tabItem.term.attachCustomKeyEventHandler((event) => {
        // 处理 Ctrl+C 特殊情况
        if (event.ctrlKey && event.key === 'c' && event.type === 'keydown') {
          if (tabItem.websocket && tabItem.websocket.readyState === WebSocket.OPEN) {
            const message = JSON.stringify({ type: 'input', data: '\x03' });
            tabItem.websocket.send(message);
            event.preventDefault();
            return false;
          }
        }
        return true;
      });

      // 调整大小
      tabItem.term.onResize(() => {
        sendResize(tabItem);
      });

      const resizeObserver = new ResizeObserver(() => {
        if (tabItem.fitAddon) {
          try {
            tabItem.fitAddon.fit();
          } catch (e) {
            console.warn('Fit addon error:', e);
          }
        }
      });

      if (terminalElement?.parentElement) {
        resizeObserver.observe(terminalElement.parentElement);
      }

    const handleWindowResize = () => {
        if (tabItem.fitAddon) {
          try {
            tabItem.fitAddon.fit();
          } catch (e) {
            console.warn('Fit addon error:', e);
          }
        }
      };
      window.addEventListener('resize', handleWindowResize);
      window.handleWindowResize = handleWindowResize;

      // 延迟执行fit以确保DOM已经渲染完成
      setTimeout(() => {
        if (tabItem.fitAddon) {
          try {
            tabItem.fitAddon.fit();
          } catch (e) {
            console.warn('Initial fit error:', e);
          }
        }
        sendResize(tabItem);
      }, 100);
    };

    // 发送大小
    const sendResize = (tabItem) => {
      if (tabItem.websocket && tabItem.websocket.readyState === WebSocket.OPEN && tabItem.term) {
        const dimensions = { cols: tabItem.term.cols, rows: tabItem.term.rows };
        const message = JSON.stringify({ type: 'resize', data: dimensions });
        tabItem.websocket.send(message);
      }
    };

    // 清屏
    const clearTerminal = (tabItem) => {
      if (tabItem.term) {
        tabItem.term.clear();
      }
    };

    // 重连
    const handleReconnect = (tabItem) => {
      handleDisconnect(tabItem);
      if (tabItem.connectTimeout) clearTimeout(tabItem.connectTimeout);
      tabItem.connectTimeout = setTimeout(() => {
        initConnection(tabItem);
      }, 500);
    };

    // 断开
    const handleDisconnect = (tabItem) => {
      tabItem.connectionStatus = 'disconnected';
      tabItem.disconnectReason = t.value('userDisconnected');
      tabItem.isConnecting = false;

      if (tabItem.connectTimeout) {
        clearTimeout(tabItem.connectTimeout);
        tabItem.connectTimeout = null;
      }

      if (tabItem.websocket) {
        tabItem.websocket.close();
        tabItem.websocket = null;
      }

      if (window.handleWindowResize) {
        window.removeEventListener('resize', window.handleWindowResize);
        window.handleWindowResize = null;
      }

      if (tabItem.term) {
        try {
          tabItem.term.dispose();
        } catch (e) {
          console.warn('Terminal dispose error:', e);
        }
        tabItem.term = null;
      }

      if (tabItem.fitAddon) {
        try {
          tabItem.fitAddon.dispose();
        } catch (e) {
          console.warn('FitAddon dispose error:', e);
        }
        tabItem.fitAddon = null;
      }
    };

    // 处理主机选择
    const handleHostSelect = (host) => {
      console.log('选择主机:', host.address);
      
      // 计算同一主机的连接数量，用于生成唯一标题
      const sameHostCount = data.value.filter(item => 
        item.hostInfo && item.hostInfo.id === host.id
      ).length;
      
      // 生成唯一的标签页标题
      const title = sameHostCount > 0 ? `${host.address} (${sameHostCount + 1})` : host.address;
      
      // 添加新的标签页
      const newKey = `${Date.now()}-${Math.random()}`;
      const newTab = {
        key: newKey,
        title: title,
        content: '',
        terminal: true,
        hostInfo: host,
        connectionStatus: 'disconnected',
        errorMessage: '',
        disconnectReason: '',
        websocket: null,
        isConnecting: false,
        connectTimeout: null,
        term: null,
        fitAddon: null
      };
      
      data.value.push(newTab);
      
      // 自动选中新添加的标签页
      activeKey.value = newTab.key;
      
      // 自动连接到选择的主机
      nextTick(() => {
        initConnection(newTab);
      });
    };
    
    const handleDelete = (key) => {
      // 先断开连接
      const tabItem = data.value.find(item => item.key === key);
      if (tabItem) {
        handleDisconnect(tabItem);
      }
      
      // 只有当标签页数量大于1时才能删除
      if (data.value.length > 1) {
        // 如果删除的是当前激活的标签页，需要切换到其他标签页
        if (activeKey.value === key) {
          const currentIndex = data.value.findIndex(item => item.key === key);
          // 优先选择下一个标签页，如果没有则选择上一个
          const nextTab = data.value[currentIndex + 1] || data.value[currentIndex - 1];
          if (nextTab) {
            activeKey.value = nextTab.key;
          }
        }
        
        data.value = data.value.filter(item => item.key !== key);
        
        // 如果删除后只剩一个标签页，确保它被选中
        if (data.value.length === 1) {
          activeKey.value = data.value[0].key;
        }
      }
    };
    
    const connectToHost = (record) => {
      console.log('连接到主机:', record.address);
      
      // 计算同一主机的连接数量，用于生成唯一标题
      const sameHostCount = data.value.filter(item => 
        item.hostInfo && item.hostInfo.id === record.id
      ).length;
      
      // 生成唯一的标签页标题
      const title = sameHostCount > 0 ? `${record.address} (${sameHostCount + 1})` : record.address;
      
      // 添加新的标签页，标题为主机地址
      const newKey = `${Date.now()}-${Math.random()}`;
      const newTab = {
        key: newKey,
        title: title,
        content: '',
        terminal: true,
        hostInfo: record,
        connectionStatus: 'disconnected',
        errorMessage: '',
        disconnectReason: '',
        websocket: null,
        isConnecting: false,
        connectTimeout: null,
        term: null,
        fitAddon: null
      };
      
      data.value.push(newTab);
      
      // 自动选中新添加的标签页
      activeKey.value = newTab.key;
      
      // 自动连接到选择的主机
      nextTick(() => {
        initConnection(newTab);
      });
    };

    // 切换侧边栏收起状态
    const toggleSidebar = () => {
      sidebarCollapsed.value = !sidebarCollapsed.value;
    };

    // 切换全屏状态
    const toggleFullscreen = () => {
      isFullscreen.value = !isFullscreen.value;
      
      // 全屏时需要重新调整终端大小
      nextTick(() => {
        const currentTab = data.value.find(item => item.key === activeKey.value);
        if (currentTab && currentTab.fitAddon) {
          setTimeout(() => {
            try {
              currentTab.fitAddon.fit();
            } catch (e) {
              console.warn('Fullscreen fit error:', e);
            }
          }, 100);
        }
      });
    };

    // 处理添加按钮点击
    const handleAddClick = () => {
      if (isFullscreen.value) {
        // 全屏状态下显示弹窗
        showHostModal.value = true;
        // 确保弹窗在全屏容器之上
        nextTick(() => {
          const modalWrapper = document.querySelector('.arco-modal-wrapper');
          const modalMask = document.querySelector('.arco-modal-mask');
          if (modalWrapper) {
            modalWrapper.style.zIndex = '100000';
          }
          if (modalMask) {
            modalMask.style.zIndex = '99999';
          }
        });
      }
      // 非全屏状态下使用原有的下拉菜单，不需要额外处理
    };

    // 关闭主机选择弹窗
    const closeHostModal = () => {
      showHostModal.value = false;
    };

    // 从弹窗中选择主机
    const selectHostFromModal = (host) => {
      handleHostSelect(host);
      closeHostModal();
    };

    // 命令表格列定义
    const commandColumns = computed(() => [
      {
        title: t.value('commandName'),
        dataIndex: 'name',
        width: 100,
        align: 'left' // 命令名称列靠左对齐
      },
      {
        title: t.value('actions'),
        slotName: 'actions',
        width: 100,
        align: 'right' // 操作列靠右对齐
      }
    ]);
    
    const commandData = ref([]);
    const commandLoading = ref(false);
    
    // 添加命令弹窗相关状态
    const addCommandModalVisible = ref(false);
    const addCommandForm = ref({
      name: '',
      command: ''
    });
    const addCommandLoading = ref(false);
    
    // 编辑命令弹窗相关状态
    const editCommandModalVisible = ref(false);
    const editCommandForm = ref({
      id: null,
      name: '',
      command: ''
    });
    const editCommandLoading = ref(false);
    
    // 获取命令列表
    const fetchCommands = async () => {
      try {
        commandLoading.value = true;
        const response = await getHostCommands();
        console.log('命令API响应数据:', response);
        
        // 根据实际API响应结构调整
        let commands = [];
        
        if (response && Array.isArray(response)) {
          // 如果响应直接是数组
          commands = response;
        } else if (response && response.data && Array.isArray(response.data)) {
          // 如果响应包含data字段且为数组
          commands = response.data;
        } else {
          // 如果以上都不匹配，使用空数组
          commands = [];
        }
        
        commandData.value = commands;
        console.log('处理后的命令数据:', commandData.value);
      } catch (error) {
        console.error('获取命令列表失败:', error);
        Message.error(t.value('fetchCommandsFailed'));
      } finally {
        commandLoading.value = false;
      }
    };
    
    // 执行命令
    const executeCommand = (record) => {
      console.log('执行命令:', record);
      
      // 获取当前激活的终端标签页
      const currentTab = data.value.find(item => item.key === activeKey.value);
      if (!currentTab) {
        Message.warning(t.value('noActiveTerminal'));
        return;
      }
      
      // 检查终端连接状态
      if (currentTab.connectionStatus !== 'connected') {
        Message.warning(t.value('terminalNotConnected'));
        return;
      }
      
      // 发送命令到终端
      if (currentTab.websocket && currentTab.websocket.readyState === WebSocket.OPEN) {
        const command = record.command || record.name;
        const message = JSON.stringify({ type: 'input', data: command + '\n' });
        currentTab.websocket.send(message);
        Message.success(t.value('commandExecuted'));
      } else {
        Message.error(t.value('terminalConnectionError'));
      }
    };
    
    // 显示添加命令弹窗
    const showAddCommandModal = () => {
      addCommandModalVisible.value = true;
      // 重置表单
      addCommandForm.value = {
        name: '',
        command: ''
      };
    };
    
    // 关闭添加命令弹窗
    const closeAddCommandModal = () => {
      addCommandModalVisible.value = false;
      addCommandForm.value = {
        name: '',
        command: ''
      };
    };
    
    // 提交添加命令
    const submitAddCommand = async () => {
      // 验证表单
      if (!addCommandForm.value.name.trim()) {
        Message.error(t.value('commandNameRequired'));
        return;
      }
      
      if (!addCommandForm.value.command.trim()) {
        Message.error(t.value('commandContentRequired'));
        return;
      }
      
      try {
        addCommandLoading.value = true;
        
        const response = await createHostCommand({
          name: addCommandForm.value.name.trim(),
          command: addCommandForm.value.command.trim()
        });
        
        if (response) {
          Message.success(t.value('commandAddedSuccessfully'));
          closeAddCommandModal();
          // 重新获取命令列表
          await fetchCommands();
        }
      } catch (error) {
        console.error('添加命令失败:', error);
        Message.error(t.value('addCommandFailed'));
      } finally {
        addCommandLoading.value = false;
      }
    };
    
    // 编辑命令
    const editCommand = (record) => {
      console.log('编辑命令:', record);
      editCommandModalVisible.value = true;
      // 填充表单数据
      editCommandForm.value = {
        id: record.id,
        name: record.name,
        command: record.command
      };
    };
    
    // 关闭编辑命令弹窗
    const closeEditCommandModal = () => {
      editCommandModalVisible.value = false;
      editCommandForm.value = {
        id: null,
        name: '',
        command: ''
      };
    };
    
    // 提交编辑命令
    const submitEditCommand = async () => {
      // 验证表单
      if (!editCommandForm.value.name.trim()) {
        Message.error(t.value('commandNameRequired'));
        return;
      }
      
      if (!editCommandForm.value.command.trim()) {
        Message.error(t.value('commandContentRequired'));
        return;
      }
      
      try {
        editCommandLoading.value = true;
        
        const response = await updateHostCommand(editCommandForm.value.id, {
          name: editCommandForm.value.name.trim(),
          command: editCommandForm.value.command.trim()
        });
        
        if (response) {
          Message.success(t.value('commandUpdatedSuccessfully'));
          closeEditCommandModal();
          // 重新获取命令列表
          await fetchCommands();
        }
      } catch (error) {
        console.error('更新命令失败:', error);
        Message.error(t.value('updateCommandFailed'));
      } finally {
        editCommandLoading.value = false;
      }
    };
    
    // 删除命令
    const deleteCommand = (record) => {
      console.log('删除命令:', record);
      
      // 显示确认对话框
      Modal.confirm({
        title: t.value('confirmDelete'),
        content: t.value('confirmDeleteCommand', { name: record.name }),
        okText: t.value('delete'),
        cancelText: t.value('cancel'),
        okButtonProps: { status: 'danger' },
        onOk: async () => {
          try {
            const response = await deleteHostCommand(record.id);
            if (response) {
              Message.success(t.value('commandDeletedSuccessfully'));
              // 重新获取命令列表
              await fetchCommands();
            }
          } catch (error) {
            console.error('删除命令失败:', error);
            Message.error(t.value('deleteCommandFailed'));
          }
        }
      });
    };
    
    // 根据窗口宽度自动调整侧边栏状态
    const autoAdjustSidebar = () => {
      // 定义阈值，当窗口宽度小于1200px时自动收起侧边栏
      const threshold = 1200;
      if (window.innerWidth < threshold) {
        sidebarCollapsed.value = true;
      } else {
        sidebarCollapsed.value = false;
      }
    };

    // 组件挂载时获取主机列表
    onMounted(() => {
      fetchHosts();
      fetchCommands(); // 获取命令列表
      
      // 初始调用一次，根据当前窗口大小调整侧边栏状态
      autoAdjustSidebar();
      
      // 添加窗口大小监听事件
      window.addEventListener('resize', autoAdjustSidebar);
    });

    // 组件卸载时移除窗口大小监听事件
    onUnmounted(() => {
      window.removeEventListener('resize', autoAdjustSidebar);
    });

    return {
      columns,
      hostData,
      loading,
      data,
      activeKey,
      sidebarCollapsed,
      isFullscreen,
      showHostModal,
      toggleSidebar,
      toggleFullscreen,
      handleAddClick,
      closeHostModal,
      selectHostFromModal,
      handleHostSelect,
      handleDelete,
      connectToHost,
      initConnection,
      handleReconnect,
      handleDisconnect,
      clearTerminal,
      setTerminalRef,
      t,
      commandColumns,
      commandData,
      commandLoading,
      executeCommand,
      addCommandModalVisible,
      addCommandForm,
      addCommandLoading,
      showAddCommandModal,
      closeAddCommandModal,
      submitAddCommand,
      editCommandModalVisible,
      editCommandForm,
      editCommandLoading,
      editCommand,
      closeEditCommandModal,
      submitEditCommand,
      deleteCommand,
    }
  },
}
</script>


<style scoped>
.terminal-container {
  border: 1px solid var(--color-border-2, #e5e5e5);
  border-radius: 4px;
  padding: 20px;
  height: calc(100vh - 120px); /* 减去导航栏等其他元素的高度 */
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

.terminal-layout {
  display: flex;
  height: 100%;
  width: 100%;
}

.tabs-container {
  flex: 8; /* 占据7份宽度 */
  padding-right: 10px;
  box-sizing: border-box;
  min-height: 400px; /* 设置最小高度 */
  min-width: 0; /* 允许flex项目收缩到内容宽度以下 */
  overflow: hidden; /* 防止内容溢出 */
}

.sidebar {
  flex: 2; /* 占据3份宽度 */
  border-left: 1px solid var(--color-border-2, #e5e5e5);
  padding-left: 10px;
  box-sizing: border-box;
  transition: all 0.3s ease;
  min-width: 300px; /* 设置最小宽度确保内容可读 */
}

.sidebar-toggle {
  position: relative;
  width: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background-color: var(--color-bg-2, #ffffff);
  border: 1px solid var(--color-border-2, #e5e5e5);
  border-radius: 10px;
  height: 40px;
  margin: auto 0;
  transition: all 0.2s ease;
  z-index: 10;
}

.sidebar-toggle:hover {
  background-color: var(--color-bg-3, #f7f8fa);
  border-color: var(--color-border-3, #d4d6d9);
}

.toggle-icon {
  font-size: 16px;
  color: var(--color-text-2, #4e5969);
  transition: color 0.2s ease;
}

.sidebar-toggle:hover .toggle-icon {
  color: var(--color-primary-6, #165dff);
}

.placeholder-content {
  padding: 20px;
  text-align: center;
  color: #999;
}

.terminal-content {
  height: calc(100vh - 200px); /* 根据视口高度计算终端内容高度 */
  width: 100%;
  box-sizing: border-box;
}

.terminal-wrapper {
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
  width: 100%;
  box-sizing: border-box;
}

.terminal-element {
  flex: 1;
  background-color: #000000;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px; /* 减少底部边距 */
  padding: 8px;
  width: 100%;
  box-sizing: border-box;
  min-height: 300px; /* 设置最小高度 */
}

.terminal-overlay {
  position: absolute;
  top: 8px;
  left: 8px;
  right: 8px;
  bottom: 60px; /* 调整底部距离，为工具栏留出空间 */
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(0, 0, 0, 0.7);
  border-radius: 4px;
  z-index: 10;
  box-sizing: border-box;
}

.status-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 20px;
  max-width: 80%;
}

.status-info .arco-spin {
  margin-bottom: 16px;
}

.status-info span {
  font-size: 14px;
  color: #fff;
}

.action-buttons {
  margin-top: 20px;
}

.terminal-toolbar {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  background-color: var(--color-bg-2, #ffffff);
  padding: 12px;
  border-radius: 4px;
  border: 1px solid var(--color-border-2, #e5e5e5);
  position: relative;
  z-index: 20; /* 确保工具栏在覆盖层之上 */
  margin-top: auto; /* 确保工具栏在底部 */
  transition: background-color 0.2s ease, border-color 0.2s ease;
}

:deep(.arco-alert) {
  margin-bottom: 20px;
  color: #fff;
}

:deep(.arco-alert-warning) {
  background-color: rgba(255, 127, 0, 0.2);
  border-color: #faad14;
}

:deep(.arco-alert-error) {
  background-color: rgba(255, 0, 0, 0.2);
  border-color: #f53f3f;
}

/* 标签页溢出处理 */
:deep(.arco-tabs-nav) {
  overflow: hidden;
}

:deep(.arco-tabs-nav-tab-list) {
  overflow-x: auto;
  overflow-y: hidden;
  white-space: nowrap;
  scrollbar-width: thin;
  scrollbar-color: #ccc transparent;
}

:deep(.arco-tabs-nav-tab-list)::-webkit-scrollbar {
  height: 4px;
}

:deep(.arco-tabs-nav-tab-list)::-webkit-scrollbar-track {
  background: transparent;
}

:deep(.arco-tabs-nav-tab-list)::-webkit-scrollbar-thumb {
  background-color: #ccc;
  border-radius: 2px;
}

:deep(.arco-tabs-nav-tab-list)::-webkit-scrollbar-thumb:hover {
  background-color: #999;
}

/* 标签页标题最大宽度限制 */
:deep(.arco-tabs-tab) {
  max-width: 150px;
  flex-shrink: 0;
}

:deep(.arco-tabs-tab .arco-tabs-tab-title) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 下拉菜单样式 */
:deep(.arco-dropdown-option) {
  padding: 8px 12px;
  cursor: pointer;
}

:deep(.arco-dropdown-option:hover) {
  background-color: #f5f5f5;
}

:deep(.arco-dropdown-option[disabled]) {
  color: #ccc;
  cursor: not-allowed;
}

/* 确保下拉菜单在全屏时也能正常显示 */
:deep(.arco-dropdown) {
  z-index: 10000;
}

:deep(.arco-dropdown-list) {
  z-index: 10001;
}

/* 全屏状态下强制提升下拉菜单层级 */
.fullscreen :deep(.arco-dropdown) {
  z-index: 99999;
}

.fullscreen :deep(.arco-dropdown-list) {
  z-index: 100000;
  position: fixed !important;
}

/* 全屏状态下的下拉菜单样式调整 */
.fullscreen :deep(.arco-dropdown-list) {
  background-color: var(--color-bg-2, #ffffff);
  border: 1px solid var(--color-border-2, #e5e5e5);
  border-radius: 6px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  min-width: 200px;
  max-height: 300px;
  overflow-y: auto;
}

.fullscreen :deep(.arco-dropdown-option) {
  padding: 10px 16px;
  font-size: 14px;
  transition: background-color 0.2s ease;
}

.fullscreen :deep(.arco-dropdown-option:hover) {
  background-color: var(--color-primary-light-1, #e8f4ff);
  color: var(--color-primary-6, #165dff);
}

.fullscreen :deep(.arco-dropdown-option[disabled]) {
  color: var(--color-text-4, #c9cdd4);
  background-color: transparent;
  cursor: not-allowed;
}

/* 暗色主题下全屏状态的下拉菜单 */
[data-theme='dark'] .fullscreen :deep(.arco-dropdown-list) {
  background-color: var(--color-bg-3, #2a2a2b);
  border-color: var(--color-border-3, #3a3a3b);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

[data-theme='dark'] .fullscreen :deep(.arco-dropdown-option:hover) {
  background-color: var(--color-primary-light-2, rgba(22, 93, 255, 0.15));
  color: var(--color-primary-5, #4080ff);
}

[data-theme='dark'] .fullscreen :deep(.arco-dropdown-option[disabled]) {
  color: var(--color-text-4, #6b7785);
}

/* 调试：确保全屏状态下下拉菜单可见 */
.fullscreen :deep(.arco-dropdown-list) {
  visibility: visible !important;
  opacity: 1 !important;
  pointer-events: auto !important;
}

/* 全屏状态下的下拉菜单容器 */
body > .arco-dropdown {
  z-index: 100001 !important;
}

/* 标签页额外内容区域样式 */
:deep(.arco-tabs-nav-extra) {
  margin-left: 8px;
}

/* 全屏时确保标签页导航区域在最上层 */
.fullscreen :deep(.arco-tabs-nav) {
  position: relative;
  z-index: 10000;
  background-color: var(--color-bg-1, #ffffff);
  border-bottom: 1px solid var(--color-border-2, #e5e5e5);
  padding: 8px 16px;
}

/* 暗色主题下全屏状态的标签页导航 */
[data-theme='dark'] .fullscreen :deep(.arco-tabs-nav) {
  background-color: var(--color-bg-2, #1d1d20);
  border-bottom-color: var(--color-border-3, #3a3a3b);
}

.fullscreen :deep(.arco-tabs-nav-extra) {
  z-index: 10001;
}

/* 全屏状态下的添加按钮样式 */
.fullscreen :deep(.arco-tabs-nav-extra .arco-btn) {
  background-color: var(--color-bg-2, #ffffff);
  border: 1px solid var(--color-border-2, #e5e5e5);
  border-radius: 4px;
  padding: 6px 8px;
  transition: all 0.2s ease;
}

.fullscreen :deep(.arco-tabs-nav-extra .arco-btn:hover) {
  background-color: var(--color-primary-light-1, #e8f4ff);
  border-color: var(--color-primary-6, #165dff);
  color: var(--color-primary-6, #165dff);
}

/* 暗色主题下全屏状态的添加按钮 */
[data-theme='dark'] .fullscreen :deep(.arco-tabs-nav-extra .arco-btn) {
  background-color: var(--color-bg-3, #2a2a2b);
  border-color: var(--color-border-3, #3a3a3b);
  color: var(--color-text-1, #ffffff);
}

[data-theme='dark'] .fullscreen :deep(.arco-tabs-nav-extra .arco-btn:hover) {
  background-color: var(--color-primary-light-2, rgba(22, 93, 255, 0.15));
  border-color: var(--color-primary-5, #4080ff);
  color: var(--color-primary-5, #4080ff);
}

/* 暗色主题支持 */
[data-theme='dark'] .terminal-toolbar {
  background-color: var(--color-bg-3, #2a2a2b);
  border-color: var(--color-border-3, #3a3a3b);
}

/* 工具栏按钮在暗色主题下的样式调整 */
[data-theme='dark'] .terminal-toolbar :deep(.arco-btn-outline) {
  border-color: var(--color-border-2, #4a4a4b);
  color: var(--color-text-1, #ffffff);
}

[data-theme='dark'] .terminal-toolbar :deep(.arco-btn-outline:hover) {
  border-color: var(--color-primary-6, #165dff);
  background-color: var(--color-primary-light-1, rgba(22, 93, 255, 0.1));
}

/* 暗色主题下的侧边栏切换按钮 */
[data-theme='dark'] .sidebar-toggle {
  background-color: var(--color-bg-3, #2a2a2b);
  border-color: var(--color-border-3, #3a3a3b);
}

[data-theme='dark'] .sidebar-toggle:hover {
  background-color: var(--color-bg-4, #3a3a3b);
  border-color: var(--color-border-4, #4a4a4b);
}

[data-theme='dark'] .toggle-icon {
  color: var(--color-text-2, #c9cdd4);
}

[data-theme='dark'] .sidebar-toggle:hover .toggle-icon {
  color: var(--color-primary-6, #165dff);
}

/* 全屏样式 */
.terminal-container.fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100vw;
  height: 100vh;
  z-index: 9999;
  border: none;
  border-radius: 0;
  padding: 0;
  background-color: var(--color-bg-1, #ffffff);
  overflow: visible; /* 确保下拉菜单可以显示 */
}

/* 全屏时标签页容器的样式调整 */
.fullscreen .tabs-container {
  position: relative;
  z-index: 10000;
  overflow: visible; /* 允许下拉菜单显示 */
}

.terminal-layout.fullscreen-layout {
  height: 100vh;
}

.fullscreen .tabs-container {
  padding-right: 0;
}

.fullscreen .sidebar-toggle,
.fullscreen .sidebar {
  display: none;
}

.fullscreen .terminal-content {
  height: calc(100vh - 80px);
}

.fullscreen .terminal-element {
  margin-bottom: 8px;
}

/* 全屏时的工具栏样式 */
.fullscreen .terminal-toolbar {
  position: relative;
  background-color: var(--color-bg-2, #ffffff);
  border-top: 1px solid var(--color-border-2, #e5e5e5);
  border-radius: 0;
  margin: 0;
}

/* 暗色主题下的全屏样式 */
[data-theme='dark'] .terminal-container.fullscreen {
  background-color: var(--color-bg-1, #17171a);
}

[data-theme='dark'] .fullscreen .terminal-toolbar {
  background-color: var(--color-bg-3, #2a2a2b);
  border-top-color: var(--color-border-3, #3a3a3b);
}

/* 主机选择弹窗样式 */
.host-modal-content {
  max-height: 400px;
  overflow-y: auto;
}

.no-hosts {
  text-align: center;
  padding: 40px 20px;
  color: var(--color-text-3, #86909c);
}

.no-hosts-icon {
  margin-bottom: 16px;
}

.host-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.host-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border: 1px solid var(--color-border-2, #e5e5e5);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.host-item:hover {
  background-color: var(--color-primary-light-1, #e8f4ff);
  border-color: var(--color-primary-6, #165dff);
}

.host-address {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-1, #1d2129);
}

.host-connect-btn {
  opacity: 0;
  transition: opacity 0.2s ease;
}

.host-item:hover .host-connect-btn {
  opacity: 1;
}

/* 暗色主题下的弹窗样式 */
[data-theme='dark'] .no-hosts {
  color: var(--color-text-3, #6b7785);
}

[data-theme='dark'] .host-item {
  border-color: var(--color-border-3, #3a3a3b);
}

[data-theme='dark'] .host-item:hover {
  background-color: var(--color-primary-light-2, rgba(22, 93, 255, 0.15));
  border-color: var(--color-primary-5, #4080ff);
}

[data-theme='dark'] .host-address {
  color: var(--color-text-1, #ffffff);
}

/* 确保弹窗在全屏状态下正确显示 */
:deep(.arco-modal-wrapper) {
  z-index: 100000 !important;
}

:deep(.arco-modal-mask) {
  z-index: 99999 !important;
}

:deep(.arco-modal) {
  z-index: 100001 !important;
}

/* 全屏状态下的弹窗特殊处理 */
.fullscreen ~ :deep(.arco-modal-wrapper),
.fullscreen ~ :deep(.arco-modal-mask) {
  z-index: 100000 !important;
}

/* 强制弹窗显示在最上层 */
body > .arco-modal-wrapper {
  z-index: 100000 !important;
}

body > .arco-modal-mask {
  z-index: 99999 !important;
}

/* 全屏状态下强制弹窗可见 */
.arco-modal-wrapper[style*="z-index"] {
  z-index: 100000 !important;
}

.arco-modal-mask[style*="z-index"] {
  z-index: 99999 !important;
}

/* 确保弹窗内容可见 */
.arco-modal {
  z-index: 100001 !important;
}

/* 调试用：强制所有弹窗相关元素可见 */
.arco-modal-wrapper,
.arco-modal-mask,
.arco-modal {
  visibility: visible !important;
  opacity: 1 !important;
  display: block !important;
}

/* 命令内容文本域样式 */
.command-textarea {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}

.command-textarea :deep(.arco-textarea) {
  background-color: #000000 !important; /* 黑色背景 */
  color: #ffffff !important; /* 白色字体 */
  border: 1px solid #333333;
  font-size: 14px;
  line-height: 1.4;
  resize: vertical !important; /* 允许垂直调整大小 */
  min-height: 120px;
}

.command-textarea :deep(.arco-textarea:focus) {
  border-color: var(--color-primary-6, #165dff);
  box-shadow: 0 0 0 2px rgba(22, 93, 255, 0.3);
  background-color: #000000 !important;
  color: #ffffff !important;
}

.command-textarea :deep(.arco-textarea::placeholder) {
  color: #888888 !important;
  font-style: italic;
}

/* 暗色主题下保持一致 */
[data-theme='dark'] .command-textarea :deep(.arco-textarea) {
  background-color: #000000 !important;
  color: #ffffff !important;
  border-color: #333333;
}

[data-theme='dark'] .command-textarea :deep(.arco-textarea:focus) {
  border-color: var(--color-primary-5, #4080ff);
  box-shadow: 0 0 0 2px rgba(64, 128, 255, 0.3);
  background-color: #000000 !important;
  color: #ffffff !important;
}

/* 文本域包装器样式 */
.textarea-wrapper {
  position: relative;
}

.resize-hint {
  position: absolute;
  bottom: 4px;
  right: 24px;
  font-size: 11px;
  color: #cccccc !important;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.3s ease;
  background-color: rgba(0, 0, 0, 0.9);
  padding: 3px 6px;
  border-radius: 3px;
  z-index: 10;
  font-weight: 500;
  white-space: nowrap;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.textarea-wrapper:hover .resize-hint {
  opacity: 1;
}


</style>
