<template>
  <a-card class="sec-container">
    <template #title>
      <div class="card-header">
        <div class="header-left">
          <span class="title">{{ t('firewall') }}</span>
          <a-tag>{{ firewallInfo.type }}</a-tag>
          <a-tag :color="firewallInfo.status ? 'green' : 'red'">
            {{ firewallInfo.status ? t('running') : t('stopped') }}
          </a-tag>
          <div class="fw-actions">
            <a-link type="text" size="small" :loading="actionLoading.reload" @click="handleAction('reload')">
              {{ t('reload') }}
            </a-link>
            <a-link type="text" size="small" :loading="actionLoading.stop" @click="handleAction('stop')" :disabled="!firewallInfo.status || actionLoading.stop">
              {{ t('stop') }}
            </a-link>
            <a-link type="text" size="small" :loading="actionLoading.restart" @click="handleAction('restart')" :disabled="!firewallInfo.status || actionLoading.restart">
              {{ t('restart') }}
            </a-link>
            <a-link type="text" size="small" :loading="actionLoading.start" @click="handleAction('start')" :disabled="firewallInfo.status || actionLoading.start">
              {{ t('start') }}
            </a-link>
          </div>
        </div>
        <div class="header-ping">
          <a-switch
            v-model="pingEnabled"
            @change="handlePingChange"
          />
          <span class="switch-label">{{ pingEnabled ? t('enablePing') : t('disablePing') }}</span>
        </div>
      </div>
    </template>
    <!-- 防火墙规则显示区域 -->
    <a-tabs v-if="firewallInfo.status" default-active-key="1" type="card">
      <a-tab-pane key="1" :title="`${t('portRules')} (${firewallInfo.port})`">
        <PortRulesList />
      </a-tab-pane>
      <a-tab-pane key="2" :title="`${t('ipRules')} (${firewallInfo.ip})`">
        <IpRulesList />
      </a-tab-pane>
      <a-tab-pane key="3" :title="`${t('portForwarding')} (${firewallInfo.trans})`">
        <PortForwardingList />
      </a-tab-pane>
      <a-tab-pane key="4" :title="`${t('regionalRestrictions')} (${firewallInfo.country})`">
        <RegionalRestrictions />
      </a-tab-pane>
    </a-tabs>
    <!-- 防火墙未运行时的提示信息 -->
    <div v-else class="fw-stopped-hint">
      <a-result status="warning" :title="t('startFirewallFirst')" />
    </div>
  </a-card>

  <a-modal
    v-model:visible="showActionDialog"
    :title="t('confirmAction')"
    @ok="handleConfirmAction"
    @cancel="handleCancelAction"
    :ok-loading="actionLoading[pendingAction]"
    :cancel-text="t('cancel')"
    :ok-text="t('confirm')"
  >
    <p>{{ t(getActionConfirmKey()) }}</p>
  </a-modal>

  <a-modal
    v-model:visible="showPingDialog"
    :title="t('confirmAction')"
    @ok="handleConfirmPing"
    @cancel="handleCancelPing"
    :ok-loading="pingLoading"
    :cancel-text="t('cancel')"
    :ok-text="t('confirm')"
  >
    <p>{{ t(pingEnabled ? 'confirmEnablePing' : 'confirmDisablePing') }}</p>
  </a-modal>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue';
import { t } from '../../utils/locale';
import { firewallInfoGet, firewallStatusSet, firewallSetPing, } from '../../api/security';
import { Message } from '@arco-design/web-vue';
import PortRulesList from '../../components/security/PortRulesList.vue';
import IpRulesList from '../../components/security/IpRulesList.vue';
import PortForwardingList from '../../components/security/PortForwardingList.vue';
import RegionalRestrictions from '../../components/security/RegionalRestrictions.vue';

const firewallInfo = reactive({
  port: 0,
  ip: 0,
  trans: 0,
  country: 0,
  ping: true,
  status: false,
  type: '',
});

const pingEnabled = ref(true);
const pingLoading = ref(false);
const showPingDialog = ref(false);

const actionLoading = reactive({
  start: false,
  stop: false,
  restart: false,
  reload: false,
});
const showActionDialog = ref(false);
const pendingAction = ref('');

const fetchFirewallInfo = async () => {
  try {
    const res = await firewallInfoGet();
    if (res) {
      firewallInfo.port = res.port || 0;
      firewallInfo.ip = res.ip || 0;
      firewallInfo.trans = res.trans || 0;
      firewallInfo.country = res.country || 0;
      firewallInfo.ping = res.ping !== undefined ? res.ping : true;
      firewallInfo.status = res.status || false;
      firewallInfo.type = res.type || '';
      pingEnabled.value = res.ping !== undefined ? res.ping : true;
    }
  } catch (error) {
    console.error('获取防火墙信息失败:', error);
  }
};

const handlePingChange = () => {
  showPingDialog.value = true;
};

const handleConfirmPing = async () => {
  pingLoading.value = true;
  try {
    const status = pingEnabled.value ? '0' : '1';
    const res = await firewallSetPing(status);
    if (res && res.success) {
      Message.success(t.value('operationSuccess'));
      await fetchFirewallInfo();
    } else {
      throw new Error(res?.message || t.value('operationFailed'));
    }
  } catch (error) {
    pingEnabled.value = !pingEnabled.value;
    Message.error(error.message || t.value('operationFailed'));
  } finally {
    pingLoading.value = false;
    showPingDialog.value = false;
  }
};

const handleCancelPing = () => {
  pingEnabled.value = !pingEnabled.value;
  showPingDialog.value = false;
};

const getActionConfirmKey = () => {
  const map = {
    start: 'confirmStartFirewall',
    stop: 'confirmStopFirewall',
    restart: 'confirmRestartFirewall',
    reload: 'confirmReloadFirewall',
  };
  return map[pendingAction.value] || 'confirmAction';
};

const handleAction = (action) => {
  pendingAction.value = action;
  showActionDialog.value = true;
};

const handleConfirmAction = async () => {
  const action = pendingAction.value;
  if (!action) return;

  actionLoading[action] = true;
  try {
    const res = await firewallStatusSet(action);
    if (res && res.success) {
      Message.success(t.value('operationSuccess'));
      await fetchFirewallInfo();
    } else {
      throw new Error(res?.message || t.value('operationFailed'));
    }
  } catch (error) {
    Message.error(error.message || t.value('operationFailed'));
  } finally {
    actionLoading[action] = false;
    showActionDialog.value = false;
  }
};

const handleCancelAction = () => {
  pendingAction.value = '';
  showActionDialog.value = false;
};

onMounted(() => {
  fetchFirewallInfo();
});
</script>

<style scoped>
.sec-container {
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 1.3em;
  padding: 20px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.header-ping {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.title {
  margin: 0;
  padding: 0;
}

.fw-actions {
  display: flex;
  gap: 8px;
}

.switch-label {
  font-size: 14px;
  color: #8c8c8c;
}

.fw-stopped-hint {
  padding: 60px 20px;
  text-align: center;
}
</style>
