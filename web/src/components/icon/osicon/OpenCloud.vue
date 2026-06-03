<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    :viewBox="'0 0 1024 1024'"
    :style="iconStyle"
    version="1.1"
    p-id="5103"
    xmlns:xlink="http://www.w3.org/1999/xlink"
  >
    <path d="M168.96 675.84l168.96-168.96 168.96 168.96a238.912 238.912 0 0 1-337.92 0zM506.848 337.92a238.944 238.944 0 0 1 337.92 0l-168.96 168.96-168.96-168.96z" fill="#060198" p-id="5104"></path>
    <path d="M168.96 675.84a238.944 238.944 0 0 1 0-337.92L506.88 0a238.944 238.944 0 0 1 0 337.92L168.96 675.84z" fill="#00C0FF" p-id="5105"></path>
    <path d="M675.808 844.736l-168.96 168.96a238.944 238.944 0 0 1 0-337.92l168.96-168.928 168.96-168.96a238.944 238.944 0 0 1 0 337.92l-168.96 168.96z" fill="#0368EC" p-id="5106"></path>
  </svg>
</template>

<script setup>
import { defineProps, computed } from 'vue'

const props = defineProps({
  size: {
    type: [Number, String],
    default: 16
  },
  color: {
    type: String,
    default: 'currentColor'
  },
  spin: {
    type: Boolean,
    default: false
  }
})

const iconStyle = computed(() => ({
  width: typeof props.size === 'number' ? `${props.size}px` : props.size,
  height: typeof props.size === 'number' ? `${props.size}px` : props.size,
  color: props.color,
  animation: props.spin ? 'spin 1s infinite linear' : 'none'
}))
</script>

<style scoped>
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
