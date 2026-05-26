<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    :viewBox="'0 0 1024 1024'"
    :style="iconStyle"
    version="1.1"
    p-id="24418"
    xmlns:xlink="http://www.w3.org/1999/xlink"
  >
    <path
      d="M615.6 123.6h165.5L512 589.7 242.9 123.6H63.5L512 900.4l448.5-776.9z"
      p-id="24419"
      :fill="greenColor"
    ></path>
    <path
      d="M781.1 123.6H615.6L512 303 408.4 123.6H242.9L512 589.7z"
      p-id="24420"
      :fill="darkColor"
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
  greenColor: {
    type: String,
    default: '#41B883'
  },
  darkColor: {
    type: String,
    default: '#34495E'
  },
  spin: {
    type: Boolean,
    default: false
  }
})

const iconStyle = computed(() => ({
  width: typeof props.size === 'number' ? `${props.size}px` : props.size,
  height: typeof props.size === 'number' ? `${props.size}px` : props.size,
  color: props.greenColor,
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
