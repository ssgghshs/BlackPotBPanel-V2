<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    :viewBox="'0 0 1024 1024'"
    :style="iconStyle"
    version="1.1"
    p-id="6036"
    xmlns:xlink="http://www.w3.org/1999/xlink"
  >
    <path 
      d="M233.386667 318.72a32 32 0 0 1 45.226666 0l167.68 167.637333a36.266667 36.266667 0 0 1 0 51.285334l-167.68 167.68a32 32 0 0 1-45.226666-45.269334L381.44 512 233.386667 363.946667a32 32 0 0 1 0-45.226667zM480 682.666667a32 32 0 0 1 32-32h277.333333a32 32 0 0 1 0 64H512a32 32 0 0 1-32-32z" 
      fill="currentColor"
      p-id="6037"
    />
    <path 
      d="M85.333333 245.333333C85.333333 204.117333 118.784 170.666667 160 170.666667h704c41.216 0 74.666667 33.450667 74.666667 74.666666v533.333334A74.666667 74.666667 0 0 1 864 853.333333H160A74.666667 74.666667 0 0 1 85.333333 778.666667V245.333333z m74.666667-10.666666a10.666667 10.666667 0 0 0-10.666667 10.666666v533.333334c0 5.888 4.778667 10.666667 10.666667 10.666666h704a10.666667 10.666667 0 0 0 10.666667-10.666666V245.333333a10.666667 10.666667 0 0 0-10.666667-10.666666H160z" 
      fill="currentColor"
      p-id="6038"
    />
  </svg>
</template>

<script setup>
import { defineProps, computed } from 'vue'

const props = defineProps({
  size: {
    type: [Number, String],
    default: 20
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