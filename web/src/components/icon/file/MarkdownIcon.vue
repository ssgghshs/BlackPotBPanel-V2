<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    :viewBox="'0 0 1024 1024'"
    :style="iconStyle"
    version="1.1"
    p-id="34555"
    xmlns:xlink="http://www.w3.org/1999/xlink"
  >
    <path
      d="M96 672v-341.333333h85.333333l128 128 128-128h85.333334v341.333333h-85.333334v-220.586667l-128 128-128-128v220.586667h-85.333333m597.333333-341.333333h128v170.666666h106.666667l-170.666667 192-170.666666-192h106.666666z"
      p-id="34556"
      :fill="iconColor"
    ></path>
  </svg>
</template>

<script setup>
import { defineProps, computed } from 'vue'

const props = defineProps({
  size: {
    type: [Number, String],
    default: 20
  },
  iconColor: {
    type: String,
    default: '#42A5F5'
  },
  spin: {
    type: Boolean,
    default: false
  }
})

const iconStyle = computed(() => ({
  width: typeof props.size === 'number' ? `${props.size}px` : props.size,
  height: typeof props.size === 'number' ? `${props.size}px` : props.size,
  color: props.iconColor,
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
