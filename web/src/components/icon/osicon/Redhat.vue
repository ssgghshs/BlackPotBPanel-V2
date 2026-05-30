<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    :viewBox="'0 0 1024 1024'"
    :style="iconStyle"
    version="1.1"
    p-id="5011"
    xmlns:xlink="http://www.w3.org/1999/xlink"
  >
    <path
      d="M847.104 507.136s175.872 73.216 168.192 198.4-114.176 188.16-303.872 188.16c-229.376 0-568.064-139.52-660.992-272.128-99.84-142.592 10.24-191.488 10.24-191.488s61.952-31.232 149.248-32.768c34.56-32.512 56.064-246.784 131.84-255.488 48.896-5.376 62.464 31.232 95.744 29.184 49.152-3.328 45.056-37.632 74.24-40.448 56.576-5.632 248.576 70.144 276.48 125.184 24.576 48.128 58.88 251.392 58.88 251.392z"
      fill="#EE0000"
      p-id="5012"
    ></path>
    <path
      d="M856.832 524.288c-0.768-3.84-2.048-8.704-3.328-14.08-4.096-2.048-6.656-2.816-6.656-2.816s-2.048-12.8-5.888-33.024c-1.28 31.488-19.712 96.256-146.944 96.256-167.936 0-450.816-88.576-461.568-221.184-7.424 22.528-14.848 40.192-23.04 47.872h-1.024c-7.936 24.576-9.472 54.528 8.448 86.016 10.752 18.688 132.864 197.376 466.688 191.488 39.68 0 198.144-5.632 173.312-150.528z"
      p-id="5013"
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
