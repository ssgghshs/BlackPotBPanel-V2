<template>
  <a-card class="app-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('hostApp') }}</span>

      </div>
    </template>
 
  </a-card>

    
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { t } from '../../utils/locale'

import { Message } from '@arco-design/web-vue'


</script>

<style scoped>
.database-container {
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
</style>
