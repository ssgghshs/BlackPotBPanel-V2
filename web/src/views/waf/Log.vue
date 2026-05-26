<template>
  <a-card class="waf-container">
    <template #title>
      <div class="card-header">
        <span class="title">WAF{{ t('log') }}</span>
      </div>
    </template>

<!--  内容区域  -->
    <a-tabs position="left">
      <a-tab-pane key="1" :title="t('blocklog')">
        <BlockLog />
      </a-tab-pane>
      <a-tab-pane key="2" title="BOT">
        <BotLog />
      </a-tab-pane>
      <a-tab-pane key="3" :title="t('ipblacklist')">
        <IPblackLog />
      </a-tab-pane>
    </a-tabs>
    

  </a-card>
</template>

<script setup>
import { reactive } from 'vue';
import { t } from '../../utils/locale'
import BlockLog from '../../components/waf/BlockLog.vue';
import BotLog from '../../components/waf/BotLog.vue';
import IPblackLog from '../../components/waf/IPblackLog.vue';

</script>

<style scoped>
.waf-container {
  padding: 20px;
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

/* 根据需要调整其他样式 */
</style>