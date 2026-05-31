<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    :viewBox="'0 0 1024 1024'"
    :style="iconStyle"
    version="1.1"
    p-id="8690"
    xmlns:xlink="http://www.w3.org/1999/xlink"
  >
    <path
      d="M966.64064 662.1952c17.2544-49.42848 26.63936-102.55872 26.63936-157.8752C993.28 239.92832 778.94144 25.6 514.55488 25.6 250.16832 25.6 35.84 239.92832 35.84 504.32c0 130.816 52.48 249.38496 137.5232 335.7952l485.59616-485.6064 119.8848 119.89504 187.79648 187.79136z m-87.43936 152.32512l-220.24192-220.23168-344.87296 344.8832C375.0656 967.32672 442.97216 983.04 514.56 983.04c146.05824 0 276.83328-65.40288 364.6464-168.51968z"
      fill="#10B981"
      p-id="8691"
    ></path>
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
