<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    :viewBox="'0 0 1024 1024'"
    :style="iconStyle"
    version="1.1"
    p-id="53497"
    xmlns:xlink="http://www.w3.org/1999/xlink"
  >
    <path
      d="M514.093511 1.274311H11.377778v528.657067z"
      fill="#00AFFF"
      p-id="53498"
    ></path>
    <path
      d="M515.595378 501.896533h-4.460089L11.377778 1002.518756h1001.244444z"
      fill="#6875FF"
      p-id="53499"
    ></path>
    <path
      d="M1012.622222 1.274311L513.342578 499.643733l-2.207289 2.275556-499.757511 500.622222V529.908622l26.646755-28.034844 476.046223-500.622222z"
      fill="#F17C32"
      p-id="53500"
    ></path>
  </svg>
</template>

<script setup>
import { defineProps, computed } from 'vue'

const props = defineProps({
  size: {
    type: [Number, String],
    default: 15
  },
  spin: {
    type: Boolean,
    default: false
  }
})

const iconStyle = computed(() => ({
  width: typeof props.size === 'number' ? `${props.size}px` : props.size,
  height: typeof props.size === 'number' ? `${props.size}px` : props.size,
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
